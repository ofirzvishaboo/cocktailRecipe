from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.auth import current_active_superuser, current_active_user
from db.database import get_async_session
from db.schedule import (
    BarScheduleSettings,
    ScheduleAssignment,
    ScheduleWeek,
    ShiftTemplate,
    Staff,
    StaffAvailability,
    StaffAvailabilitySubmission,
)
from db.users import User
from schemas.schedule import (
    AppUserListItem,
    AssignmentPatch,
    AvailabilityBulkUpdate,
    BarScheduleSettingsRead,
    GenerateResult,
    MyAvailabilityMeta,
    MyStaffProfile,
    PublishedShiftEntry,
    PublishedWeekView,
    ScheduleAssignmentRead,
    ScheduleGap,
    ScheduleWeekCreate,
    ScheduleWeekRead,
    ScheduleWeekSummary,
    ShareTextResponse,
    ShiftTemplateRead,
    ShiftTemplateUpdate,
    StaffAvailabilityRead,
    StaffCreate,
    StaffRead,
    StaffSubmissionStatus,
    StaffUpdate,
)
from services.schedule_deadlines import (
    availability_deadline_for_week,
    default_target_week_start,
    staff_may_submit_availability,
)
from services.schedule_generator import run_generate_for_week
from services.schedule_rules import SATURDAY, template_allowed_on_day
from services.schedule_seed import ensure_schedule_defaults

router = APIRouter()

DAY_NAMES_EN = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
DAY_NAMES_HE = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"]


def _sunday_week_start(d: date) -> date:
    """Normalize any date to the Sunday that starts its week (0=Mon in weekday(), Sun=6)."""
    wd = d.weekday()  # Mon=0 .. Sun=6
    days_since_sunday = (wd + 1) % 7
    return d - timedelta(days=days_since_sunday)


async def _get_settings(db: AsyncSession) -> BarScheduleSettings:
    res = await db.execute(select(BarScheduleSettings).where(BarScheduleSettings.id == 1))
    row = res.scalar_one_or_none()
    if not row:
        row = BarScheduleSettings(id=1)
        db.add(row)
        await db.flush()
    return row


async def _staff_for_user(db: AsyncSession, user_id: UUID) -> Optional[Staff]:
    res = await db.execute(select(Staff).where(Staff.user_id == user_id, Staff.is_active.is_(True)))
    return res.scalar_one_or_none()


def _fmt_time(t) -> str:
    return t.strftime("%H:%M") if t else ""


def _serialize_assignment(a: ScheduleAssignment, staff_map: dict, tpl_map: dict) -> ScheduleAssignmentRead:
    s = staff_map.get(a.staff_id)
    t = tpl_map.get(a.shift_template_id)
    return ScheduleAssignmentRead(
        id=a.id,
        day_of_week=a.day_of_week,
        shift_template_id=a.shift_template_id,
        shift_name=t.name if t else "",
        start_time=t.start_time if t else datetime.min.time(),
        end_time=t.end_time if t else datetime.min.time(),
        staff_id=a.staff_id,
        staff_name=s.display_name if s else "",
        role=a.role,
    )


async def _submission_map(db: AsyncSession, week_id: UUID) -> dict:
    res = await db.execute(
        select(StaffAvailabilitySubmission).where(
            StaffAvailabilitySubmission.schedule_week_id == week_id
        )
    )
    return {row.staff_id: row for row in (res.scalars().all() or [])}


async def _upsert_submission(db: AsyncSession, week_id: UUID, staff_id: UUID) -> None:
    res = await db.execute(
        select(StaffAvailabilitySubmission).where(
            StaffAvailabilitySubmission.schedule_week_id == week_id,
            StaffAvailabilitySubmission.staff_id == staff_id,
        )
    )
    row = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row:
        row.submitted_at = now
    else:
        db.add(
            StaffAvailabilitySubmission(
                schedule_week_id=week_id,
                staff_id=staff_id,
                submitted_at=now,
            )
        )


