"""
Seed Signature Menu: cocktails with Hebrew and English names, ingredients, bottles, kinds, and prices.

Cocktails: Raanana, Fuzzy Tiki, Spicy Señorita, Greek Sunset, Cosmo Violets, Negroni,
Dionysus Penicillin, Piña Colada, Piña Diablo, Jasmine.

Run (additive – does not truncate; adds to existing data):
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/seed_signature_menu.py"

Or after seed_everything_demo for full demo + signature menu.
"""

import asyncio
import sys
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, text  # noqa: E402
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

password_helper = PasswordHelper()


def _volume_ml_from_key(size_key: str) -> int:
    if not size_key:
        return 700
    s = size_key.strip().lower()
    if "1 liter" in s or "1 liter" == s or s == "1l":
        return 1000
    if "700" in s or "700ml" in s:
        return 700
    if "750" in s:
        return 750
    if "400" in s:
        return 400
    if "200" in s:
        return 200
    return 1000


# Your bottle names + Hebrew names + prices (size key -> price ILS). Used for signature menu ingredients.
BOTTLE_PRICES_DATA = {
    "Gin": {"name": "Greenall's", "name_he": "גרינלס", "1 liter": 85.0},
    "Vodka": {"name": "Rusky standard", "name_he": "רוסקי סטנדרט", "1 liter": 75.5},
    "Rum": {"name": "Saint james imperial", "name_he": "רום סיינט גיימס", "700ml": 64.9},
    "Ouzo": {"name": "Ouzo Solaris", "name_he": "אוזו סולאריס", "700ml": 45.0},
    "Tequila": {"name": "Lunazul", "name_he": "לונאזול", "700ml": 106.0},
    "Elderflower Liqueur": {"name": "Vedrenne Elderflower", "name_he": "ודרן אלד פלוואר", "700ml": 86},
    "Triple Sec": {"name": "Vedrenne Triple Sec", "name_he": "ודרן טריפל סק", "700ml": 80},
    "Amaretto": {"name": "Vedrenne Amaretto", "name_he": "ודרן אמרטו", "700ml": 80},
    "Passion Fruit Syrup": {"name": "Vedrenne Passion Fruit", "name_he": "ודרן סירופ פסיפלורה", "1 liter": 50},
    "Hibiscus Syrup": {"name": "Vedrenne Hibiscus", "name_he": "ודרן היביסקוס", "1 liter": 50},
    "Orgeat Syrup": {"name": "Marie brizard Orgeat", "name_he": "מרי בריזארד סירופ שקדים", "1 liter": 30},
    "Grape Syrup": {"name": "Marie brizard Grape", "name_he": "מרי בריזארד סירופ תפוז", "1 liter": 30},
    "Lemon Juice": {"name": "Vedrenne Lemon", "name_he": "ודרן לימון", "1 liter": 12},
    "Apple Lime Juice": {"name": "Vedrenne Apple Lime", "name_he": "ודרן תפוח ליים", "1 liter": 18},
    "Pineapple Juice": {"name": "Vedrenne Pineapple", "name_he": "ודרן אננס", "1 liter": 16},
    "Red Grapefruit Juice": {"name": "Vedrenne Red Grapefruit", "name_he": "ודרן אשכולית אדומה", "1 liter": 18},
    "Chili Pepper Juice": {"name": "Vedrenne Chili Pepper", "name_he": "ודרן פלפלים", "1 liter": 22},
    "Hibiscus Juice": {"name": "Vedrenne Hibiscus", "name_he": "ודרן היביסקוס", "1 liter": 20},
    "Orgeat Juice": {"name": "Marie brizard Orgeat", "name_he": "מרי בריזארד מיץ שקדים", "1 liter": 26},
    "Grape Juice": {"name": "Marie brizard Grape", "name_he": "מרי בריזארד מיץ תפוז", "1 liter": 26},
}

# Map SeedIngredient name -> BOTTLE_PRICES_DATA key (when different)
BOTTLE_PRICES_KEY_ALIAS = {
    "White Rum": "Rum",
    "Tequila Blanco": "Tequila",
    "Chili Pepper Syrup": "Chili Pepper Juice",
    "Almond Syrup": "Orgeat Syrup",
}


