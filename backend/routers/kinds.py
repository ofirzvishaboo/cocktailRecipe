from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List

from db.database import get_async_session, Kind as KindModel

router = APIRouter()


@router.get("/", response_model=List[Dict])
async def list_kinds(db: AsyncSession = Depends(get_async_session)):
    res = await db.execute(select(KindModel).order_by(func.lower(KindModel.name).asc()))
    kinds = res.scalars().all()
    return [{"id": k.id, "name": k.name} for k in kinds]

