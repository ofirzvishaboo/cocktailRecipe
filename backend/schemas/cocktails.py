from pydantic import BaseModel
from typing import List
from uuid import UUID
from .ingredient import Ingredient, IngredientUpdate

# Schema for ingredient with ml amount in a cocktail recipe
class CocktailIngredientInput(BaseModel):
    name: str
    ml: int

class CocktailRecipe(BaseModel):
    id: UUID
    name: str
    ingredients: List[Ingredient]

class CocktailRecipeCreate(BaseModel):
    name: str
    ingredients: List[CocktailIngredientInput]

class CocktailRecipeUpdate(BaseModel):
    name: str
    ingredients: List[CocktailIngredientInput]

class CocktailRecipeDelete(BaseModel):
    id: UUID