@dataclass(frozen=True)
class SeedBottle:
    name: str
    name_he: str | None
    volume_ml: int
    price_ils: float
    is_default_cost: bool = True


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


def _bottle_from_prices(ingredient_name: str) -> list[SeedBottle] | None:
    key = BOTTLE_PRICES_KEY_ALIAS.get(ingredient_name) or ingredient_name
    entry = BOTTLE_PRICES_DATA.get(key)
    if not entry:
        return None
    for size_key, price in entry.items():
        if size_key in ("name", "name_he"):
            continue
        vol = _volume_ml_from_key(size_key)
        base_name = entry["name"]
        name_suffix = "1L" if vol == 1000 else f"{vol}ml"
        bottle_name = f"{base_name} {name_suffix}"
        return [
            SeedBottle(
                name=bottle_name,
                name_he=entry.get("name_he"),
                volume_ml=vol,
                price_ils=float(price),
                is_default_cost=True,
            )
        ]
    return None


async def ensure_hebrew_columns(session) -> None:
    await session.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS menus TEXT[] DEFAULT '{}'"))
    for stmt in [
        "ALTER TABLE brands ADD COLUMN IF NOT EXISTS name_he TEXT",
        "ALTER TABLE glass_types ADD COLUMN IF NOT EXISTS name_he TEXT",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS name_he TEXT",
        "ALTER TABLE bottles ADD COLUMN IF NOT EXISTS name_he TEXT",
        "ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS name_he TEXT",
        "ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS preparation_method_he TEXT",
        "ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS garnish_text_he TEXT",
        "ALTER TABLE kinds ADD COLUMN IF NOT EXISTS name_he TEXT",
        "ALTER TABLE subcategories ADD COLUMN IF NOT EXISTS name_he TEXT",
    ]:
        await session.execute(text(stmt))


async def get_or_create_admin(session) -> User:
    res = await session.execute(select(User).where(User.is_superuser).limit(1))
    user = res.scalar_one_or_none()
    if user:
        return user
    res = await session.execute(select(User).order_by(User.email.asc()).limit(1))
    user = res.scalar_one_or_none()
    if user:
        user.is_superuser = True
        user.is_active = True
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

