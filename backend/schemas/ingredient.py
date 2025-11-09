from pydantic import BaseModel

class Ingredient(BaseModel):
    name: str
    ml: int

class IngredientCreate(BaseModel):
    name: str
    ml: int

class IngredientUpdate(BaseModel):
    name: str
    ml: int

class IngredientDelete(BaseModel):
    name: str