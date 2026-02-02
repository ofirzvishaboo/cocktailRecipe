import asyncio
import sys
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

"""
Seed EVERYTHING (demo dataset):
- Keeps users, ensures an admin exists.
- Resets normalized cocktail data (kinds/subcategories/brands/ingredients/bottles/prices/cocktails/recipe_ingredients).
- Seeds Hebrew name fields where supported.
- Seeds Suppliers + assigns default suppliers.
- Seeds Inventory (items + stock rows) including glass + garnish inferred from garnish_text.
- Seeds 10 Classic cocktails (is_base=True).

Run inside docker (recommended):
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/seed_everything_demo.py"
"""

# Allow running from repo root by ensuring `backend/` is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text, select, func  # noqa: E402
from fastapi_users.password import PasswordHelper  # noqa: E402

from db.database import async_session_maker  # noqa: E402
from db.users import User  # noqa: E402
from db.brand import Brand  # noqa: E402
from db.kind import Kind  # noqa: E402
from db.subcategory import Subcategory  # noqa: E402
from db.ingredient import Ingredient  # noqa: E402
from db.bottle import Bottle  # noqa: E402
from db.bottle_price import BottlePrice  # noqa: E402
from db.glass_type import GlassType  # noqa: E402
from db.cocktail_recipe import CocktailRecipe  # noqa: E402
from db.recipe_ingredient import RecipeIngredient  # noqa: E402

from db.database import Supplier  # noqa: E402

from scripts.seed_inventory_v3 import seed as seed_inventory_v3  # noqa: E402
from scripts.seed_suppliers import _pick_supplier_name_for_ingredient, SEED_SUPPLIERS  # noqa: E402

from sqlalchemy.exc import DBAPIError  # noqa: E402

password_helper = PasswordHelper()


@dataclass(frozen=True)
class SeedBottle:
    name: str
    name_he: str | None
    volume_ml: int
    price_ils: float
    is_default_cost: bool = True
    description: str | None = None
    description_he: str | None = None


@dataclass(frozen=True)
class SeedIngredient:
    name: str
    name_he: str | None
    brand_name: str | None
    brand_name_he: str | None
    subcategory_name: str | None
    subcategory_name_he: str | None
    bottles: list[SeedBottle]


def _hm(en: str, he: str) -> tuple[str, str]:
    return en, he


async def _ensure_admin(session) -> User:
    res = await session.execute(select(User).order_by(User.email.asc()))
    user = res.scalars().first()
    if user:
        # Ensure the first user is admin in demo DB
        user.is_active = True
        user.is_superuser = True
        user.is_verified = True
        return user

    user = User(
        email="admin@admin.com",
        hashed_password=password_helper.hash("admin"),
        is_active=True,
        is_superuser=True,
        is_verified=True,
        first_name="Admin",
        last_name="User",
    )
    session.add(user)
    await session.flush()
    return user


async def reset_demo_data(session):
    # Keep users. Wipe app data so the demo is deterministic.
    # Order matters; use CASCADE to keep it simple.
    # PostgreSQL does NOT support "TRUNCATE ... IF EXISTS".
    # Also: asyncpg does not allow bind params inside DO $$ ... $$ blocks.
    # So we do a safe 2-step approach:
    # 1) SELECT to_regclass('public.<table>')
    # 2) if exists, TRUNCATE TABLE "<table>" CASCADE
    #
    # Table names are hardcoded in this script (not user input), so this is safe.
    async def _truncate_if_exists(table_name: str) -> None:
        reg = f"public.{table_name}"
        res = await session.execute(text("SELECT to_regclass(:reg)"), {"reg": reg})
        exists = res.scalar_one_or_none() is not None
        if not exists:
            return
        # Quote identifier to avoid issues with reserved words.
        await session.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))

    for tname in [
        "order_items",
        "orders",
        "event_menu_items",
        "events",
        "inventory_movements",
        "inventory_stock",
        "inventory_items",
        "recipe_ingredients",
        "cocktail_recipes",
        "bottle_prices",
        "bottles",
        "ingredient_suppliers",
        "ingredients",
        "brands",
        "subcategories",
        "kinds",
        "glass_types",
        "importers",
        "suppliers",
    ]:
        await _truncate_if_exists(tname)


