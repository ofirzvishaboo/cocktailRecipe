from pydantic import BaseModel
from typing import List
from . import Ingredient

class CocktailRecipe(BaseModel):
    name: str
    ingredients: List[Ingredient]