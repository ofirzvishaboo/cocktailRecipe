from pydantic import BaseModel
from typing import List
from uuid import UUID
from .ingredient import Ingredient, IngredientCreate, IngredientUpdate

class CocktailRecipe(BaseModel):
    id: UUID
    name: str
    ingredients: List[Ingredient]

class CocktailRecipeCreate(BaseModel):
    name: str
    ingredients: List[IngredientCreate]

class CocktailRecipeUpdate(BaseModel):
    name: str
    ingredients: List[IngredientUpdate]

class CocktailRecipeDelete(BaseModel):
    id: UUID
