from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.auth import current_active_superuser, current_active_user
from db.checklist import (
    ChecklistItem,
    ChecklistRun,
    ChecklistRunCompletion,
    ChecklistRunNote,
    ChecklistSection,
    ChecklistTemplate,
)
from db.database import get_async_session
from db.schedule import Staff
from db.users import User
from schemas.checklist import (
    ChecklistItemCompletionRead,
    ChecklistRunRead,
    ChecklistRunSummary,
    ChecklistRunUpdate,
    ChecklistTemplateRead,
)

router = APIRouter()

CHECKBOX_SECTION_TYPES = {"checkbox", "daily_rotation"}


async def _staff_for_user(db: AsyncSession, user_id: UUID) -> Optional[Staff]:
    res = await db.execute(select(Staff).where(Staff.user_id == user_id, Staff.is_active.is_(True)))
    return res.scalar_one_or_none()


async def _require_bartender(db: AsyncSession, user: User) -> Optional[Staff]:
    """Return the staff profile for a bartender, or None for superusers (who are allowed through)."""
    if user.is_superuser:
        return None
    staff = await _staff_for_user(db, user.id)
    if not staff:
        raise HTTPException(status_code=403, detail="No staff profile linked to your account")
    if staff.role != "bartender":
        raise HTTPException(status_code=403, detail="Checklists are available to bartenders only")
    return staff


async def _get_template_by_type(db: AsyncSession, checklist_type: str) -> ChecklistTemplate:
    res = await db.execute(
        select(ChecklistTemplate)
        .where(ChecklistTemplate.type == checklist_type)
        .options(
            selectinload(ChecklistTemplate.sections).selectinload(ChecklistSection.items),
        )
    )
    template = res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail=f"Checklist template '{checklist_type}' not found")
    return template


def _checkbox_items(template: ChecklistTemplate, run_date: Optional[date] = None) -> List[ChecklistItem]:
    """Return the items that count as required checkboxes for a run.

    For daily_rotation sections, only the item matching run_date's day-of-week is
    included (0=Sun … 6=Sat, matching the app convention). All 7 items are still
    stored/displayed, but only today's counts toward progress and submission.
    """
    items: List[ChecklistItem] = []
    today_dow: Optional[int] = None
    if run_date is not None:
        # Python weekday(): Mon=0 … Sun=6 → app convention: Sun=0 … Sat=6
        today_dow = (run_date.weekday() + 1) % 7

    for section in sorted(template.sections, key=lambda s: s.sort_order):
        if section.section_type in CHECKBOX_SECTION_TYPES:
            for item in sorted(section.items, key=lambda i: i.sort_order):
                if section.section_type == "daily_rotation":
                    # Only count today's rotation item; skip the rest
                    if today_dow is not None and item.day_of_week != today_dow:
                        continue
                items.append(item)
    return items


def _count_completions(run: ChecklistRun, checkbox_items: List[ChecklistItem]) -> tuple[int, int]:
    completion_map = {c.item_id: c.completed for c in run.completions}
    total = len(checkbox_items)
    completed = sum(1 for item in checkbox_items if completion_map.get(item.id, False))
    return total, completed


def _serialize_run(
    run: ChecklistRun,
    template: ChecklistTemplate,
    *,
    can_edit: bool = True,
) -> ChecklistRunRead:
    checkbox_items = _checkbox_items(template, run.run_date)
    total, completed = _count_completions(run, checkbox_items)
    notes = {n.field_key: n.value for n in run.notes}
    if run.submitted_by:
        submitted_name = run.submitted_by.display_name
    elif run.submitted_by_user:
        u = run.submitted_by_user
        submitted_name = ((u.first_name or '') + ' ' + (u.last_name or '')).strip() or u.email
    else:
        submitted_name = None

    return ChecklistRunRead(
        id=run.id,
        template_id=template.id,
        type=template.type,  # type: ignore[arg-type]
        run_date=run.run_date,
        status=run.status,  # type: ignore[arg-type]
        submitted_by_staff_id=run.submitted_by_staff_id,
        submitted_by_name=submitted_name,
        submitted_at=run.submitted_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        can_edit=can_edit and run.status == "in_progress",
        sections=sorted(template.sections, key=lambda s: s.sort_order),
        completions=[
            ChecklistItemCompletionRead(
                item_id=c.item_id,
                completed=c.completed,
                completed_at=c.completed_at,
            )
            for c in run.completions
        ],
        notes=notes,
        total_items=total,
        completed_items=completed,
    )


