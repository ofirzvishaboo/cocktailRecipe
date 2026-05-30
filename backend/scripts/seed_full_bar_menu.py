"""
Seed Full Bar Menu – The Cocktail Factory
Exact cocktail list from the physical menu (May 2026).

SIGNATURE (5): Cool(H)er, Freaky Tiki, Take Him to the Greek, Senorita, Hibiscus Cosmo
CLASSICS (7):  Negroni, Boulvardier, Mule(s), Jasmine, Basil Smash, Espresso Martini, Last Word
SPRITZ (4):   Lillet, Pampelle, Linoncello, Hugo

Strategy: delete ALL existing signature/classic/spritz cocktails, then recreate.
Also seeds beers and wines as beverage inventory items.

Run:
  docker exec -i cocktail-api sh -lc \
    "cd /app && PYTHONPATH=/app uv run python scripts/seed_full_bar_menu.py"
"""

import asyncio
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, text, or_  # noqa: E402
from fastapi_users.password import PasswordHelper  # noqa: E402

from db.database import async_session_maker  # noqa: E402
from db.users import User  # noqa: E402
from db.kind import Kind  # noqa: E402
from db.subcategory import Subcategory  # noqa: E402
from db.ingredient import Ingredient  # noqa: E402
from db.bottle import Bottle  # noqa: E402
from db.bottle_price import BottlePrice  # noqa: E402
from db.glass_type import GlassType  # noqa: E402
from db.cocktail_recipe import CocktailRecipe  # noqa: E402
from db.recipe_ingredient import RecipeIngredient  # noqa: E402

password_helper = PasswordHelper()

# ──────────────────────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SeedBottle:
    name: str
    name_he: str | None
    volume_ml: int
    price_ils: float


@dataclass(frozen=True)
class SeedIngredient:
    name: str
    name_he: str | None
    subcategory_name: str
    subcategory_name_he: str
    bottles: list[SeedBottle]


