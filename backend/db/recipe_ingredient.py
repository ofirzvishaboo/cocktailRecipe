import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("cocktail_recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String, nullable=False)  # 'ml', 'oz', etc.

    # Per-recipe bottle override for costing
    bottle_id = Column(UUID(as_uuid=True), ForeignKey("bottles.id", ondelete="SET NULL"), nullable=True, index=True)

    is_garnish = Column(Boolean, nullable=False, default=False)
    is_optional = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=True)

    recipe = relationship("CocktailRecipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient")
    bottle = relationship("Bottle")

