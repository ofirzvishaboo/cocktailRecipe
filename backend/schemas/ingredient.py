from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date

class Ingredient(BaseModel):
    name: str

class IngredientRead(BaseModel):
    id: UUID
    name: str
    name_he: Optional[str] = None
    brand_id: Optional[UUID] = None
    kind_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    abv_percent: Optional[float] = None
    notes: Optional[str] = None
    supplier_ids: Optional[List[UUID]] = None
    default_supplier_id: Optional[UUID] = None

class IngredientCreate(BaseModel):
    name: str
    name_he: Optional[str] = None
    brand_id: Optional[UUID] = None
    kind_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    abv_percent: Optional[float] = None
    notes: Optional[str] = None
    supplier_ids: Optional[List[UUID]] = None
    default_supplier_id: Optional[UUID] = None

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    name_he: Optional[str] = None
    brand_id: Optional[UUID] = None
    kind_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    abv_percent: Optional[float] = None
    notes: Optional[str] = None
    supplier_ids: Optional[List[UUID]] = None
    default_supplier_id: Optional[UUID] = None

class IngredientDelete(BaseModel):
    name: str


# Normalized reference DTOs
class BrandRead(BaseModel):
    id: UUID
    name: str
    name_he: Optional[str] = None


class KindRead(BaseModel):
    id: UUID
    name: str


class SubcategoryRead(BaseModel):
    id: UUID
    kind_id: UUID
    name: str


class ImporterRead(BaseModel):
    id: UUID
    name: str


class GlassTypeRead(BaseModel):
    id: UUID
    name: str
    name_he: Optional[str] = None
    capacity_ml: Optional[int] = None


class GlassTypeUpdate(BaseModel):
    name: Optional[str] = None
    name_he: Optional[str] = None
    capacity_ml: Optional[int] = None


class BottleRead(BaseModel):
    id: UUID
    ingredient_id: UUID
    name: str
    name_he: Optional[str] = None
    volume_ml: int
    importer_id: Optional[UUID] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    is_default_cost: bool


class BottleCreate(BaseModel):
    name: str
    name_he: Optional[str] = None
    volume_ml: int
    importer_id: Optional[UUID] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    is_default_cost: bool = False


class BottleUpdate(BaseModel):
    name: Optional[str] = None
    name_he: Optional[str] = None
    volume_ml: Optional[int] = None
    importer_id: Optional[UUID] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    is_default_cost: Optional[bool] = None


class BottlePriceRead(BaseModel):
    id: UUID
    bottle_id: UUID
    price_minor: int
    currency: str
    start_date: date
    end_date: Optional[date] = None
    source: Optional[str] = None

    # Convenience for UI
    price: float


class BottlePriceCreate(BaseModel):
    price: float
    currency: str = "ILS"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source: Optional[str] = None


class BottlePriceUpdate(BaseModel):
    price: Optional[float] = None
    currency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source: Optional[str] = None


class BottleWithCurrentPrice(BaseModel):
    bottle: BottleRead
    current_price: Optional[BottlePriceRead] = None