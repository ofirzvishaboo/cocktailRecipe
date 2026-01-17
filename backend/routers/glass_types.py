from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict

from db.database import get_async_session, GlassType as GlassTypeModel

router = APIRouter()


@router.get("/", response_model=List[Dict])
async def list_glass_types(db: AsyncSession = Depends(get_async_session)):
    """List all glass types."""
    result = await db.execute(select(GlassTypeModel).order_by(GlassTypeModel.name))
    items = result.scalars().all()
    return [{"id": g.id, "name": g.name, "name_he": getattr(g, "name_he", None), "capacity_ml": g.capacity_ml} for g in items]

