from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base


class CocktailRecipeModel(Base):
    __tablename__ = "cocktail_recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)

    ingredients = relationship(
        "IngredientModel",
        back_populates="cocktail",
        cascade="all, delete-orphan"
    )


class IngredientModel(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ml = Column(Integer, nullable=False)
    cocktail_id = Column(Integer, ForeignKey("cocktail_recipes.id", ondelete="CASCADE"), nullable=False)

    cocktail = relationship("CocktailRecipeModel", back_populates="ingredients")
