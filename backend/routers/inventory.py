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
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryMovementCreate,
    InventoryTransferCreate,
)

router = APIRouter()


def _as_decimal(x: float) -> Decimal:
    # Avoid float noise in NUMERIC; still not perfect but good enough for v3.
    return Decimal(str(float(x)))


def _to_ml(quantity: Decimal, unit: str) -> Optional[Decimal]:
    u = (unit or "").strip().lower()
    if u == "ml":
        return quantity
    if u == "oz":
        # US fluid ounce to ml
        return (quantity * Decimal("29.5735"))
    return None


async def _upsert_stock_and_add_movement(
    *,
    db: AsyncSession,
    user: User,
    location: str,
    inventory_item_id: UUID,
    delta: Decimal,
    reason: Optional[str],
    source_type: Optional[str],
    source_id: Optional[int],
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
            reserved_quantity=Decimal("0"),
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
            "change": float(delta),
            "reason": reason,
            "source_type": source_type,
            "source_id": source_id,
            "created_by_user_id": user.id,
        },
        "stock": {
            "location": location,
            "inventory_item_id": inventory_item_id,
            "quantity": float(upserted.quantity) if upserted else 0.0,
            "reserved_quantity": float(upserted.reserved_quantity) if upserted else 0.0,
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

    delta = _as_decimal(payload.change)
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
                reserved_quantity=Decimal("0"),
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
                "change": float(delta),
                "reason": payload.reason,
                "source_type": payload.source_type,
                "source_id": payload.source_id,
                "created_by_user_id": user.id,
            },
            "stock": {
                "location": payload.location,
                "inventory_item_id": payload.inventory_item_id,
                "quantity": float(upserted.quantity) if upserted else 0.0,
                "reserved_quantity": float(upserted.reserved_quantity) if upserted else 0.0,
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

    qty = _as_decimal(payload.quantity)
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

        available = (stock.quantity or Decimal("0")) - (stock.reserved_quantity or Decimal("0"))
        if available < qty:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Not enough quantity in {payload.from_location}. Available={float(available)} requested={float(qty)}",
            )

        reason = payload.reason or "TRANSFER"

        out_from = await _upsert_stock_and_add_movement(
            db=db,
            user=user,
            location=payload.from_location,
            inventory_item_id=payload.inventory_item_id,
            delta=-qty,
            reason=reason,
            source_type=payload.source_type or "transfer",
            source_id=payload.source_id,
        )
        out_to = await _upsert_stock_and_add_movement(
            db=db,
            user=user,
            location=payload.to_location,
            inventory_item_id=payload.inventory_item_id,
            delta=qty,
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

        target_ml = _as_decimal(payload.liters * 1000.0)
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
                    delta = -(ml * scale_factor)
                else:
                    delta = -(q * servings_estimate)

                movements_out.append(
                    await _upsert_stock_and_add_movement(
                        db=db,
                        user=user,
                        location=payload.location,
                        inventory_item_id=inv_item.id,
                        delta=delta,
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
            delta = -bottles_used

            movements_out.append(
                await _upsert_stock_and_add_movement(
                    db=db,
                    user=user,
                    location=payload.location,
                    inventory_item_id=inv_item.id,
                    delta=delta,
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

