import asyncio
import base64
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

"""
Reset + seed the NEW normalized schema:
- Deletes existing sample data (cocktails, recipe_ingredients, bottles, prices, ingredients, reference rows).
- Keeps users.
- Seeds fresh data (ingredients, bottles, bottle_prices, cocktails, recipe_ingredients).
- Uploads simple SVG "cocktail cards" to ImageKit (if credentials are configured) and stores the URL in cocktail_recipes.picture_url.

Run:
- inside backend/: `uv run python scripts/seed_normalized_data.py`
- from repo root: `uv run python backend/scripts/seed_normalized_data.py`
"""

# Allow running from repo root by ensuring `backend/` is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text, select
from fastapi_users.password import PasswordHelper

from db.database import async_session_maker
from db.users import User
from db.ingredient import Ingredient
from db.brand import Brand
from db.bottle import Bottle
from db.bottle_price import BottlePrice
from db.cocktail_recipe import CocktailRecipe
from db.recipe_ingredient import RecipeIngredient
from db.glass_type import GlassType

from core.imagekit_client import upload_base64_to_imagekit


password_helper = PasswordHelper()


@dataclass(frozen=True)
class SeedBottle:
    name: str
    volume_ml: int
    price_ils: float
    is_default_cost: bool = True


@dataclass(frozen=True)
class SeedIngredient:
    name: str
    brand_name: str | None
    bottles: list[SeedBottle]


def _svg_card(title: str, subtitle: str = "") -> bytes:
    # Keep > 100 bytes (ImageKit validation in our helper)
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_sub = subtitle.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b1220"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="60" y="60" width="1080" height="510" rx="28" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)"/>
  <text x="120" y="260" font-family="Inter, Arial, sans-serif" font-size="72" fill="#ffffff" font-weight="700">{safe_title}</text>
  <text x="120" y="330" font-family="Inter, Arial, sans-serif" font-size="34" fill="rgba(255,255,255,0.85)">{safe_sub}</text>
  <text x="120" y="520" font-family="Inter, Arial, sans-serif" font-size="22" fill="rgba(255,255,255,0.7)">cocktail cost management</text>
