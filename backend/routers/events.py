from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import date

from core.auth import current_active_superuser
from db.database import (
    get_async_session,
    Event as EventModel,
    EventMenuItem as EventMenuItemModel,
    CocktailRecipe as CocktailRecipeModel,
    Order as OrderModel,
)
from schemas.events import EventRead, EventCreate, EventUpdate, EventMenuItemRead
from schemas.orders import WeeklyOrderRequest
from routers.orders import generate_weekly_orders_by_event
from db.users import User

router = APIRouter()


def _serialize_event(e: EventModel) -> EventRead:
    items = []
    for mi in (e.menu_items or []):
        c = getattr(mi, "cocktail", None)
        items.append(
            EventMenuItemRead(
                id=mi.id,
                cocktail_recipe_id=mi.cocktail_recipe_id,
                cocktail_name=getattr(c, "name", None) if c else None,
                cocktail_name_he=getattr(c, "name_he", None) if c else None,
            )
        )
    return EventRead(
        id=e.id,
        name=e.name,
        notes=e.notes,
        event_date=e.event_date,
        people=int(e.people),
        servings_per_person=float(e.servings_per_person or 0),
        menu_items=items,
    )


async def _resolve_cocktails_by_names(db: AsyncSession, names: List[str]) -> tuple[List[CocktailRecipeModel], List[str]]:
    names_in = [(n or "").strip() for n in names]
    names_lower = [n.lower() for n in names_in if n]
    unique_lower = sorted(set(names_lower))

    stmt = select(CocktailRecipeModel).where(
        or_(
            func.lower(CocktailRecipeModel.name).in_(unique_lower),
            func.lower(CocktailRecipeModel.name_he).in_(unique_lower),
        )
    )
    res = await db.execute(stmt)
    found = res.scalars().all() or []

    by_lower: dict[str, CocktailRecipeModel] = {}
    for c in found:
        en = (getattr(c, "name", "") or "").strip().lower()
        he = (getattr(c, "name_he", "") or "").strip().lower()
        if en:
            by_lower.setdefault(en, c)
        if he:
            by_lower.setdefault(he, c)

    missing: List[str] = []
    selected: List[CocktailRecipeModel] = []
    for raw in names_in:
        key = (raw or "").strip().lower()
        c = by_lower.get(key)
        if not c:
            missing.append(raw)
            continue
        selected.append(c)
    return selected, missing


@router.get("/", response_model=List[EventRead])
async def list_events(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    stmt = select(EventModel).options(selectinload(EventModel.menu_items).selectinload(EventMenuItemModel.cocktail))
    if from_date:
        stmt = stmt.where(EventModel.event_date >= from_date)
    if to_date:
        stmt = stmt.where(EventModel.event_date <= to_date)
    stmt = stmt.order_by(EventModel.event_date.asc())
    res = await db.execute(stmt)
    events = res.scalars().all() or []
    return [_serialize_event(e) for e in events]


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(
        select(EventModel)
        .options(selectinload(EventModel.menu_items).selectinload(EventMenuItemModel.cocktail))
        .where(EventModel.id == event_id)
    )
    e = res.scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return _serialize_event(e)


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    cocktails, missing = await _resolve_cocktails_by_names(db, payload.cocktail_names)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown cocktails: {', '.join(missing)}")
    if len(cocktails) != 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exactly 4 cocktails are required")

    e = EventModel(
        name=payload.name,
        notes=payload.notes,
        event_date=payload.event_date,
        people=int(payload.people),
        servings_per_person=float(payload.servings_per_person),
        created_by_user_id=user.id,
    )
    db.add(e)
    await db.flush()

    for c in cocktails:
        db.add(EventMenuItemModel(event_id=e.id, cocktail_recipe_id=c.id))

    await db.commit()

    res = await db.execute(
        select(EventModel)
        .options(selectinload(EventModel.menu_items).selectinload(EventMenuItemModel.cocktail))
        .where(EventModel.id == e.id)
    )
    e2 = res.scalar_one()
    return _serialize_event(e2)


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(EventModel).where(EventModel.id == event_id))
    e = res.scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        e.name = data["name"]
    if "notes" in data:
        e.notes = data["notes"]
    if "event_date" in data and data["event_date"] is not None:
        e.event_date = data["event_date"]
    if "people" in data and data["people"] is not None:
        e.people = int(data["people"])
    if "servings_per_person" in data and data["servings_per_person"] is not None:
        e.servings_per_person = float(data["servings_per_person"])

    if "cocktail_names" in data and data["cocktail_names"] is not None:
        cocktails, missing = await _resolve_cocktails_by_names(db, data["cocktail_names"])
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown cocktails: {', '.join(missing)}")
        if len(cocktails) != 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exactly 4 cocktails are required")

        # replace menu items
        existing = await db.execute(select(EventMenuItemModel).where(EventMenuItemModel.event_id == event_id))
        for mi in existing.scalars().all():
            await db.delete(mi)
        await db.flush()
        for c in cocktails:
            db.add(EventMenuItemModel(event_id=e.id, cocktail_recipe_id=c.id))

    await db.commit()
    res2 = await db.execute(
        select(EventModel)
        .options(selectinload(EventModel.menu_items).selectinload(EventMenuItemModel.cocktail))
        .where(EventModel.id == event_id)
    )
    e2 = res2.scalar_one()
    return _serialize_event(e2)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(EventModel).where(EventModel.id == event_id))
    e = res.scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # If weekly summary orders exist for this event's date, regenerate them after deletion
    # so the deleted event no longer contributes to totals.
    affected_week_starts_res = await db.execute(
        select(OrderModel.period_start)
        .where(OrderModel.scope == "WEEKLY")
        .where(OrderModel.status == "DRAFT")
        .where(OrderModel.period_start <= e.event_date)
        .where(OrderModel.period_end >= e.event_date)
        .distinct()
    )
    affected_week_starts = [r[0] for r in (affected_week_starts_res.fetchall() or [])]

    # Delete EVENT-scoped orders for this event (otherwise they become orphaned with event_id=NULL).
    event_orders_res = await db.execute(
        select(OrderModel).where(OrderModel.scope == "EVENT").where(OrderModel.event_id == event_id)
    )
    for o in (event_orders_res.scalars().all() or []):
        await db.delete(o)

    await db.delete(e)
    await db.commit()

    # Recompute weekly totals for any affected windows (idempotent; updates existing DRAFT orders).
    for ws in affected_week_starts:
        await generate_weekly_orders_by_event(
            payload=WeeklyOrderRequest(order_date=ws, location_scope="ALL"),
            db=db,
            user=user,
        )
    return None

