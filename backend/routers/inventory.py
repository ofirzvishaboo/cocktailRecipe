import uuid
from datetime import date
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload
import traceback

from core.auth import current_active_user
from db.database import (
    get_async_session,
    Bottle as BottleModel,
    BottlePrice as BottlePriceModel,
    CocktailRecipe as CocktailRecipeModel,
    Event as EventModel,
    Order as OrderModel,
    OrderItem as OrderItemModel,
    Ingredient as IngredientModel,
    Kind as KindModel,
    RecipeIngredient as RecipeIngredientModel,
    Subcategory as SubcategoryModel,
)
from db.inventory.item import InventoryItem as InventoryItemModel
from db.inventory.stock import InventoryStock as InventoryStockModel
from db.inventory.movement import InventoryMovement as InventoryMovementModel
from db.users import User
from schemas.inventory import (
    ConsumeCocktailBatchRequest,
    ConsumeEventRequest,
    UnconsumeEventRequest,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryMovementCreate,
    InventoryTransferCreate,
)

router = APIRouter()


def _as_int(x) -> int:
    try:
        return int(x)
    except Exception:
        return 0


def _to_ml(quantity: Decimal, unit: str) -> Optional[Decimal]:
    u = (unit or "").strip().lower()
    if u == "ml":
        return quantity
    if u == "oz":
        # US fluid ounce to ml
        return (quantity * Decimal("29.5735"))
    return None


def _trunc_int(x: Decimal) -> int:
    # Truncate toward 0 (matches user's "round down" choice for fractional bottles).
    return int(x)


def _default_event_consumed_reason(ev: EventModel) -> str:
    # Include id to make the reason uniquely traceable (helps future unconsume).
    name = (getattr(ev, "name", None) or "").strip()
    if name:
        return f"Event consumed: {name} ({ev.id})"
    return f"Event consumed: {ev.id}"


def _default_event_unconsumed_reason(ev: EventModel) -> str:
    name = (getattr(ev, "name", None) or "").strip()
    if name:
        return f"Event unconsumed: {name} ({ev.id})"
    return f"Event unconsumed: {ev.id}"


def _legacy_event_reason_candidates(ev: EventModel) -> List[str]:
    """Legacy reasons from before we included event_id in the reason."""
    name = (getattr(ev, "name", None) or "").strip()
    out = [f"Event consumed: {ev.id}"]
    if name:
        out.insert(0, f"Event consumed: {name}")
    return out


async def _upsert_stock_and_add_movement(
    *,
    db: AsyncSession,
    user: User,
    location: str,
    inventory_item_id: UUID,
    delta: int,
    reason: Optional[str],
    source_type: Optional[str],
    source_id: Optional[int],
    source_event_id: Optional[UUID] = None,
    is_reversal: bool = False,
    reversal_of_id: Optional[UUID] = None,
) -> dict:
    movement_id = uuid.uuid4()
    stock_insert_id = uuid.uuid4()

    db.add(
        InventoryMovementModel(
            id=movement_id,
            location=location,
            inventory_item_id=inventory_item_id,
            change=delta,
            reason=reason,
            source_type=source_type,
            source_id=source_id,
            source_event_id=source_event_id,
            is_reversal=is_reversal,
            reversal_of_id=reversal_of_id,
            created_by_user_id=user.id,
        )
    )

    stock_tbl = InventoryStockModel.__table__
    upsert = (
        insert(stock_tbl)
        .values(
            id=stock_insert_id,
            location=location,
            inventory_item_id=inventory_item_id,
            quantity=delta,
            reserved_quantity=0,
        )
        .on_conflict_do_update(
            constraint="ux_inventory_stock_location_item",
            set_={"quantity": stock_tbl.c.quantity + delta},
        )
        .returning(
            stock_tbl.c.id,
            stock_tbl.c.location,
            stock_tbl.c.inventory_item_id,
            stock_tbl.c.quantity,
            stock_tbl.c.reserved_quantity,
        )
    )
    upserted = (await db.execute(upsert)).first()
    return {
        "movement": {
            "id": movement_id,
            "location": location,
            "inventory_item_id": inventory_item_id,
            "change": int(delta),
            "reason": reason,
            "source_type": source_type,
            "source_id": source_id,
            "source_event_id": source_event_id,
            "is_reversal": bool(is_reversal),
            "reversal_of_id": reversal_of_id,
            "created_by_user_id": user.id,
        },
        "stock": {
            "location": location,
            "inventory_item_id": inventory_item_id,
            "quantity": int(upserted.quantity) if upserted else 0,
            "reserved_quantity": int(upserted.reserved_quantity) if upserted else 0,
        },
    }

def _minor_from_price(price: Optional[float]) -> Optional[int]:
    if price is None:
        return None
    try:
        return int(round(float(price) * 100))
    except Exception:
        return None

async def _load_current_bottle_prices(
    db: AsyncSession, bottle_ids: List[UUID]
) -> dict[UUID, dict]:
    if not bottle_ids:
        return {}
    today = date.today()
    q = (
        select(BottlePriceModel)
        .where(BottlePriceModel.bottle_id.in_(bottle_ids))
        .where(BottlePriceModel.start_date <= today)
        .where((BottlePriceModel.end_date == None) | (BottlePriceModel.end_date >= today))  # noqa: E711
        # Postgres DISTINCT ON: pick the most recent row per bottle_id.
        .distinct(BottlePriceModel.bottle_id)
        .order_by(
            BottlePriceModel.bottle_id,
            BottlePriceModel.start_date.desc(),
            BottlePriceModel.id.desc(),
        )
    )
    res = await db.execute(q)
    out: dict[UUID, dict] = {}
    for p in res.scalars().all():
        out[p.bottle_id] = {
            "price_minor": int(p.price_minor),
            "currency": p.currency,
            "price": float(p.price_minor) / 100.0,
        }
    return out