</svg>
"""
    return svg.encode("utf-8")


async def _ensure_admin(session) -> User:
    res = await session.execute(select(User).order_by(User.email.asc()))
    user = res.scalars().first()
    if user:
        return user

    user = User(
        email="admin@admin.com",
        hashed_password=password_helper.hash("admin"),
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _try_upload_cocktail_image(cocktail_name: str, subtitle: str) -> str | None:
    try:
        svg_bytes = _svg_card(cocktail_name, subtitle)
        b64 = base64.b64encode(svg_bytes).decode("ascii")
        data_url = f"data:image/svg+xml;base64,{b64}"
        result = await upload_base64_to_imagekit(data_url, f"{cocktail_name.lower().replace(' ', '_')}.svg", folder="cocktails")
        return result.get("url")
    except Exception as e:
        print(f"[seed] ImageKit upload skipped for '{cocktail_name}': {e}")
        return None


async def reset_db(session):
    # Keep users. Wipe everything else (normalized + legacy) so you get a clean dataset.
    # Order matters; use CASCADE to keep it simple.
    await session.execute(text("TRUNCATE TABLE recipe_ingredients CASCADE"))
    await session.execute(text("TRUNCATE TABLE cocktail_recipes CASCADE"))

    await session.execute(text("TRUNCATE TABLE bottle_prices CASCADE"))
    await session.execute(text("TRUNCATE TABLE bottles CASCADE"))

    await session.execute(text("TRUNCATE TABLE ingredients CASCADE"))

    await session.execute(text("TRUNCATE TABLE brands CASCADE"))
    await session.execute(text("TRUNCATE TABLE subcategories CASCADE"))
    await session.execute(text("TRUNCATE TABLE kinds CASCADE"))
    await session.execute(text("TRUNCATE TABLE glass_types CASCADE"))
    await session.execute(text("TRUNCATE TABLE importers CASCADE"))


async def seed():
    seed_ingredients: list[SeedIngredient] = [
        SeedIngredient(
            name="Tequila Blanco",
            brand_name="Sierra",
            bottles=[
                SeedBottle(name="Sierra Tequila Blanco 700ml", volume_ml=700, price_ils=119.90, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Triple Sec",
            brand_name="Cointreau",
            bottles=[
                SeedBottle(name="Cointreau 700ml", volume_ml=700, price_ils=139.90, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Gin",
            brand_name="Beefeater",
            bottles=[
                SeedBottle(name="Beefeater 700ml", volume_ml=700, price_ils=109.90, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Campari",
            brand_name="Campari",
            bottles=[
                SeedBottle(name="Campari 1000ml", volume_ml=1000, price_ils=119.90, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Sweet Vermouth",
            brand_name="Martini",
            bottles=[
                SeedBottle(name="Martini Rosso 1000ml", volume_ml=1000, price_ils=59.90, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="White Rum",
            brand_name="Bacardi",
            bottles=[
                SeedBottle(name="Bacardi Carta Blanca 700ml", volume_ml=700, price_ils=79.90, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Vodka",
            brand_name="Smirnoff",
            bottles=[
                SeedBottle(name="Smirnoff Red 700ml", volume_ml=700, price_ils=69.90, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Lime Juice",
            brand_name=None,
            bottles=[
                SeedBottle(name="Fresh Lime Juice 1000ml", volume_ml=1000, price_ils=12.00, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Lemon Juice",
            brand_name=None,
            bottles=[
                SeedBottle(name="Fresh Lemon Juice 1000ml", volume_ml=1000, price_ils=12.00, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Simple Syrup",
            brand_name=None,
            bottles=[
                SeedBottle(name="House Simple Syrup 1000ml", volume_ml=1000, price_ils=6.00, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Soda Water",
            brand_name=None,
            bottles=[
                SeedBottle(name="Club Soda 1000ml", volume_ml=1000, price_ils=4.50, is_default_cost=True),
            ],
        ),
        SeedIngredient(
            name="Mint",
            brand_name=None,
            bottles=[
                SeedBottle(name="Fresh Mint (bundle equiv 100ml)", volume_ml=100, price_ils=4.00, is_default_cost=True),
            ],
        ),
    ]

    async with async_session_maker() as session:
        async with session.begin():
            await reset_db(session)

            user = await _ensure_admin(session)

            # Seed reference data: glass types
            glass_types_seed = [
                ("Coupe", 180),
                ("Nick & Nora", 150),
                ("Martini", 180),
                ("Rocks", 250),
                ("Highball", 350),
                ("Collins", 400),
                ("Tiki Mug", 450),
                ("Wine", 350),
                ("Shot", 60),
                ("Flute", 160),
            ]
            glass_type_cache: dict[str, GlassType] = {}
            for (name, capacity_ml) in glass_types_seed:
                gt = GlassType(name=name, capacity_ml=capacity_ml)
                session.add(gt)
                await session.flush()
                glass_type_cache[name] = gt

            # Create brands + ingredients + bottles + prices
            brand_cache: dict[str, Brand] = {}
            ingredient_cache: dict[str, Ingredient] = {}
            bottle_cache: dict[str, Bottle] = {}

            for si in seed_ingredients:
                brand_id = None
                if si.brand_name:
                    if si.brand_name not in brand_cache:
                        b = Brand(name=si.brand_name)
                        session.add(b)
                        await session.flush()
                        brand_cache[si.brand_name] = b
                    brand_id = brand_cache[si.brand_name].id

                ing = Ingredient(name=si.name, brand_id=brand_id)
                session.add(ing)
                await session.flush()
                ingredient_cache[si.name] = ing

                for sb in si.bottles:
                    # Ensure only one default cost bottle per ingredient
                    if sb.is_default_cost:
                        for existing in bottle_cache.values():
                            if existing.ingredient_id == ing.id:
                                existing.is_default_cost = False

                    bottle = Bottle(
                        ingredient_id=ing.id,
                        name=sb.name,
                        volume_ml=sb.volume_ml,
                        is_default_cost=sb.is_default_cost,
                    )
                    session.add(bottle)
                    await session.flush()
                    bottle_cache[sb.name] = bottle

                    session.add(
                        BottlePrice(
                            bottle_id=bottle.id,
                            price_minor=int(round(sb.price_ils * 100)),
                            currency="ILS",
                            start_date=date.today(),
                            end_date=None,
                            source="seed",
                        )
                    )

            async def mk_cocktail(
                name: str,
                desc: str,
                lines: list[tuple[str, float, str, str | None]],
                glass_type_name: str | None = None,
                garnish_text: str | None = None,
            ):
                # lines: (ingredient_name, qty, unit, bottle_name(optional))
                picture_url = await _try_upload_cocktail_image(name, "seeded via ImageKit")
                glass_type_id = glass_type_cache.get(glass_type_name).id if glass_type_name else None
                c = CocktailRecipe(
                    created_by_user_id=user.id,
                    name=name,
                    description=desc,
                    picture_url=picture_url,
                    glass_type_id=glass_type_id,
                    garnish_text=garnish_text,
                )
                session.add(c)
                await session.flush()

                for idx, (ing_name, qty, unit, bottle_name) in enumerate(lines, start=1):
                    ing = ingredient_cache[ing_name]
                    bottle_id = bottle_cache[bottle_name].id if bottle_name else None
                    session.add(
                        RecipeIngredient(
                            recipe_id=c.id,
                            ingredient_id=ing.id,
                            quantity=qty,
                            unit=unit,
                            bottle_id=bottle_id,
                            sort_order=idx,
                            is_garnish=False,
                            is_optional=False,
                        )
                    )

            await mk_cocktail(
                "Margarita",
                "Tequila, lime, and orange liqueur.",
                [
                    ("Tequila Blanco", 60, "ml", "Sierra Tequila Blanco 700ml"),
                    ("Lime Juice", 30, "ml", "Fresh Lime Juice 1000ml"),
                    ("Triple Sec", 30, "ml", "Cointreau 700ml"),
                ],
                glass_type_name="Coupe",
                garnish_text="Salt rim + lime wheel",
            )
            await mk_cocktail(
                "Daiquiri",
                "Rum, lime, and simple syrup.",
                [
                    ("White Rum", 60, "ml", "Bacardi Carta Blanca 700ml"),
                    ("Lime Juice", 30, "ml", "Fresh Lime Juice 1000ml"),
                    ("Simple Syrup", 15, "ml", "House Simple Syrup 1000ml"),
                ],
                glass_type_name="Coupe",
                garnish_text="Lime wheel (optional)",
            )
            await mk_cocktail(
                "Negroni",
                "Gin, Campari, and sweet vermouth.",
                [
                    ("Gin", 30, "ml", "Beefeater 700ml"),
                    ("Campari", 30, "ml", "Campari 1000ml"),
                    ("Sweet Vermouth", 30, "ml", "Martini Rosso 1000ml"),
                ],
                glass_type_name="Rocks",
                garnish_text="Orange peel",
            )
            await mk_cocktail(
                "Mojito",
                "Rum, lime, mint, sugar, topped with soda.",
                [
                    ("White Rum", 60, "ml", "Bacardi Carta Blanca 700ml"),
                    ("Lime Juice", 30, "ml", "Fresh Lime Juice 1000ml"),
                    ("Simple Syrup", 15, "ml", "House Simple Syrup 1000ml"),
                    ("Mint", 5, "ml", "Fresh Mint (bundle equiv 100ml)"),
                    ("Soda Water", 90, "ml", "Club Soda 1000ml"),
                ],
                glass_type_name="Highball",
                garnish_text="Mint sprig + lime wheel",
            )
            await mk_cocktail(
                "Vodka Sour",
                "Vodka, lemon, and simple syrup.",
                [
                    ("Vodka", 60, "ml", "Smirnoff Red 700ml"),
                    ("Lemon Juice", 30, "ml", "Fresh Lemon Juice 1000ml"),
                    ("Simple Syrup", 15, "ml", "House Simple Syrup 1000ml"),
                ],
                glass_type_name="Coupe",
                garnish_text="Lemon peel",
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())

