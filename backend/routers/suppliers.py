from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from core.auth import current_active_superuser
from db.database import get_async_session, Supplier as SupplierModel
from schemas.suppliers import SupplierRead, SupplierCreate, SupplierUpdate
from db.users import User

router = APIRouter()


@router.get("/", response_model=List[SupplierRead])
async def list_suppliers(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(SupplierModel).order_by(func.lower(SupplierModel.name).asc()))
    items = res.scalars().all()
    return [SupplierRead(**s.to_schema) for s in items]


@router.post("/", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")

    existing = await db.execute(select(SupplierModel).where(func.lower(SupplierModel.name) == name.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Supplier already exists")

    m = SupplierModel(name=name, contact=payload.contact, notes=payload.notes)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return SupplierRead(**m.to_schema)


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_superuser),
):
    res = await db.execute(select(SupplierModel).where(SupplierModel.id == supplier_id))
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        m.name = data["name"].strip()
    if "contact" in data:
        m.contact = data["contact"]
    if "notes" in data:
        m.notes = data["notes"]

    await db.commit()
    await db.refresh(m)
    return SupplierRead(**m.to_schema)

