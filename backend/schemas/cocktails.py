from pydantic import BaseModel
from typing import List
from . import Ingredient, IngredientCreate, IngredientUpdate, IngredientDelete

class CocktailRecipe(BaseModel):
    name: str
    ingredients: List[Ingredient]

class CocktailRecipeCreate(BaseModel):
    name: str
    ingredients: List[IngredientCreate]

class CocktailRecipeUpdate(BaseModel):
    name: str
    ingredients: List[IngredientUpdate]

class CocktailRecipeDelete(BaseModel):
    id: int
