import asyncio
import sys
from pathlib import Path
from decimal import Decimal

"""
Seed demo data (ingredients, brands, cocktails) into the Postgres DB.

This script can be run from either:
- backend/: `uv run python scripts/seed_demo_data.py`
- repo root: `uv run python backend/scripts/seed_demo_data.py`
"""

# Allow running from repo root by ensuring `backend/` is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select, delete

from db.database import async_session_maker
from db.users import User
from db.ingredient import Ingredient
from db.ingredient_brand import IngredientBrand
from db.cocktail_recipe import CocktailRecipe
from db.cocktail_ingredient import CocktailIngredient

from fastapi_users.password import PasswordHelper


password_helper = PasswordHelper()


async def get_or_create_user(session, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        email=email,
        hashed_password=password_helper.hash(password),
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_ingredient(session, name: str) -> Ingredient:
    result = await session.execute(
        select(Ingredient).where(func.lower(Ingredient.name) == name.strip().lower())
    )
    ingredient = result.scalar_one_or_none()
    if ingredient:
        return ingredient

    ingredient = Ingredient(name=name.strip())
    session.add(ingredient)
    await session.flush()
    return ingredient


async def get_or_create_brand(
    session,
    ingredient_id,
    brand_name: str,
    bottle_size_ml: int,
    bottle_price: Decimal,
) -> IngredientBrand:
    result = await session.execute(
        select(IngredientBrand).where(
            IngredientBrand.ingredient_id == ingredient_id,
            func.lower(IngredientBrand.brand_name) == brand_name.strip().lower(),
            IngredientBrand.bottle_size_ml == bottle_size_ml,
        )
    )
    brand = result.scalar_one_or_none()
    if brand:
        # Keep price up-to-date if you re-run seed with new values
        brand.bottle_price = bottle_price
        await session.flush()
        return brand

    brand = IngredientBrand(
        ingredient_id=ingredient_id,
        brand_name=brand_name.strip(),
        bottle_size_ml=bottle_size_ml,
        bottle_price=bottle_price,
    )
    session.add(brand)
    await session.flush()
    return brand


async def upsert_cocktail(
    session,
    user_id,
    name: str,
    description: str | None,
    ingredients: list[dict],
) -> CocktailRecipe:
    result = await session.execute(
        select(CocktailRecipe).where(
            CocktailRecipe.user_id == user_id,
            func.lower(CocktailRecipe.name) == name.strip().lower(),
        )
    )
    cocktail = result.scalar_one_or_none()
    if not cocktail:
        cocktail = CocktailRecipe(
            user_id=user_id,
            name=name.strip(),
            description=description,
            image_url=None,
        )
        session.add(cocktail)
        await session.flush()
    else:
        cocktail.name = name.strip()
        cocktail.description = description

        # Replace ingredient associations
        await session.execute(
            delete(CocktailIngredient).where(CocktailIngredient.cocktail_id == cocktail.id)
        )
        await session.flush()

    # Add ingredients
    for item in ingredients:
        ing = await get_or_create_ingredient(session, item["name"])
        brand_id = item.get("brand_id")
        session.add(
            CocktailIngredient(
                cocktail_id=cocktail.id,
                ingredient_id=ing.id,
                ml=int(item["ml"]),
                ingredient_brand_id=brand_id,
            )
        )

    await session.flush()
    return cocktail


async def seed():
    async with async_session_maker() as session:
        async with session.begin():
            user = await get_or_create_user(session, "admin@admin.com", "admin")

            # Ingredients + Brands (prices are example values)
            tequila = await get_or_create_ingredient(session, "tequila")
            tequila_cuervo = await get_or_create_brand(
                session, tequila.id, "Cuervo", 700, Decimal("100.00")
            )

            rum = await get_or_create_ingredient(session, "rum")
            rum_bacardi = await get_or_create_brand(
                session, rum.id, "Bacardi", 700, Decimal("85.00")
            )

            gin = await get_or_create_ingredient(session, "gin")
            gin_beefeater = await get_or_create_brand(
                session, gin.id, "Beefeater", 700, Decimal("110.00")
            )

            vodka = await get_or_create_ingredient(session, "vodka")
            vodka_smirnoff = await get_or_create_brand(
                session, vodka.id, "Smirnoff", 700, Decimal("75.00")
            )

            triple_sec = await get_or_create_ingredient(session, "triple sec")
            triple_sec_cointreau = await get_or_create_brand(
                session, triple_sec.id, "Cointreau", 700, Decimal("140.00")
            )

            campari = await get_or_create_ingredient(session, "campari")
            campari_brand = await get_or_create_brand(
                session, campari.id, "Campari", 1000, Decimal("120.00")
            )

            vermouth = await get_or_create_ingredient(session, "sweet vermouth")
            vermouth_brand = await get_or_create_brand(
                session, vermouth.id, "Martini Rosso", 1000, Decimal("60.00")
            )

            lime = await get_or_create_ingredient(session, "lime")
            lime_squeezed = await get_or_create_brand(
                session, lime.id, "squeezed", 1000, Decimal("10.00")
            )

            lemon = await get_or_create_ingredient(session, "lemon")
            lemon_squeezed = await get_or_create_brand(
                session, lemon.id, "squeezed", 1000, Decimal("10.00")
            )

            simple = await get_or_create_ingredient(session, "simple syrup")
            simple_house = await get_or_create_brand(
                session, simple.id, "house", 1000, Decimal("6.00")
            )

            soda = await get_or_create_ingredient(session, "soda water")
            await get_or_create_brand(session, soda.id, "club soda", 1000, Decimal("4.00"))

            mint = await get_or_create_ingredient(session, "mint")
            await get_or_create_brand(session, mint.id, "fresh", 100, Decimal("3.00"))

            # Cocktails (ml)
            await upsert_cocktail(
                session,
                user.id,
                "Margarita",
                "Tequila, lime, and orange liqueur.",
                [
                    {"name": "tequila", "ml": 60, "brand_id": tequila_cuervo.id},
                    {"name": "lime", "ml": 30, "brand_id": lime_squeezed.id},
                    {"name": "triple sec", "ml": 30, "brand_id": triple_sec_cointreau.id},
                ],
            )

            await upsert_cocktail(
                session,
                user.id,
                "Daiquiri",
                "Rum, lime, and simple syrup.",
                [
                    {"name": "rum", "ml": 60, "brand_id": rum_bacardi.id},
                    {"name": "lime", "ml": 30, "brand_id": lime_squeezed.id},
                    {"name": "simple syrup", "ml": 15, "brand_id": simple_house.id},
                ],
            )

            await upsert_cocktail(
                session,
                user.id,
                "Negroni",
                "Gin, Campari, and sweet vermouth.",
                [
                    {"name": "gin", "ml": 30, "brand_id": gin_beefeater.id},
                    {"name": "campari", "ml": 30, "brand_id": campari_brand.id},
                    {"name": "sweet vermouth", "ml": 30, "brand_id": vermouth_brand.id},
                ],
            )

            await upsert_cocktail(
                session,
                user.id,
                "Mojito",
                "Rum, lime, mint, sugar, topped with soda.",
                [
                    {"name": "rum", "ml": 60, "brand_id": rum_bacardi.id},
                    {"name": "lime", "ml": 30, "brand_id": lime_squeezed.id},
                    {"name": "simple syrup", "ml": 15, "brand_id": simple_house.id},
                    {"name": "mint", "ml": 5, "brand_id": None},
                    {"name": "soda water", "ml": 90, "brand_id": None},
                ],
            )

            await upsert_cocktail(
                session,
                user.id,
                "Vodka Sour",
                "Vodka, lemon, and simple syrup.",
                [
                    {"name": "vodka", "ml": 60, "brand_id": vodka_smirnoff.id},
                    {"name": "lemon", "ml": 30, "brand_id": lemon_squeezed.id},
                    {"name": "simple syrup", "ml": 15, "brand_id": simple_house.id},
                ],
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())

