from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas import CocktailRecipe, Ingredient
from core.models import CocktailRecipeModel, IngredientModel
from core.converters import model_to_schema
from db.database import get_db
from typing import List, Dict


router = APIRouter()


@router.get("/cocktail-recipes", response_model=List[Dict])
def get_cocktail_recipes(db: Session = Depends(get_db)):
    cocktails = db.query(CocktailRecipeModel).all()
    return [model_to_schema(cocktail) for cocktail in cocktails]


@router.get("/cocktail-recipes/{cocktail_id}", response_model=CocktailRecipe)
def get_cocktail_recipe(cocktail_id: int, db: Session = Depends(get_db)):
    cocktail = db.query(CocktailRecipeModel).filter(CocktailRecipeModel.id == cocktail_id).first()
    if cocktail:
        return model_to_schema(cocktail)
    return {"error": "Cocktail not found"}


@router.post("/cocktail-recipes/{cocktail_id}", response_model=CocktailRecipe)
def post_cocktail_recipe(cocktail: CocktailRecipe, db: Session = Depends(get_db)):
    cocktail_model = CocktailRecipeModel(name=cocktail.name, ingredients=[IngredientModel(name=ingredient.name, ml=ingredient.ml) for ingredient in cocktail.ingredients])
    db.add(cocktail_model)
    db.commit()
    db.refresh(cocktail_model)
    return model_to_schema(cocktail_model)


@router.put("/cocktail-recipes/{cocktail_id}", response_model=CocktailRecipe)
def update_cocktail_recipe(cocktail: CocktailRecipe, cocktail_id: int):
    return cocktail


@router.delete("/cocktail-recipes/{cocktail_id}")
def delete_cocktail_recipe(cocktail_id: int):
    if cocktail_id in cocktail_memory:
        del cocktail_memory[cocktail_id]
        return {"message": "Cocktail deleted successfully"}
    return {"error": "Cocktail not found"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)