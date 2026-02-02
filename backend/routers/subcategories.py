from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional
from uuid import UUID

from db.database import get_async_session, Subcategory as SubcategoryModel

router = APIRouter()


@router.get("/", response_model=List[Dict])
async def list_subcategories(
    kind_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    stmt = select(SubcategoryModel)
    if kind_id:
        stmt = stmt.where(SubcategoryModel.kind_id == kind_id)
    stmt = stmt.order_by(func.lower(SubcategoryModel.name).asc())
    res = await db.execute(stmt)
    subs = res.scalars().all()
    return [{"id": s.id, "kind_id": s.kind_id, "name": s.name, "name_he": getattr(s, "name_he", None)} for s in subs]