# Signature menu ingredients: English + Hebrew names; bottles use BOTTLE_PRICES_DATA when available
SIGNATURE_INGREDIENTS: list[SeedIngredient] = [
    SeedIngredient("Lemon Juice", "מיץ לימון", None, None, "Juice", "מיץ", [SeedBottle("Lemon Juice 1L", "מיץ לימון 1 ליטר", 1000, 12.0)]),
    SeedIngredient("Apple Lime Juice", "תפוח ליים", None, None, "Juice", "מיץ", [SeedBottle("Apple Lime Juice 1L", "תפוח ליים 1 ליטר", 1000, 18.0)]),
    SeedIngredient("Gin", "ג'ין", "Beefeater", "ביפיטר", "Spirit", "אלכוהול", [SeedBottle("Beefeater 700ml", "ביפיטר 700 מ״ל", 700, 109.90)]),
    SeedIngredient("Green Tea Syrup", "סירופ תה ירוק", None, None, "Syrup", "סירופ", [SeedBottle("Green Tea Syrup 1L", "סירופ תה ירוק 1 ליטר", 1000, 25.0)]),
    SeedIngredient("Elderflower Liqueur", "ליקר אלדר פלוואר", "St-Germain", "סן ז'רמן", "Liqueur", "ליקר", [SeedBottle("St-Germain 700ml", "סן ז'רמן 700 מ״ל", 700, 169.0)]),
    SeedIngredient("White Rum", "רום", "Bacardi", "בקרדי", "Spirit", "אלכוהול", [SeedBottle("Bacardi Carta Blanca 700ml", "בקרדי קרטה בלנקה 700 מ״ל", 700, 79.90)]),
    SeedIngredient("Amaretto", "אמרטו", "Disaronno", "דיזרונו", "Liqueur", "ליקר", [SeedBottle("Disaronno 700ml", "דיזרונו 700 מ״ל", 700, 119.0)]),
    SeedIngredient("Pineapple Juice", "מיץ אננס", None, None, "Juice", "מיץ", [SeedBottle("Pineapple Juice 1L", "מיץ אננס 1 ליטר", 1000, 16.0)]),
    SeedIngredient("Passion Fruit Syrup", "סירופ פסיפלורה", None, None, "Syrup", "סירופ", [SeedBottle("Passion Fruit Syrup 1L", "סירופ פסיפלורה 1 ליטר", 1000, 28.0)]),
    SeedIngredient("Tequila Blanco", "טקילה", "Sierra", "סיירה", "Spirit", "אלכוהול", [SeedBottle("Sierra Tequila Blanco 700ml", "סיירה טקילה 700 מ״ל", 700, 119.90)]),
    SeedIngredient("Triple Sec", "טריפל סק", "Cointreau", "קואנטרו", "Liqueur", "ליקר", [SeedBottle("Cointreau 700ml", "קואנטרו 700 מ״ל", 700, 139.90)]),
    SeedIngredient("Chili Pepper Syrup", "סירופ פלפלים", None, None, "Syrup", "סירופ", [SeedBottle("Chili Syrup 1L", "סירופ פלפלים 1 ליטר", 1000, 22.0)]),
    SeedIngredient("Ouzo", "אוזו", "Ouzo 12", "אוזו 12", "Spirit", "אלכוהול", [SeedBottle("Ouzo 12 700ml", "אוזו 12 700 מ״ל", 700, 89.0)]),
    SeedIngredient("Red Grapefruit Juice", "מיץ אשכולית אדומה", None, None, "Juice", "מיץ", [SeedBottle("Red Grapefruit Juice 1L", "מיץ אשכולית אדומה 1 ליטר", 1000, 18.0)]),
    SeedIngredient("Almond Syrup", "סירופ שקדים", None, None, "Syrup", "סירופ", [SeedBottle("Almond Syrup 1L", "סירופ שקדים 1 ליטר", 1000, 26.0)]),
    SeedIngredient("Red Wine", "יין אדום", None, None, "Spirit", "אלכוהול", [SeedBottle("House Red Wine 750ml", "יין אדום בית 750 מ״ל", 750, 45.0)]),
    SeedIngredient("Vodka", "וודקה", "Smirnoff", "סמירנוף", "Spirit", "אלכוהול", [SeedBottle("Smirnoff Red 700ml", "סמירנוף 700 מ״ל", 700, 69.90)]),
    SeedIngredient("Cranberry Juice", "מיץ חמוציות", None, None, "Juice", "מיץ", [SeedBottle("Cranberry Juice 1L", "מיץ חמוציות 1 ליטר", 1000, 20.0)]),
    SeedIngredient("Hibiscus Syrup", "סירופ היביסקוס", None, None, "Syrup", "סירופ", [SeedBottle("Hibiscus Syrup 1L", "סירופ היביסקוס 1 ליטר", 1000, 30.0)]),
    SeedIngredient("Campari", "קמפרי", "Campari", "קמפרי", "Liqueur", "ליקר", [SeedBottle("Campari 1000ml", "קמפרי 1000 מ״ל", 1000, 119.90)]),
    SeedIngredient("Sweet Vermouth", "וורמוט אדום", "Martini", "מרטיני", "Liqueur", "ליקר", [SeedBottle("Martini Rosso 1000ml", "מרטיני רוסו 1000 מ״ל", 1000, 59.90)]),
    SeedIngredient("Blended Whisky", "ויסקי בלנדד", "Johnnie Walker", "ג'וני ווקר", "Spirit", "אלכוהול", [SeedBottle("Johnnie Walker Red 700ml", "ג'וני ווקר רד 700 מ״ל", 700, 99.90)]),
    SeedIngredient("Penicillin Mix", "מיקס פניצילין", None, None, "Syrup", "סירופ", [SeedBottle("Penicillin Mix 1L", "מיקס פניצילין 1 ליטר", 1000, 35.0)]),
    SeedIngredient("Smoky Whisky", "ויסקי מעושן", "Johnnie Walker", "ג'וני ווקר", "Spirit", "אלכוהול", [SeedBottle("JW Double Black 700ml", "ג'וני ווקר דאבל בלק 700 מ״ל", 700, 149.0)]),
    SeedIngredient("Coconut Cream", "קוקוס", None, None, "Syrup", "סירופ", [SeedBottle("Coconut Cream 400ml", "קרם קוקוס 400 מ״ל", 400, 18.0)]),
    SeedIngredient("Chili Rum", "רום צ'ילי", "Bacardi", "בקרדי", "Spirit", "אלכוהול", [SeedBottle("Bacardi Chili 700ml", "בקרדי צ'ילי 700 מ״ל", 700, 89.0)]),
]