async def _load_week_detail(
    db: AsyncSession,
    week: ScheduleWeek,
    gaps: Optional[List[ScheduleGap]] = None,
) -> ScheduleWeekRead:
    staff_res = await db.execute(
        select(Staff).where(Staff.is_active.is_(True)).order_by(Staff.sort_order, Staff.display_name)
    )
    staff_list = list(staff_res.scalars().all() or [])
    staff_map = {s.id: s for s in staff_list}
    submissions = await _submission_map(db, week.id)

    tpl_res = await db.execute(select(ShiftTemplate).order_by(ShiftTemplate.sort_order, ShiftTemplate.name))
    templates = list(tpl_res.scalars().all() or [])
    tpl_map = {t.id: t for t in templates}

    av_res = await db.execute(
        select(StaffAvailability)
        .where(StaffAvailability.schedule_week_id == week.id)
        .options(selectinload(StaffAvailability.staff))
    )
    availability_rows = list(av_res.scalars().all() or [])
    availability: List[StaffAvailabilityRead] = []
    for av in availability_rows:
        s = av.staff or staff_map.get(av.staff_id)
        availability.append(
            StaffAvailabilityRead(
                staff_id=av.staff_id,
                staff_name=s.display_name if s else "",
                role=s.role if s else "",
                day_of_week=av.day_of_week,
                available=av.available,
                notes=av.notes,
            )
        )

    asg_res = await db.execute(
        select(ScheduleAssignment).where(ScheduleAssignment.schedule_week_id == week.id)
    )
    assignments = [
        _serialize_assignment(a, staff_map, tpl_map) for a in (asg_res.scalars().all() or [])
    ]

    today = datetime.now(timezone.utc).date()
    deadline = availability_deadline_for_week(week.week_start_date)
    submission_status: List[StaffSubmissionStatus] = []
    for s in staff_list:
        sub = submissions.get(s.id)
        must_self = s.user_id is not None
        submission_status.append(
            StaffSubmissionStatus(
                staff_id=s.id,
                display_name=s.display_name,
                role=s.role,
                user_id=s.user_id,
                must_self_submit=must_self,
                submitted=sub is not None,
                submitted_at=sub.submitted_at if sub else None,
            )
        )

    return ScheduleWeekRead(
        id=week.id,
        week_start_date=week.week_start_date,
        status=week.status,
        availability_deadline=deadline,
        can_staff_submit=staff_may_submit_availability(week.week_start_date, today),
        submission_status=submission_status,
        templates=[ShiftTemplateRead.model_validate(t) for t in templates],
        staff=[StaffRead.model_validate(s) for s in staff_list],
        availability=availability,
        assignments=assignments,
        gaps=gaps or [],
    )


# --- Staff roster ---


