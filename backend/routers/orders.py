from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import date, timedelta
import math

from core.auth import current_active_superuser
from db.users import User
from db.database import (
    get_async_session,
    Order as OrderModel,
    OrderItem as OrderItemModel,
    Supplier as SupplierModel,
    Event as EventModel,
    EventMenuItem as EventMenuItemModel,
    CocktailRecipe as CocktailRecipeModel,
    RecipeIngredient as RecipeIngredientModel,
    Ingredient as IngredientModel,
    Bottle as BottleModel,
    InventoryItem as InventoryItemModel,
    InventoryStock as InventoryStockModel,
)
from schemas.orders import (
    OrderRead,
    OrderItemRead,
    OrderUpdate,
    OrderItemUpdate,
    WeeklyOrderRequest,
    WeeklyOrderResponse,
    WeeklyByEventResponse,
    WeeklyByEventEventGroup,
    WeeklyByEventSupplierGroup,
)
from routers.cocktails import _unit_to_ml

router = APIRouter()


def _next_wednesday(d: date) -> date:
    # Monday=0 ... Sunday=6 ; Wednesday=2
    weekday = d.weekday()
    days_ahead = (2 - weekday) % 7
    if days_ahead == 0:
        return d
    return d + timedelta(days=days_ahead)


def _serialize_order(o: OrderModel) -> OrderRead:
    supplier = getattr(o, "supplier", None)
    ev = getattr(o, "event", None)
    items_out: List[OrderItemRead] = []
    for it in (o.items or []):
        ing = getattr(it, "ingredient", None)
        b = getattr(it, "bottle", None)
        items_out.append(
            OrderItemRead(
                id=it.id,
                ingredient_id=it.ingredient_id,
                ingredient_name=getattr(ing, "name", None) if ing else None,
                ingredient_name_he=getattr(ing, "name_he", None) if ing else None,
                requested_ml=float(it.requested_ml) if getattr(it, "requested_ml", None) is not None else None,
                requested_quantity=float(it.requested_quantity) if getattr(it, "requested_quantity", None) is not None else None,
                requested_unit=getattr(it, "requested_unit", None),
                used_from_stock_ml=float(it.used_from_stock_ml) if getattr(it, "used_from_stock_ml", None) is not None else None,
                used_from_stock_quantity=float(it.used_from_stock_quantity) if getattr(it, "used_from_stock_quantity", None) is not None else None,
                needed_ml=float(it.needed_ml) if it.needed_ml is not None else None,
                needed_quantity=float(it.needed_quantity) if it.needed_quantity is not None else None,
                unit=it.unit,
                bottle_id=it.bottle_id,
                bottle_name=getattr(b, "name", None) if b else None,
                bottle_name_he=getattr(b, "name_he", None) if b else None,
                bottle_volume_ml=it.bottle_volume_ml,
                recommended_bottles=it.recommended_bottles,
                leftover_ml=float(it.leftover_ml) if it.leftover_ml is not None else None,
            )
        )
    return OrderRead(
        id=o.id,
        scope=getattr(o, "scope", None) or "WEEKLY",
        event_id=getattr(o, "event_id", None),
        event_date=getattr(ev, "event_date", None) if ev else None,
        event_name=getattr(ev, "name", None) if ev else None,
        supplier_id=o.supplier_id,
        supplier_name=getattr(supplier, "name", None) if supplier else None,
        status=o.status,
        period_start=o.period_start,
        period_end=o.period_end,
        notes=o.notes,
        items=items_out,
    )


@router.get("/", response_model=List[OrderRead])
async def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    supplier_id: Optional[UUID] = None,
    scope: Optional[str] = None,
    event_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.supplier),
            selectinload(OrderModel.event),
            selectinload(OrderModel.items).selectinload(OrderItemModel.ingredient),
            selectinload(OrderModel.items).selectinload(OrderItemModel.bottle),
        )
        .order_by(OrderModel.period_start.desc())
    )
    if status_filter:
        stmt = stmt.where(OrderModel.status == status_filter)
    if supplier_id:
        stmt = stmt.where(OrderModel.supplier_id == supplier_id)
    if scope:
        stmt = stmt.where(OrderModel.scope == scope)
    if event_id:
        stmt = stmt.where(OrderModel.event_id == event_id)
    if from_date:
        stmt = stmt.where(OrderModel.period_end >= from_date)
    if to_date:
        stmt = stmt.where(OrderModel.period_start <= to_date)

    res = await db.execute(stmt)
    orders = res.scalars().all() or []

    # Hide stale WEEKLY DRAFT orders when there are no events in their window.
    # (Older data can linger if events were deleted before cleanup logic existed.)
    if (scope or "").upper() == "WEEKLY" and (status_filter or "").upper() == "DRAFT" and orders:
        min_start = min(o.period_start for o in orders)
        max_end = max(o.period_end for o in orders)
        ev_res = await db.execute(
            select(EventModel.event_date)
            .where(EventModel.event_date >= min_start)
            .where(EventModel.event_date <= max_end)
        )
        event_dates = [r[0] for r in (ev_res.fetchall() or [])]
        if event_dates:
            filtered = []
            for o in orders:
                has_any = any((d >= o.period_start and d <= o.period_end) for d in event_dates)
                if has_any:
                    filtered.append(o)
            orders = filtered
        else:
            orders = []

    return [_serialize_order(o) for o in orders]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(
        select(OrderModel)
        .options(
            selectinload(OrderModel.supplier),
            selectinload(OrderModel.event),
            selectinload(OrderModel.items).selectinload(OrderItemModel.ingredient),
            selectinload(OrderModel.items).selectinload(OrderItemModel.bottle),
        )
        .where(OrderModel.id == order_id)
    )
    o = res.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _serialize_order(o)


