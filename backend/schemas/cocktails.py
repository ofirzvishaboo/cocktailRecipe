from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from .ingredient import Ingredient, IngredientUpdate

# Schema for ingredient with ml amount in a cocktail recipe
class CocktailIngredientInput(BaseModel):
    name: str
    ml: int
    ingredient_brand_id: Optional[UUID] = None

# User info for cocktail responses
class CocktailUser(BaseModel):
    id: UUID
    email: EmailStr

    class Config:
        from_attributes = True

class CocktailRecipe(BaseModel):
    id: UUID
    user_id: UUID  # ID of the user who created this cocktail
    user: CocktailUser  # User information (name/email)
    name: str
    description: Optional[str] = None  # Optional description
    created_at: Optional[datetime] = None
    image_url: Optional[str] = None
    ingredients: List[Ingredient]

    class Config:
        from_attributes = True

class CocktailRecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None  # Optional description
    ingredients: List[CocktailIngredientInput]
    image_url: Optional[str] = None  # ImageKit URL

class CocktailRecipeUpdate(BaseModel):
    name: str
    description: Optional[str] = None  # Optional description
    ingredients: List[CocktailIngredientInput]
    image_url: Optional[str] = None  # ImageKit URL

class CocktailRecipeDelete(BaseModel):
    id: UUID


class CocktailIngredientCostLine(BaseModel):
    ingredient_name: str
    ml: float
    scaled_ml: float
    ingredient_brand_id: Optional[UUID] = None
    brand_name: Optional[str] = None
    bottle_size_ml: Optional[int] = None
    bottle_price: Optional[float] = None
    cost_per_ml: float
    ingredient_cost: float


class CocktailCostResponse(BaseModel):
    lines: List[CocktailIngredientCostLine]
    total_cocktail_cost: float
    scaled_total_cost: float
    scale_factor: float
