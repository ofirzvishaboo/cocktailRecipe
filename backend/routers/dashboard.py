from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.auth import current_active_superuser
from db.checklist import ChecklistRun, ChecklistRunCompletion, ChecklistTemplate
from db.database import (
    Bottle as BottleModel,
    BottlePrice as BottlePriceModel,
    Event as EventModel,
    EventMenuItem as EventMenuItemModel,
    Order as OrderModel,
    OrderItem as OrderItemModel,
    get_async_session,
)
from db.schedule import (
    ScheduleAssignment,
    ScheduleWeek,
    ShiftTemplate,
    Staff,
    StaffAvailabilitySubmission,
)
from db.users import User
from services.schedule_deadlines import default_target_week_start

router = APIRouter()


def _sunday_of_week(d: date) -> date:
    """Return the Sunday (start) of the week containing d."""
    days_since_sunday = (d.weekday() + 1) % 7
    return d - timedelta(days=days_since_sunday)


def _fmt_time(t) -> str:
    return t.strftime("%H:%M") if t else ""


@router.get("/", response_model=dict)
async def get_dashboard(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
    from_date: str | None = Query(None, description="Week start (Sunday) as YYYY-MM-DD"),
):
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

    # ── Events ────────────────────────────────────────────────────────
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

    # ── Orders ────────────────────────────────────────────────────────
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

    # Order cost summary
    bottle_ids = list({
        it.bottle_id
        for o in orders
        for it in (o.items or [])
        if it.bottle_id and (it.recommended_bottles or 0) > 0
    })
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
        seen: set = set()
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

    # ── Today's shifts ────────────────────────────────────────────────
    today_dow = (today.weekday() + 1) % 7  # Sun=0 … Sat=6
    current_sunday = _sunday_of_week(today)

    week_res = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.week_start_date == current_sunday)
    )
    current_week = week_res.scalar_one_or_none()

    today_shifts: List[dict] = []
    if current_week:
        asg_res = await db.execute(
            select(ScheduleAssignment)
            .where(ScheduleAssignment.schedule_week_id == current_week.id)
            .where(ScheduleAssignment.day_of_week == today_dow)
        )
        assignments = asg_res.scalars().all() or []

        staff_ids = {a.staff_id for a in assignments}
        tpl_ids = {a.shift_template_id for a in assignments}

        staff_map: dict = {}
        if staff_ids:
            s_res = await db.execute(select(Staff).where(Staff.id.in_(staff_ids)))
            staff_map = {s.id: s for s in s_res.scalars().all()}

        tpl_map: dict = {}
        if tpl_ids:
            t_res = await db.execute(
                select(ShiftTemplate).where(ShiftTemplate.id.in_(tpl_ids))
            )
            tpl_map = {t.id: t for t in t_res.scalars().all()}

        for a in sorted(assignments, key=lambda x: (tpl_map.get(x.shift_template_id) and tpl_map[x.shift_template_id].start_time) or ""):
            s = staff_map.get(a.staff_id)
            tpl = tpl_map.get(a.shift_template_id)
            today_shifts.append({
                "staff_name": s.display_name if s else "",
                "role": a.role,
                "shift_name": tpl.name if tpl else "",
                "start_time": _fmt_time(tpl.start_time) if tpl else "",
                "end_time": _fmt_time(tpl.end_time) if tpl else "",
            })

    # ── Checklist status this week ────────────────────────────────────
    cl_res = await db.execute(
        select(ChecklistRun)
        .options(
            selectinload(ChecklistRun.completions),
            selectinload(ChecklistRun.submitted_by),
            selectinload(ChecklistRun.template),
        )
        .join(ChecklistTemplate)
        .where(ChecklistRun.run_date >= start_of_week)
        .where(ChecklistRun.run_date <= end_of_week)
        .order_by(ChecklistRun.run_date, ChecklistTemplate.type)
    )
    cl_runs = cl_res.scalars().unique().all() or []

    checklist_week: List[dict] = []
    for run in cl_runs:
        total = len(run.completions)
        completed = sum(1 for c in run.completions if c.completed)
        submitted_name: str | None = None
        if run.submitted_by:
            submitted_name = run.submitted_by.display_name
        checklist_week.append({
            "run_date": run.run_date.isoformat(),
            "type": run.template.type if run.template else "",
            "status": run.status,
            "total_items": total,
            "completed_items": completed,
            "submitted_by_name": submitted_name,
        })

    # ── Availability submission status (next target week) ─────────────
    target_week_start = default_target_week_start(today)

    target_week_res = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.week_start_date == target_week_start)
    )
    target_week_obj = target_week_res.scalar_one_or_none()

    staff_with_login_res = await db.execute(
        select(Staff)
        .where(Staff.is_active.is_(True))
        .where(Staff.user_id.isnot(None))
        .order_by(Staff.sort_order, Staff.display_name)
    )
    staff_with_login = staff_with_login_res.scalars().all() or []

    submitted_staff_ids: set = set()
    if target_week_obj:
        subs_res = await db.execute(
            select(StaffAvailabilitySubmission).where(
                StaffAvailabilitySubmission.schedule_week_id == target_week_obj.id
            )
        )
        submitted_staff_ids = {s.staff_id for s in (subs_res.scalars().all() or [])}

    availability_next_week = [
        {
            "staff_id": str(s.id),
            "display_name": s.display_name,
            "role": s.role,
            "submitted": s.id in submitted_staff_ids,
        }
        for s in staff_with_login
    ]

    # ── Serialize ─────────────────────────────────────────────────────
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
        "today_shifts": today_shifts,
        "checklist_week": checklist_week,
        "availability_next_week": availability_next_week,
        "target_week_start": target_week_start.isoformat(),
    }
