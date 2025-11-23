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
    ingredients: List[Ingredient]

class CocktailRecipeCreate(BaseModel):
    name: str
    ingredients: List[CocktailIngredientInput]

class CocktailRecipeUpdate(BaseModel):
    name: str
    ingredients: List[CocktailIngredientInput]

class CocktailRecipeDelete(BaseModel):
    id: UUID
