from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class CocktailIngredient(Base):
    """Association object for many-to-many relationship between CocktailRecipe and Ingredient
    Stores the ml amount for each ingredient in each recipe"""
    __tablename__ = "cocktail_ingredients"

    cocktail_id = Column(UUID(as_uuid=True), ForeignKey('cocktail_recipes.id', ondelete='CASCADE'), primary_key=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), primary_key=True)
    ml = Column(Integer, nullable=False)  # ml amount specific to this recipe
    ingredient_brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingredient_brands.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships to access the related objects
    cocktail = relationship("CocktailRecipe")
    ingredient = relationship("Ingredient")
    ingredient_brand = relationship("IngredientBrand")

