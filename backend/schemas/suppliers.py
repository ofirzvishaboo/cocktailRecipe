from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class SupplierRead(BaseModel):
    id: UUID
    name: str
    contact: Optional[str] = None
    notes: Optional[str] = None


class SupplierCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    notes: Optional[str] = None

