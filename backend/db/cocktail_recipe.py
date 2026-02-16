import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from .database import Base

class CocktailRecipe(Base):
    """CocktailRecipe model - recipes with unique id, name, and ingredients with ml amounts"""
    __tablename__ = "cocktail_recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Stored in DB as 'user_id' (existing column), but semantically it's created_by_user_id
    created_by_user_id = Column("user_id", UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    name_he = Column(String, nullable=True)
    description = Column(Text, nullable=True)  # Optional description
    description_he = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    glass_type_id = Column(UUID(as_uuid=True), ForeignKey("glass_types.id", ondelete="SET NULL"), nullable=True)
    picture_url = Column(String, nullable=True)  # replaces image_url
    garnish_text = Column(Text, nullable=True)
    garnish_text_he = Column(Text, nullable=True)
    base_recipe_id = Column(UUID(as_uuid=True), ForeignKey("cocktail_recipes.id", ondelete="SET NULL"), nullable=True)
    is_base = Column(Boolean, nullable=False, default=False)  # legacy; prefer menus
    menus = Column(ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]"))  # e.g. ['classic', 'signature', 'seasonal']
    preparation_method = Column(Text, nullable=True)
    preparation_method_he = Column(Text, nullable=True)
    batch_type = Column(String, nullable=True)  # 'base' or 'batch'

    recipe_ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan"
    )

    user = relationship("User", back_populates="cocktails", foreign_keys=[created_by_user_id])
    glass_type = relationship("GlassType", back_populates="recipes")
    base_recipe = relationship("CocktailRecipe", remote_side=[id])

    # Property to convert model to schema dictionary
    @property
    def to_schema(self):
        """Convert CocktailRecipe model to schema dictionary format"""
        user_data = None
        if self.user:
            user_data = {
                "id": self.user.id,
                "email": self.user.email
            }

        return {
            "id": self.id,
            "created_by_user_id": self.created_by_user_id,
            "user": user_data,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "glass_type_id": self.glass_type_id,
            "glass_type_name": self.glass_type.name if self.glass_type else None,
            "glass_type_name_he": self.glass_type.name_he if self.glass_type else None,
            "picture_url": self.picture_url,
            "garnish_text": self.garnish_text,
            "garnish_text_he": self.garnish_text_he,
            "base_recipe_id": self.base_recipe_id,
            "is_base": self.is_base,
            "menus": list(self.menus) if self.menus else [],
            "preparation_method": self.preparation_method,
            "batch_type": self.batch_type,
            "recipe_ingredients": [
                {
                    "id": ri.id,
                    "ingredient_id": ri.ingredient_id,
                    "quantity": float(ri.quantity),
                    "unit": ri.unit,
                    "bottle_id": ri.bottle_id,
                    "is_garnish": ri.is_garnish,
                    "is_optional": ri.is_optional,
                    "sort_order": ri.sort_order,
                }
                for ri in (self.recipe_ingredients or [])
            ],
        }

        def schema_no_juice(self):
            return {
            "id": self.id,
            "created_by_user_id": self.created_by_user_id,
            "user": user_data,
            "name": self.name,
            "name_he": self.name_he,
            "description": self.description,
            "description_he": self.description_he,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "glass_type_id": self.glass_type_id,
            "picture_url": self.picture_url,
            "garnish_text": self.garnish_text,
            "garnish_text_he": self.garnish_text_he,
            "base_recipe_id": self.base_recipe_id,
            "is_base": self.is_base,
            "menus": list(self.menus) if self.menus else [],
            "preparation_method": self.preparation_method,
            "preparation_method_he": self.preparation_method_he,
            "batch_type": self.batch_type,
            "recipe_ingredients": [
                {
                    "id": ri.id,
                    "ingredient_id": ri.ingredient_id,
                    "ingredient_name": ri.ingredient.name if ri.ingredient else None,
                    "ingredient_name_he": ri.ingredient.name_he if ri.ingredient else None,
                    "quantity": float(ri.quantity),
                    "unit": ri.unit,
                    "bottle_id": ri.bottle_id,
                    "is_garnish": ri.is_garnish,
                    "is_optional": ri.is_optional,
                    "sort_order": ri.sort_order,
                }
                for ri in (self.recipe_ingredients or [])
                if ri.ingredient and ri.ingredient.subcategory
                and ri.ingredient.subcategory.name.lower() != 'juice'
            ],
        }