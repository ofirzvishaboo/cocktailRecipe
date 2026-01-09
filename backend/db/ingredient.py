import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Ingredient(Base):
    """Ingredient model - reusable ingredients with unique id and name"""
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)  # Unique ingredient names

    # Relationship through association object
    cocktail_ingredients = relationship(
        "CocktailIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan"
    )

    brands = relationship(
        "IngredientBrand",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )

    # Property to convert model to schema dictionary
    @property
    def to_schema(self):
        """Convert Ingredient model to schema dictionary format"""
        return {
            "id": self.id,
            "name": self.name
        }