# Cocktails: (name, name_he, desc, desc_he, glass, garnish, garnish_he, prep, prep_he, lines (ing_name, qty_ml, bottle_name))
SIGNATURE_COCKTAILS = [
    (
        "Raanana", "רעננה",
        "Lemon, apple lime, gin, green tea and elderflower.",
        "לימון, תפוח ליים, ג'ין, תה ירוק ואלדר פלוואר.",
        "Collins", "Lemon slice", "פרוסת לימון",
        "Shake with ice, strain.", "לנער עם קרח ולסנן.",
        [("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Apple Lime Juice", 60, "Vedrenne Apple Lime 1L"), ("Gin", 60, "Greenall's 1L"), ("Green Tea Syrup", 10, "Green Tea Syrup 1L"), ("Elderflower Liqueur", 30, "Vedrenne Elderflower 700ml")],
    ),
    (
        "Fuzzy Tiki", "פריקי טיקי",
        "Rum, amaretto, pineapple and lemon with passion fruit syrup.",
        "רום, אמרטו, אננס ולימון עם סירופ פסיפלורה.",
        "Highball", "Pineapple wedge", "פלח אננס",
        "Shake with ice, strain.", "לנער עם קרח ולסנן.",
        [("White Rum", 45, "Saint james imperial 700ml"), ("Amaretto", 30, "Vedrenne Amaretto 700ml"), ("Pineapple Juice", 60, "Vedrenne Pineapple 1L"), ("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Passion Fruit Syrup", 10, "Vedrenne Passion Fruit 1L")],
    ),
    (
        "Spicy Señorita", "ספייסי סניוריטה",
        "Tequila, triple sec, lemon and chili syrup.",
        "טקילה, טריפל סק, לימון וסירופ פלפלים.",
        "Rocks", "Chili slice", "פרוסת צ'ילי",
        "Shake with ice, strain.", "לנער עם קרח ולסנן.",
        [("Tequila Blanco", 60, "Lunazul 700ml"), ("Triple Sec", 30, "Vedrenne Triple Sec 700ml"), ("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Chili Pepper Syrup", 10, "Vedrenne Chili Pepper 1L")],
    ),
    (
        "Greek Sunset", "שקיעה יוונית",
        "Ouzo, red grapefruit, lemon, almond syrup and red wine.",
        "אוזו, אשכולית אדומה, לימון, סירופ שקדים ויין אדום.",
        "Highball", "Grapefruit slice", "פרוסת אשכולית",
        "Build over ice, float red wine.", "לבנות על קרח, לצוף יין אדום.",
        [("Ouzo", 60, "Ouzo Solaris 700ml"), ("Red Grapefruit Juice", 60, "Vedrenne Red Grapefruit 1L"), ("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Almond Syrup", 10, "Marie brizard Orgeat 1L"), ("Red Wine", 10, "House Red Wine 750ml")],
    ),
    (
        "Cosmo Violets", "קוסמו סיגליות",
        "Vodka, triple sec, cranberry, lemon and hibiscus syrup.",
        "וודקה, טריפל סק, חמוציות, לימון וסירופ היביסקוס.",
        "Coupe", "Lemon twist", "טוויסט לימון",
        "Shake with ice, strain.", "לנער עם קרח ולסנן.",
        [("Vodka", 45, "Rusky standard 1L"), ("Triple Sec", 15, "Vedrenne Triple Sec 700ml"), ("Cranberry Juice", 60, "Cranberry Juice 1L"), ("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Hibiscus Syrup", 10, "Vedrenne Hibiscus 1L")],
    ),
    (
        "Negroni", "נגרוני",
        "Gin, Campari and red vermouth.",
        "ג'ין, קמפרי וורמוט אדום.",
        "Rocks", "Orange peel", "קליפת תפוז",
        "Stir on ice, serve over a big cube.", "לערבב עם קרח ולהגיש על קוביית קרח.",
        [("Gin", 30, "Greenall's 1L"), ("Campari", 30, "Campari 1000ml"), ("Sweet Vermouth", 30, "Martini Rosso 1000ml")],
    ),
    (
        "Dionysus Penicillin", "דיוניסוס פניצילין",
        "Blended whisky, lemon, penicillin mix, smoky whisky float.",
        "ויסקי בלנדד, לימון, מיקס פניצילין, שפריץ ויסקי מעושן.",
        "Rocks", "Smoky whisky spray on top", "שפריץ ויסקי מעושן למעלה",
        "Shake first three, strain; float smoky whisky.", "לנער את שלושת הראשונים ולסנן; לצוף ויסקי מעושן.",
        [("Blended Whisky", 50, "Johnnie Walker Red 700ml"), ("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Penicillin Mix", 30, "Penicillin Mix 1L"), ("Smoky Whisky", 5, "JW Double Black 700ml")],
    ),
    (
        "Piña Colada", "פינה קולדה",
        "Rum, pineapple, coconut and lemon.",
        "רום, אננס, קוקוס ולימון.",
        "Highball", "Pineapple wedge", "פלח אננס",
        "Blend or shake with ice.", "לבנד או לנער עם קרח.",
        [("White Rum", 50, "Saint james imperial 700ml"), ("Pineapple Juice", 50, "Vedrenne Pineapple 1L"), ("Coconut Cream", 30, "Coconut Cream 400ml"), ("Lemon Juice", 30, "Vedrenne Lemon 1L")],
    ),
    (
        "Piña Diablo", "פינה דיאבלו",
        "Chili rum, pineapple, lemon and passion fruit syrup.",
        "רום צ'ילי, אננס, לימון וסירופ פסיפלורה.",
        "Highball", "Chili", "צ'ילי",
        "Shake with ice, strain.", "לנער עם קרח ולסנן.",
        [("Chili Rum", 50, "Bacardi Chili 700ml"), ("Pineapple Juice", 50, "Vedrenne Pineapple 1L"), ("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Passion Fruit Syrup", 15, "Vedrenne Passion Fruit 1L")],
    ),
    (
        "Jasmine", "ג'סמין",
        "Gin, triple sec, Campari, lemon and passion fruit syrup.",
        "ג'ין, טריפל סק, קמפרי, לימון וסירופ פסיפלורה.",
        "Coupe", "Lemon twist", "טוויסט לימון",
        "Shake with ice, strain.", "לנער עם קרח ולסנן.",
        [("Gin", 60, "Greenall's 1L"), ("Triple Sec", 15, "Vedrenne Triple Sec 700ml"), ("Campari", 15, "Campari 1000ml"), ("Lemon Juice", 30, "Vedrenne Lemon 1L"), ("Passion Fruit Syrup", 10, "Vedrenne Passion Fruit 1L")],
    ),
]


