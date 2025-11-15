from pydantic import BaseModel
from uuid import UUID

class CocktailIngredient(BaseModel):
    cocktail_id: UUID
    ingredient_id: UUID
    ml: int

class CocktailIngredientCreate(BaseModel):
    cocktail_id: UUID
    ingredient_id: UUID
    ml: int

class CocktailIngredientUpdate(BaseModel):
    cocktail_id: UUID | None = None
    ingredient_id: UUID | None = None
    ml: int | None = None

class CocktailIngredientDelete(BaseModel):
    cocktail_name: str
    ingredient_name: str

