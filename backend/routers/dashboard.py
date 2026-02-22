from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.auth import current_active_superuser
from db.users import User
from db.database import (
    get_async_session,
    Event as EventModel,
    EventMenuItem as EventMenuItemModel,
    Order as OrderModel,
    OrderItem as OrderItemModel,
    Bottle as BottleModel,
    BottlePrice as BottlePriceModel,
)

router = APIRouter()


def _sunday_of_week(d: datetime.date) -> datetime.date:
    """Return the Sunday (start) of the week containing d. Sunday = first day."""
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)


@router.get("/", response_model=dict)
async def get_dashboard(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
    from_date: str | None = Query(None, description="Week start (Sunday) as YYYY-MM-DD"),
):
    """
    Return events and orders for the current user for a given week.
    Use from_date (Sunday) to choose the week; defaults to current week.
    """
    today = datetime.utcnow().date()
    if from_date:
        try:
            parsed = datetime.strptime(from_date, "%Y-%m-%d").date()
            start_of_week = _sunday_of_week(parsed)
        except ValueError:
            start_of_week = _sunday_of_week(today)
    else:
        start_of_week = _sunday_of_week(today)
    end_of_week = start_of_week + timedelta(days=6)

    # Events: created by current user, event_date within this week
    events_stmt = (
        select(EventModel)
        .options(
            selectinload(EventModel.menu_items).selectinload(EventMenuItemModel.cocktail),
        )
        .where(EventModel.created_by_user_id == user.id)
        .where(EventModel.event_date >= start_of_week)
        .where(EventModel.event_date <= end_of_week)
        .order_by(EventModel.event_date.desc())
    )
    events_res = await db.execute(events_stmt)
    events = events_res.scalars().all() or []

    # Orders: created by current user, period overlaps this week, not yet arrived (exclude RECEIVED, CANCELLED)
    orders_stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.supplier),
            selectinload(OrderModel.items).selectinload(OrderItemModel.bottle),
        )
        .where(OrderModel.created_by_user_id == user.id)
        .where(OrderModel.period_start <= end_of_week)
        .where(OrderModel.period_end >= start_of_week)
        .where(OrderModel.status.notin_(["RECEIVED", "CANCELLED"]))
        .order_by(OrderModel.period_start.desc())
    )
    orders_res = await db.execute(orders_stmt)
    orders = orders_res.scalars().all() or []

    # Order cost summary: sum (recommended_bottles * bottle_price) for items with bottle + price
    bottle_ids = []
    for o in orders:
        for it in o.items or []:
            if it.bottle_id and (it.recommended_bottles or 0) > 0:
                bottle_ids.append(it.bottle_id)
    bottle_ids = list(set(bottle_ids))

    bottle_prices: dict = {}
    if bottle_ids:
        today_d = date.today()
        bp_res = await db.execute(
            select(BottlePriceModel)
            .where(BottlePriceModel.bottle_id.in_(bottle_ids))
            .where(BottlePriceModel.start_date <= today_d)
            .where((BottlePriceModel.end_date.is_(None)) | (BottlePriceModel.end_date >= today_d))
            .order_by(BottlePriceModel.bottle_id, BottlePriceModel.start_date.desc())
        )
        seen = set()
        for bp in bp_res.scalars().all():
            if bp.bottle_id not in seen:
                seen.add(bp.bottle_id)
                bottle_prices[bp.bottle_id] = {
                    "price_minor": int(bp.price_minor),
                    "currency": bp.currency or "ILS",
                }

    orders_total_minor = 0
    orders_currency = "ILS"
    for o in orders:
        for it in o.items or []:
            bots = int(it.recommended_bottles or 0)
            if bots <= 0 or not it.bottle_id:
                continue
            price_info = bottle_prices.get(it.bottle_id)
            if not price_info:
                continue
            orders_total_minor += bots * price_info["price_minor"]
            orders_currency = price_info["currency"]

    events_data = [
        {
            "id": str(e.id),
            "event_name": e.name or "",
            "event_date": e.event_date.isoformat() if e.event_date else "",
            "people": e.people or 0,
            "cocktail_names": [
                (m.cocktail.name or m.cocktail.name_he or "") if m.cocktail else ""
                for m in (e.menu_items or [])
            ],
        }
        for e in events
    ]

    orders_data = [
        {
            "id": str(o.id),
            "supplier": o.supplier.name if o.supplier else None,
            "status": o.status or "DRAFT",
            "period_start": o.period_start.isoformat() if o.period_start else None,
            "period_end": o.period_end.isoformat() if o.period_end else None,
            "scope": o.scope,
        }
        for o in orders
    ]

    return {
        "events_data": events_data,
        "orders_data": orders_data,
        "week_start": start_of_week.isoformat(),
        "week_end": end_of_week.isoformat(),
        "orders_total_minor": orders_total_minor,
        "orders_total_currency": orders_currency,
    }