@router.get("/items", response_model=List[Dict])
async def list_inventory_items(
    item_type: Optional[str] = None,
    kind_id: Optional[UUID] = None,
    brand_id: Optional[UUID] = None,
    location: Optional[str] = None,
    q: Optional[str] = None,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    List inventory items with optional filters.

    - kind_id/brand_id apply to bottle-backed items via bottle -> ingredient.
    - location optionally attaches stock quantities for that location.
    """
    stmt = select(InventoryItemModel)

    BottleIngredient = aliased(IngredientModel)
    GarnishIngredient = aliased(IngredientModel)
    BottleKind = aliased(KindModel)
    GarnishKind = aliased(KindModel)
    BottleSubcategory = aliased(SubcategoryModel)
    GarnishSubcategory = aliased(SubcategoryModel)

    # bottle-backed chain: inventory_items -> bottle -> ingredient
    stmt = stmt.outerjoin(BottleModel, InventoryItemModel.bottle_id == BottleModel.id)
    stmt = stmt.outerjoin(BottleIngredient, BottleModel.ingredient_id == BottleIngredient.id)
    stmt = stmt.outerjoin(BottleKind, BottleIngredient.kind_id == BottleKind.id)
    stmt = stmt.outerjoin(BottleSubcategory, BottleIngredient.subcategory_id == BottleSubcategory.id)

    # garnish-backed chain: inventory_items -> ingredient
    stmt = stmt.outerjoin(GarnishIngredient, InventoryItemModel.ingredient_id == GarnishIngredient.id)
    stmt = stmt.outerjoin(GarnishKind, GarnishIngredient.kind_id == GarnishKind.id)
    stmt = stmt.outerjoin(GarnishSubcategory, GarnishIngredient.subcategory_id == GarnishSubcategory.id)

    # Select kind fields for convenience in the response
    stmt = stmt.add_columns(
        BottleIngredient.kind_id.label("bottle_kind_id"),
        BottleKind.name.label("bottle_kind_name"),
        BottleIngredient.subcategory_id.label("bottle_subcategory_id"),
        BottleSubcategory.name.label("bottle_subcategory_name"),
        GarnishIngredient.kind_id.label("garnish_kind_id"),
        GarnishKind.name.label("garnish_kind_name"),
        GarnishIngredient.subcategory_id.label("garnish_subcategory_id"),
        GarnishSubcategory.name.label("garnish_subcategory_name"),
    )

    if item_type:
        stmt = stmt.where(InventoryItemModel.item_type == item_type)
    if q:
        qq = f"%{q.strip().lower()}%"
        stmt = stmt.where(func.lower(InventoryItemModel.name).like(qq))
    if kind_id:
        stmt = stmt.where(
            ((InventoryItemModel.item_type == "BOTTLE") & (BottleIngredient.kind_id == kind_id))
            | ((InventoryItemModel.item_type == "GARNISH") & (GarnishIngredient.kind_id == kind_id))
        )
    if brand_id:
        stmt = stmt.where(
            ((InventoryItemModel.item_type == "BOTTLE") & (BottleIngredient.brand_id == brand_id))
            | ((InventoryItemModel.item_type == "GARNISH") & (GarnishIngredient.brand_id == brand_id))
        )

    # Attach stock for location if requested
    stock_by_item: dict[UUID, dict] = {}
    if location:
        sres = await db.execute(
            select(InventoryStockModel)
            .where(InventoryStockModel.location == location)
        )
        for s in sres.scalars().all():
            stock_by_item[s.inventory_item_id] = {
                "location": s.location,
                "quantity": float(s.quantity or 0),
                "reserved_quantity": float(s.reserved_quantity or 0),
            }

    res = await db.execute(stmt.order_by(func.lower(InventoryItemModel.name).asc()))
    rows = res.all()
    bottle_ids = [
        it.bottle_id
        for (
            it,
            _bottle_kind_id,
            _bottle_kind_name,
            _bottle_subcategory_id,
            _bottle_subcategory_name,
            _garnish_kind_id,
            _garnish_kind_name,
            _garnish_subcategory_id,
            _garnish_subcategory_name,
        ) in rows
        if it.item_type == "BOTTLE" and it.bottle_id is not None
    ]
    bottle_prices = await _load_current_bottle_prices(db, bottle_ids)

    out = []
    for (
        it,
        bottle_kind_id,
        bottle_kind_name,
        bottle_subcategory_id,
        bottle_subcategory_name,
        garnish_kind_id,
        garnish_kind_name,
        garnish_subcategory_id,
        garnish_subcategory_name,
    ) in rows:
        kind_id_out = None
        kind_name_out = None
        subcategory_id_out = None
        subcategory_name_out = None
        if it.item_type == "BOTTLE":
            kind_id_out = bottle_kind_id
            kind_name_out = bottle_kind_name
            subcategory_id_out = bottle_subcategory_id
            subcategory_name_out = bottle_subcategory_name
        elif it.item_type == "GARNISH":
            kind_id_out = garnish_kind_id
            kind_name_out = garnish_kind_name
            subcategory_id_out = garnish_subcategory_id
            subcategory_name_out = garnish_subcategory_name
        elif it.item_type == "GLASS":
            kind_name_out = "Glass"

        row_out = {
                "id": it.id,
                "item_type": it.item_type,
                "bottle_id": it.bottle_id,
                "ingredient_id": it.ingredient_id,
                "glass_type_id": it.glass_type_id,
                "name": it.name,
                "unit": it.unit,
                "kind_id": kind_id_out,
                "kind_name": kind_name_out,
                "subcategory_id": subcategory_id_out,
                "subcategory_name": subcategory_name_out,
                # Price source priority:
                # 1) manual price on inventory_items (supports GLASS/GARNISH and optional override)
                # 2) bottle_prices (for bottle-backed items)
                "price_minor": (
                    int(it.price_minor)
                    if it.price_minor is not None
                    else (bottle_prices.get(it.bottle_id, {}).get("price_minor") if it.item_type == "BOTTLE" else None)
                ),
                "currency": (
                    it.currency
                    if it.currency
                    else (bottle_prices.get(it.bottle_id, {}).get("currency") if it.item_type == "BOTTLE" else None)
                ),
                "price": (
                    (float(it.price_minor) / 100.0)
                    if it.price_minor is not None
                    else (bottle_prices.get(it.bottle_id, {}).get("price") if it.item_type == "BOTTLE" else None)
                ),
                "is_active": bool(it.is_active),
                "min_level": float(it.min_level) if it.min_level is not None else None,
                "reorder_level": float(it.reorder_level) if it.reorder_level is not None else None,
                "stock": stock_by_item.get(it.id) if location else None,
            }

        if not user.is_superuser:
            row_out["price_minor"] = None
            row_out["currency"] = None
            row_out["price"] = None

        out.append(row_out)
    return out


@router.post("/items", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    payload: InventoryItemCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    model = InventoryItemModel(
        item_type=payload.item_type,
        bottle_id=payload.bottle_id,
        ingredient_id=payload.ingredient_id,
        glass_type_id=payload.glass_type_id,
        name=payload.name,
        unit=payload.unit,
        is_active=True,
        min_level=payload.min_level,
        reorder_level=payload.reorder_level,
        price_minor=_minor_from_price(payload.price),
        currency=payload.currency,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return {
        "id": model.id,
        "item_type": model.item_type,
        "bottle_id": model.bottle_id,
        "ingredient_id": model.ingredient_id,
        "glass_type_id": model.glass_type_id,
        "name": model.name,
        "unit": model.unit,
        "price_minor": model.price_minor,
        "currency": model.currency,
        "price": float(model.price_minor) / 100.0 if model.price_minor is not None else None,
        "is_active": bool(model.is_active),
        "min_level": float(model.min_level) if model.min_level is not None else None,
        "reorder_level": float(model.reorder_level) if model.reorder_level is not None else None,
    }


@router.patch("/items/{item_id}", response_model=Dict)
async def update_inventory_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    res = await db.execute(select(InventoryItemModel).where(InventoryItemModel.id == item_id))
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if payload.name is not None:
        model.name = payload.name
    if payload.unit is not None:
        model.unit = payload.unit
    if payload.is_active is not None:
        model.is_active = bool(payload.is_active)
    if payload.min_level is not None:
        model.min_level = payload.min_level
    if payload.reorder_level is not None:
        model.reorder_level = payload.reorder_level
    if payload.price is not None:
        model.price_minor = _minor_from_price(payload.price)
    if payload.currency is not None:
        model.currency = payload.currency

    await db.commit()
    await db.refresh(model)
    return {
        "id": model.id,
        "item_type": model.item_type,
        "bottle_id": model.bottle_id,
        "ingredient_id": model.ingredient_id,
        "glass_type_id": model.glass_type_id,
        "name": model.name,
        "unit": model.unit,
        "price_minor": model.price_minor,
        "currency": model.currency,
        "price": float(model.price_minor) / 100.0 if model.price_minor is not None else None,
        "is_active": bool(model.is_active),
        "min_level": float(model.min_level) if model.min_level is not None else None,
        "reorder_level": float(model.reorder_level) if model.reorder_level is not None else None,
    }


@router.delete("/items/{item_id}", response_model=Dict)
async def soft_delete_inventory_item(
    item_id: UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    res = await db.execute(select(InventoryItemModel).where(InventoryItemModel.id == item_id))
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    model.is_active = False
    await db.commit()
    return {"ok": True}


@router.get("/stock", response_model=List[Dict])
async def get_stock(
    location: str = Query(..., pattern="^(BAR|WAREHOUSE)$"),
    item_type: Optional[str] = None,
    include_inactive: bool = False,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    BottleIngredient = aliased(IngredientModel)
    GarnishIngredient = aliased(IngredientModel)
    BottleSubcategory = aliased(SubcategoryModel)
    GarnishSubcategory = aliased(SubcategoryModel)

    stmt = select(InventoryItemModel, InventoryStockModel)

    stmt = stmt.outerjoin(
        InventoryStockModel,
        and_(
            InventoryStockModel.inventory_item_id == InventoryItemModel.id,
            InventoryStockModel.location == location,
        ),
    )

    # bottle-backed chain -> ingredient -> subcategory
    stmt = stmt.outerjoin(BottleModel, InventoryItemModel.bottle_id == BottleModel.id)
    stmt = stmt.outerjoin(BottleIngredient, BottleModel.ingredient_id == BottleIngredient.id)
    stmt = stmt.outerjoin(BottleSubcategory, BottleIngredient.subcategory_id == BottleSubcategory.id)

    # garnish-backed chain -> ingredient -> subcategory
    stmt = stmt.outerjoin(GarnishIngredient, InventoryItemModel.ingredient_id == GarnishIngredient.id)
    stmt = stmt.outerjoin(GarnishSubcategory, GarnishIngredient.subcategory_id == GarnishSubcategory.id)

    stmt = stmt.add_columns(
        BottleIngredient.subcategory_id.label("bottle_subcategory_id"),
        BottleSubcategory.name.label("bottle_subcategory_name"),
        GarnishIngredient.subcategory_id.label("garnish_subcategory_id"),
        GarnishSubcategory.name.label("garnish_subcategory_name"),
    )
    if item_type:
        stmt = stmt.where(InventoryItemModel.item_type == item_type)
    if not include_inactive:
        stmt = stmt.where(InventoryItemModel.is_active == True)  # noqa: E712

    res = await db.execute(stmt.order_by(func.lower(InventoryItemModel.name).asc()))
    rows = res.all()
    bottle_ids = [it.bottle_id for (it, _st, *_rest) in rows if it.item_type == "BOTTLE" and it.bottle_id is not None]
    bottle_prices = await _load_current_bottle_prices(db, bottle_ids)

    out = []
    for (it, st, bottle_subcategory_id, bottle_subcategory_name, garnish_subcategory_id, garnish_subcategory_name) in rows:
        subcategory_id = None
        subcategory_name = None
        if it.item_type == "BOTTLE":
            subcategory_id = bottle_subcategory_id
            subcategory_name = bottle_subcategory_name
        elif it.item_type == "GARNISH":
            subcategory_id = garnish_subcategory_id
            subcategory_name = garnish_subcategory_name

        row_out = {
                "location": location,
                "inventory_item_id": it.id,
                "item_type": it.item_type,
                "name": it.name,
                "unit": it.unit,
                "is_active": bool(it.is_active),
                "quantity": float(st.quantity) if st and st.quantity is not None else 0.0,
                "reserved_quantity": float(st.reserved_quantity) if st and st.reserved_quantity is not None else 0.0,
                "subcategory_id": subcategory_id,
                "subcategory_name": subcategory_name,
                "price_minor": (
                    int(it.price_minor)
                    if it.price_minor is not None
                    else (bottle_prices.get(it.bottle_id, {}).get("price_minor") if it.item_type == "BOTTLE" else None)
                ),
                "currency": (
                    it.currency
                    if it.currency
                    else (bottle_prices.get(it.bottle_id, {}).get("currency") if it.item_type == "BOTTLE" else None)
                ),
                "price": (
                    (float(it.price_minor) / 100.0)
                    if it.price_minor is not None
                    else (bottle_prices.get(it.bottle_id, {}).get("price") if it.item_type == "BOTTLE" else None)
                ),
            }

        if not user.is_superuser:
            row_out["price_minor"] = None
            row_out["currency"] = None
            row_out["price"] = None

        out.append(row_out)
    return out


@router.get("/stock/all", response_model=Dict)
async def get_stock_all(
    item_type: Optional[str] = None,
    include_inactive: bool = False,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    bar = await get_stock(location="BAR", item_type=item_type, include_inactive=include_inactive, user=user, db=db)
    wh = await get_stock(location="WAREHOUSE", item_type=item_type, include_inactive=include_inactive, user=user, db=db)
    return {"BAR": bar, "WAREHOUSE": wh}


@router.get("/stock/item/{item_id}", response_model=Dict)
async def get_stock_for_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Return stock for a single inventory item in both locations.
    """
    res = await db.execute(select(InventoryItemModel).where(InventoryItemModel.id == item_id))
    it = res.scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    sres = await db.execute(
        select(InventoryStockModel).where(InventoryStockModel.inventory_item_id == item_id)
    )
    by_loc: dict[str, InventoryStockModel] = {s.location: s for s in sres.scalars().all()}

    def _loc_out(loc: str) -> dict:
        s = by_loc.get(loc)
        return {
            "quantity": float(s.quantity) if s and s.quantity is not None else 0.0,
            "reserved_quantity": float(s.reserved_quantity) if s and s.reserved_quantity is not None else 0.0,
        }

    return {
        "inventory_item_id": it.id,
        "name": it.name,
        "unit": it.unit,
        "item_type": it.item_type,
        "BAR": _loc_out("BAR"),
        "WAREHOUSE": _loc_out("WAREHOUSE"),
    }


@router.post("/movements", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_movement(
    payload: InventoryMovementCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    delta = int(payload.change)
    reason_upper = (payload.reason or "").strip().upper()
    if reason_upper in {"USAGE", "WASTE"} and delta > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{reason_upper} movements must have a negative change",
        )
    if reason_upper == "TRANSFER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /inventory/transfers for transfers between locations",
        )
    movement_id = uuid.uuid4()
    stock_insert_id = uuid.uuid4()

    try:
        # NOTE: `current_active_user` may have already used this same session (FastAPI dependency cache),
        # which triggers SQLAlchemy autobegin. Therefore we must NOT call `db.begin()` here.
        # Instead, rely on the existing transaction and explicitly commit/rollback.

        # Ensure item exists
        res = await db.execute(select(InventoryItemModel).where(InventoryItemModel.id == payload.inventory_item_id))
        it = res.scalar_one_or_none()
        if not it:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

        db.add(
            InventoryMovementModel(
                id=movement_id,
                location=payload.location,
                inventory_item_id=payload.inventory_item_id,
                change=delta,
                reason=payload.reason,
                source_type=payload.source_type,
                source_id=payload.source_id,
                created_by_user_id=user.id,
            )
        )

        stock_tbl = InventoryStockModel.__table__
        upsert = (
            insert(stock_tbl)
            .values(
                id=stock_insert_id,
                location=payload.location,
                inventory_item_id=payload.inventory_item_id,
                quantity=delta,
                reserved_quantity=0,
            )
            # Deterministic conflict target
            .on_conflict_do_update(
                constraint="ux_inventory_stock_location_item",
                set_={"quantity": stock_tbl.c.quantity + delta},
            )
            .returning(
                stock_tbl.c.id,
                stock_tbl.c.location,
                stock_tbl.c.inventory_item_id,
                stock_tbl.c.quantity,
                stock_tbl.c.reserved_quantity,
            )
        )
        upserted = (await db.execute(upsert)).first()

        await db.commit()

        return {
            "movement": {
                "id": movement_id,
                "location": payload.location,
                "inventory_item_id": payload.inventory_item_id,
                "change": int(delta),
                "reason": payload.reason,
                "source_type": payload.source_type,
                "source_id": payload.source_id,
                "created_by_user_id": user.id,
            },
            "stock": {
                "location": payload.location,
                "inventory_item_id": payload.inventory_item_id,
                "quantity": int(upserted.quantity) if upserted else 0,
                "reserved_quantity": int(upserted.reserved_quantity) if upserted else 0,
            },
        }
    except HTTPException:
        # Let FastAPI handle status codes; txn will rollback automatically.
        raise
    except Exception as e:
        await db.rollback()
        print("[inventory] create_movement failed:", repr(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create movement: {e}")


@router.post("/transfers", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: InventoryTransferCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Transfer stock between BAR and WAREHOUSE.

    - Creates two movement rows (negative in from_location, positive in to_location).
    - Requires the inventory item to already exist in the source location and have enough available quantity.
    """
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    qty = int(payload.quantity)
    if qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity must be > 0")

    try:
        # Ensure item exists
        res = await db.execute(select(InventoryItemModel).where(InventoryItemModel.id == payload.inventory_item_id))
        it = res.scalar_one_or_none()
        if not it:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

        # Validate source stock exists and has enough available
        sres = await db.execute(
            select(InventoryStockModel).where(
                InventoryStockModel.location == payload.from_location,
                InventoryStockModel.inventory_item_id == payload.inventory_item_id,
            )
        )
        stock = sres.scalar_one_or_none()
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item not found in {payload.from_location} stock",
            )

        available = int(stock.quantity or 0) - int(stock.reserved_quantity or 0)
        if available < qty:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Not enough quantity in {payload.from_location}. Available={int(available)} requested={int(qty)}",
            )

        reason = payload.reason or "TRANSFER"

        out_from = await _upsert_stock_and_add_movement(
            db=db,
            user=user,
            location=payload.from_location,
            inventory_item_id=payload.inventory_item_id,
            delta=-int(qty),
            reason=reason,
            source_type=payload.source_type or "transfer",
            source_id=payload.source_id,
        )
        out_to = await _upsert_stock_and_add_movement(
            db=db,
            user=user,
            location=payload.to_location,
            inventory_item_id=payload.inventory_item_id,
            delta=int(qty),
            reason=reason,
            source_type=payload.source_type or "transfer",
            source_id=payload.source_id,
        )

        await db.commit()
        return {
            "from": out_from,
            "to": out_to,
            "inventory_item_id": payload.inventory_item_id,
            "from_location": payload.from_location,
            "to_location": payload.to_location,
            "quantity": float(qty),
            "reason": reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print("[inventory] create_transfer failed:", repr(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create transfer: {e}")


@router.post("/cocktails/{cocktail_id}/consume-batch", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def consume_cocktail_batch(
    cocktail_id: UUID,
    payload: ConsumeCocktailBatchRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reduce inventory according to a scaled cocktail batch.

    - `liters` is the desired batch size (in liters).
    - For bottle-backed ingredients: usage in ml is converted to fractional bottles using Bottle.volume_ml.
    - Garnish/optional ingredients are excluded by default (can be included via flags).
    """
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    try:
        result = await db.execute(
            select(CocktailRecipeModel)
            .options(
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient),
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
            )
            .where(CocktailRecipeModel.id == cocktail_id)
        )
        cocktail = result.scalar_one_or_none()
        if not cocktail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cocktail not found")

        recipe_ingredients: List[RecipeIngredientModel] = list(cocktail.recipe_ingredients or [])

        # Build total ml for scaling (exclude garnishes; exclude optional unless requested).
        total_ml = Decimal("0")
        for ri in recipe_ingredients:
            if ri.is_garnish and not payload.include_garnish:
                continue
            if ri.is_optional and not payload.include_optional:
                continue
            q = Decimal(str(ri.quantity))
            ml = _to_ml(q, ri.unit)
            if ml is None:
                # Non-volume units (e.g. piece) do not contribute to total volume scaling.
                continue
            total_ml += ml

        if total_ml <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot compute batch scaling: recipe has no ml/oz volume ingredients",
            )

        target_ml = Decimal(str(float(payload.liters) * 1000.0))
        scale_factor = (target_ml / total_ml) if total_ml else Decimal("0")
        servings_estimate = scale_factor  # assumes recipe is one serving/base build

        # Preload bottles for ingredient ids (for when recipe ingredient doesn't specify bottle_id)
        ingredient_ids = [ri.ingredient_id for ri in recipe_ingredients if ri.ingredient_id]
        bottles_by_ingredient: Dict[UUID, List[BottleModel]] = {}
        if ingredient_ids:
            bres = await db.execute(select(BottleModel).where(BottleModel.ingredient_id.in_(ingredient_ids)))
            for b in bres.scalars().all():
                bottles_by_ingredient.setdefault(b.ingredient_id, []).append(b)

        def _pick_bottle_for_ingredient(ingredient_id: UUID) -> Optional[BottleModel]:
            bs = bottles_by_ingredient.get(ingredient_id, [])
            if not bs:
                return None
            # Prefer default-cost bottle, otherwise first.
            for b in bs:
                if getattr(b, "is_default_cost", False):
                    return b
            return bs[0]

        movements_out: List[dict] = []

        for ri in recipe_ingredients:
            if ri.is_garnish and not payload.include_garnish:
                continue
            if ri.is_optional and not payload.include_optional:
                continue

            q = Decimal(str(ri.quantity))
            unit = (ri.unit or "").strip().lower()

            # GARNISH: map by ingredient_id -> inventory_items(item_type=GARNISH)
            if ri.is_garnish:
                inv_item_res = await db.execute(
                    select(InventoryItemModel).where(
                        InventoryItemModel.item_type == "GARNISH",
                        InventoryItemModel.ingredient_id == ri.ingredient_id,
                    )
                )
                inv_item = inv_item_res.scalar_one_or_none()
                if not inv_item:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No inventory GARNISH item found for ingredient_id={ri.ingredient_id}",
                    )

                ml = _to_ml(q, unit)
                if ml is not None:
                    delta = -_trunc_int(ml * scale_factor)
                else:
                    delta = -_trunc_int(q * servings_estimate)

                movements_out.append(
                    await _upsert_stock_and_add_movement(
                        db=db,
                        user=user,
                        location=payload.location,
                        inventory_item_id=inv_item.id,
                        delta=int(delta),
                        reason=payload.reason or f"Cocktail batch consumed: {cocktail.name}",
                        source_type=payload.source_type or "cocktail_batch",
                        source_id=payload.source_id,
                    )
                )
                continue

            # BOTTLE-backed ingredient: compute ml used, convert to bottle fractions.
            ml = _to_ml(q, unit)
            if ml is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported non-volume unit '{ri.unit}' for non-garnish ingredient '{ri.ingredient.name if ri.ingredient else ri.ingredient_id}'",
                )
            ml_used = ml * scale_factor

            bottle: Optional[BottleModel] = ri.bottle
            if bottle is None and ri.bottle_id:
                bottle = (await db.execute(select(BottleModel).where(BottleModel.id == ri.bottle_id))).scalar_one_or_none()
            if bottle is None and ri.ingredient_id:
                bottle = _pick_bottle_for_ingredient(ri.ingredient_id)

            if bottle is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"No bottle found for ingredient_id={ri.ingredient_id}. Set recipe_ingredient.bottle_id or create bottles for the ingredient.",
                )
            if not getattr(bottle, "volume_ml", None):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Bottle '{bottle.name}' missing volume_ml; cannot convert ml usage to bottles",
                )

            inv_item_res = await db.execute(
                select(InventoryItemModel).where(
                    InventoryItemModel.item_type == "BOTTLE",
                    InventoryItemModel.bottle_id == bottle.id,
                )
            )
            inv_item = inv_item_res.scalar_one_or_none()
            if not inv_item:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"No inventory BOTTLE item found for bottle_id={bottle.id} ({bottle.name})",
                )

            bottles_used = (ml_used / Decimal(str(bottle.volume_ml)))
            delta = -_trunc_int(bottles_used)

            movements_out.append(
                await _upsert_stock_and_add_movement(
                    db=db,
                    user=user,
                    location=payload.location,
                    inventory_item_id=inv_item.id,
                    delta=int(delta),
                    reason=payload.reason or f"Cocktail batch consumed: {cocktail.name}",
                    source_type=payload.source_type or "cocktail_batch",
                    source_id=payload.source_id,
                )
            )

        await db.commit()
        return {
            "cocktail_id": cocktail_id,
            "cocktail_name": getattr(cocktail, "name", None),
            "liters": float(payload.liters),
            "location": payload.location,
            "scale_factor": float(scale_factor),
            "movements_count": len(movements_out),
            "movements": movements_out,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print("[inventory] consume_cocktail_batch failed:", repr(e))
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consume cocktail batch: {e}",
        )


