from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict

from db.database import get_async_session, GlassType as GlassTypeModel
from schemas.ingredient import GlassTypeUpdate
from core.auth import current_active_superuser
from db.users import User
from uuid import UUID

router = APIRouter()


@router.get("/", response_model=List[Dict])
async def list_glass_types(db: AsyncSession = Depends(get_async_session)):
    """List all glass types."""
    result = await db.execute(select(GlassTypeModel).order_by(GlassTypeModel.name))
    items = result.scalars().all()
    return [{"id": g.id, "name": g.name, "name_he": getattr(g, "name_he", None), "capacity_ml": g.capacity_ml} for g in items]


@router.put("/{glass_type_id}", response_model=Dict)
async def update_glass_type(
    glass_type_id: UUID,
    payload: GlassTypeUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    """Update a glass type (superuser only)."""
    # ensure it exists
    res = await db.execute(select(GlassTypeModel).where(GlassTypeModel.id == glass_type_id))
    g = res.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glass type not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        g.name = data["name"]
    if "name_he" in data:
        g.name_he = data["name_he"]
    if "capacity_ml" in data:
        g.capacity_ml = data["capacity_ml"]

    await db.commit()
    await db.refresh(g)
    return {"id": g.id, "name": g.name, "name_he": getattr(g, "name_he", None), "capacity_ml": g.capacity_ml}