async def _load_stock_maps(db: AsyncSession, location_scope: str) -> tuple[dict[UUID, float], dict[tuple[UUID, str], float]]:
    loc = (location_scope or "ALL").upper()
    stock_stmt = (
        select(InventoryItemModel, InventoryStockModel, BottleModel)
        .outerjoin(InventoryStockModel, InventoryStockModel.inventory_item_id == InventoryItemModel.id)
        .outerjoin(BottleModel, InventoryItemModel.bottle_id == BottleModel.id)
    )
    if loc in {"BAR", "WAREHOUSE"}:
        stock_stmt = stock_stmt.where(InventoryStockModel.location == loc)
    s_res = await db.execute(stock_stmt)
    rows = s_res.all() or []

    stock_ml: dict[UUID, float] = {}
    stock_qty: dict[tuple[UUID, str], float] = {}
    for (inv_item, st, bottle) in rows:
        if not inv_item or not st:
            continue
        q = float(st.quantity or 0)
        if inv_item.item_type == "BOTTLE" and bottle is not None and bottle.ingredient_id and bottle.volume_ml:
            stock_ml[bottle.ingredient_id] = stock_ml.get(bottle.ingredient_id, 0.0) + (q * float(bottle.volume_ml))
        elif inv_item.item_type == "GARNISH" and inv_item.ingredient_id:
            unit = (inv_item.unit or "").strip().lower()
            stock_qty[(inv_item.ingredient_id, unit)] = stock_qty.get((inv_item.ingredient_id, unit), 0.0) + q
    return stock_ml, stock_qty


async def _compute_event_needs(
    *,
    db: AsyncSession,
    event: EventModel,
    cocktails_by_id: dict[UUID, CocktailRecipeModel],
    default_bottles: dict[UUID, BottleModel],
) -> tuple[dict[UUID, float], dict[tuple[UUID, str], float], dict[UUID, IngredientModel], dict[UUID, BottleModel]]:
    """Return (ml_need, non_ml_need, ingredient_cache, bottle_choice) for one event."""
    ml_need: dict[UUID, float] = {}
    non_ml_need: dict[tuple[UUID, str], float] = {}
    ingredient_cache: dict[UUID, IngredientModel] = {}
    bottle_choice: dict[UUID, BottleModel] = {}

    servings_total = float(event.people or 0) * float(event.servings_per_person or 3.0)
    servings_per_cocktail = servings_total / 4.0

    for mi in (event.menu_items or []):
        c = cocktails_by_id.get(mi.cocktail_recipe_id)
        if not c:
            continue
        for ri in (c.recipe_ingredients or []):
            ingredient_id = ri.ingredient_id
            if not ingredient_id:
                continue
            ing = getattr(ri, "ingredient", None)
            if ing is not None:
                ingredient_cache[ingredient_id] = ing

            qty = float(ri.quantity or 0)
            unit = (ri.unit or "").strip().lower()
            scaled_qty = qty * servings_per_cocktail

            scaled_ml = _unit_to_ml(scaled_qty, unit)
            if scaled_ml is not None:
                ml_need[ingredient_id] = ml_need.get(ingredient_id, 0.0) + float(scaled_ml)
                if ingredient_id not in bottle_choice:
                    b = getattr(ri, "bottle", None) or default_bottles.get(ingredient_id)
                    if b is not None and getattr(b, "volume_ml", None):
                        bottle_choice[ingredient_id] = b
            else:
                non_ml_need[(ingredient_id, unit)] = non_ml_need.get((ingredient_id, unit), 0.0) + float(scaled_qty)

    return ml_need, non_ml_need, ingredient_cache, bottle_choice


