from pydantic import BaseModel

class Ingredient(BaseModel):
    name: str

class IngredientCreate(BaseModel):
    name: str

class IngredientUpdate(BaseModel):
    name: str

class IngredientDelete(BaseModel):
    name: str