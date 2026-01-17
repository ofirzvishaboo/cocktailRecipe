from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from .ingredient import Ingredient, IngredientUpdate

class RecipeIngredientInput(BaseModel):
    ingredient_id: UUID
    quantity: float
    unit: str
    bottle_id: Optional[UUID] = None
    is_garnish: bool = False
    is_optional: bool = False
    sort_order: Optional[int] = None

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if not v:
            raise ValueError("unit is required")
        return v

# User info for cocktail responses
class CocktailUser(BaseModel):
    id: UUID
    email: EmailStr

    class Config:
        from_attributes = True

class CocktailRecipe(BaseModel):
    id: UUID
    created_by_user_id: UUID  # ID of the user who created this cocktail
    user: CocktailUser  # User information (name/email)
    name: str
    name_he: Optional[str] = None
    description: Optional[str] = None  # Optional description
    description_he: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    glass_type_id: Optional[UUID] = None
    picture_url: Optional[str] = None
    garnish_text: Optional[str] = None
    garnish_text_he: Optional[str] = None
    base_recipe_id: Optional[UUID] = None
    is_base: bool = False
    preparation_method: Optional[str] = None
    preparation_method_he: Optional[str] = None
    batch_type: Optional[str] = None  # 'base' or 'batch'
    ingredients: List[Ingredient]
    recipe_ingredients: Optional[List[RecipeIngredientInput]] = None

    class Config:
        from_attributes = True

class CocktailRecipeCreate(BaseModel):
    name: str
    name_he: Optional[str] = None
    description: Optional[str] = None  # Optional description
    description_he: Optional[str] = None
    recipe_ingredients: List[RecipeIngredientInput]
    picture_url: Optional[str] = None
    garnish_text: Optional[str] = None
    garnish_text_he: Optional[str] = None
    glass_type_id: Optional[UUID] = None
    base_recipe_id: Optional[UUID] = None
    is_base: bool = False
    preparation_method: Optional[str] = None
    preparation_method_he: Optional[str] = None
    batch_type: Optional[str] = None  # 'base' or 'batch'

class CocktailRecipeUpdate(BaseModel):
    name: str
    name_he: Optional[str] = None
    description: Optional[str] = None  # Optional description
    description_he: Optional[str] = None
    recipe_ingredients: List[RecipeIngredientInput]
    picture_url: Optional[str] = None
    garnish_text: Optional[str] = None
    garnish_text_he: Optional[str] = None
    glass_type_id: Optional[UUID] = None
    base_recipe_id: Optional[UUID] = None
    is_base: bool = False
    preparation_method: Optional[str] = None
    preparation_method_he: Optional[str] = None
    batch_type: Optional[str] = None  # 'base' or 'batch'

class CocktailRecipeDelete(BaseModel):
    id: UUID


class CocktailIngredientCostLine(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    scaled_quantity: float
    bottle_id: Optional[UUID] = None
    bottle_name: Optional[str] = None
    bottle_volume_ml: Optional[int] = None
    price_minor: Optional[int] = None
    currency: Optional[str] = None
    cost_per_ml: float
    ingredient_cost: float


class CocktailCostResponse(BaseModel):
    lines: List[CocktailIngredientCostLine]
    total_cocktail_cost: float
    scaled_total_cost: float
    scale_factor: float
