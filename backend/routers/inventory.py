import uuid
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
import traceback

from core.auth import current_active_user
from db.database import (
    get_async_session,
    Bottle as BottleModel,
    Ingredient as IngredientModel,
    Kind as KindModel,
)
from db.inventory.item import InventoryItem as InventoryItemModel
from db.inventory.stock import InventoryStock as InventoryStockModel
from db.inventory.movement import InventoryMovement as InventoryMovementModel
from db.users import User
from schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryMovementCreate

router = APIRouter()


def _as_decimal(x: float) -> Decimal:
    # Avoid float noise in NUMERIC; still not perfect but good enough for v3.
    return Decimal(str(float(x)))


@router.get("/items", response_model=List[Dict])
async def list_inventory_items(
    item_type: Optional[str] = None,
    kind_id: Optional[UUID] = None,
    brand_id: Optional[UUID] = None,
    location: Optional[str] = None,
    q: Optional[str] = None,
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

    # bottle-backed chain: inventory_items -> bottle -> ingredient
    stmt = stmt.outerjoin(BottleModel, InventoryItemModel.bottle_id == BottleModel.id)
    stmt = stmt.outerjoin(BottleIngredient, BottleModel.ingredient_id == BottleIngredient.id)
    stmt = stmt.outerjoin(BottleKind, BottleIngredient.kind_id == BottleKind.id)

    # garnish-backed chain: inventory_items -> ingredient
    stmt = stmt.outerjoin(GarnishIngredient, InventoryItemModel.ingredient_id == GarnishIngredient.id)
    stmt = stmt.outerjoin(GarnishKind, GarnishIngredient.kind_id == GarnishKind.id)

    # Select kind fields for convenience in the response
    stmt = stmt.add_columns(
        BottleIngredient.kind_id.label("bottle_kind_id"),
        BottleKind.name.label("bottle_kind_name"),
        GarnishIngredient.kind_id.label("garnish_kind_id"),
        GarnishKind.name.label("garnish_kind_name"),
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
    out = []
    for (it, bottle_kind_id, bottle_kind_name, garnish_kind_id, garnish_kind_name) in rows:
        kind_id_out = None
        kind_name_out = None
        if it.item_type == "BOTTLE":
            kind_id_out = bottle_kind_id
            kind_name_out = bottle_kind_name
        elif it.item_type == "GARNISH":
            kind_id_out = garnish_kind_id
            kind_name_out = garnish_kind_name
        elif it.item_type == "GLASS":
            kind_name_out = "Glass"

        out.append(
            {
                "id": it.id,
                "item_type": it.item_type,
                "bottle_id": it.bottle_id,
                "ingredient_id": it.ingredient_id,
                "glass_type_id": it.glass_type_id,
                "name": it.name,
                "unit": it.unit,
                "kind_id": kind_id_out,
                "kind_name": kind_name_out,
                "is_active": bool(it.is_active),
                "min_level": float(it.min_level) if it.min_level is not None else None,
                "reorder_level": float(it.reorder_level) if it.reorder_level is not None else None,
                "stock": stock_by_item.get(it.id) if location else None,
            }
        )
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
    db: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(InventoryItemModel, InventoryStockModel)
        .outerjoin(
            InventoryStockModel,
            and_(
                InventoryStockModel.inventory_item_id == InventoryItemModel.id,
                InventoryStockModel.location == location,
            ),
        )
    )
    if item_type:
        stmt = stmt.where(InventoryItemModel.item_type == item_type)
    if not include_inactive:
        stmt = stmt.where(InventoryItemModel.is_active == True)  # noqa: E712

    res = await db.execute(stmt.order_by(func.lower(InventoryItemModel.name).asc()))
    rows = res.all()
    out = []
    for (it, st) in rows:
        out.append(
            {
                "location": location,
                "inventory_item_id": it.id,
                "item_type": it.item_type,
                "name": it.name,
                "unit": it.unit,
                "is_active": bool(it.is_active),
                "quantity": float(st.quantity) if st and st.quantity is not None else 0.0,
                "reserved_quantity": float(st.reserved_quantity) if st and st.reserved_quantity is not None else 0.0,
            }
        )
    return out


@router.get("/stock/all", response_model=Dict)
async def get_stock_all(
    item_type: Optional[str] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_async_session),
):
    bar = await get_stock(location="BAR", item_type=item_type, include_inactive=include_inactive, db=db)
    wh = await get_stock(location="WAREHOUSE", item_type=item_type, include_inactive=include_inactive, db=db)
    return {"BAR": bar, "WAREHOUSE": wh}


@router.post("/movements", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_movement(
    payload: InventoryMovementCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    delta = _as_decimal(payload.change)
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


@router.get("/movements", response_model=List[Dict])
async def list_movements(
    location: Optional[str] = Query(None, pattern="^(BAR|WAREHOUSE)$"),
    item_type: Optional[str] = None,
    inventory_item_id: Optional[UUID] = None,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
):
    stmt = select(InventoryMovementModel, InventoryItemModel).join(
        InventoryItemModel, InventoryMovementModel.inventory_item_id == InventoryItemModel.id
    )
    if location:
        stmt = stmt.where(InventoryMovementModel.location == location)
    if item_type:
        stmt = stmt.where(InventoryItemModel.item_type == item_type)
    if inventory_item_id:
        stmt = stmt.where(InventoryMovementModel.inventory_item_id == inventory_item_id)

    stmt = stmt.order_by(InventoryMovementModel.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    out = []
    for (mv, it) in rows:
        out.append(
            {
                "id": mv.id,
                "created_at": mv.created_at.isoformat() if mv.created_at else None,
                "location": mv.location,
                "inventory_item_id": mv.inventory_item_id,
                "item_type": it.item_type if it else None,
                "item_name": it.name if it else None,
                "change": float(mv.change),
                "reason": mv.reason,
                "source_type": mv.source_type,
                "source_id": mv.source_id,
                "created_by_user_id": mv.created_by_user_id,
            }
        )
    return out

