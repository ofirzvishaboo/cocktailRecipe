"""Auto-generate weekly staff schedule from availability."""
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.schedule import (
    ScheduleAssignment,
    ScheduleWeek,
    ShiftTemplate,
    Staff,
    StaffAvailability,
)
from schemas.schedule import ScheduleGap
from services.schedule_rules import FRIDAY, SATURDAY, is_day_open, template_allowed_on_day


def _available_staff_by_role(
    availability: List[StaffAvailability],
    staff_by_id: Dict[UUID, Staff],
    day: int,
) -> Dict[str, List[Staff]]:
    by_role: Dict[str, List[Staff]] = defaultdict(list)
    for av in availability:
        if av.day_of_week != day or not av.available:
            continue
        s = staff_by_id.get(av.staff_id)
        if s and s.is_active:
            by_role[s.role].append(s)
    for role in by_role:
        by_role[role].sort(key=lambda x: (x.sort_order, x.display_name))
    return by_role


def _pick_staff(
    candidates: List[Staff],
    assigned_today: Set[UUID],
) -> Optional[Staff]:
    for s in candidates:
        if s.id not in assigned_today:
            return s
    return None


def generate_assignments(
    *,
    templates: List[ShiftTemplate],
    staff_list: List[Staff],
    availability: List[StaffAvailability],
    friday_last_start_hour: int = 18,
    saturday_closed: bool = True,
) -> Tuple[List[dict], List[ScheduleGap]]:
    """
    Returns list of assignment dicts and gaps.
    Each assignment dict: day_of_week, shift_template_id, staff_id, role
    """
    staff_by_id = {s.id: s for s in staff_list if s.is_active}
    active_templates = [t for t in templates if t.active]
    assignments: List[dict] = []
    gaps: List[ScheduleGap] = []

    for day in range(7):
        if not is_day_open(day, saturday_closed=saturday_closed):
            continue

        day_templates = [
            t
            for t in sorted(active_templates, key=lambda x: (x.sort_order, x.name))
            if template_allowed_on_day(
                t, day, friday_last_start_hour=friday_last_start_hour, saturday_closed=saturday_closed
            )
        ]
        if not day_templates:
            continue

        by_role = _available_staff_by_role(availability, staff_by_id, day)
        assigned_today: Set[UUID] = set()

        def assign_role(role: str, count: int, template_index: int) -> int:
            nonlocal assigned_today
            assigned = 0
            candidates = by_role.get(role, [])
            idx = 0
            for _ in range(count):
                staff = _pick_staff(candidates, assigned_today)
                if not staff:
                    gaps.append(
                        ScheduleGap(
                            day_of_week=day,
                            role=role,
                            reason="no_available_staff",
                        )
                    )
                    break
                tpl = day_templates[min(template_index + assigned, len(day_templates) - 1)]
                assignments.append(
                    {
                        "day_of_week": day,
                        "shift_template_id": tpl.id,
                        "staff_id": staff.id,
                        "role": role,
                    }
                )
                assigned_today.add(staff.id)
                assigned += 1
            return assigned

        # Manager and cleaner: exactly one each per day
        assign_role("manager", 1, 0)
        assign_role("cleaner", 1, min(1, len(day_templates) - 1))

        # Bartenders: min 1, max 2 across the day
        bartenders_needed_min = 1
        bartenders_needed_max = 2
        bartender_count = assign_role("bartender", bartenders_needed_max, 0)
        if bartender_count < bartenders_needed_min:
            gaps.append(
                ScheduleGap(
                    day_of_week=day,
                    role="bartender",
                    reason="below_minimum_bartenders",
                )
            )

    return assignments, gaps


async def run_generate_for_week(
    db: AsyncSession,
    week_id: UUID,
    *,
    friday_last_start_hour: int = 18,
    saturday_closed: bool = True,
) -> Tuple[List[ScheduleAssignment], List[ScheduleGap]]:
    res = await db.execute(select(ScheduleWeek).where(ScheduleWeek.id == week_id))
    week = res.scalar_one_or_none()
    if not week:
        raise ValueError("week_not_found")

    tpl_res = await db.execute(select(ShiftTemplate).where(ShiftTemplate.active.is_(True)))
    templates = list(tpl_res.scalars().all() or [])

    staff_res = await db.execute(select(Staff).where(Staff.is_active.is_(True)))
    staff_list = list(staff_res.scalars().all() or [])

    av_res = await db.execute(
        select(StaffAvailability).where(StaffAvailability.schedule_week_id == week_id)
    )
    availability = list(av_res.scalars().all() or [])

    raw_assignments, gaps = generate_assignments(
        templates=templates,
        staff_list=staff_list,
        availability=availability,
        friday_last_start_hour=friday_last_start_hour,
        saturday_closed=saturday_closed,
    )

    await db.execute(delete(ScheduleAssignment).where(ScheduleAssignment.schedule_week_id == week_id))

    created: List[ScheduleAssignment] = []
    for a in raw_assignments:
        row = ScheduleAssignment(
            schedule_week_id=week_id,
            day_of_week=a["day_of_week"],
            shift_template_id=a["shift_template_id"],
            staff_id=a["staff_id"],
            role=a["role"],
        )
        db.add(row)
        created.append(row)

    await db.flush()
    return created, gaps