async def ensure_hebrew_columns(session) -> None:
    """
    Make this seed script self-contained by adding Hebrew columns if missing.
    This avoids needing to restart the API container to run startup migrations first.
    """
    await session.execute(text("ALTER TABLE brands ADD COLUMN IF NOT EXISTS name_he TEXT"))
    await session.execute(text("ALTER TABLE glass_types ADD COLUMN IF NOT EXISTS name_he TEXT"))
    await session.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS name_he TEXT"))
    await session.execute(text("ALTER TABLE bottles ADD COLUMN IF NOT EXISTS name_he TEXT"))
    await session.execute(text("ALTER TABLE bottles ADD COLUMN IF NOT EXISTS description_he TEXT"))
    await session.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS name_he TEXT"))
    await session.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS description_he TEXT"))
    await session.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS garnish_text_he TEXT"))
    await session.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS preparation_method_he TEXT"))
    await session.execute(text("ALTER TABLE kinds ADD COLUMN IF NOT EXISTS name_he TEXT"))
    await session.execute(text("ALTER TABLE subcategories ADD COLUMN IF NOT EXISTS name_he TEXT"))


async def seed():
    # Bottle categories (subcategory under kind "Ingredient")
    kind_en, kind_he = _hm("Ingredient", "מרכיבים")
    subcats = [
        _hm("Spirit", "אלכוהול"),
        _hm("Liqueur", "ליקר"),
        _hm("Juice", "מיץ"),
        _hm("Syrup", "סירופ"),
        _hm("Sparkling", "מוגז"),
        _hm("Garnish", "קישוט"),
    ]

    # Glass types
    glass_seed = [
        ("Coupe", "קופה", 180),
        ("Rocks", "רוקס", 250),
        ("Highball", "הייבול", 350),
        ("Collins", "קולינס", 400),
        ("Martini", "מרטיני", 180),
    ]

    # Ingredients/Bottles for classic cocktails
    seed_ingredients: list[SeedIngredient] = [
        SeedIngredient(
            name="Tequila Blanco",
            name_he="טקילה בלאנקו",
            brand_name="Sierra",
            brand_name_he="סיירה",
            subcategory_name="Spirit",
            subcategory_name_he="אלכוהול",
            bottles=[SeedBottle("Sierra Tequila Blanco 700ml", "סיירה טקילה בלאנקו 700 מ״ל", 700, 119.90, True)],
        ),
        SeedIngredient(
            name="Gin",
            name_he="ג׳ין",
            brand_name="Beefeater",
            brand_name_he="ביפיטר",
            subcategory_name="Spirit",
            subcategory_name_he="אלכוהול",
            bottles=[SeedBottle("Beefeater 700ml", "ביפיטר 700 מ״ל", 700, 109.90, True)],
        ),
        SeedIngredient(
            name="Vodka",
            name_he="וודקה",
            brand_name="Smirnoff",
            brand_name_he="סמירנוף",
            subcategory_name="Spirit",
            subcategory_name_he="אלכוהול",
            bottles=[SeedBottle("Smirnoff Red 700ml", "סמירנוף אדום 700 מ״ל", 700, 69.90, True)],
        ),
        SeedIngredient(
            name="White Rum",
            name_he="רום לבן",
            brand_name="Bacardi",
            brand_name_he="בקרדי",
            subcategory_name="Spirit",
            subcategory_name_he="אלכוהול",
            bottles=[SeedBottle("Bacardi Carta Blanca 700ml", "בקרדי קרטה בלנקה 700 מ״ל", 700, 79.90, True)],
        ),
        SeedIngredient(
            name="Bourbon",
            name_he="בורבון",
            brand_name="Jim Beam",
            brand_name_he="ג׳ים בים",
            subcategory_name="Spirit",
            subcategory_name_he="אלכוהול",
            bottles=[SeedBottle("Jim Beam White 700ml", "ג׳ים בים 700 מ״ל", 700, 99.90, True)],
        ),
        SeedIngredient(
            name="Rye Whiskey",
            name_he="וויסקי שיפון",
            brand_name="Bulleit",
            brand_name_he="בולט",
            subcategory_name="Spirit",
            subcategory_name_he="אלכוהול",
            bottles=[SeedBottle("Bulleit Rye 700ml", "בולט ריי 700 מ״ל", 700, 149.90, True)],
        ),
        SeedIngredient(
            name="Triple Sec",
            name_he="טריפל סק",
            brand_name="Cointreau",
            brand_name_he="קואנטרו",
            subcategory_name="Liqueur",
            subcategory_name_he="ליקר",
            bottles=[SeedBottle("Cointreau 700ml", "קואנטרו 700 מ״ל", 700, 139.90, True)],
        ),
        SeedIngredient(
            name="Campari",
            name_he="קמפרי",
            brand_name="Campari",
            brand_name_he="קמפרי",
            subcategory_name="Liqueur",
            subcategory_name_he="ליקר",
            bottles=[SeedBottle("Campari 1000ml", "קמפרי 1000 מ״ל", 1000, 119.90, True)],
        ),
        SeedIngredient(
            name="Sweet Vermouth",
            name_he="ורמוט מתוק",
            brand_name="Martini",
            brand_name_he="מרטיני",
            subcategory_name="Liqueur",
            subcategory_name_he="ליקר",
            bottles=[SeedBottle("Martini Rosso 1000ml", "מרטיני רוסו 1000 מ״ל", 1000, 59.90, True)],
        ),
        SeedIngredient(
            name="Dry Vermouth",
            name_he="ורמוט יבש",
            brand_name="Martini",
            brand_name_he="מרטיני",
            subcategory_name="Liqueur",
            subcategory_name_he="ליקר",
            bottles=[SeedBottle("Martini Extra Dry 1000ml", "מרטיני אקסטרה דריי 1000 מ״ל", 1000, 59.90, True)],
        ),
        SeedIngredient(
            name="Angostura Bitters",
            name_he="ביטר אנגוסטורה",
            brand_name="Angostura",
            brand_name_he="אנגוסטורה",
            subcategory_name="Liqueur",
            subcategory_name_he="ליקר",
            bottles=[SeedBottle("Angostura Bitters 200ml", "אנגוסטורה ביטר 200 מ״ל", 200, 49.90, True)],
        ),
        SeedIngredient(
            name="Simple Syrup",
            name_he="סירופ סוכר",
            brand_name=None,
            brand_name_he=None,
            subcategory_name="Syrup",
            subcategory_name_he="סירופ",
            bottles=[SeedBottle("House Simple Syrup 1000ml", "סירופ סוכר ביתי 1000 מ״ל", 1000, 6.00, True)],
        ),
        SeedIngredient(
            name="Lime Juice",
            name_he="מיץ ליים",
            brand_name=None,
            brand_name_he=None,
            subcategory_name="Juice",
            subcategory_name_he="מיץ",
            bottles=[SeedBottle("Fresh Lime Juice 1000ml", "מיץ ליים טרי 1000 מ״ל", 1000, 12.00, True)],
        ),
        SeedIngredient(
            name="Lemon Juice",
            name_he="מיץ לימון",
            brand_name=None,
            brand_name_he=None,
            subcategory_name="Juice",
            subcategory_name_he="מיץ",
            bottles=[SeedBottle("Fresh Lemon Juice 1000ml", "מיץ לימון טרי 1000 מ״ל", 1000, 12.00, True)],
        ),
        SeedIngredient(
            name="Grapefruit Juice",
            name_he="מיץ אשכוליות",
            brand_name=None,
            brand_name_he=None,
            subcategory_name="Juice",
            subcategory_name_he="מיץ",
            bottles=[SeedBottle("Grapefruit Juice 1000ml", "מיץ אשכוליות 1000 מ״ל", 1000, 14.00, True)],
        ),
        SeedIngredient(
            name="Soda Water",
            name_he="סודה",
            brand_name=None,
            brand_name_he=None,
            subcategory_name="Sparkling",
            subcategory_name_he="מוגז",
            bottles=[SeedBottle("Club Soda 1000ml", "סודה 1000 מ״ל", 1000, 4.50, True)],
        ),
    ]

    cocktails_10 = [
        # name, name_he, desc, desc_he, glass, garnish, garnish_he, prep, prep_he, lines (ingredient, qty, unit, bottle_name)
        (
            "Margarita",
            "מרגריטה",
            "Tequila, lime, and orange liqueur.",
            "טקילה, ליים וליקר תפוזים.",
            "Coupe",
            "Salt rim + lime wheel",
            "שפת כוס מלח + פלח ליים",
            "Shake with ice and strain.",
            "לנער עם קרח ולסנן.",
            [("Tequila Blanco", 60, "ml", "Sierra Tequila Blanco 700ml"), ("Lime Juice", 30, "ml", "Fresh Lime Juice 1000ml"), ("Triple Sec", 30, "ml", "Cointreau 700ml")],
        ),
        (
            "Daiquiri",
            "דאיקירי",
            "Rum, lime, and simple syrup.",
            "רום, ליים וסירופ סוכר.",
            "Coupe",
            "Lime wheel (optional)",
            "פלח ליים (אופציונלי)",
            "Shake hard, strain to coupe.",
            "לנער חזק ולסנן לקופה.",
            [("White Rum", 60, "ml", "Bacardi Carta Blanca 700ml"), ("Lime Juice", 30, "ml", "Fresh Lime Juice 1000ml"), ("Simple Syrup", 15, "ml", "House Simple Syrup 1000ml")],
        ),
        (
            "Negroni",
            "נגרוני",
            "Gin, Campari, and sweet vermouth.",
            "ג׳ין, קמפרי וורמוט מתוק.",
            "Rocks",
            "Orange peel",
            "קליפת תפוז",
            "Stir on ice, serve over a big cube.",
            "לערבב עם קרח ולהגיש על קוביית קרח גדולה.",
            [("Gin", 30, "ml", "Beefeater 700ml"), ("Campari", 30, "ml", "Campari 1000ml"), ("Sweet Vermouth", 30, "ml", "Martini Rosso 1000ml")],
        ),
        (
            "Martini",
            "מרטיני",
            "Gin and dry vermouth.",
            "ג׳ין וורמוט יבש.",
            "Martini",
            "Lemon twist or olive",
            "טוויסט לימון או זית",
            "Stir very cold, strain.",
            "לערבב עד קר מאוד ולסנן.",
            [("Gin", 60, "ml", "Beefeater 700ml"), ("Dry Vermouth", 10, "ml", "Martini Extra Dry 1000ml")],
        ),
        (
            "Manhattan",
            "מנהטן",
            "Whiskey and sweet vermouth with bitters.",
            "וויסקי וורמוט מתוק עם ביטר.",
            "Coupe",
            "Cherry",
            "דובדבן",
            "Stir with ice, strain.",
            "לערבב עם קרח ולסנן.",
            [("Rye Whiskey", 60, "ml", "Bulleit Rye 700ml"), ("Sweet Vermouth", 30, "ml", "Martini Rosso 1000ml"), ("Angostura Bitters", 2, "ml", "Angostura Bitters 200ml")],
        ),
        (
            "Old Fashioned",
            "אולד פאשנד",
            "Whiskey, sugar, and bitters.",
            "וויסקי, סוכר וביטר.",
            "Rocks",
            "Orange peel",
            "קליפת תפוז",
            "Build in glass, stir.",
            "לבנות בכוס ולערבב.",
            [("Bourbon", 60, "ml", "Jim Beam White 700ml"), ("Simple Syrup", 7.5, "ml", "House Simple Syrup 1000ml"), ("Angostura Bitters", 2, "ml", "Angostura Bitters 200ml")],
        ),
        (
            "Whiskey Sour",
            "וויסקי סאוור",
            "Whiskey, lemon, and simple syrup.",
            "וויסקי, לימון וסירופ סוכר.",
            "Rocks",
            "Lemon peel",
            "קליפת לימון",
            "Shake with ice, strain.",
            "לנער עם קרח ולסנן.",
            [("Bourbon", 60, "ml", "Jim Beam White 700ml"), ("Lemon Juice", 30, "ml", "Fresh Lemon Juice 1000ml"), ("Simple Syrup", 15, "ml", "House Simple Syrup 1000ml")],
        ),
        (
            "Tom Collins",
            "טום קולינס",
            "Gin, lemon, sugar, topped with soda.",
            "ג׳ין, לימון, סוכר, השלמה בסודה.",
            "Collins",
            "Lemon wheel",
            "פלח לימון",
            "Build over ice, top with soda.",
            "לבנות על קרח ולהשלים בסודה.",
            [("Gin", 60, "ml", "Beefeater 700ml"), ("Lemon Juice", 30, "ml", "Fresh Lemon Juice 1000ml"), ("Simple Syrup", 15, "ml", "House Simple Syrup 1000ml"), ("Soda Water", 90, "ml", "Club Soda 1000ml")],
        ),
        (
            "Paloma",
            "פלומה",
            "Tequila, grapefruit, lime, topped with soda.",
            "טקילה, אשכוליות, ליים, השלמה בסודה.",
            "Highball",
            "Grapefruit wedge",
            "פלח אשכולית",
            "Build over ice, top with soda.",
            "לבנות על קרח ולהשלים בסודה.",
            [("Tequila Blanco", 50, "ml", "Sierra Tequila Blanco 700ml"), ("Grapefruit Juice", 90, "ml", "Grapefruit Juice 1000ml"), ("Lime Juice", 15, "ml", "Fresh Lime Juice 1000ml"), ("Soda Water", 60, "ml", "Club Soda 1000ml")],
        ),
        (
            "Vodka Sour",
            "וודקה סאוור",
            "Vodka, lemon, and simple syrup.",
            "וודקה, לימון וסירופ סוכר.",
            "Coupe",
            "Lemon peel",
            "קליפת לימון",
            "Shake with ice and strain.",
            "לנער עם קרח ולסנן.",
            [("Vodka", 60, "ml", "Smirnoff Red 700ml"), ("Lemon Juice", 30, "ml", "Fresh Lemon Juice 1000ml"), ("Simple Syrup", 15, "ml", "House Simple Syrup 1000ml")],
        ),
    ]

    async with async_session_maker() as session:
        async with session.begin():
            await ensure_hebrew_columns(session)
            await reset_demo_data(session)
            user = await _ensure_admin(session)

            # Kind + subcategories
            kind = Kind(name=kind_en, name_he=kind_he)
            session.add(kind)
            await session.flush()

            subcat_by_name: dict[str, Subcategory] = {}
            for en, he in subcats:
                sc = Subcategory(kind_id=kind.id, name=en, name_he=he)
                session.add(sc)
                await session.flush()
                subcat_by_name[en.lower()] = sc

            # Glass types
            glass_by_name: dict[str, GlassType] = {}
            for en, he, cap in glass_seed:
                gt = GlassType(name=en, name_he=he, capacity_ml=cap)
                session.add(gt)
                await session.flush()
                glass_by_name[en.lower()] = gt

            # Brands + ingredients + bottles + prices
            brand_by_name: dict[str, Brand] = {}
            ing_by_name: dict[str, Ingredient] = {}
            bottle_by_name: dict[str, Bottle] = {}

            today = date.today()
            for si in seed_ingredients:
                brand_id = None
                if si.brand_name:
                    bkey = si.brand_name.lower()
                    if bkey not in brand_by_name:
                        b = Brand(name=si.brand_name, name_he=si.brand_name_he)
                        session.add(b)
                        await session.flush()
                        brand_by_name[bkey] = b
                    brand_id = brand_by_name[bkey].id

                subcat = subcat_by_name.get((si.subcategory_name or "").lower())
                ing = Ingredient(
                    name=si.name,
                    name_he=si.name_he,
                    brand_id=brand_id,
                    kind_id=kind.id,
                    subcategory_id=subcat.id if subcat else None,
                )
                session.add(ing)
                await session.flush()
                ing_by_name[si.name.lower()] = ing

                for sb in si.bottles:
                    bottle = Bottle(
                        ingredient_id=ing.id,
                        name=sb.name,
                        name_he=sb.name_he,
                        volume_ml=sb.volume_ml,
                        description=sb.description,
                        description_he=sb.description_he,
                        is_default_cost=sb.is_default_cost,
                    )
                    session.add(bottle)
                    await session.flush()
                    bottle_by_name[sb.name.lower()] = bottle

                    session.add(
                        BottlePrice(
                            bottle_id=bottle.id,
                            price_minor=int(round(sb.price_ils * 100)),
                            currency="ILS",
                            start_date=today,
                            end_date=None,
                            source="seed_everything_demo",
                        )
                    )

            # Suppliers (seed + assign)
            suppliers_by_name = {}
            for s in SEED_SUPPLIERS:
                sup = Supplier(id=uuid.uuid4(), name=s.name, contact=s.contact, notes=s.notes)
                session.add(sup)
                suppliers_by_name[s.name] = sup
            await session.flush()

            res = await session.execute(select(Ingredient).order_by(func.lower(Ingredient.name).asc()))
            all_ings = res.scalars().all()
            for ing in all_ings:
                pick = _pick_supplier_name_for_ingredient(ing)
                sup = suppliers_by_name.get(pick)
                if not sup:
                    continue
                ing.default_supplier_id = sup.id

            # Cocktails
            for (
                name,
                name_he,
                desc,
                desc_he,
                glass_name,
                garnish,
                garnish_he,
                prep,
                prep_he,
                lines,
            ) in cocktails_10:
                gt = glass_by_name.get((glass_name or "").lower())
                c = CocktailRecipe(
                    created_by_user_id=user.id,
                    name=name,
                    name_he=name_he,
                    description=desc,
                    description_he=desc_he,
                    glass_type_id=gt.id if gt else None,
                    picture_url=None,
                    garnish_text=garnish,
                    garnish_text_he=garnish_he,
                    is_base=True,  # Classic
                    preparation_method=prep,
                    preparation_method_he=prep_he,
                    # Keep null so the Scaler UI stays on its default ("batch") unless user chooses otherwise.
                    batch_type=None,
                )
                session.add(c)
                await session.flush()

                for idx, (ing_name, qty, unit, bottle_name) in enumerate(lines, start=1):
                    ing = ing_by_name[ing_name.lower()]
                    bottle = bottle_by_name.get((bottle_name or "").lower())
                    session.add(
                        RecipeIngredient(
                            id=uuid.uuid4(),
                            recipe_id=c.id,
                            ingredient_id=ing.id,
                            quantity=qty,
                            unit=unit,
                            bottle_id=bottle.id if bottle else None,
                            sort_order=idx,
                            is_garnish=False,
                            is_optional=False,
                        )
                    )

        await session.commit()

    # Inventory items + stock rows + garnish/glass items
    # NOTE: right after `docker compose up`, the API startup may still be running migrations/DDL.
    # That can temporarily deadlock with the inventory seeding. Retry a few times.
    for attempt in range(1, 6):
        try:
            await seed_inventory_v3(with_glass=True, for_cocktails=True, from_garnish_text=True, create_missing_garnish_ingredients=True)
            break
        except DBAPIError as e:
            msg = str(getattr(e, "orig", e) or "")
            if "deadlock detected" not in msg.lower():
                raise
            wait_s = min(10, 2 * attempt)
            print(f"[seed_everything_demo] Deadlock during inventory seed; retrying in {wait_s}s (attempt {attempt}/5)")
            await asyncio.sleep(wait_s)
    print("[seed_everything_demo] done.")


if __name__ == "__main__":
    asyncio.run(seed())

