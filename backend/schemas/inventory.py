from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


InventoryLocation = Literal["BAR", "WAREHOUSE"]
InventoryItemType = Literal["BOTTLE", "GARNISH", "GLASS"]


class InventoryItemCreate(BaseModel):
    item_type: InventoryItemType
    bottle_id: Optional[UUID] = None
    ingredient_id: Optional[UUID] = None
    glass_type_id: Optional[UUID] = None

    name: str
    unit: str
    min_level: Optional[float] = None
    reorder_level: Optional[float] = None
    price: Optional[float] = None
    currency: Optional[str] = None

    @field_validator("name", "unit")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("field is required")
        return v

    @field_validator("currency")
    @classmethod
    def _currency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().upper()
        if not v:
            return None
        if len(v) != 3:
            raise ValueError("currency must be a 3-letter code (e.g. ILS)")
        return v

    @model_validator(mode="after")
    def _validate_backing_fk(self):
        # exactly one backing FK, depending on item_type
        if self.item_type == "BOTTLE":
            if not self.bottle_id or self.ingredient_id or self.glass_type_id:
                raise ValueError("BOTTLE requires bottle_id and no other backing ids")
        if self.item_type == "GARNISH":
            if not self.ingredient_id or self.bottle_id or self.glass_type_id:
                raise ValueError("GARNISH requires ingredient_id and no other backing ids")
        if self.item_type == "GLASS":
            if not self.glass_type_id or self.bottle_id or self.ingredient_id:
                raise ValueError("GLASS requires glass_type_id and no other backing ids")
        return self


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    is_active: Optional[bool] = None
    min_level: Optional[float] = None
    reorder_level: Optional[float] = None
    price: Optional[float] = None
    currency: Optional[str] = None

    @field_validator("name", "unit")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = (v or "").strip()
        if not v:
            raise ValueError("cannot be empty")
        return v

    @field_validator("currency")
    @classmethod
    def _currency_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().upper()
        if not v:
            return None
        if len(v) != 3:
            raise ValueError("currency must be a 3-letter code (e.g. ILS)")
        return v


class InventoryMovementCreate(BaseModel):
    location: InventoryLocation
    inventory_item_id: UUID
    change: float
    reason: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None

    @field_validator("reason", "source_type")
    @classmethod
    def _strip_nullable(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class ConsumeCocktailBatchRequest(BaseModel):
    liters: float
    location: InventoryLocation
    include_garnish: bool = False
    include_optional: bool = False
    reason: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None

    @field_validator("liters")
    @classmethod
    def _liters_positive(cls, v: float) -> float:
        try:
            v = float(v)
        except Exception:
            raise ValueError("liters must be a number")
        if v <= 0:
            raise ValueError("liters must be > 0")
        return v

    @field_validator("reason", "source_type")
    @classmethod
    def _strip_nullable2(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class InventoryItemOut(BaseModel):
    id: UUID
    item_type: InventoryItemType
    bottle_id: Optional[UUID] = None
    ingredient_id: Optional[UUID] = None
    glass_type_id: Optional[UUID] = None
    name: str
    unit: str
    is_active: bool
    min_level: Optional[float] = None
    reorder_level: Optional[float] = None
    price: Optional[float] = None
    currency: Optional[str] = None

    class Config:
        from_attributes = True


class InventoryStockOut(BaseModel):
    id: UUID
    location: InventoryLocation
    inventory_item_id: UUID
    quantity: float
    reserved_quantity: float


class InventoryMovementOut(BaseModel):
    id: UUID
    location: InventoryLocation
    inventory_item_id: UUID
    change: float
    reason: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    created_at: datetime
    created_by_user_id: Optional[UUID] = None

