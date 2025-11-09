from typing import Dict
from core.models import CocktailRecipeModel
from schemas import CocktailRecipe, Ingredient


def model_to_schema(cocktail_model: CocktailRecipeModel) -> Dict:
    """Convert SQLAlchemy model to Pydantic schema dict"""
    return {
        "id": cocktail_model.id,
        "name": cocktail_model.name,
        "ingredients": [
            {"name": ing.name, "ml": ing.ml}
            for ing in cocktail_model.ingredients
        ]
    }


def schema_to_model_data(cocktail_schema: CocktailRecipe) -> Dict:
    """Convert Pydantic schema to dict for model creation"""
    return {
        "name": cocktail_schema.name,
        "ingredients": [
            {"name": ing.name, "ml": ing.ml}
            for ing in cocktail_schema.ingredients
        ]
    }

