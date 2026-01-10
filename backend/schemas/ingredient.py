from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date

class Ingredient(BaseModel):
    name: str

class IngredientRead(BaseModel):
    id: UUID
    name: str
    brand_id: Optional[UUID] = None
    kind_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    abv_percent: Optional[float] = None
    notes: Optional[str] = None

class IngredientCreate(BaseModel):
    name: str
    brand_id: Optional[UUID] = None
    kind_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    abv_percent: Optional[float] = None
    notes: Optional[str] = None

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    brand_id: Optional[UUID] = None
    kind_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    abv_percent: Optional[float] = None
    notes: Optional[str] = None

class IngredientDelete(BaseModel):
    name: str


class IngredientBrandRead(BaseModel):
    id: UUID
    ingredient_id: UUID
    brand_name: str
    bottle_size_ml: int
    bottle_price: float


class IngredientBrandCreate(BaseModel):
    brand_name: str
    bottle_size_ml: int
    bottle_price: float


class IngredientBrandUpdate(BaseModel):
    brand_name: Optional[str] = None
    bottle_size_ml: Optional[int] = None
    bottle_price: Optional[float] = None


# Normalized reference DTOs
class BrandRead(BaseModel):
    id: UUID
    name: str


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
    capacity_ml: Optional[int] = None


class BottleRead(BaseModel):
    id: UUID
    ingredient_id: UUID
    name: str
    volume_ml: int
    importer_id: Optional[UUID] = None
    description: Optional[str] = None
    is_default_cost: bool


class BottleCreate(BaseModel):
    name: str
    volume_ml: int
    importer_id: Optional[UUID] = None
    description: Optional[str] = None
    is_default_cost: bool = False


class BottleUpdate(BaseModel):
    name: Optional[str] = None
    volume_ml: Optional[int] = None
    importer_id: Optional[UUID] = None
    description: Optional[str] = None
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