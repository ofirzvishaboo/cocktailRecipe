from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class Ingredient(BaseModel):
    name: str

class IngredientRead(BaseModel):
    id: UUID
    name: str

class IngredientCreate(BaseModel):
    name: str

class IngredientUpdate(BaseModel):
    name: str

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