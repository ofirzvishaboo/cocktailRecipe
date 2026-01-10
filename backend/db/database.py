from collections.abc import AsyncGenerator
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from fastapi_users.db import SQLAlchemyUserDatabase
from uuid import UUID

load_dotenv()

DATABASE_USER = os.getenv("DATABASE_USER", "user")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "cocktaildb")

# URL encode username and password to handle special characters
encoded_user = quote_plus(DATABASE_USER)
encoded_password = quote_plus(DATABASE_PASSWORD)

DATABASE_URL = f"postgresql+asyncpg://{encoded_user}:{encoded_password}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

class Base(DeclarativeBase):
    pass

# Import all models to ensure they're registered with Base.metadata
# This must be done after Base is defined to avoid circular imports
from . import (
    ingredient,
    cocktail_recipe,
    users,
    brand,
    kind,
    subcategory,
    glass_type,
    importer,
    bottle,
    bottle_price,
    recipe_ingredient,
)

from .ingredient import Ingredient
from .cocktail_recipe import CocktailRecipe
from .users import User

from .brand import Brand
from .kind import Kind
from .subcategory import Subcategory
from .glass_type import GlassType
from .importer import Importer
from .bottle import Bottle
from .bottle_price import BottlePrice
from .recipe_ingredient import RecipeIngredient

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run migrations
    from .migrations import (
        add_missing_user_columns,
        add_user_id_column_if_missing,
        add_normalized_schema_tables_if_missing,
        add_normalized_columns_if_missing,
        drop_legacy_tables_if_exist,
    )
    await add_missing_user_columns(engine)
    await add_user_id_column_if_missing(engine)
    await add_normalized_schema_tables_if_missing(engine)
    await add_normalized_columns_if_missing(engine)
    await drop_legacy_tables_if_exist(engine)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_user_db(session: AsyncSession = Depends(get_async_session)) -> SQLAlchemyUserDatabase[User, UUID]:
    yield SQLAlchemyUserDatabase(session, User)