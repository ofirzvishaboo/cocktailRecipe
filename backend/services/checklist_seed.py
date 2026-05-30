"""Seed default opening/closing checklist templates (Bar Merlin)."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.checklist import ChecklistItem, ChecklistSection, ChecklistTemplate

OPENING_TEMPLATE_ID = uuid.UUID("a1000001-0001-4001-8001-000000000001")
CLOSING_TEMPLATE_ID = uuid.UUID("a1000001-0001-4001-8001-000000000002")

OPENING_SECTIONS = [
    {
        "id": uuid.UUID("a1000002-0002-4002-8002-000000000001"),
        "key": "completeness",
        "title_he": "השלמות",
        "title_en": "Completeness",
        "sort_order": 0,
        "section_type": "checkbox",
        "items": [
            ("clock_in", "לפני הכל – להיכנס לשעון", "First — clock in"),
            (
                "stock_levels",
                "מלאים: שתיה קלה זכוכית, 6 מכל יין ו-8 שרדונה, בקאפ ספיד וקוקטיילים: 1 מכל אחד מתחת לכיור, 1 מכל אחד מאחור ארגז בק אפ, דיספליי אם משהו עומד להיגמר, שתיה קלה 1.5 ליטר – 2 מכל אחד ( אשכוליות,לימונענע, תפוזים,חמוציות)",
                "Stock: soft drinks, wine, speed rail & cocktails under sink and back bar, display restock, 1.5L soft drinks (2 each: grapefruit, lemon-mint, orange, cranberry)",
            ),
            (
                "freezer",
                "מקפיא: 2 גרייגוס, 2 סטולי, 2 ערק, 1 טקילה, 1 ייגר, זוברובקה",
                "Freezer: 2 Grey Goose, 2 Stoli, 2 Arak, 1 Tequila, 1 Jäger, Zubrowka",
            ),
            (
                "cocktails_stock",
                "קוקטיילים: 2 מכל אחד : וודקה חריפה, טוניק, ג'ינג'ר ביר, קוביות קרח גדולות, קיסמי קוקטייל, קשי קרטון",
                "Cocktails: 2 each — spicy vodka, tonic, ginger beer, large ice cubes, cocktail picks, paper straws",
            ),
            (
                "kegs",
                "חביות ספייר: לוונבראו מתחת לכיור, בקס ובלו מון מתחת לחבית המחוברת",
                "Spare kegs: Leffe Blonde under sink, Beck's and Blue Moon under connected keg",
            ),
            (
                "table_setup",
                "עריכה: צלחות, סכום, מגבונים, קיסמים, מפיות עריכה, מפיות קוקטייל, קוקוטים וצלוחיות, תפריטים, רטבים (מיונש,קטשופ,חרדל,סרירצה)",
                "Table setup: plates, cutlery, wipes, picks, table napkins, cocktail napkins, coasters & saucers, menus, sauces",
            ),
            (
                "cleaning_supplies",
                "ניקיון: נייר עבודה, מגבונים ניקוי, שפריצר כחול, סקוטצ', סבון כלים, סבון ידיים, כפפות ל-טקס",
                "Cleaning: paper towels, cleaning wipes, blue spray, scotch pads, dish soap, hand soap, gloves for tax",
            ),
            (
                "glasses_water",
                "כוסות וקנקני מים",
                "Glasses and water jugs",
            ),
            (
                "register",
                "קופה: כוס טיפים, פריטה, מגשיות עודף, עטים, דוקרני בונים",
                "Register: tip jar, receipt roll, spare trays, pens, order spikes",
            ),
        ],
    },
    {
        "id": uuid.UUID("a1000002-0002-4002-8002-000000000002"),
        "key": "preparations",
        "title_he": "הכנות",
        "title_en": "Preparations",
        "sort_order": 1,
        "section_type": "checkbox",
        "items": [
            (
                "garnishes",
                "גרנישים: אננס משולשים, תפוז מיובש, מקלות קינמון, גינגר מסוכר, כוכבי אניס, סטריפים מלפפון, קוביות מלפפון, טחין, פלפל, לימונים, תפוזים, תפוזים בלו מון, נענע ובזיליקום עם קרח ומעט מים",
                "Garnishes: pineapple triangles, dried orange, cinnamon sticks, candied ginger, star anise, cucumber strips/cubes, tahini, pepper, lemons, oranges, Blue Moon oranges, mint & basil with ice and water",
            ),
            (
                "cocktail_prep",
                "קוקטיילים: אננס, מיץ לימון, אשכולית אדומה, תפוזים, סירופים, מי סוכר, מקציף, גרנדין + ספיירים",
                "Cocktails: pineapple, lemon juice, red grapefruit, oranges, syrups, sugar water, foamer, grenadine + spares",
            ),
            ("beer_gas", "בדיקת שעוני גז של הבירה", "Check beer gas gauges"),
            ("run_beers", "הרצת בירות", "Run beer lines"),
            ("fill_water_jugs", "מילוי קנקני מים", "Fill water jugs"),
            (
                "speed_rail",
                "סידור ספיד קוקטיילים לפי הסוגים, סידור ספיד והוצאת אפרול מהמקרר",
                "Organize cocktail speed rail by type, organize speed rail, take Aperol out of fridge",
            ),
            ("condoms_pourers", "הורדת קונדומים, לשים פוררים", "Put on bottle condoms and pourers"),
            (
                "champagne_bucket",
                "שמפניירה גדולה: 1 מכל סוג יין וקאווה + קרח",
                "Large champagne bucket: 1 of each wine and cava + ice",
            ),
            ("ice", "קרח וקרח גרוס", "Ice and crushed ice"),
        ],
    },
    {
        "id": uuid.UUID("a1000002-0002-4002-8002-000000000003"),
        "key": "daily_rotation",
        "title_he": "משימה יומית",
        "title_en": "Daily task",
        "sort_order": 2,
        "section_type": "daily_rotation",
        "items": [
            (0, "day_sun", "יום א' - ניקוי דיספליי", "Sunday — clean display"),
            (1, "day_mon", "יום ב' - הברקת קנקני מים, הברקת שמפניירה גדולה", "Monday — polish water jugs and champagne bucket"),
            (2, "day_tue", "יום ג' - ניקיון רגליים של כיסאות בר", "Tuesday — clean bar stool legs"),
            (3, "day_wed", "יום ד' - רשימת מלאי", "Wednesday — inventory list"),
            (4, "day_thu", "יום ה' - ניקיון מקררי יין מבפנים", "Thursday — clean wine fridges inside"),
            (5, "day_fri", "יום ו' - ניקיון מקרר קוקטיילים/גרנishes מבפנים", "Friday — clean cocktail/garnish fridge inside"),
            (6, "day_sat", "יום ש' – השרייה של הספוגים של מכונת הפוליש במים + ג'el כביסה", "Saturday — soak polish machine sponges in water + laundry gel"),
        ],
    },
    {
        "id": uuid.UUID("a1000002-0002-4002-8002-000000000004"),
        "key": "briefing",
        "title_he": "תדריך",
        "title_en": "Briefing",
        "sort_order": 3,
        "section_type": "text_fields",
        "items": [
            ("bar_shortages", "חוסרים בר:", "Bar shortages:"),
            ("kitchen_shortages", "חוסרים מטבח:", "Kitchen shortages:"),
            ("bar_specials", "ספיישלים בר:", "Bar specials:"),
            ("kitchen_specials", "ספיישלים מטבח:", "Kitchen specials:"),
            ("misc", "שונות:", "Misc:"),
        ],
    },
]

CLOSING_SECTIONS = [
    {
        "id": uuid.UUID("a1000003-0003-4003-8003-000000000001"),
        "key": "cocktails_speed",
        "title_he": "קוקטיילים וספיד",
        "title_en": "Cocktails & speed rail",
        "sort_order": 0,
        "section_type": "checkbox",
        "items": [
            (
                "send_to_wash",
                "לשלוח לשטיפה: קרש חיתוך, סכין, קולפנים, גסטרונומים ומלקחיים, כל ציוד הקוקטיילים, רשת שעובדים עליה, צלוחית טחין, גומיות בר",
                "Send to wash: cutting board, knife, peelers, gastronorms & tongs, all cocktail equipment, work mesh, tahini plate, bar rubbers",
            ),
            (
                "wrap_garnishes_wet",
                "לעטוף גרנishes בניילון נצמד ולוודא שהם במצב תקין (אם רטובים/הרוסים לזרוק). נענע ובזיליקום – בנייר סופג עבה",
                "Wrap garnishes in cling film; discard if wet/ruined. Mint & basil in thick paper towel",
            ),
            (
                "wrap_garnishes_dry",
                "לעטוף גרנishes יבשים בניילון נצמד – ג'ינג'ר , תפוזים",
                "Wrap dry garnishes in cling film — ginger, oranges",
            ),
            (
                "refrigerate_juices",
                "להכניס למקרר: מיצים, מיץ לימון, סירופים, מקציף, גרנדין (לשטוף במים לפני שלא יהיו דביקים)",
                "Refrigerate: juices, lemon juice, syrups, foamer, grenadine (rinse first)",
            ),
            (
                "wash_stations",
                "לשטוף עם סקוץ' וסבון את העמדות, את העמדת עבודה עם הרשת. בסוף שפריצר כחול/מבריק נירוסטה ונייר",
                "Scrub stations and mesh work area with scotch + soap; finish with blue spray/polish stainless and paper",
            ),
            ("wash_speed", "לשטוף עם סקוץ' וסבון ספיד עבודה", "Scrub speed rail with scotch + soap"),
            (
                "organize_speed",
                "לסדר את הספיד, ספיד קוקטיילים לפי הסדר ולאחר מכן גרנishes יבשים",
                "Organize speed rail, cocktail speed by order, then dry garnishes",
            ),
            ("condoms_corks", "קונדומים/פקקים לבקבוקים", "Bottle condoms/corks on bottles"),
        ],
    },
    {
        "id": uuid.UUID("a1000003-0003-4003-8003-000000000002"),
        "key": "prep_ahead",
        "title_he": "קידומים",
        "title_en": "Prep for tomorrow",
        "sort_order": 1,
        "section_type": "checkbox",
        "items": [
            (
                "glasses",
                "כוסות : להחזיר מהשטיפה בהקדם + פוליש , לסדר במקום",
                "Glasses: return from wash ASAP + polish, put away",
            ),
            (
                "wine_bottles",
                "צמצום בקבוקי יין פתוחים, החזרה למקום – כל בקבוק פתוח בפרונט של השורה של הבקבוקים משאר הסוגים. יין אדום פתוח מקרר אמצעי למטה, ורמוטים, בייליס, אפרול – מקרר אמצעי למעלה",
                "Consolidate open wine bottles, return to place; open red wine lower middle fridge, vermouths/Baileys/Aperol upper middle fridge",
            ),
            ("ice_cubes", "הכנת קוביות קרח גדולות למחר", "Prepare large ice cubes for tomorrow"),
            ("empty_water_jugs", "לרוקן קנקני מים", "Empty water jugs"),
            (
                "stock_shortages",
                "תשומת לב למלאים חסרים למחר – אם יש משהו שאין גם במחסן לעדכן אחמ\"ש",
                "Note stock shortages for tomorrow — update manager if not in warehouse either",
            ),
        ],
    },
    {
        "id": uuid.UUID("a1000003-0003-4003-8003-000000000003"),
        "key": "cleaning",
        "title_he": "ניקיונות",
        "title_en": "Cleaning",
        "sort_order": 2,
        "section_type": "checkbox",
        "items": [
            ("bar_rubbers", "הרמת כל הגומיות בר, ניקיון עם סקוץ' + סבון", "Lift all bar rubbers, clean with scotch + soap"),
            (
                "beer_surfaces",
                "ניקיון של המשטחי בירה והוצאה למלצרים: רשת לשטיפה, סקוץ' + סבון ובסוף קצת אקונומיקה",
                "Clean beer surfaces, send mesh to servers; scotch + soap then a little sanitizer",
            ),
            (
                "fridges",
                "ניקיון כל המקררים עם מגבון ואז שפריצר כחול",
                "Clean all fridges with wipe then blue spray",
            ),
            ("surfaces", "ניקיון כל המשטחים", "Clean all surfaces"),
            (
                "register_tablet",
                "ניקיון של הקופה, הטאבלט והמסופון (לשים לב מטען מחובר ועובד)",
                "Clean register, tablet and terminal (check charger connected and working)",
            ),
            (
                "beer_taps",
                "ניקיון ברזי בירה עם פרוסת לימון, לאחר מכן ניילון נצמד",
                "Clean beer taps with lemon slice, then cling film",
            ),
            ("bar_seating", "ניקיון של כל משטח הישיבה בבר", "Clean all bar seating surfaces"),
            (
                "floor_bar",
                "שטיפת כל הרצפה בבר, גם מאחורי החבית ספייר (מתחת לכיור)",
                "Mop entire bar floor, including behind spare keg (under sink)",
            ),
            ("floor_outside", "שטיפה של הרצפה מחוץ לבר", "Mop floor outside the bar"),
            (
                "floor_drain",
                "הוצאת המסננת של הרצפה, ניקיון של הרשת רצפה",
                "Remove floor drain filter, clean floor mesh",
            ),
            ("trash", "הוצאת זבל", "Take out trash"),
            (
                "chairs",
                "הרמת כיסאות על הבר, הכנסת כיסאות מבחוץ",
                "Stack chairs on bar, bring in outside chairs",
            ),
        ],
    },
]


def _add_checkbox_items(db: AsyncSession, section: ChecklistSection, items: list) -> None:
    for i, (key, text_he, text_en) in enumerate(items):
        db.add(ChecklistItem(
            id=uuid.uuid4(),
            section_id=section.id,
            key=key,
            text_he=text_he,
            text_en=text_en,
            sort_order=i,
        ))


def _add_daily_items(db: AsyncSession, section: ChecklistSection, items: list) -> None:
    for i, (dow, key, text_he, text_en) in enumerate(items):
        db.add(ChecklistItem(
            id=uuid.uuid4(),
            section_id=section.id,
            key=key,
            text_he=text_he,
            text_en=text_en,
            sort_order=i,
            day_of_week=dow,
        ))


def _add_text_field_items(db: AsyncSession, section: ChecklistSection, items: list) -> None:
    for i, (key, text_he, text_en) in enumerate(items):
        db.add(ChecklistItem(
            id=uuid.uuid4(),
            section_id=section.id,
            key=key,
            text_he=text_he,
            text_en=text_en,
            sort_order=i,
        ))


async def ensure_checklist_defaults(db: AsyncSession) -> None:
    res = await db.execute(select(ChecklistTemplate.id).limit(1))
    if res.scalar_one_or_none() is not None:
        return

    opening = ChecklistTemplate(
        id=OPENING_TEMPLATE_ID,
        type="opening",
        name="צ'ק ליסט פתיחה – בר מרלן",
    )
    db.add(opening)

    for sec_data in OPENING_SECTIONS:
        section = ChecklistSection(
            id=sec_data["id"],
            template_id=opening.id,
            key=sec_data["key"],
            title_he=sec_data["title_he"],
            title_en=sec_data["title_en"],
            sort_order=sec_data["sort_order"],
            section_type=sec_data["section_type"],
        )
        db.add(section)
        await db.flush()

        if sec_data["section_type"] == "daily_rotation":
            _add_daily_items(db, section, sec_data["items"])
        elif sec_data["section_type"] == "text_fields":
            _add_text_field_items(db, section, sec_data["items"])
        else:
            _add_checkbox_items(db, section, sec_data["items"])

    closing = ChecklistTemplate(
        id=CLOSING_TEMPLATE_ID,
        type="closing",
        name="צ'ק ליסט סגירה – בר מרלן",
    )
    db.add(closing)

    for sec_data in CLOSING_SECTIONS:
        section = ChecklistSection(
            id=sec_data["id"],
            template_id=closing.id,
            key=sec_data["key"],
            title_he=sec_data["title_he"],
            title_en=sec_data["title_en"],
            sort_order=sec_data["sort_order"],
            section_type=sec_data["section_type"],
        )
        db.add(section)
        await db.flush()
        _add_checkbox_items(db, section, sec_data["items"])

    await db.flush()