async def seed():
    async with async_session_maker() as session:
        async with session.begin():
            await ensure_hebrew_columns(session)
            user = await get_or_create_admin(session)

            # Kind + subcategories (get or create)
            kind_res = await session.execute(select(Kind).where(Kind.name == "Ingredient").limit(1))
            kind = kind_res.scalar_one_or_none()
            if not kind:
                kind = Kind(name="Ingredient", name_he="מרכיבים")
                session.add(kind)
                await session.flush()

            subcats_seed = [
                _hm("Spirit", "אלכוהול"),
                _hm("Liqueur", "ליקר"),
                _hm("Juice", "מיץ"),
                _hm("Syrup", "סירופ"),
                _hm("Sparkling", "מוגז"),
                _hm("Garnish", "קישוט"),
            ]
            subcat_by_name: dict[str, Subcategory] = {}
            for en, he in subcats_seed:
                res = await session.execute(select(Subcategory).where(Subcategory.kind_id == kind.id, Subcategory.name == en).limit(1))
                sc = res.scalar_one_or_none()
                if not sc:
                    sc = Subcategory(kind_id=kind.id, name=en, name_he=he)
                    session.add(sc)
                    await session.flush()
                subcat_by_name[en.lower()] = sc

            # Glass types (get or create)
            glass_seed = [("Coupe", "קופה", 180), ("Rocks", "רוקס", 250), ("Highball", "הייבול", 350), ("Collins", "קולינס", 400)]
            glass_by_name: dict[str, GlassType] = {}
            for en, he, cap in glass_seed:
                res = await session.execute(select(GlassType).where(GlassType.name == en).limit(1))
                gt = res.scalar_one_or_none()
                if not gt:
                    gt = GlassType(name=en, name_he=he, capacity_ml=cap)
                    session.add(gt)
                    await session.flush()
                glass_by_name[en.lower()] = gt

            # Load existing ingredients/bottles by name (so we don't duplicate if already seeded)
            res = await session.execute(select(Ingredient))
            ing_by_name: dict[str, Ingredient] = {i.name.lower(): i for i in res.scalars().all()}
            res = await session.execute(select(Bottle))
            bottle_by_name: dict[str, Bottle] = {b.name.lower(): b for b in res.scalars().all()}
            brand_by_name: dict[str, Brand] = {}
            res = await session.execute(select(Brand))
            for b in res.scalars().all():
                brand_by_name[b.name.lower()] = b

            today = date.today()

            for si in SIGNATURE_INGREDIENTS:
                bottles_to_use = _bottle_from_prices(si.name) or si.bottles
                if si.name.lower() in ing_by_name:
                    # Ingredient exists (e.g. from seed_everything_demo); still add signature bottles if missing
                    ing = ing_by_name[si.name.lower()]
                    for sb in bottles_to_use:
                        if sb.name.lower() in bottle_by_name:
                            continue
                        bottle = Bottle(
                            ingredient_id=ing.id,
                            name=sb.name,
                            name_he=sb.name_he,
                            volume_ml=sb.volume_ml,
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
                            )
                        )
                    continue
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

                for sb in bottles_to_use:
                    if sb.name.lower() in bottle_by_name:
                        continue
                    bottle = Bottle(
                        ingredient_id=ing.id,
                        name=sb.name,
                        name_he=sb.name_he,
                        volume_ml=sb.volume_ml,
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
                            source="seed_signature_menu",
                        )
                    )

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
            ) in SIGNATURE_COCKTAILS:
                res = await session.execute(select(CocktailRecipe).where(CocktailRecipe.name == name).limit(1))
                existing = res.scalar_one_or_none()
                if existing:
                    existing.menus = ["signature"]
                    existing.is_base = False
                    continue
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
                    is_base=False,
                    menus=["signature"],
                    preparation_method=prep,
                    preparation_method_he=prep_he,
                    batch_type=None,
                )
                session.add(c)
                await session.flush()

                for idx, (ing_name, qty, bottle_name) in enumerate(lines, start=1):
                    ing = ing_by_name.get(ing_name.lower())
                    bottle = bottle_by_name.get((bottle_name or "").lower()) if bottle_name else None
                    if not ing:
                        raise RuntimeError(f"Missing ingredient: {ing_name}")
                    session.add(
                        RecipeIngredient(
                            id=uuid.uuid4(),
                            recipe_id=c.id,
                            ingredient_id=ing.id,
                            quantity=qty,
                            unit="ml",
                            bottle_id=bottle.id if bottle else None,
                            sort_order=idx,
                            is_garnish=False,
                            is_optional=False,
                        )
                    )

        await session.commit()
    print("[seed_signature_menu] done.")


if __name__ == "__main__":
    asyncio.run(seed())
