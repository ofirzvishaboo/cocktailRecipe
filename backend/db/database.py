from collections.abc import AsyncGenerator
import uuid
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

DATABASE_URL = "postgresql://user:password@localhost/cocktaildb"

class Base(DeclarativeBase):
    pass

class CocktailIngredient(Base):
    """Association object for many-to-many relationship between CocktailRecipe and Ingredient
    Stores the ml amount for each ingredient in each recipe"""
    __tablename__ = "cocktail_ingredients"

    cocktail_id = Column(UUID(as_uuid=True), ForeignKey('cocktail_recipes.id', ondelete='CASCADE'), primary_key=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='CASCADE'), primary_key=True)
    ml = Column(Integer, nullable=False)  # ml amount specific to this recipe

    # Relationships to access the related objects
    cocktail = relationship("CocktailRecipe", back_populates="cocktail_ingredients")
    ingredient = relationship("Ingredient", back_populates="cocktail_ingredients")


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


class CocktailRecipe(Base):
    """CocktailRecipe model - recipes with unique id, name, and ingredients with ml amounts"""
    __tablename__ = "cocktail_recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)

    # Relationship through association object to access ingredients with ml amounts
    cocktail_ingredients = relationship(
        "CocktailIngredient",
        back_populates="cocktail",
        cascade="all, delete-orphan"
    )

    # Property to easily access ingredients list
    @property
    def ingredients(self):
        """Get list of ingredients with their ml amounts for this recipe"""
        return [
            {"id": ci.ingredient.id, "name": ci.ingredient.name, "ml": ci.ml}
            for ci in self.cocktail_ingredients
        ]

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session