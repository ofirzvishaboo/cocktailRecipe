import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base
from .users import User
from sqlalchemy import ForeignKey

class CocktailRecipe(Base):
    """CocktailRecipe model - recipes with unique id, name, and ingredients with ml amounts"""
    __tablename__ = "cocktail_recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    image_url = Column(String, nullable=True)  # ImageKit URL

    # Relationship through association object to access ingredients with ml amounts
    cocktail_ingredients = relationship(
        "CocktailIngredient",
        back_populates="cocktail",
        cascade="all, delete-orphan"
    )

    user = relationship("User", back_populates="cocktail")

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
            "user_id": self.user_id,
            "user": user_data,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "image_url": self.image_url,
            "ingredients": [
                {"name": ci.ingredient.name, "ml": ci.ml}
                for ci in self.cocktail_ingredients
            ]
        }