@router.get("/users", response_model=List[AppUserListItem])
async def list_app_users(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    """List app users with IDs (for linking staff profiles)."""
    res = await db.execute(select(User).order_by(User.email.asc()))
    rows = res.scalars().all() or []
    out: List[AppUserListItem] = []
    for u in rows:
        out.append(
            AppUserListItem(
                id=u.id,
                email=u.email,
                first_name=getattr(u, "first_name", None),
                last_name=getattr(u, "last_name", None),
                is_superuser=bool(u.is_superuser),
            )
        )
    return out


@router.get("/staff", response_model=List[StaffRead])
async def list_staff(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    await ensure_schedule_defaults(db)
    res = await db.execute(select(Staff).order_by(Staff.sort_order, Staff.display_name))
    return [StaffRead.model_validate(s) for s in (res.scalars().all() or [])]


@router.post("/staff", response_model=StaffRead, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: StaffCreate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    if payload.user_id:
        existing = await db.execute(select(Staff).where(Staff.user_id == payload.user_id))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already linked to staff")
    row = Staff(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return StaffRead.model_validate(row)


@router.put("/staff/{staff_id}", response_model=StaffRead)
async def update_staff(
    staff_id: UUID,
    payload: StaffUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(Staff).where(Staff.id == staff_id))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    data = payload.model_dump(exclude_unset=True)
    if "user_id" in data and data["user_id"]:
        dup = await db.execute(
            select(Staff).where(Staff.user_id == data["user_id"], Staff.id != staff_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already linked to staff")
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return StaffRead.model_validate(row)


@router.delete("/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff(
    staff_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(Staff).where(Staff.id == staff_id))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    row.is_active = False
    await db.commit()


# --- Templates & settings ---


@router.get("/templates", response_model=List[ShiftTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    await ensure_schedule_defaults(db)
    res = await db.execute(select(ShiftTemplate).order_by(ShiftTemplate.sort_order, ShiftTemplate.name))
    return [ShiftTemplateRead.model_validate(t) for t in (res.scalars().all() or [])]


@router.put("/templates/{template_id}", response_model=ShiftTemplateRead)
async def update_template(
    template_id: UUID,
    payload: ShiftTemplateUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(ShiftTemplate).where(ShiftTemplate.id == template_id))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return ShiftTemplateRead.model_validate(row)


@router.get("/settings", response_model=BarScheduleSettingsRead)
async def get_settings(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    await ensure_schedule_defaults(db)
    settings = await _get_settings(db)
    return BarScheduleSettingsRead.model_validate(settings)


# --- Weeks ---


@router.get("/weeks", response_model=List[ScheduleWeekSummary])
async def list_weeks(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    stmt = select(ScheduleWeek).order_by(ScheduleWeek.week_start_date.desc())
    if from_date:
        stmt = stmt.where(ScheduleWeek.week_start_date >= from_date)
    if to_date:
        stmt = stmt.where(ScheduleWeek.week_start_date <= to_date)
    res = await db.execute(stmt)
    weeks = res.scalars().all() or []
    return [
        ScheduleWeekSummary(id=w.id, week_start_date=w.week_start_date, status=w.status) for w in weeks
    ]


@router.post("/weeks", response_model=ScheduleWeekRead, status_code=status.HTTP_201_CREATED)
async def create_week(
    payload: ScheduleWeekCreate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    await ensure_schedule_defaults(db)
    week_start = _sunday_week_start(payload.week_start)
    existing = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.week_start_date == week_start)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Week already exists")
    week = ScheduleWeek(
        week_start_date=week_start,
        status="draft",
        created_by_user_id=user.id,
    )
    db.add(week)
    await db.commit()
    await db.refresh(week)
    return await _load_week_detail(db, week)


@router.get("/weeks/{week_id}", response_model=ScheduleWeekRead)
async def get_week(
    week_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(ScheduleWeek).where(ScheduleWeek.id == week_id))
    week = res.scalar_one_or_none()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")
    return await _load_week_detail(db, week)


@router.put("/weeks/{week_id}/availability", response_model=List[StaffAvailabilityRead])
async def bulk_update_availability(
    week_id: UUID,
    payload: AvailabilityBulkUpdate,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    week_res = await db.execute(select(ScheduleWeek).where(ScheduleWeek.id == week_id))
    week = week_res.scalar_one_or_none()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    staff_res = await db.execute(select(Staff))
    staff_map = {s.id: s for s in (staff_res.scalars().all() or [])}

    for entry in payload.entries:
        if entry.staff_id not in staff_map:
            raise HTTPException(status_code=400, detail=f"Unknown staff {entry.staff_id}")
        s = staff_map[entry.staff_id]
        if s.user_id is not None and not force:
            raise HTTPException(
                status_code=400,
                detail="Staff with a linked login must submit their own availability. Use force=true to override.",
            )
        av_res = await db.execute(
            select(StaffAvailability).where(
                StaffAvailability.schedule_week_id == week_id,
                StaffAvailability.staff_id == entry.staff_id,
                StaffAvailability.day_of_week == entry.day_of_week,
            )
        )
        row = av_res.scalar_one_or_none()
        if row:
            row.available = entry.available
            row.notes = entry.notes
        else:
            db.add(
                StaffAvailability(
                    schedule_week_id=week_id,
                    staff_id=entry.staff_id,
                    day_of_week=entry.day_of_week,
                    available=entry.available,
                    notes=entry.notes,
                )
            )

    if force:
        force_staff_ids = {entry.staff_id for entry in payload.entries if staff_map.get(entry.staff_id) and staff_map[entry.staff_id].user_id is not None}
        for staff_id in force_staff_ids:
            await _upsert_submission(db, week_id, staff_id)

    await db.commit()

    av_res = await db.execute(
        select(StaffAvailability).where(StaffAvailability.schedule_week_id == week_id)
    )
    out: List[StaffAvailabilityRead] = []
    for av in av_res.scalars().all() or []:
        s = staff_map.get(av.staff_id)
        out.append(
            StaffAvailabilityRead(
                staff_id=av.staff_id,
                staff_name=s.display_name if s else "",
                role=s.role if s else "",
                day_of_week=av.day_of_week,
                available=av.available,
                notes=av.notes,
            )
        )
    return out


@router.post("/weeks/{week_id}/generate", response_model=GenerateResult)
async def generate_week(
    week_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    settings = await _get_settings(db)
    try:
        created, gaps = await run_generate_for_week(
            db,
            week_id,
            friday_last_start_hour=settings.friday_last_start_hour,
            saturday_closed=settings.saturday_closed,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Week not found")
    await db.commit()

    staff_res = await db.execute(select(Staff))
    staff_map = {s.id: s for s in (staff_res.scalars().all() or [])}
    tpl_res = await db.execute(select(ShiftTemplate))
    tpl_map = {t.id: t for t in (tpl_res.scalars().all() or [])}

    assignments = [_serialize_assignment(a, staff_map, tpl_map) for a in created]
    return GenerateResult(assignments=assignments, gaps=gaps)


@router.put("/weeks/{week_id}/assignments")
async def patch_assignment(
    week_id: UUID,
    payload: AssignmentPatch,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    settings = await _get_settings(db)
    if payload.day_of_week == SATURDAY and settings.saturday_closed:
        raise HTTPException(status_code=400, detail="Saturday is closed")
    if payload.staff_id is None:
        await db.execute(
            delete(ScheduleAssignment).where(
                ScheduleAssignment.schedule_week_id == week_id,
                ScheduleAssignment.day_of_week == payload.day_of_week,
                ScheduleAssignment.shift_template_id == payload.shift_template_id,
            )
        )
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    tpl_res = await db.execute(
        select(ShiftTemplate).where(ShiftTemplate.id == payload.shift_template_id)
    )
    tpl = tpl_res.scalar_one_or_none()
    if not tpl or not template_allowed_on_day(
        tpl,
        payload.day_of_week,
        friday_last_start_hour=settings.friday_last_start_hour,
        saturday_closed=settings.saturday_closed,
    ):
        raise HTTPException(status_code=400, detail="Shift not allowed on this day")

    staff_res = await db.execute(select(Staff).where(Staff.id == payload.staff_id))
    staff = staff_res.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    existing = await db.execute(
        select(ScheduleAssignment).where(
            ScheduleAssignment.schedule_week_id == week_id,
            ScheduleAssignment.day_of_week == payload.day_of_week,
            ScheduleAssignment.shift_template_id == payload.shift_template_id,
            ScheduleAssignment.staff_id == payload.staff_id,
        )
    )
    if existing.scalar_one_or_none():
        row = existing.scalar_one()
    else:
        row = ScheduleAssignment(
            schedule_week_id=week_id,
            day_of_week=payload.day_of_week,
            shift_template_id=payload.shift_template_id,
            staff_id=payload.staff_id,
            role=staff.role,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    staff_map = {staff.id: staff}
    tpl_map = {tpl.id: tpl}
    return _serialize_assignment(row, staff_map, tpl_map)


@router.post("/weeks/{week_id}/publish", response_model=ScheduleWeekRead)
async def publish_week(
    week_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(ScheduleWeek).where(ScheduleWeek.id == week_id))
    week = res.scalar_one_or_none()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")
    week.status = "published"
    await db.commit()
    return await _load_week_detail(db, week)


@router.get("/weeks/{week_id}/share-text", response_model=ShareTextResponse)
async def share_text(
    week_id: UUID,
    lang: str = Query("en"),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(ScheduleWeek).where(ScheduleWeek.id == week_id))
    week = res.scalar_one_or_none()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    detail = await _load_week_detail(db, week)
    use_he = (lang or "en").split("-")[0].lower() == "he"
    day_names = DAY_NAMES_HE if use_he else DAY_NAMES_EN

    start = week.week_start_date
    end = start + timedelta(days=6)
    header = f"{'לוח משמרות' if use_he else 'Work schedule'}: {start.isoformat()} – {end.isoformat()}\n\n"

    by_day: dict = {d: [] for d in range(7)}
    for a in detail.assignments:
        by_day[a.day_of_week].append(a)

    lines: List[str] = []
    for d in range(7):
        if d == SATURDAY:
            continue
        day_date = start + timedelta(days=d)
        assigns = by_day.get(d) or []
        if not assigns and d == SATURDAY:
            continue
        managers = [a.staff_name for a in assigns if a.role == "manager"]
        cleaners = [a.staff_name for a in assigns if a.role == "cleaner"]
        bartenders = [a.staff_name for a in assigns if a.role == "bartender"]
        shift_parts = []
        for a in assigns:
            shift_parts.append(
                f"{a.shift_name} {_fmt_time(a.start_time)}-{_fmt_time(a.end_time)}: {a.staff_name}"
            )
        label = day_names[d]
        if use_he:
            line = f"{label} {day_date.strftime('%d/%m')}: "
            if managers:
                line += f"מנהל: {', '.join(dict.fromkeys(managers))}. "
            if cleaners:
                line += f"ניקיון: {', '.join(dict.fromkeys(cleaners))}. "
            if bartenders:
                line += f"ברמנים: {', '.join(dict.fromkeys(bartenders))}. "
            if shift_parts:
                line += " | ".join(shift_parts)
        else:
            line = f"{label} {day_date.strftime('%d/%m')}: "
            if managers:
                line += f"Manager: {', '.join(dict.fromkeys(managers))}. "
            if cleaners:
                line += f"Cleaner: {', '.join(dict.fromkeys(cleaners))}. "
            if bartenders:
                line += f"Bartenders: {', '.join(dict.fromkeys(bartenders))}. "
            if shift_parts:
                line += " | ".join(shift_parts)
        if not assigns and d != SATURDAY:
            line += ("סגור" if use_he else "Closed") if d == SATURDAY else ""
        lines.append(line.strip())

    return ShareTextResponse(text=header + "\n".join(lines))


# --- Public schedule view (all authenticated users) ---


@router.get("/weeks/public", response_model=PublishedWeekView)
async def get_public_week(
    week_start: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Return the schedule for a given week. Accessible to all authenticated users."""
    target = _sunday_week_start(week_start) if week_start else _sunday_week_start(date.today())

    week_res = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.week_start_date == target)
    )
    week = week_res.scalar_one_or_none()

    if not week:
        return PublishedWeekView(week_start_date=target, status="not_created", assignments=[])

    staff_res = await db.execute(select(Staff).where(Staff.is_active.is_(True)))
    staff_map = {s.id: s for s in (staff_res.scalars().all() or [])}

    tpl_res = await db.execute(select(ShiftTemplate))
    tpl_map = {t.id: t for t in (tpl_res.scalars().all() or [])}

    asg_res = await db.execute(
        select(ScheduleAssignment)
        .where(ScheduleAssignment.schedule_week_id == week.id)
        .order_by(ScheduleAssignment.day_of_week, ScheduleAssignment.shift_template_id)
    )
    assignments: List[PublishedShiftEntry] = []
    for a in asg_res.scalars().all() or []:
        s = staff_map.get(a.staff_id)
        tpl = tpl_map.get(a.shift_template_id)
        assignments.append(
            PublishedShiftEntry(
                day_of_week=a.day_of_week,
                shift_name=tpl.name if tpl else "",
                start_time=tpl.start_time if tpl else datetime.min.time(),
                end_time=tpl.end_time if tpl else datetime.min.time(),
                staff_name=s.display_name if s else "",
                staff_id=a.staff_id,
                role=a.role,
            )
        )

    return PublishedWeekView(
        week_start_date=week.week_start_date,
        status=week.status,
        assignments=assignments,
    )


# --- Staff self-service availability ---


@router.get("/weeks/current/meta", response_model=MyAvailabilityMeta)
async def my_availability_meta(
    week_start: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    staff = await _staff_for_user(db, user.id)
    if not staff:
        raise HTTPException(status_code=404, detail="No staff profile linked to your account")

    target = _sunday_week_start(week_start) if week_start else default_target_week_start()
    deadline = availability_deadline_for_week(target)
    today = datetime.now(timezone.utc).date()

    week_res = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.week_start_date == target)
    )
    week = week_res.scalar_one_or_none()
    submitted = False
    submitted_at = None
    if week:
        subs = await _submission_map(db, week.id)
        sub = subs.get(staff.id)
        if sub:
            submitted = True
            submitted_at = sub.submitted_at

    return MyAvailabilityMeta(
        week_start_date=target,
        availability_deadline=deadline,
        can_submit=staff_may_submit_availability(target, today),
        submitted=submitted,
        submitted_at=submitted_at,
        default_week_start=default_target_week_start(today),
    )


@router.get("/me/staff", response_model=MyStaffProfile)
async def my_staff_profile(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    staff = await _staff_for_user(db, user.id)
    if not staff:
        raise HTTPException(status_code=404, detail="No staff profile linked to your account")
    return MyStaffProfile(staff_id=staff.id, display_name=staff.display_name, role=staff.role)


@router.get("/weeks/current/availability", response_model=List[StaffAvailabilityRead])
async def my_availability_get(
    week_start: date = Query(...),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    staff = await _staff_for_user(db, user.id)
    if not staff:
        raise HTTPException(status_code=404, detail="No staff profile linked to your account")
    week_start = _sunday_week_start(week_start)
    week_res = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.week_start_date == week_start)
    )
    week = week_res.scalar_one_or_none()
    if not week:
        return [
            StaffAvailabilityRead(
                staff_id=staff.id,
                staff_name=staff.display_name,
                role=staff.role,
                day_of_week=d,
                available=False,
                notes=None,
            )
            for d in range(7)
        ]
    av_res = await db.execute(
        select(StaffAvailability).where(
            StaffAvailability.schedule_week_id == week.id,
            StaffAvailability.staff_id == staff.id,
        )
    )
    by_day = {av.day_of_week: av for av in (av_res.scalars().all() or [])}
    out: List[StaffAvailabilityRead] = []
    for d in range(7):
        av = by_day.get(d)
        out.append(
            StaffAvailabilityRead(
                staff_id=staff.id,
                staff_name=staff.display_name,
                role=staff.role,
                day_of_week=d,
                available=av.available if av else False,
                notes=av.notes if av else None,
            )
        )
    return out


@router.put("/weeks/current/availability", response_model=List[StaffAvailabilityRead])
async def my_availability_put(
    week_start: date = Query(...),
    payload: AvailabilityBulkUpdate = ...,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    staff = await _staff_for_user(db, user.id)
    if not staff:
        raise HTTPException(status_code=404, detail="No staff profile linked to your account")

    week_start = _sunday_week_start(week_start)
    if not staff_may_submit_availability(week_start):
        raise HTTPException(
            status_code=403,
            detail="Availability deadline has passed (due by Tuesday before the schedule week)",
        )

    week_res = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.week_start_date == week_start)
    )
    week = week_res.scalar_one_or_none()
    if not week:
        week = ScheduleWeek(week_start_date=week_start, status="draft")
        db.add(week)
        await db.flush()

    for entry in payload.entries:
        if entry.staff_id != staff.id:
            raise HTTPException(status_code=403, detail="Cannot edit other staff availability")
        av_res = await db.execute(
            select(StaffAvailability).where(
                StaffAvailability.schedule_week_id == week.id,
                StaffAvailability.staff_id == staff.id,
                StaffAvailability.day_of_week == entry.day_of_week,
            )
        )
        row = av_res.scalar_one_or_none()
        if row:
            row.available = entry.available
            row.notes = entry.notes
        else:
            db.add(
                StaffAvailability(
                    schedule_week_id=week.id,
                    staff_id=staff.id,
                    day_of_week=entry.day_of_week,
                    available=entry.available,
                    notes=entry.notes,
                )
            )
    await _upsert_submission(db, week.id, staff.id)
    await db.commit()
    return await my_availability_get(week_start=week_start, db=db, user=user)