def _order_item_read_from_line(
    *,
    ingredient_id: UUID,
    ingredient: Optional[IngredientModel],
    bottle: Optional[BottleModel],
    requested_ml: Optional[float] = None,
    requested_qty: Optional[float] = None,
    requested_unit: Optional[str] = None,
    used_stock_ml: Optional[float] = None,
    used_stock_qty: Optional[float] = None,
    needed_ml: Optional[float] = None,
    needed_qty: Optional[float] = None,
    unit: Optional[str] = None,
    recommended_bottles: Optional[int] = None,
    leftover_ml: Optional[float] = None,
) -> OrderItemRead:
    return OrderItemRead(
        id=None,
        ingredient_id=ingredient_id,
        ingredient_name=getattr(ingredient, "name", None) if ingredient else None,
        ingredient_name_he=getattr(ingredient, "name_he", None) if ingredient else None,
        requested_ml=requested_ml,
        requested_quantity=requested_qty,
        requested_unit=requested_unit,
        used_from_stock_ml=used_stock_ml,
        used_from_stock_quantity=used_stock_qty,
        needed_ml=needed_ml,
        needed_quantity=needed_qty,
        unit=unit,
        bottle_id=getattr(bottle, "id", None) if bottle else None,
        bottle_name=getattr(bottle, "name", None) if bottle else None,
        bottle_name_he=getattr(bottle, "name_he", None) if bottle else None,
        bottle_volume_ml=int(getattr(bottle, "volume_ml", 0) or 0) if bottle else None,
        recommended_bottles=recommended_bottles,
        leftover_ml=leftover_ml,
    )


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: UUID,
    payload: OrderUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    o = res.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        o.status = data["status"]
    if "notes" in data:
        o.notes = data["notes"]
    await db.commit()
    return await get_order(order_id, db=db, user=user)


@router.patch("/{order_id}/items/{item_id}", response_model=OrderRead)
async def update_order_item(
    order_id: UUID,
    item_id: UUID,
    payload: OrderItemUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(OrderItemModel).where(OrderItemModel.id == item_id, OrderItemModel.order_id == order_id))
    it = res.scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(it, k, v)
    await db.commit()
    return await get_order(order_id, db=db, user=user)