async def _get_or_create_run(
    db: AsyncSession,
    template: ChecklistTemplate,
    run_date: date,
) -> ChecklistRun:
    res = await db.execute(
        select(ChecklistRun)
        .where(ChecklistRun.template_id == template.id, ChecklistRun.run_date == run_date)
        .options(
            selectinload(ChecklistRun.completions),
            selectinload(ChecklistRun.notes),
            selectinload(ChecklistRun.submitted_by),
            selectinload(ChecklistRun.submitted_by_user),
        )
    )
    run = res.scalar_one_or_none()
    if run:
        return run

    run = ChecklistRun(template_id=template.id, run_date=run_date, status="in_progress")
    db.add(run)
    await db.flush()

    for item in _checkbox_items(template):
        db.add(ChecklistRunCompletion(run_id=run.id, item_id=item.id, completed=False))

    for section in template.sections:
        if section.section_type == "text_fields":
            for item in section.items:
                db.add(ChecklistRunNote(run_id=run.id, field_key=item.key, value=""))

    await db.flush()
    await db.refresh(run, ["completions", "notes", "submitted_by", "submitted_by_user"])
    return run


@router.get("/templates/{checklist_type}", response_model=ChecklistTemplateRead)
async def get_template(
    checklist_type: str,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await _require_bartender(db, user)
    if checklist_type not in ("opening", "closing"):
        raise HTTPException(status_code=400, detail="type must be opening or closing")
    template = await _get_template_by_type(db, checklist_type)
    return template


@router.get("/me/runs/today", response_model=ChecklistRunRead)
async def get_or_create_today_run(
    type: str = Query(..., pattern="^(opening|closing)$"),
    run_date: Optional[date] = Query(None, alias="date"),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await _require_bartender(db, user)
    target_date = run_date or datetime.now(timezone.utc).date()
    template = await _get_template_by_type(db, type)
    run = await _get_or_create_run(db, template, target_date)
    await db.commit()
    return _serialize_run(run, template)


@router.put("/me/runs/{run_id}", response_model=ChecklistRunRead)
async def update_run(
    run_id: UUID,
    body: ChecklistRunUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    await _require_bartender(db, user)

    res = await db.execute(
        select(ChecklistRun)
        .where(ChecklistRun.id == run_id)
        .options(
            selectinload(ChecklistRun.completions),
            selectinload(ChecklistRun.notes),
            selectinload(ChecklistRun.submitted_by),
            selectinload(ChecklistRun.submitted_by_user),
            selectinload(ChecklistRun.template).selectinload(ChecklistTemplate.sections).selectinload(ChecklistSection.items),
        )
    )
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    if run.status == "submitted":
        raise HTTPException(status_code=400, detail="Submitted checklists cannot be edited")

    template = run.template
    checkbox_item_ids = {item.id for item in _checkbox_items(template)}

    if body.completions is not None:
        completion_map = {c.item_id: c for c in run.completions}
        now = datetime.now(timezone.utc)
        for upd in body.completions:
            if upd.item_id not in checkbox_item_ids:
                continue
            comp = completion_map.get(upd.item_id)
            if not comp:
                comp = ChecklistRunCompletion(run_id=run.id, item_id=upd.item_id)
                db.add(comp)
                completion_map[upd.item_id] = comp
            comp.completed = upd.completed
            comp.completed_at = now if upd.completed else None

    if body.notes is not None:
        note_map = {n.field_key: n for n in run.notes}
        text_field_keys = {
            item.key
            for section in template.sections
            if section.section_type == "text_fields"
            for item in section.items
        }
        for field_key, value in body.notes.items():
            if field_key not in text_field_keys:
                continue
            note = note_map.get(field_key)
            if not note:
                note = ChecklistRunNote(run_id=run.id, field_key=field_key, value=value or "")
                db.add(note)
                note_map[field_key] = note
            else:
                note.value = value or ""

    run.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run, ["completions", "notes", "submitted_by", "submitted_by_user", "template"])
    return _serialize_run(run, template)


@router.post("/me/runs/{run_id}/submit", response_model=ChecklistRunRead)
async def submit_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    staff = await _require_bartender(db, user)

    res = await db.execute(
        select(ChecklistRun)
        .where(ChecklistRun.id == run_id)
        .options(
            selectinload(ChecklistRun.completions),
            selectinload(ChecklistRun.notes),
            selectinload(ChecklistRun.submitted_by),
            selectinload(ChecklistRun.submitted_by_user),
            selectinload(ChecklistRun.template).selectinload(ChecklistTemplate.sections).selectinload(ChecklistSection.items),
        )
    )
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    if run.status == "submitted":
        raise HTTPException(status_code=400, detail="Checklist already submitted")

    template = run.template
    total, completed = _count_completions(run, _checkbox_items(template, run.run_date))
    if completed < total:
        raise HTTPException(
            status_code=400,
            detail=f"All checklist items must be completed before submitting ({completed}/{total})",
        )

    now = datetime.now(timezone.utc)
    run.status = "submitted"
    run.submitted_by_staff_id = staff.id if staff else None
    run.submitted_by_user_id = user.id
    run.submitted_at = now
    run.updated_at = now
    await db.commit()
    await db.refresh(run, ["completions", "notes", "submitted_by", "submitted_by_user", "template"])
    return _serialize_run(run, template, can_edit=False)


@router.get("/runs", response_model=List[ChecklistRunSummary])
async def list_runs(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    type: Optional[str] = Query(None, pattern="^(opening|closing)$"),
    staff_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    q = (
        select(ChecklistRun)
        .options(
            selectinload(ChecklistRun.completions),
            selectinload(ChecklistRun.submitted_by),
            selectinload(ChecklistRun.submitted_by_user),
            selectinload(ChecklistRun.template).selectinload(ChecklistTemplate.sections).selectinload(ChecklistSection.items),
        )
        .order_by(ChecklistRun.run_date.desc(), ChecklistRun.created_at.desc())
    )
    if date_from:
        q = q.where(ChecklistRun.run_date >= date_from)
    if date_to:
        q = q.where(ChecklistRun.run_date <= date_to)
    if staff_id:
        q = q.where(ChecklistRun.submitted_by_staff_id == staff_id)
    if type:
        q = q.join(ChecklistTemplate).where(ChecklistTemplate.type == type)

    res = await db.execute(q)
    runs = res.scalars().unique().all()
    out: List[ChecklistRunSummary] = []
    for run in runs:
        template = run.template
        total, completed = _count_completions(run, _checkbox_items(template, run.run_date))
        out.append(
            ChecklistRunSummary(
                id=run.id,
                type=template.type,  # type: ignore[arg-type]
                run_date=run.run_date,
                status=run.status,  # type: ignore[arg-type]
                submitted_by_staff_id=run.submitted_by_staff_id,
                submitted_by_name=(
                    run.submitted_by.display_name
                    if run.submitted_by
                    else (
                        (((run.submitted_by_user.first_name or '') + ' ' + (run.submitted_by_user.last_name or '')).strip() or run.submitted_by_user.email)
                        if run.submitted_by_user
                        else None
                    )
                ),
                submitted_at=run.submitted_at,
                total_items=total,
                completed_items=completed,
            )
        )
    return out


@router.get("/runs/{run_id}", response_model=ChecklistRunRead)
async def get_run_detail(
    run_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(
        select(ChecklistRun)
        .where(ChecklistRun.id == run_id)
        .options(
            selectinload(ChecklistRun.completions),
            selectinload(ChecklistRun.notes),
            selectinload(ChecklistRun.submitted_by),
            selectinload(ChecklistRun.submitted_by_user),
            selectinload(ChecklistRun.template).selectinload(ChecklistTemplate.sections).selectinload(ChecklistSection.items),
        )
    )
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    return _serialize_run(run, run.template, can_edit=False)


@router.post("/runs/{run_id}/reopen", response_model=ChecklistRunRead)
async def reopen_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(
        select(ChecklistRun)
        .where(ChecklistRun.id == run_id)
        .options(
            selectinload(ChecklistRun.completions),
            selectinload(ChecklistRun.notes),
            selectinload(ChecklistRun.submitted_by),
            selectinload(ChecklistRun.submitted_by_user),
            selectinload(ChecklistRun.template).selectinload(ChecklistTemplate.sections).selectinload(ChecklistSection.items),
        )
    )
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Checklist run not found")

    run.status = "in_progress"
    run.submitted_by_staff_id = None
    run.submitted_at = None
    run.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run, ["completions", "notes", "submitted_by", "submitted_by_user", "template"])
    return _serialize_run(run, run.template, can_edit=True)