@dataclass
class SeedCocktail:
    name: str
    name_he: str
    description: str
    description_he: str
    glass: str
    garnish: str
    garnish_he: str
    prep: str
    prep_he: str
    menu: str
    lines: list[tuple[str, int]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Ingredients
# ──────────────────────────────────────────────────────────────────────────────

COCKTAIL_INGREDIENTS: list[SeedIngredient] = [
    # ── Spirits / infusions ──
    SeedIngredient("Lemongrass Gin", "ג׳ין למון גראס", "Spirit", "אלכוהול",
        [SeedBottle("Lemongrass Infused Gin 700ml", "ג׳ין בהשריית למון גראס 700 מ״ל", 700, 95.0)]),
    SeedIngredient("Elderflower Liqueur", "ליקר אלדר פלוואר", "Liqueur", "ליקר",
        [SeedBottle("St-Germain 700ml", "סן ז'רמן 700 מ״ל", 700, 169.0)]),
    SeedIngredient("Cinnamon Rum", "רום קינמון", "Spirit", "אלכוהול",
        [SeedBottle("Cinnamon Infused Rum 700ml", "רום בהשריית קינמון 700 מ״ל", 700, 80.0)]),
    SeedIngredient("Rhubarb Liqueur", "ליקר רוברב", "Liqueur", "ליקר",
        [SeedBottle("Rhubarb Liqueur 700ml", "ליקר רוברב 700 מ״ל", 700, 95.0)]),
    SeedIngredient("Orange Peel Ouzo", "אוזו קליפות תפוז", "Spirit", "אלכוהול",
        [SeedBottle("Orange Peel Infused Ouzo 700ml", "אוזו בהשריית קליפות תפוז 700 מ״ל", 700, 80.0)]),
    SeedIngredient("Tequila Blanco", "טקילה", "Spirit", "אלכוהול",
        [SeedBottle("Lunazul 700ml", "לונאזול 700 מ״ל", 700, 106.0)]),
    SeedIngredient("Mezcal", "מזקל", "Spirit", "אלכוהול",
        [SeedBottle("San Cosme Mezcal 700ml", "סן קוסמה מזקל 700 מ״ל", 700, 120.0)]),
    SeedIngredient("Lemon Vodka", "וודקה לימון", "Spirit", "אלכוהול",
        [SeedBottle("Lemon Infused Vodka 700ml", "וודקה בהשריית לימון 700 מ״ל", 700, 70.0)]),
    SeedIngredient("Gin", "ג׳ין", "Spirit", "אלכוהול",
        [SeedBottle("Greenall's 1L", "גרינלס 1 ליטר", 1000, 85.0)]),
    SeedIngredient("Campari", "קמפרי", "Liqueur", "ליקר",
        [SeedBottle("Campari 1000ml", "קמפרי 1000 מ״ל", 1000, 119.90)]),
    SeedIngredient("Sweet Vermouth", "וורמוט אדום", "Liqueur", "ליקר",
        [SeedBottle("Martini Rosso 1000ml", "מרטיני רוסו 1000 מ״ל", 1000, 59.90)]),
    SeedIngredient("Bourbon Whiskey", "ויסקי בורבון", "Spirit", "אלכוהול",
        [SeedBottle("Maker's Mark 700ml", "מייקרס מארק 700 מ״ל", 700, 129.0)]),
    SeedIngredient("Vodka", "וודקה", "Spirit", "אלכוהול",
        [SeedBottle("Mont Blanc Vodka 700ml", "מון בלאן וודקה 700 מ״ל", 700, 69.90)]),
    SeedIngredient("Green Chartreuse", "שרטרז ירוק", "Liqueur", "ליקר",
        [SeedBottle("Green Chartreuse 700ml", "שרטרז ירוק 700 מ״ל", 700, 180.0)]),
    SeedIngredient("Maraschino Liqueur", "ליקר מרסקינו", "Liqueur", "ליקר",
        [SeedBottle("Luxardo Maraschino 700ml", "לוקסארדו מרסקינו 700 מ״ל", 700, 95.0)]),
    SeedIngredient("Lillet Blanc", "לילה בלאן", "Liqueur", "ליקר",
        [SeedBottle("Lillet Blanc 750ml", "לילה בלאן 750 מ״ל", 750, 95.0)]),
    SeedIngredient("Pampelle", "פמפל", "Liqueur", "ליקר",
        [SeedBottle("Pampelle 700ml", "פמפל 700 מ״ל", 700, 95.0)]),
    SeedIngredient("Limoncello", "לימונצ׳לו", "Liqueur", "ליקר",
        [SeedBottle("Dionisius Limoncello 700ml", "דיוניסוס לימונצ׳לו 700 מ״ל", 700, 60.0)]),
    SeedIngredient("Triple Sec", "טריפל סק", "Liqueur", "ליקר",
        [SeedBottle("Vedrenne Triple Sec 700ml", "ודרן טריפל סק 700 מ״ל", 700, 80.0)]),
    SeedIngredient("Coffee Liqueur", "ליקר קפה", "Liqueur", "ליקר",
        [SeedBottle("Kahlua 700ml", "קהלואה 700 מ״ל", 700, 95.0)]),
    # ── Juices ──
    SeedIngredient("Apple Lime Juice", "מיץ תפוח ליים", "Juice", "מיץ",
        [SeedBottle("Apple Lime Juice 1L", "מיץ תפוח ליים 1 ליטר", 1000, 18.0)]),
    SeedIngredient("Lime Juice", "מיץ ליים", "Juice", "מיץ",
        [SeedBottle("Fresh Lime Juice 1L", "מיץ ליים טרי 1 ליטר", 1000, 20.0)]),
    SeedIngredient("Pineapple Juice", "מיץ אננס", "Juice", "מיץ",
        [SeedBottle("Pineapple Juice 1L", "מיץ אננס 1 ליטר", 1000, 16.0)]),
    SeedIngredient("Lemon Juice", "מיץ לימון", "Juice", "מיץ",
        [SeedBottle("Lemon Juice 1L", "מיץ לימון 1 ליטר", 1000, 18.0)]),
    SeedIngredient("Red Grapefruit Juice", "מיץ אשכולית אדומה", "Juice", "מיץ",
        [SeedBottle("Red Grapefruit Juice 1L", "מיץ אשכולית אדומה 1 ליטר", 1000, 18.0)]),
    SeedIngredient("Espresso", "אספרסו", "Juice", "מיץ",
        [SeedBottle("Espresso Shot", "שוט אספרסו", 30, 5.0)]),
    # ── Syrups / purées ──
    SeedIngredient("Green Tea Syrup", "סירופ תה ירוק", "Syrup", "סירופ",
        [SeedBottle("Green Tea Syrup 1L", "סירופ תה ירוק 1 ליטר", 1000, 25.0)]),
    SeedIngredient("Passion Fruit Purée", "מחית פסיפלורה", "Syrup", "סירופ",
        [SeedBottle("Passion Fruit Purée 1L", "מחית פסיפלורה 1 ליטר", 1000, 45.0)]),
    SeedIngredient("Almond Syrup", "סירופ שקדים", "Syrup", "סירופ",
        [SeedBottle("Almond Syrup 1L", "סירופ שקדים 1 ליטר", 1000, 26.0)]),
    SeedIngredient("Chili Ginger Syrup", "סירופ פלפל ג׳ינג׳ר", "Syrup", "סירופ",
        [SeedBottle("Chili Ginger Syrup 1L", "סירופ פלפל ג׳ינג׳ר 1 ליטר", 1000, 28.0)]),
    SeedIngredient("Hibiscus Syrup", "סירופ היביסקוס", "Syrup", "סירופ",
        [SeedBottle("Hibiscus Syrup 1L", "סירופ היביסקוס 1 ליטר", 1000, 30.0)]),
    SeedIngredient("Yuzu Purée", "מחית יוזו", "Syrup", "סירופ",
        [SeedBottle("Yuzu Purée 1L", "מחית יוזו 1 ליטר", 1000, 55.0)]),
    SeedIngredient("Simple Syrup", "סירופ סוכר", "Syrup", "סירופ",
        [SeedBottle("Simple Syrup 1L", "סירופ סוכר 1 ליטר", 1000, 12.0)]),
    SeedIngredient("Red Wine", "יין אדום", "Syrup", "סירופ",
        [SeedBottle("House Red Wine 750ml", "יין אדום בית 750 מ״ל", 750, 45.0)]),
    # ── Sparkling / sodas ──
    SeedIngredient("Ginger Beer", "בירת ג׳ינג׳ר", "Sparkling", "מוגז",
        [SeedBottle("Ginger Beer 200ml", "בירת ג׳ינג׳ר 200 מ״ל", 200, 8.0)]),
    SeedIngredient("Prosecco", "פרוסקו", "Sparkling", "מוגז",
        [SeedBottle("Gancia Prosecco 750ml", "גנציה פרוסקו 750 מ״ל", 750, 65.0)]),
    SeedIngredient("Soda Water", "מים מוגזים", "Sparkling", "מוגז",
        [SeedBottle("Soda Water 1L", "מים מוגזים 1 ליטר", 1000, 5.0)]),
    # ── Garnish ──
    SeedIngredient("Fresh Basil", "בזיליקום טרי", "Garnish", "קישוט",
        [SeedBottle("Fresh Basil 100g", "בזיליקום טרי 100 גרם", 100, 8.0)]),
    SeedIngredient("Mint Leaves", "עלי נענע", "Garnish", "קישוט",
        [SeedBottle("Fresh Mint 100g", "נענע טרייה 100 גרם", 100, 10.0)]),
]

# ──────────────────────────────────────────────────────────────────────────────
# The exact menu – 16 cocktails
# ──────────────────────────────────────────────────────────────────────────────

ALL_COCKTAILS: list[SeedCocktail] = [
    # ── FACTORY SIGNATURE ──
    SeedCocktail(
        name="Cool(H)er", name_he="קול(ה)ר",
        description="Floral & refreshing long drink",
        description_he="קוקטייל ארוך פרחוני ומרענן",
        glass="Collins", garnish="Lemongrass stalk", garnish_he="גבעול למון גראס",
        prep="Shake with ice, strain into a Collins glass over ice.",
        prep_he="לנער עם קרח ולסנן לכוס קולינס על קרח.",
        menu="signature",
        lines=[
            ("Lemongrass Gin", 50),
            ("Elderflower Liqueur", 20),
            ("Apple Lime Juice", 30),
            ("Lime Juice", 20),
            ("Green Tea Syrup", 10),
        ],
    ),
    SeedCocktail(
        name="Freaky Tiki", name_he="פריקי טיקי",
        description="Tropical & fruity tiki cocktail",
        description_he="קוקטייל טיקי טרופי ופירותי",
        glass="Highball", garnish="Pineapple wedge and cinnamon stick", garnish_he="פלח אננס ומקל קינמון",
        prep="Shake with ice, strain over crushed ice.",
        prep_he="לנער עם קרח ולסנן על קרח כתוש.",
        menu="signature",
        lines=[
            ("Cinnamon Rum", 50),
            ("Rhubarb Liqueur", 20),
            ("Pineapple Juice", 30),
            ("Lemon Juice", 20),
            ("Passion Fruit Purée", 15),
        ],
    ),
    SeedCocktail(
        name="Take Him to the Greek", name_he="שקיעה יוונית",
        description="Citrus & herbal with a red wine float",
        description_he="קוקטייל הדרי ועשבוני עם יין אדום",
        glass="Highball", garnish="Grapefruit slice", garnish_he="פרוסת אשכולית",
        prep="Build over ice; float red wine last.",
        prep_he="לבנות על קרח; לצוף יין אדום בסוף.",
        menu="signature",
        lines=[
            ("Orange Peel Ouzo", 60),
            ("Red Grapefruit Juice", 50),
            ("Lime Juice", 20),
            ("Almond Syrup", 15),
            ("Red Wine", 10),
        ],
    ),
    SeedCocktail(
        name="Senorita", name_he="סניוריטה",
        description="Spicy & smoky agave sour",
        description_he="קוקטייל אגב חריף ומעושן",
        glass="Rocks", garnish="Chili slice", garnish_he="פרוסת צ׳ילי",
        prep="Shake with ice, strain over a large cube.",
        prep_he="לנער עם קרח ולסנן על קוביית קרח גדולה.",
        menu="signature",
        lines=[
            ("Tequila Blanco", 40),
            ("Mezcal", 20),
            ("Triple Sec", 20),
            ("Lime Juice", 15),
            ("Chili Ginger Syrup", 10),
        ],
    ),
    SeedCocktail(
        name="Hibiscus Cosmo", name_he="היביסקוס קוסמו",
        description="Floral & tart citrus cosmopolitan",
        description_he="קוסמופוליטן פרחוני וחמצמץ",
        glass="Coupe", garnish="Dehydrated lemon wheel", garnish_he="גלגל לימון מיובש",
        prep="Shake with ice, double-strain into a chilled coupe.",
        prep_he="לנער עם קרח ולסנן פעמיים לקופ מקורר.",
        menu="signature",
        lines=[
            ("Lemon Vodka", 50),
            ("Triple Sec", 20),
            ("Hibiscus Syrup", 15),
            ("Yuzu Purée", 15),
        ],
    ),
    # ── CLASSICS ──
    SeedCocktail(
        name="Negroni", name_he="נגרוני",
        description="Bitter & aromatic Italian classic",
        description_he="קלאסיק איטלקי מר ואורומטי",
        glass="Rocks", garnish="Orange peel", garnish_he="קליפת תפוז",
        prep="Stir on ice, serve over a large cube.",
        prep_he="לערבב עם קרח ולהגיש על קוביית קרח גדולה.",
        menu="classic",
        lines=[("Gin", 30), ("Campari", 30), ("Sweet Vermouth", 30)],
    ),
    SeedCocktail(
        name="Boulvardier", name_he="בולוורדייה",
        description="Bourbon twist on the Negroni",
        description_he="נגרוני עם בורבון",
        glass="Rocks", garnish="Orange peel", garnish_he="קליפת תפוז",
        prep="Stir on ice, serve over a large cube.",
        prep_he="לערבב עם קרח ולהגיש על קוביית קרח גדולה.",
        menu="classic",
        lines=[("Bourbon Whiskey", 45), ("Campari", 25), ("Sweet Vermouth", 25)],
    ),
    SeedCocktail(
        name="Mule(s)", name_he="מיול",
        description="Crisp & refreshing ginger highball",
        description_he="קוקטייל ג׳ינג׳ר מרענן וצונן",
        glass="Highball", garnish="Lime wedge and ginger", garnish_he="פלח ליים וג׳ינג׳ר",
        prep="Build in glass over ice; top with ginger beer.",
        prep_he="לבנות בכוס על קרח; לסיים בבירת ג׳ינג׳ר.",
        menu="classic",
        lines=[("Vodka", 50), ("Lime Juice", 20), ("Ginger Beer", 120)],
    ),
    SeedCocktail(
        name="Jasmine", name_he="ג׳סמין",
        description="Light & bittersweet gin sour",
        description_he="סאור ג׳ין קליל ומתוק-מר",
        glass="Coupe", garnish="Lemon twist", garnish_he="טוויסט לימון",
        prep="Shake with ice, strain into a chilled coupe.",
        prep_he="לנער עם קרח ולסנן לקופ מקורר.",
        menu="classic",
        lines=[("Gin", 45), ("Triple Sec", 15), ("Campari", 15), ("Lemon Juice", 30)],
    ),
    SeedCocktail(
        name="Basil Smash", name_he="בזיל סמאש",
        description="Herbaceous & fresh garden sour",
        description_he="סאור עשבוני ורענן מהגינה",
        glass="Rocks", garnish="Basil sprig", garnish_he="ענף בזיליקום",
        prep="Muddle basil, shake all with ice, double-strain over ice.",
        prep_he="למוסס בזיליקום, לנער הכל עם קרח ולסנן על קרח.",
        menu="classic",
        lines=[("Gin", 50), ("Lemon Juice", 25), ("Simple Syrup", 15), ("Fresh Basil", 8)],
    ),
    SeedCocktail(
        name="Espresso Martini", name_he="אספרסו מרטיני",
        description="Rich & energising coffee cocktail",
        description_he="קוקטייל קפה עשיר ומעורר",
        glass="Coupe", garnish="Three coffee beans", garnish_he="שלושה פולי קפה",
        prep="Shake vigorously with ice, strain into a chilled coupe.",
        prep_he="לנער בחוזקה עם קרח ולסנן לקופ מקורר.",
        menu="classic",
        lines=[("Vodka", 50), ("Coffee Liqueur", 25), ("Espresso", 30), ("Simple Syrup", 10)],
    ),
    SeedCocktail(
        name="Last Word", name_he="המילה האחרונה",
        description="Equal parts herbal & balanced classic",
        description_he="קלאסיק עשבוני ומאוזן בחלקים שווים",
        glass="Coupe", garnish="Lime wheel", garnish_he="גלגל ליים",
        prep="Shake with ice, strain into a chilled coupe.",
        prep_he="לנער עם קרח ולסנן לקופ מקורר.",
        menu="classic",
        lines=[("Gin", 25), ("Green Chartreuse", 25), ("Maraschino Liqueur", 25), ("Lime Juice", 25)],
    ),
    # ── SPRITZ ──
    SeedCocktail(
        name="Lillet Spritz", name_he="לילה ספריץ׳",
        description="Light & elegant aperitif spritz",
        description_he="ספריץ׳ אפריטיף קליל ואלגנטי",
        glass="Highball", garnish="Orange slice", garnish_he="פרוסת תפוז",
        prep="Build in glass over ice.",
        prep_he="לבנות בכוס על קרח.",
        menu="spritz",
        lines=[("Lillet Blanc", 60), ("Prosecco", 60), ("Soda Water", 30)],
    ),
    SeedCocktail(
        name="Pampelle Spritz", name_he="פמפל ספריץ׳",
        description="Grapefruit & bubbly aperitif spritz",
        description_he="ספריץ׳ אשכולית מרענן ומבעבע",
        glass="Highball", garnish="Grapefruit slice", garnish_he="פרוסת אשכולית",
        prep="Build in glass over ice.",
        prep_he="לבנות בכוס על קרח.",
        menu="spritz",
        lines=[("Pampelle", 60), ("Prosecco", 90), ("Soda Water", 30)],
    ),
    SeedCocktail(
        name="Linoncello Spritz", name_he="לימונצ׳לו ספריץ׳",
        description="Bright lemon Italian sparkler",
        description_he="ספריץ׳ לימוני איטלקי ומרענן",
        glass="Highball", garnish="Lemon wheel", garnish_he="גלגל לימון",
        prep="Build in glass over ice.",
        prep_he="לבנות בכוס על קרח.",
        menu="spritz",
        lines=[("Limoncello", 45), ("Prosecco", 90), ("Soda Water", 30)],
    ),
    SeedCocktail(
        name="Hugo", name_he="הוגו",
        description="Floral & refreshing elderflower spritz",
        description_he="ספריץ׳ אלדר פלוואר פרחוני ורענן",
        glass="Highball", garnish="Mint sprig and lime slice", garnish_he="ענף נענע ופרוסת ליים",
        prep="Build in glass over ice.",
        prep_he="לבנות בכוס על קרח.",
        menu="spritz",
        lines=[
            ("Elderflower Liqueur", 30),
            ("Prosecco", 90),
            ("Lime Juice", 15),
            ("Mint Leaves", 5),
            ("Soda Water", 30),
        ],
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# Beers & Wines (inventory beverage items)
# ──────────────────────────────────────────────────────────────────────────────

BEVERAGE_ITEMS: list[tuple[str, str, str, str, int]] = [
    # (name, name_he, subcategory_en, subcategory_he, price_ils)
    ("Hobgoblin IPA", "הובגובלין IPA", "Beer – Tap", "בירה – שאיבה", 32),
    ("Tucher Lager", "טוכר לאגר", "Beer – Tap", "בירה – שאיבה", 29),
    ("Tucher Weiss", "טוכר ווייס", "Beer – Tap", "בירה – שאיבה", 29),
    ("Peroni", "פרוני", "Beer – Bottle", "בירה – בקבוק", 29),
    ("Flora Cactus & Lime", "פלורה קקטוס וליים", "Beer – Bottle", "בירה – בקבוק", 31),
    ("Kozel Dark Lager", "קוזל דארק לאגר", "Beer – Bottle", "בירה – בקבוק", 31),
    ("Guinness", "גינס", "Beer – Bottle", "בירה – בקבוק", 32),
    ("Brewdog Wingman", "ברודוג ווינגמן", "Beer – Can", "בירה – פחית", 31),
    ("Brewdog Fruit Burst", "ברודוג פרוט ברסט", "Beer – Can", "בירה – פחית", 31),
    ("Brewdog X-Mass Edition", "ברודוג מהדורת חג", "Beer – Can", "בירה – פחית", 31),
    ("Brewdog Hazy Jane", "ברודוג הייזי ג׳ין", "Beer – Can", "בירה – פחית", 31),
    ("Shoshana", "שושנה", "Beer – Can", "בירה – פחית", 32),
    ("Gancia Prosecco", "גנציה פרוסקו", "Sparkling Wine", "יין מבעבע", 43),
    ("Alfabeto Vento", "אלפבטו ונטו", "Sparkling Wine", "יין מבעבע", 47),
    ("Janela Branca White", "ג׳נלה ברנקה לבן", "Wine – White", "יין לבן", 38),
    ("Yarden Har Hermon", "ירדן הר הרמון", "Wine – White", "יין לבן", 41),
    ("Luis Eschenhauer Sauvignon Blanc", "לואיס אשנהאואר סוביניון בלאן", "Wine – White", "יין לבן", 43),
    ("Kastel La Vie White", "קסטל לה-וי לבן", "Wine – White", "יין לבן", 45),
    ("Chablis", "שבליס", "Wine – White", "יין לבן", 61),
    ("Hans Baer Gorz", "האנס בר גורץ", "Wine – White", "יין לבן", 47),
    ("Janela Branca Rosé", "ג׳נלה ברנקה רוזה", "Wine – Rosé", "יין רוזה", 40),
    ("Miraval Rosé", "מירוול רוזה", "Wine – Rosé", "יין רוזה", 65),
    ("Piccini Memoro", "פיצ׳יני ממורו", "Wine – Red", "יין אדום", 40),
    ("Janela Branca Red", "ג׳נלה ברנקה אדום", "Wine – Red", "יין אדום", 41),
    ("Kastel La Vie Red", "קסטל לה-וי אדום", "Wine – Red", "יין אדום", 45),
]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

async def ensure_columns(session) -> None:
    for stmt in [
        "ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS menus TEXT[] DEFAULT '{}'",
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
        is_active=True, is_superuser=True, is_verified=True,
        first_name="Admin", last_name="User",
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_kind(session, name, name_he) -> Kind:
    res = await session.execute(select(Kind).where(Kind.name == name).limit(1))
    k = res.scalar_one_or_none()
    if not k:
        k = Kind(name=name, name_he=name_he)
        session.add(k)
        await session.flush()
    return k


async def get_or_create_subcat(session, kind_id, name, name_he) -> Subcategory:
    res = await session.execute(
        select(Subcategory).where(Subcategory.kind_id == kind_id, Subcategory.name == name).limit(1)
    )
    sc = res.scalar_one_or_none()
    if not sc:
        sc = Subcategory(kind_id=kind_id, name=name, name_he=name_he)
        session.add(sc)
        await session.flush()
    return sc


async def get_or_create_glass(session, name, name_he, capacity_ml) -> GlassType:
    res = await session.execute(select(GlassType).where(GlassType.name == name).limit(1))
    gt = res.scalar_one_or_none()
    if not gt:
        gt = GlassType(name=name, name_he=name_he, capacity_ml=capacity_ml)
        session.add(gt)
        await session.flush()
    return gt


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

async def seed():
    async with async_session_maker() as session:
        async with session.begin():
            await ensure_columns(session)
            user = await get_or_create_admin(session)
            today = date.today()

            # ── Delete ALL cocktails in managed menus (clean slate) ──
            managed_menus = ["signature", "classic", "spritz", "seasonal"]
            res = await session.execute(select(CocktailRecipe))
            all_recipes = res.scalars().all()
            deleted = 0
            for r in all_recipes:
                menus = list(r.menus or [])
                if any(m in managed_menus for m in menus) or (not menus):
                    await session.delete(r)
                    deleted += 1
            await session.flush()
            print(f"  deleted {deleted} old cocktails")

            # ── Ingredient kind + subcategories ──
            ing_kind = await get_or_create_kind(session, "Ingredient", "מרכיבים")
            subcat_map: dict[str, Subcategory] = {}
            for en, he in [
                ("Spirit", "אלכוהול"), ("Liqueur", "ליקר"), ("Juice", "מיץ"),
                ("Syrup", "סירופ"), ("Sparkling", "מוגז"), ("Garnish", "קישוט"),
            ]:
                subcat_map[en] = await get_or_create_subcat(session, ing_kind.id, en, he)

            # ── Beverage kind + subcategories ──
            bev_kind = await get_or_create_kind(session, "Beverage", "משקאות")
            bev_subcat_map: dict[str, Subcategory] = {}
            for en, he in [
                ("Beer – Tap", "בירה – שאיבה"), ("Beer – Bottle", "בירה – בקבוק"),
                ("Beer – Can", "בירה – פחית"), ("Sparkling Wine", "יין מבעבע"),
                ("Wine – White", "יין לבן"), ("Wine – Rosé", "יין רוזה"), ("Wine – Red", "יין אדום"),
            ]:
                bev_subcat_map[en] = await get_or_create_subcat(session, bev_kind.id, en, he)

            # ── Glass types ──
            glass_map: dict[str, GlassType] = {}
            for en, he, cap in [
                ("Coupe", "קופ", 180), ("Rocks", "רוקס", 250),
                ("Highball", "הייבול", 350), ("Collins", "קולינס", 400),
            ]:
                glass_map[en.lower()] = await get_or_create_glass(session, en, he, cap)

            # ── Load existing ingredients & bottles ──
            res = await session.execute(select(Ingredient))
            ing_by_name: dict[str, Ingredient] = {i.name.lower(): i for i in res.scalars()}
            res = await session.execute(select(Bottle))
            bottle_by_name: dict[str, Bottle] = {b.name.lower(): b for b in res.scalars()}

            # ── Seed cocktail ingredients ──
            for si in COCKTAIL_INGREDIENTS:
                if si.name.lower() in ing_by_name:
                    ing = ing_by_name[si.name.lower()]
                else:
                    sc = subcat_map.get(si.subcategory_name)
                    ing = Ingredient(
                        name=si.name, name_he=si.name_he,
                        kind_id=ing_kind.id,
                        subcategory_id=sc.id if sc else None,
                    )
                    session.add(ing)
                    await session.flush()
                    ing_by_name[si.name.lower()] = ing

                for sb in si.bottles:
                    if sb.name.lower() in bottle_by_name:
                        continue
                    bottle = Bottle(
                        ingredient_id=ing.id, name=sb.name, name_he=sb.name_he,
                        volume_ml=sb.volume_ml, is_default_cost=True,
                    )
                    session.add(bottle)
                    await session.flush()
                    bottle_by_name[sb.name.lower()] = bottle
                    session.add(BottlePrice(
                        bottle_id=bottle.id,
                        price_minor=int(round(sb.price_ils * 100)),
                        currency="ILS", start_date=today, end_date=None,
                        source="seed_full_bar_menu",
                    ))

            # ── Seed beverage items (beers & wines) ──
            for bev_name, bev_name_he, subcat_en, _subcat_he, price_ils in BEVERAGE_ITEMS:
                if bev_name.lower() not in ing_by_name:
                    bev_sc = bev_subcat_map.get(subcat_en)
                    bev_ing = Ingredient(
                        name=bev_name, name_he=bev_name_he,
                        kind_id=bev_kind.id,
                        subcategory_id=bev_sc.id if bev_sc else None,
                    )
                    session.add(bev_ing)
                    await session.flush()
                    ing_by_name[bev_name.lower()] = bev_ing
                else:
                    bev_ing = ing_by_name[bev_name.lower()]

                bottle_key = f"{bev_name.lower()} glass"
                if bottle_key not in bottle_by_name:
                    bev_bottle = Bottle(
                        ingredient_id=bev_ing.id, name=f"{bev_name} (glass)",
                        name_he=f"{bev_name_he} (כוס)", volume_ml=330, is_default_cost=True,
                    )
                    session.add(bev_bottle)
                    await session.flush()
                    bottle_by_name[bottle_key] = bev_bottle
                    session.add(BottlePrice(
                        bottle_id=bev_bottle.id, price_minor=price_ils * 100,
                        currency="ILS", start_date=today, end_date=None,
                        source="seed_full_bar_menu",
                    ))

            # ── Seed the 16 cocktails ──
            for sc in ALL_COCKTAILS:
                gt = glass_map.get(sc.glass.lower())
                recipe = CocktailRecipe(
                    created_by_user_id=user.id,
                    name=sc.name, name_he=sc.name_he,
                    description=sc.description, description_he=sc.description_he,
                    glass_type_id=gt.id if gt else None,
                    garnish_text=sc.garnish, garnish_text_he=sc.garnish_he,
                    preparation_method=sc.prep, preparation_method_he=sc.prep_he,
                    is_base=False, menus=[sc.menu], batch_type=None, picture_url=None,
                )
                session.add(recipe)
                await session.flush()

                for idx, (ing_name, qty_ml) in enumerate(sc.lines, start=1):
                    ing = ing_by_name.get(ing_name.lower())
                    if not ing:
                        print(f"  WARNING: ingredient '{ing_name}' not found for '{sc.name}'")
                        continue
                    first_bottle = next(
                        (b for b in bottle_by_name.values() if b.ingredient_id == ing.id), None
                    )
                    session.add(RecipeIngredient(
                        id=uuid.uuid4(), recipe_id=recipe.id,
                        ingredient_id=ing.id, quantity=qty_ml, unit="ml",
                        bottle_id=first_bottle.id if first_bottle else None,
                        sort_order=idx, is_garnish=False, is_optional=False,
                    ))
                print(f"  created [{sc.menu}]: {sc.name}")

        await session.commit()
    print("[seed_full_bar_menu] done.")


if __name__ == "__main__":
    asyncio.run(seed())