@router.post("/weekly", response_model=WeeklyOrderResponse, status_code=status.HTTP_201_CREATED)
async def generate_weekly_orders(
    payload: WeeklyOrderRequest,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    start = payload.order_date or date.today()
    end = _next_wednesday(start)

    # Load events and their cocktails
    ev_res = await db.execute(
        select(EventModel)
        .options(
            selectinload(EventModel.menu_items).selectinload(EventMenuItemModel.cocktail),
        )
        .where(EventModel.event_date >= start)
        .where(EventModel.event_date <= end)
        .order_by(EventModel.event_date.asc())
    )
    events = ev_res.scalars().all() or []

    # Accumulate needs by ingredient:
    ml_need: dict[UUID, float] = {}
    non_ml_need: dict[tuple[UUID, str], float] = {}
    ingredient_cache: dict[UUID, IngredientModel] = {}
    bottle_choice: dict[UUID, BottleModel] = {}

    # Preload recipe ingredients for all cocktails used in events
    cocktail_ids: set[UUID] = set()
    for e in events:
        for mi in (e.menu_items or []):
            if mi.cocktail_recipe_id:
                cocktail_ids.add(mi.cocktail_recipe_id)

    if cocktail_ids:
        c_res = await db.execute(
            select(CocktailRecipeModel)
            .options(
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
            )
            .where(CocktailRecipeModel.id.in_(list(cocktail_ids)))
        )
        cocktails = {c.id: c for c in (c_res.scalars().all() or [])}
    else:
        cocktails = {}

    # Preload default bottles for involved ingredients
    involved_ingredient_ids: set[UUID] = set()
    for c in cocktails.values():
        for ri in (c.recipe_ingredients or []):
            if ri.ingredient_id:
                involved_ingredient_ids.add(ri.ingredient_id)
    default_bottles: dict[UUID, BottleModel] = {}
    if involved_ingredient_ids:
        b_res = await db.execute(
            select(BottleModel)
            .where(BottleModel.ingredient_id.in_(list(involved_ingredient_ids)))
            .where(BottleModel.is_default_cost == True)  # noqa: E712
        )
        for b in b_res.scalars().all():
            default_bottles.setdefault(b.ingredient_id, b)

    for e in events:
        servings_total = float(e.people or 0) * float(e.servings_per_person or 3.0)
        servings_per_cocktail = servings_total / 4.0

        for mi in (e.menu_items or []):
            c = cocktails.get(mi.cocktail_recipe_id)
            if not c:
                continue
            for ri in (c.recipe_ingredients or []):
                ingredient_id = ri.ingredient_id
                if not ingredient_id:
                    continue
                ing = getattr(ri, "ingredient", None)
                if ing is not None:
                    ingredient_cache[ingredient_id] = ing

                qty = float(ri.quantity or 0)
                unit = (ri.unit or "").strip().lower()
                scaled_qty = qty * servings_per_cocktail

                scaled_ml = _unit_to_ml(scaled_qty, unit)
                if scaled_ml is not None:
                    ml_need[ingredient_id] = ml_need.get(ingredient_id, 0.0) + float(scaled_ml)
                    if ingredient_id not in bottle_choice:
                        b = getattr(ri, "bottle", None) or default_bottles.get(ingredient_id)
                        if b is not None and getattr(b, "volume_ml", None):
                            bottle_choice[ingredient_id] = b
                else:
                    non_ml_need[(ingredient_id, unit)] = non_ml_need.get((ingredient_id, unit), 0.0) + float(scaled_qty)

    # Compute current stock in ml per ingredient (bottle-backed) and per-unit for garnish-like
    loc = (payload.location_scope or "ALL").upper()
    stock_stmt = (
        select(InventoryItemModel, InventoryStockModel, BottleModel)
        .outerjoin(InventoryStockModel, InventoryStockModel.inventory_item_id == InventoryItemModel.id)
        .outerjoin(BottleModel, InventoryItemModel.bottle_id == BottleModel.id)
    )
    if loc in {"BAR", "WAREHOUSE"}:
        stock_stmt = stock_stmt.where(InventoryStockModel.location == loc)

    s_res = await db.execute(stock_stmt)
    rows = s_res.all() or []

    stock_ml: dict[UUID, float] = {}
    stock_qty: dict[tuple[UUID, str], float] = {}
    for (inv_item, st, bottle) in rows:
        if not inv_item or not st:
            continue
        q = float(st.quantity or 0)
        if inv_item.item_type == "BOTTLE" and bottle is not None and bottle.ingredient_id and bottle.volume_ml:
            stock_ml[bottle.ingredient_id] = stock_ml.get(bottle.ingredient_id, 0.0) + (q * float(bottle.volume_ml))
        elif inv_item.item_type == "GARNISH" and inv_item.ingredient_id:
            unit = (inv_item.unit or "").strip().lower()
            stock_qty[(inv_item.ingredient_id, unit)] = stock_qty.get((inv_item.ingredient_id, unit), 0.0) + q

    # Subtract stock once; group by default supplier
    # Load ingredients to get default_supplier_id for all involved ingredient ids
    all_ing_ids = set(ml_need.keys()) | {k[0] for k in non_ml_need.keys()}
    if all_ing_ids:
        ing_res = await db.execute(select(IngredientModel).where(IngredientModel.id.in_(list(all_ing_ids))))
        for ing in ing_res.scalars().all():
            ingredient_cache.setdefault(ing.id, ing)

    # supplier_id can be None (unknown supplier) so we can still show ALL required ingredients.
    orders_by_supplier: dict[Optional[UUID], list[dict]] = {}
    missing_supplier_ids: List[UUID] = []
    missing_supplier_names: List[str] = []

    def _assign(ingredient_id: UUID) -> Optional[UUID]:
        ing = ingredient_cache.get(ingredient_id)
        sid = getattr(ing, "default_supplier_id", None) if ing is not None else None
        if not sid:
            missing_supplier_ids.append(ingredient_id)
            missing_supplier_names.append(getattr(ing, "name", None) or str(ingredient_id))
            return None
        return sid

    # ml lines
    for ingredient_id, need_ml in ml_need.items():
        have = stock_ml.get(ingredient_id, 0.0)
        short = max(0.0, float(need_ml) - float(have))
        if short <= 0:
            continue
        sid = _assign(ingredient_id)
        b = bottle_choice.get(ingredient_id)
        bottle_volume = int(getattr(b, "volume_ml", 0) or 0) if b else 0
        bottles_needed = None
        leftover_ml = None
        if bottle_volume:
            bottles_needed = int(math.ceil(short / float(bottle_volume)))
            leftover_ml = float(bottles_needed * bottle_volume) - short
        orders_by_supplier.setdefault(sid, []).append(
            {
                "ingredient_id": ingredient_id,
                "needed_ml": short,
                "bottle_id": getattr(b, "id", None) if b else None,
                "bottle_volume_ml": bottle_volume or None,
                "recommended_bottles": bottles_needed,
                "leftover_ml": leftover_ml,
            }
        )

    # non-ml lines
    for (ingredient_id, unit), need_qty in non_ml_need.items():
        have = stock_qty.get((ingredient_id, unit), 0.0)
        short = max(0.0, float(need_qty) - float(have))
        if short <= 0:
            continue
        sid = _assign(ingredient_id)
        orders_by_supplier.setdefault(sid, []).append(
            {
                "ingredient_id": ingredient_id,
                "needed_quantity": short,
                "unit": unit,
            }
        )

    # Idempotency:
    # For the same (supplier_id, period_start, period_end), do NOT create duplicates.
    # - If an existing order is DRAFT -> replace its items (update)
    # - If an existing order is not DRAFT -> skip (don't touch)
    existing_res = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(OrderModel.period_start == start)
        .where(OrderModel.period_end == end)
        .where(OrderModel.scope == "WEEKLY")
    )
    existing_orders = existing_res.scalars().all() or []
    existing_by_supplier: dict[Optional[UUID], OrderModel] = {o.supplier_id: o for o in existing_orders}

    created_ids: List[UUID] = []
    updated_ids: List[UUID] = []
    skipped_ids: List[UUID] = []

    for supplier_id, items in orders_by_supplier.items():
        if not items:
            continue
        existing = existing_by_supplier.get(supplier_id)
        if existing is not None:
            if (existing.status or "").upper() != "DRAFT":
                skipped_ids.append(existing.id)
                continue

            # Replace items
            for old in list(existing.items or []):
                await db.delete(old)
            await db.flush()
            o = existing
            updated_ids.append(o.id)
        else:
            o = OrderModel(
                scope="WEEKLY",
                supplier_id=supplier_id,
                status="DRAFT",
                period_start=start,
                period_end=end,
                created_by_user_id=user.id,
            )
            db.add(o)
            await db.flush()
            created_ids.append(o.id)

        for item in items:
            db.add(
                OrderItemModel(
                    order_id=o.id,
                    ingredient_id=item["ingredient_id"],
                    requested_ml=item.get("needed_ml"),
                    requested_quantity=item.get("needed_quantity"),
                    requested_unit=item.get("unit"),
                    used_from_stock_ml=0,
                    used_from_stock_quantity=0,
                    needed_ml=item.get("needed_ml"),
                    needed_quantity=item.get("needed_quantity"),
                    unit=item.get("unit"),
                    bottle_id=item.get("bottle_id"),
                    bottle_volume_ml=item.get("bottle_volume_ml"),
                    recommended_bottles=item.get("recommended_bottles"),
                    leftover_ml=item.get("leftover_ml"),
                )
            )

    await db.commit()

    return WeeklyOrderResponse(
        period_start=start,
        period_end=end,
        created_order_ids=created_ids,
        updated_order_ids=updated_ids,
        skipped_order_ids=skipped_ids,
        missing_suppliers_ingredient_ids=missing_supplier_ids,
        missing_suppliers_ingredient_names=missing_supplier_names,
    )