@router.post("/consume-event", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def consume_event_from_stock(
    payload: ConsumeEventRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reduce inventory according to a stored Event's EVENT-scope orders (requested amounts).

    For bottle-backed items, ml requested is converted to fractional bottles using Bottle.volume_ml.
    For garnish items, requested quantity is deducted as-is (or requested_ml if present).
    """
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    try:
        # Prevent double-consume. Must unconsume first.
        existing_consume = await db.execute(
            select(func.count())
            .select_from(InventoryMovementModel)
            .where(InventoryMovementModel.source_event_id == payload.event_id)
            .where(InventoryMovementModel.source_type == "event_consume")
            .where(InventoryMovementModel.is_reversed == False)  # noqa: E712
        )
        if int(existing_consume.scalar_one() or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event already consumed. Unconsume it before consuming again.",
            )

        ev_res = await db.execute(select(EventModel).where(EventModel.id == payload.event_id))
        ev = ev_res.scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        # Legacy double-consume check (older rows had no source_event_id; they only had source_type='event' and reason text).
        legacy_count_res = await db.execute(
            select(func.count())
            .select_from(InventoryMovementModel)
            .where(InventoryMovementModel.source_event_id.is_(None))
            .where((InventoryMovementModel.source_type.is_(None)) | (InventoryMovementModel.source_type == "event"))
            .where(InventoryMovementModel.is_reversed == False)  # noqa: E712
            .where(InventoryMovementModel.is_reversal == False)  # noqa: E712
            .where(InventoryMovementModel.change < 0)
            .where(InventoryMovementModel.reason.in_(_legacy_event_reason_candidates(ev)))
        )
        if int(legacy_count_res.scalar_one() or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event already consumed. Unconsume it before consuming again.",
            )

        orders_res = await db.execute(
            select(OrderModel)
            .options(
                selectinload(OrderModel.items).selectinload(OrderItemModel.bottle),
                selectinload(OrderModel.items).selectinload(OrderItemModel.ingredient),
            )
            .where(OrderModel.scope == "EVENT")
            .where(OrderModel.event_id == payload.event_id)
        )
        orders = orders_res.scalars().all() or []
        if not orders:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No EVENT orders found for this event. Generate orders first.",
            )

        # Aggregate deltas per inventory_item_id to avoid multiple movements per item
        deltas_by_item: dict[UUID, int] = {}
        reason = payload.reason or _default_event_consumed_reason(ev)

        inv_bottle_cache: dict[UUID, Optional[InventoryItemModel]] = {}
        inv_garnish_cache: dict[UUID, Optional[InventoryItemModel]] = {}

        for o in orders:
            for it in (o.items or []):
                requested_ml = getattr(it, "requested_ml", None)
                requested_qty = getattr(it, "requested_quantity", None)
                requested_unit = (getattr(it, "requested_unit", None) or "").strip().lower()
                # Backward compatible: older rows may only have needed_*
                if requested_ml is None and requested_qty is None:
                    requested_ml = getattr(it, "needed_ml", None)
                    requested_qty = getattr(it, "needed_quantity", None)
                    if not requested_unit:
                        requested_unit = (getattr(it, "unit", None) or "").strip().lower()

                if requested_ml is None and requested_qty is None:
                    continue

                delta: Optional[int] = None
                inv_item: Optional[InventoryItemModel] = None

                if getattr(it, "bottle_id", None):
                    bottle = getattr(it, "bottle", None)
                    if bottle is None:
                        bottle = (await db.execute(select(BottleModel).where(BottleModel.id == it.bottle_id))).scalar_one_or_none()
                    if bottle is None or not getattr(bottle, "volume_ml", None):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Bottle missing or missing volume_ml for bottle_id={it.bottle_id}",
                        )

                    if it.bottle_id not in inv_bottle_cache:
                        inv_res = await db.execute(
                            select(InventoryItemModel).where(
                                InventoryItemModel.item_type == "BOTTLE",
                                InventoryItemModel.bottle_id == it.bottle_id,
                            )
                        )
                        inv_bottle_cache[it.bottle_id] = inv_res.scalar_one_or_none()
                    inv_item = inv_bottle_cache.get(it.bottle_id)
                    if not inv_item:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"No inventory BOTTLE item found for bottle_id={it.bottle_id}",
                        )

                    if requested_ml is None:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bottle-backed line missing requested_ml")

                    bottles_used = (Decimal(str(float(requested_ml))) / Decimal(str(int(bottle.volume_ml))))
                    delta = -int(bottles_used)
                else:
                    ing_id = getattr(it, "ingredient_id", None)
                    if not ing_id:
                        continue
                    if ing_id not in inv_garnish_cache:
                        inv_res = await db.execute(
                            select(InventoryItemModel).where(
                                InventoryItemModel.item_type == "GARNISH",
                                InventoryItemModel.ingredient_id == ing_id,
                            )
                        )
                        inv_garnish_cache[ing_id] = inv_res.scalar_one_or_none()
                    inv_item = inv_garnish_cache.get(ing_id)
                    if not inv_item:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"No inventory GARNISH item found for ingredient_id={ing_id}",
                        )

                    if requested_ml is not None:
                        delta = -int(float(requested_ml))
                    else:
                        delta = -int(float(requested_qty))

                if inv_item is None or delta is None:
                    continue
                deltas_by_item[inv_item.id] = int(deltas_by_item.get(inv_item.id, 0)) + int(delta)

        # If location=ALL, split deductions across locations (WAREHOUSE then BAR).
        movements_out: List[dict] = []
        loc = (payload.location or "").upper()

        if loc == "ALL":
            item_ids = [iid for iid, d in deltas_by_item.items() if int(d) != 0]
            if item_ids:
                sres = await db.execute(
                    select(InventoryStockModel).where(InventoryStockModel.inventory_item_id.in_(item_ids))
                )
                stocks = sres.scalars().all() or []
            else:
                stocks = []

            stock_map: dict[tuple[UUID, str], InventoryStockModel] = {(s.inventory_item_id, s.location): s for s in stocks}

            for inventory_item_id, delta in deltas_by_item.items():
                delta = int(delta)
                if delta == 0:
                    continue
                if delta > 0:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="consume-event only supports negative deltas")

                need = -delta
                wh = stock_map.get((inventory_item_id, "WAREHOUSE"))
                bar = stock_map.get((inventory_item_id, "BAR"))
                wh_avail = int((wh.quantity if wh else 0) or 0) - int((wh.reserved_quantity if wh else 0) or 0)
                bar_avail = int((bar.quantity if bar else 0) or 0) - int((bar.reserved_quantity if bar else 0) or 0)
                total_avail = wh_avail + bar_avail
                if total_avail < need:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Not enough total stock for item={inventory_item_id}. Available={total_avail} requested={need}",
                    )

                take_wh = min(wh_avail, need)
                remaining = need - take_wh
                take_bar = min(bar_avail, remaining)

                if take_wh:
                    movements_out.append(
                        await _upsert_stock_and_add_movement(
                            db=db,
                            user=user,
                            location="WAREHOUSE",
                            inventory_item_id=inventory_item_id,
                            delta=-int(take_wh),
                            reason=reason,
                            source_type="event_consume",
                            source_id=payload.source_id,
                            source_event_id=payload.event_id,
                        )
                    )
                if take_bar:
                    movements_out.append(
                        await _upsert_stock_and_add_movement(
                            db=db,
                            user=user,
                            location="BAR",
                            inventory_item_id=inventory_item_id,
                            delta=-int(take_bar),
                            reason=reason,
                            source_type="event_consume",
                            source_id=payload.source_id,
                            source_event_id=payload.event_id,
                        )
                    )
        else:
            for inventory_item_id, delta in deltas_by_item.items():
                if int(delta) == 0:
                    continue
                movements_out.append(
                    await _upsert_stock_and_add_movement(
                        db=db,
                        user=user,
                        location=payload.location,
                        inventory_item_id=inventory_item_id,
                        delta=int(delta),
                        reason=reason,
                        source_type="event_consume",
                        source_id=payload.source_id,
                        source_event_id=payload.event_id,
                    )
                )

        await db.commit()
        return {
            "event_id": payload.event_id,
            "event_name": getattr(ev, "name", None),
            "location": payload.location,
            "movements_count": len(movements_out),
            "movements": movements_out,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print("[inventory] consume_event_from_stock failed:", repr(e))
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consume event from stock: {e}",
        )


@router.post("/unconsume-event", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def unconsume_event_from_stock(
    payload: UnconsumeEventRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Reverse a previous consume-event operation by creating opposite movements."""
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    try:
        ev_res = await db.execute(select(EventModel).where(EventModel.id == payload.event_id))
        ev = ev_res.scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        loc = (payload.location or "ALL").upper()
        q = (
            select(InventoryMovementModel)
            .where(InventoryMovementModel.source_event_id == payload.event_id)
            .where(InventoryMovementModel.source_type == "event_consume")
            .where(InventoryMovementModel.is_reversed == False)  # noqa: E712
        )
        if loc in ("BAR", "WAREHOUSE"):
            q = q.where(InventoryMovementModel.location == loc)
        res = await db.execute(q)
        to_reverse = res.scalars().all() or []
        # Back-compat: older consume rows were created with source_type='event' and reason "Event consumed: <name>".
        if not to_reverse:
            legacy_q = (
                select(InventoryMovementModel)
                .where(InventoryMovementModel.source_event_id.is_(None))
                .where((InventoryMovementModel.source_type.is_(None)) | (InventoryMovementModel.source_type == "event"))
                .where(InventoryMovementModel.is_reversed == False)  # noqa: E712
                .where(InventoryMovementModel.is_reversal == False)  # noqa: E712
                .where(InventoryMovementModel.change < 0)
                .where(InventoryMovementModel.reason.in_(_legacy_event_reason_candidates(ev)))
            )
            if loc in ("BAR", "WAREHOUSE"):
                legacy_q = legacy_q.where(InventoryMovementModel.location == loc)
            legacy_res = await db.execute(legacy_q)
            to_reverse = legacy_res.scalars().all() or []

            # If still nothing, we truly have nothing to unconsume.
            if not to_reverse:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nothing to unconsume for this event.")

        reason = payload.reason or _default_event_unconsumed_reason(ev)
        movements_out: List[dict] = []

        for mv in to_reverse:
            # Normalize legacy rows so future status checks can find them.
            if getattr(mv, "source_event_id", None) is None:
                mv.source_event_id = payload.event_id
            if (getattr(mv, "source_type", None) or "").strip().lower() in ("", "event"):
                mv.source_type = "event_consume"

            # Mark original as reversed and create a reversal movement.
            mv.is_reversed = True
            movements_out.append(
                await _upsert_stock_and_add_movement(
                    db=db,
                    user=user,
                    location=str(mv.location),
                    inventory_item_id=mv.inventory_item_id,
                    delta=-int(mv.change),
                    reason=reason,
                    source_type="event_unconsume",
                    source_id=None,
                    source_event_id=payload.event_id,
                    is_reversal=True,
                    reversal_of_id=mv.id,
                )
            )

        await db.commit()
        return {
            "event_id": payload.event_id,
            "event_name": getattr(ev, "name", None),
            "location": payload.location,
            "movements_count": len(movements_out),
            "movements": movements_out,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print("[inventory] unconsume_event_from_stock failed:", repr(e))
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unconsume event from stock: {e}",
        )


@router.get("/events/{event_id}/consumption", response_model=Dict)
async def event_consumption_status(
    event_id: UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return whether an event is currently consumed (i.e. has non-reversed event_consume movements)."""
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    res = await db.execute(
        select(func.count())
        .select_from(InventoryMovementModel)
        .where(InventoryMovementModel.source_event_id == event_id)
        .where(InventoryMovementModel.source_type == "event_consume")
        .where(InventoryMovementModel.is_reversed == False)  # noqa: E712
    )
    tagged = int(res.scalar_one() or 0) > 0
    if tagged:
        return {"event_id": event_id, "is_consumed": True}

    # Back-compat: legacy "event" movements with reason text.
    ev_res = await db.execute(select(EventModel).where(EventModel.id == event_id))
    ev = ev_res.scalar_one_or_none()
    if not ev:
        return {"event_id": event_id, "is_consumed": False}

    legacy_res = await db.execute(
        select(func.count())
        .select_from(InventoryMovementModel)
        .where(InventoryMovementModel.source_event_id.is_(None))
        .where((InventoryMovementModel.source_type.is_(None)) | (InventoryMovementModel.source_type == "event"))
        .where(InventoryMovementModel.is_reversed == False)  # noqa: E712
        .where(InventoryMovementModel.is_reversal == False)  # noqa: E712
        .where(InventoryMovementModel.change < 0)
        .where(InventoryMovementModel.reason.in_(_legacy_event_reason_candidates(ev)))
    )
    return {"event_id": event_id, "is_consumed": int(legacy_res.scalar_one() or 0) > 0}

@router.get("/movements", response_model=List[Dict])
async def list_movements(
    location: Optional[str] = Query(None, pattern="^(BAR|WAREHOUSE)$"),
    item_type: Optional[str] = None,
    inventory_item_id: Optional[UUID] = None,
    subcategory: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = Query(200, ge=1, le=1000),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    BottleIngredient = aliased(IngredientModel)
    GarnishIngredient = aliased(IngredientModel)
    BottleSubcategory = aliased(SubcategoryModel)
    GarnishSubcategory = aliased(SubcategoryModel)

    stmt = select(InventoryMovementModel, InventoryItemModel).join(
        InventoryItemModel, InventoryMovementModel.inventory_item_id == InventoryItemModel.id
    )
    # bottle-backed chain -> ingredient -> subcategory
    stmt = stmt.outerjoin(BottleModel, InventoryItemModel.bottle_id == BottleModel.id)
    stmt = stmt.outerjoin(BottleIngredient, BottleModel.ingredient_id == BottleIngredient.id)
    stmt = stmt.outerjoin(BottleSubcategory, BottleIngredient.subcategory_id == BottleSubcategory.id)

    # garnish-backed chain -> ingredient -> subcategory
    stmt = stmt.outerjoin(GarnishIngredient, InventoryItemModel.ingredient_id == GarnishIngredient.id)
    stmt = stmt.outerjoin(GarnishSubcategory, GarnishIngredient.subcategory_id == GarnishSubcategory.id)

    stmt = stmt.add_columns(
        BottleSubcategory.name.label("bottle_subcategory_name"),
        GarnishSubcategory.name.label("garnish_subcategory_name"),
    )

    if location:
        stmt = stmt.where(InventoryMovementModel.location == location)
    if item_type:
        stmt = stmt.where(InventoryItemModel.item_type == item_type)
    if inventory_item_id:
        stmt = stmt.where(InventoryMovementModel.inventory_item_id == inventory_item_id)
    if from_date:
        start_dt = datetime.combine(from_date, time.min)
        stmt = stmt.where(InventoryMovementModel.created_at >= start_dt)
    if to_date:
        end_excl = datetime.combine(to_date, time.min) + timedelta(days=1)
        stmt = stmt.where(InventoryMovementModel.created_at < end_excl)
    if subcategory:
        sub = (subcategory or "").strip()
        if sub.lower() == "glass":
            stmt = stmt.where(InventoryItemModel.item_type == "GLASS")
        elif sub.lower() == "uncategorized":
            stmt = stmt.where(
                (InventoryItemModel.item_type != "GLASS")
                & (BottleSubcategory.name.is_(None))
                & (GarnishSubcategory.name.is_(None))
            )
        else:
            stmt = stmt.where(
                (BottleSubcategory.name == sub) | (GarnishSubcategory.name == sub)
            )

    stmt = stmt.order_by(InventoryMovementModel.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    out = []
    for (mv, it, bottle_subcategory_name, garnish_subcategory_name) in rows:
        subcategory_name = None
        if it and it.item_type == "GLASS":
            subcategory_name = "Glass"
        elif it and it.item_type == "BOTTLE":
            subcategory_name = bottle_subcategory_name
        elif it and it.item_type == "GARNISH":
            subcategory_name = garnish_subcategory_name
        if not subcategory_name:
            subcategory_name = "Uncategorized"

        out.append(
            {
                "id": mv.id,
                "created_at": mv.created_at.isoformat() if mv.created_at else None,
                "location": mv.location,
                "inventory_item_id": mv.inventory_item_id,
                "item_type": it.item_type if it else None,
                "item_name": it.name if it else None,
                "subcategory_name": subcategory_name,
                "change": float(mv.change),
                "reason": mv.reason,
                "source_type": mv.source_type,
                "source_id": mv.source_id,
                "created_by_user_id": mv.created_by_user_id,
            }
        )
    return out

