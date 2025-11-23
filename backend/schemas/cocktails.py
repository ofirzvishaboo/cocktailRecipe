from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from .ingredient import Ingredient, IngredientUpdate

# Schema for ingredient with ml amount in a cocktail recipe
class CocktailIngredientInput(BaseModel):
    name: str
    ml: int

class CocktailRecipe(BaseModel):
    id: UUID
    name: str
    created_at: Optional[datetime] = None
    image_url: Optional[str] = None
    ingredients: List[Ingredient]

class CocktailRecipeCreate(BaseModel):
    name: str
    ingredients: List[CocktailIngredientInput]
    image_url: Optional[str] = None  # Base64 encoded image or URL

class CocktailRecipeUpdate(BaseModel):
    name: str
    ingredients: List[CocktailIngredientInput]
    image_url: Optional[str] = None  # Base64 encoded image or URL

class CocktailRecipeDelete(BaseModel):
    id: UUID