@router.post("/weekly-by-event", response_model=WeeklyByEventResponse, status_code=status.HTTP_201_CREATED)
async def generate_weekly_orders_by_event(
    payload: WeeklyOrderRequest,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    """
    Generate/persist:
    - EVENT-scope orders: one DRAFT order per (event_id, supplier_id)
      with requested/used/shortfall per ingredient.
    - WEEKLY-scope summary orders: one DRAFT order per supplier for the whole window,
      based on sum of per-event shortfalls after sequential stock allocation.
    """
    start = payload.order_date or date.today()
    end = _next_wednesday(start)

    # Load events and their cocktails
    ev_res = await db.execute(
        select(EventModel)
        .options(selectinload(EventModel.menu_items).selectinload(EventMenuItemModel.cocktail))
        .where(EventModel.event_date >= start)
        .where(EventModel.event_date <= end)
        .order_by(EventModel.event_date.asc())
    )
    events = ev_res.scalars().all() or []
    event_ids_in_window: set[UUID] = {e.id for e in events if getattr(e, "id", None)}

    # Preload recipe ingredients for all cocktails used in events
    cocktail_ids: set[UUID] = set()
    for e in events:
        for mi in (e.menu_items or []):
            if mi.cocktail_recipe_id:
                cocktail_ids.add(mi.cocktail_recipe_id)

    if cocktail_ids:
        c_res = await db.execute(
            select(CocktailRecipeModel)
            .options(
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient),
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
            )
            .where(CocktailRecipeModel.id.in_(list(cocktail_ids)))
        )
        cocktails_by_id = {c.id: c for c in (c_res.scalars().all() or [])}
    else:
        cocktails_by_id = {}

    # Default bottles per involved ingredient
    involved_ingredient_ids: set[UUID] = set()
    for c in cocktails_by_id.values():
        for ri in (c.recipe_ingredients or []):
            if ri.ingredient_id:
                involved_ingredient_ids.add(ri.ingredient_id)
    default_bottles: dict[UUID, BottleModel] = {}
    if involved_ingredient_ids:
        b_res = await db.execute(
            select(BottleModel)
            .where(BottleModel.ingredient_id.in_(list(involved_ingredient_ids)))
            .where(BottleModel.is_default_cost == True)  # noqa: E712
        )
        for b in b_res.scalars().all():
            default_bottles.setdefault(b.ingredient_id, b)

    # Starting stock (will be mutated sequentially across events)
    stock_ml, stock_qty = await _load_stock_maps(db, payload.location_scope)

    # Supplier names cache
    supplier_name_by_id: dict[UUID, str] = {}
    missing_supplier_ids: List[UUID] = []
    missing_supplier_names: List[str] = []

    # Weekly aggregation (requested/used/needed) per supplier
    weekly_ml: dict[tuple[Optional[UUID], UUID], dict] = {}
    weekly_qty: dict[tuple[Optional[UUID], UUID, str], dict] = {}

    # Idempotency caches for event + weekly
    existing_event_res = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(OrderModel.scope == "EVENT")
        .where(OrderModel.period_start >= start)
        .where(OrderModel.period_end <= end)
    )
    existing_event_orders = existing_event_res.scalars().all() or []
    existing_event_map: dict[tuple[UUID, Optional[UUID]], OrderModel] = {
        (o.event_id, o.supplier_id): o for o in existing_event_orders if o.event_id is not None
    }

    existing_weekly_res = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(OrderModel.scope == "WEEKLY")
        .where(OrderModel.period_start == start)
        .where(OrderModel.period_end == end)
    )
    existing_weekly_orders = existing_weekly_res.scalars().all() or []
    existing_weekly_map: dict[Optional[UUID], OrderModel] = {o.supplier_id: o for o in existing_weekly_orders}

    # If there are no events in the window, remove stale DRAFT orders for this window.
    # (Otherwise old items keep showing even though there is nothing to order.)
    if not events:
        for o in existing_event_orders:
            if (o.status or "").upper() == "DRAFT":
                await db.delete(o)
        for o in existing_weekly_orders:
            if (o.status or "").upper() == "DRAFT":
                await db.delete(o)
        await db.commit()
        return WeeklyByEventResponse(
            period_start=start,
            period_end=end,
            events=[],
            weekly_summary=[],
            created_event_order_ids=[],
            updated_event_order_ids=[],
            skipped_event_order_ids=[],
            created_weekly_order_ids=[],
            updated_weekly_order_ids=[],
            skipped_weekly_order_ids=[],
            missing_suppliers_ingredient_ids=[],
            missing_suppliers_ingredient_names=[],
        )

    created_event_ids: List[UUID] = []
    updated_event_ids: List[UUID] = []
    skipped_event_ids: List[UUID] = []
    created_weekly_ids: List[UUID] = []
    updated_weekly_ids: List[UUID] = []
    skipped_weekly_ids: List[UUID] = []

    response_events: List[WeeklyByEventEventGroup] = []

    async def _supplier_name(supplier_id: Optional[UUID]) -> Optional[str]:
        if supplier_id is None:
            return None
        if supplier_id in supplier_name_by_id:
            return supplier_name_by_id[supplier_id]
        res = await db.execute(select(SupplierModel).where(SupplierModel.id == supplier_id))
        s = res.scalar_one_or_none()
        if not s:
            return None
        supplier_name_by_id[supplier_id] = s.name
        return s.name

    def _assign_supplier(ing: Optional[IngredientModel], ingredient_id: UUID) -> Optional[UUID]:
        sid = getattr(ing, "default_supplier_id", None) if ing is not None else None
        if not sid:
            missing_supplier_ids.append(ingredient_id)
            missing_supplier_names.append(getattr(ing, "name", None) or str(ingredient_id))
            return None
        return sid

    for e in events:
        ml_need, non_ml_need, ingredient_cache, bottle_choice = await _compute_event_needs(
            db=db,
            event=e,
            cocktails_by_id=cocktails_by_id,
            default_bottles=default_bottles,
        )

        # Ensure we have Ingredient rows (for default_supplier_id) for all involved ingredients
        all_ing_ids = set(ml_need.keys()) | {k[0] for k in non_ml_need.keys()}
        if all_ing_ids:
            ing_res = await db.execute(select(IngredientModel).where(IngredientModel.id.in_(list(all_ing_ids))))
            for ing in ing_res.scalars().all():
                ingredient_cache.setdefault(ing.id, ing)

        # Build per-supplier lines for this event (include even if shortfall=0)
        event_lines_by_supplier: dict[Optional[UUID], List[dict]] = {}

        for ingredient_id, requested in ml_need.items():
            available = stock_ml.get(ingredient_id, 0.0)
            used = min(available, float(requested))
            stock_ml[ingredient_id] = float(available) - float(used)
            shortfall = max(0.0, float(requested) - float(used))

            ing = ingredient_cache.get(ingredient_id)
            sid = _assign_supplier(ing, ingredient_id)
            b = bottle_choice.get(ingredient_id)
            bottle_volume = int(getattr(b, "volume_ml", 0) or 0) if b else 0
            bottles_needed = None
            leftover_ml = None
            if bottle_volume and shortfall > 0:
                bottles_needed = int(math.ceil(shortfall / float(bottle_volume)))
                leftover_ml = float(bottles_needed * bottle_volume) - shortfall

            event_lines_by_supplier.setdefault(sid, []).append(
                {
                    "ingredient_id": ingredient_id,
                    "requested_ml": float(requested),
                    "used_stock_ml": float(used),
                    "needed_ml": float(shortfall),
                    "bottle": b,
                    "bottle_volume_ml": bottle_volume or None,
                    "recommended_bottles": bottles_needed,
                    "leftover_ml": leftover_ml,
                }
            )

            key = (sid, ingredient_id)
            weekly_ml.setdefault(
                key,
                {"requested_ml": 0.0, "used_stock_ml": 0.0, "needed_ml": 0.0, "bottle": b},
            )
            weekly_ml[key]["requested_ml"] += float(requested)
            weekly_ml[key]["used_stock_ml"] += float(used)
            weekly_ml[key]["needed_ml"] += float(shortfall)

        for (ingredient_id, unit), requested_qty in non_ml_need.items():
            unit_l = (unit or "").strip().lower()
            available = stock_qty.get((ingredient_id, unit_l), 0.0)
            used = min(available, float(requested_qty))
            stock_qty[(ingredient_id, unit_l)] = float(available) - float(used)
            shortfall = max(0.0, float(requested_qty) - float(used))

            ing = ingredient_cache.get(ingredient_id)
            sid = _assign_supplier(ing, ingredient_id)
            event_lines_by_supplier.setdefault(sid, []).append(
                {
                    "ingredient_id": ingredient_id,
                    "requested_quantity": float(requested_qty),
                    "requested_unit": unit_l,
                    "used_stock_quantity": float(used),
                    "needed_quantity": float(shortfall),
                    "unit": unit_l,
                }
            )

            key = (sid, ingredient_id, unit_l)
            weekly_qty.setdefault(
                key,
                {"requested_quantity": 0.0, "used_stock_quantity": 0.0, "needed_quantity": 0.0, "unit": unit_l},
            )
            weekly_qty[key]["requested_quantity"] += float(requested_qty)
            weekly_qty[key]["used_stock_quantity"] += float(used)
            weekly_qty[key]["needed_quantity"] += float(shortfall)

        # Persist event orders (one per supplier)
        suppliers_out: List[WeeklyByEventSupplierGroup] = []
        for sid, lines in event_lines_by_supplier.items():
            existing = existing_event_map.get((e.id, sid))
            if existing is not None:
                if (existing.status or "").upper() != "DRAFT":
                    skipped_event_ids.append(existing.id)
                    # still include in response by serializing existing
                    suppliers_out.append(
                        WeeklyByEventSupplierGroup(
                            supplier_id=sid,
                            supplier_name=await _supplier_name(sid),
                            order_id=existing.id,
                            items=_serialize_order(existing).items,
                        )
                    )
                    continue
                for old in list(existing.items or []):
                    await db.delete(old)
                await db.flush()
                o = existing
                updated_event_ids.append(o.id)
            else:
                o = OrderModel(
                    scope="EVENT",
                    event_id=e.id,
                    supplier_id=sid,
                    status="DRAFT",
                    period_start=e.event_date,
                    period_end=e.event_date,
                    created_by_user_id=user.id,
                )
                db.add(o)
                await db.flush()
                created_event_ids.append(o.id)

            # create items
            for line in lines:
                ingredient_id = line["ingredient_id"]
                b = line.get("bottle")
                db.add(
                    OrderItemModel(
                        order_id=o.id,
                        ingredient_id=ingredient_id,
                        requested_ml=line.get("requested_ml"),
                        requested_quantity=line.get("requested_quantity"),
                        requested_unit=line.get("requested_unit"),
                        used_from_stock_ml=line.get("used_stock_ml"),
                        used_from_stock_quantity=line.get("used_stock_quantity"),
                        needed_ml=line.get("needed_ml"),
                        needed_quantity=line.get("needed_quantity"),
                        unit=line.get("unit"),
                        bottle_id=getattr(b, "id", None) if b else None,
                        bottle_volume_ml=line.get("bottle_volume_ml"),
                        recommended_bottles=line.get("recommended_bottles"),
                        leftover_ml=line.get("leftover_ml"),
                    )
                )

            suppliers_out.append(
                WeeklyByEventSupplierGroup(
                    supplier_id=sid,
                    supplier_name=await _supplier_name(sid),
                    order_id=o.id,
                    items=[
                        _order_item_read_from_line(
                            ingredient_id=line["ingredient_id"],
                            ingredient=ingredient_cache.get(line["ingredient_id"]),
                            bottle=line.get("bottle"),
                            requested_ml=line.get("requested_ml"),
                            requested_qty=line.get("requested_quantity"),
                            requested_unit=line.get("requested_unit"),
                            used_stock_ml=line.get("used_stock_ml"),
                            used_stock_qty=line.get("used_stock_quantity"),
                            needed_ml=line.get("needed_ml"),
                            needed_qty=line.get("needed_quantity"),
                            unit=line.get("unit"),
                            recommended_bottles=line.get("recommended_bottles"),
                            leftover_ml=line.get("leftover_ml"),
                        )
                        for line in lines
                    ],
                )
            )

        response_events.append(
            WeeklyByEventEventGroup(
                event_id=e.id,
                event_date=e.event_date,
                event_name=getattr(e, "name", None),
                suppliers=suppliers_out,
            )
        )

    # Persist weekly summary orders (shortfall only), grouped by supplier
    weekly_suppliers: dict[Optional[UUID], List[dict]] = {}

    for (sid, ingredient_id), agg in weekly_ml.items():
        if float(agg.get("needed_ml", 0.0)) <= 0:
            continue
        b = agg.get("bottle")
        bottle_volume = int(getattr(b, "volume_ml", 0) or 0) if b else 0
        bottles_needed = None
        leftover_ml = None
        if bottle_volume:
            bottles_needed = int(math.ceil(float(agg["needed_ml"]) / float(bottle_volume)))
            leftover_ml = float(bottles_needed * bottle_volume) - float(agg["needed_ml"])
        weekly_suppliers.setdefault(sid, []).append(
            {
                "ingredient_id": ingredient_id,
                "requested_ml": agg.get("requested_ml"),
                "used_stock_ml": agg.get("used_stock_ml"),
                "needed_ml": agg.get("needed_ml"),
                "bottle": b,
                "bottle_volume_ml": bottle_volume or None,
                "recommended_bottles": bottles_needed,
                "leftover_ml": leftover_ml,
            }
        )

    for (sid, ingredient_id, unit), agg in weekly_qty.items():
        if float(agg.get("needed_quantity", 0.0)) <= 0:
            continue
        weekly_suppliers.setdefault(sid, []).append(
            {
                "ingredient_id": ingredient_id,
                "requested_quantity": agg.get("requested_quantity"),
                "requested_unit": agg.get("unit"),
                "used_stock_quantity": agg.get("used_stock_quantity"),
                "needed_quantity": agg.get("needed_quantity"),
                "unit": agg.get("unit"),
            }
        )

    weekly_summary_out: List[WeeklyByEventSupplierGroup] = []
    for sid, lines in weekly_suppliers.items():
        existing = existing_weekly_map.get(sid)
        if existing is not None:
            if (existing.status or "").upper() != "DRAFT":
                skipped_weekly_ids.append(existing.id)
                weekly_summary_out.append(
                    WeeklyByEventSupplierGroup(
                        supplier_id=sid,
                        supplier_name=await _supplier_name(sid),
                        order_id=existing.id,
                        items=_serialize_order(existing).items,
                    )
                )
                continue
            for old in list(existing.items or []):
                await db.delete(old)
            await db.flush()
            o = existing
            updated_weekly_ids.append(o.id)
        else:
            o = OrderModel(
                scope="WEEKLY",
                supplier_id=sid,
                status="DRAFT",
                period_start=start,
                period_end=end,
                created_by_user_id=user.id,
            )
            db.add(o)
            await db.flush()
            created_weekly_ids.append(o.id)

        for line in lines:
            b = line.get("bottle")
            db.add(
                OrderItemModel(
                    order_id=o.id,
                    ingredient_id=line["ingredient_id"],
                    requested_ml=line.get("requested_ml"),
                    requested_quantity=line.get("requested_quantity"),
                    requested_unit=line.get("requested_unit"),
                    used_from_stock_ml=line.get("used_stock_ml"),
                    used_from_stock_quantity=line.get("used_stock_quantity"),
                    needed_ml=line.get("needed_ml"),
                    needed_quantity=line.get("needed_quantity"),
                    unit=line.get("unit"),
                    bottle_id=getattr(b, "id", None) if b else None,
                    bottle_volume_ml=line.get("bottle_volume_ml"),
                    recommended_bottles=line.get("recommended_bottles"),
                    leftover_ml=line.get("leftover_ml"),
                )
            )

        # response lines
        # We may not have ingredient cache for all ids here; load on demand for names
        weekly_summary_out.append(
            WeeklyByEventSupplierGroup(
                supplier_id=sid,
                supplier_name=await _supplier_name(sid),
                order_id=o.id,
                items=[
                    _order_item_read_from_line(
                        ingredient_id=line["ingredient_id"],
                        ingredient=None,
                        bottle=line.get("bottle"),
                        requested_ml=line.get("requested_ml"),
                        requested_qty=line.get("requested_quantity"),
                        requested_unit=line.get("requested_unit"),
                        used_stock_ml=line.get("used_stock_ml"),
                        used_stock_qty=line.get("used_stock_quantity"),
                        needed_ml=line.get("needed_ml"),
                        needed_qty=line.get("needed_quantity"),
                        unit=line.get("unit"),
                        recommended_bottles=line.get("recommended_bottles"),
                        leftover_ml=line.get("leftover_ml"),
                    )
                    for line in lines
                ],
            )
        )

    # Cleanup stale DRAFT orders that no longer belong after event removal / zero shortfall:
    # - EVENT orders for events no longer in the window
    # - WEEKLY orders for suppliers with no remaining shortfall
    weekly_supplier_ids_present: set[Optional[UUID]] = set(weekly_suppliers.keys())
    for o in existing_event_orders:
        if (o.status or "").upper() != "DRAFT":
            continue
        if o.event_id is None or o.event_id not in event_ids_in_window:
            await db.delete(o)
    for o in existing_weekly_orders:
        if (o.status or "").upper() != "DRAFT":
            continue
        if o.supplier_id not in weekly_supplier_ids_present:
            await db.delete(o)

    await db.commit()

    return WeeklyByEventResponse(
        period_start=start,
        period_end=end,
        events=response_events,
        weekly_summary=weekly_summary_out,
        created_event_order_ids=created_event_ids,
        updated_event_order_ids=updated_event_ids,
        skipped_event_order_ids=skipped_event_ids,
        created_weekly_order_ids=created_weekly_ids,
        updated_weekly_order_ids=updated_weekly_ids,
        skipped_weekly_order_ids=skipped_weekly_ids,
        missing_suppliers_ingredient_ids=missing_supplier_ids,
        missing_suppliers_ingredient_names=missing_supplier_names,
    )

