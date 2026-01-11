from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List

from db.database import get_async_session, Brand as BrandModel

router = APIRouter()


@router.get("/", response_model=List[Dict])
async def list_brands(db: AsyncSession = Depends(get_async_session)):
    res = await db.execute(select(BrandModel).order_by(func.lower(BrandModel.name).asc()))
    brands = res.scalars().all()
    return [{"id": b.id, "name": b.name} for b in brands]


@router.get("/suggestions", response_model=List[str])
async def brand_suggestions(db: AsyncSession = Depends(get_async_session)):
    res = await db.execute(select(BrandModel.name).order_by(func.lower(BrandModel.name).asc()))
    names = [r[0] for r in res.all()]
    # defensive de-dupe
    seen = set()
    out: List[str] = []
    for n in names:
        if not n:
            continue
        key = n.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(n.strip())
    return out
