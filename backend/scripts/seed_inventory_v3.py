import argparse
import asyncio
import sys
import uuid
from pathlib import Path
import re

"""
Seed inventory v3:
- Create inventory_items for all bottles (type=BOTTLE).
- Optionally create inventory_items for all glass types (type=GLASS).

Also ensures inventory_stock rows exist for both BAR and WAREHOUSE with 0 quantity.

Run:
- inside backend/: `uv run python scripts/seed_inventory_v3.py`
- from repo root: `uv run python backend/scripts/seed_inventory_v3.py`
"""

# Allow running from repo root by ensuring `backend/` is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert  # noqa: E402
from sqlalchemy import func  # noqa: E402

from db.database import async_session_maker  # noqa: E402
from db.bottle import Bottle  # noqa: E402
from db.glass_type import GlassType  # noqa: E402
from db.cocktail_recipe import CocktailRecipe  # noqa: E402
from db.recipe_ingredient import RecipeIngredient  # noqa: E402
from db.ingredient import Ingredient  # noqa: E402
from db.kind import Kind  # noqa: E402
from db.inventory.item import InventoryItem  # noqa: E402
from db.inventory.stock import InventoryStock  # noqa: E402


LOCATIONS = ["BAR", "WAREHOUSE"]


def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _strip_parenthetical(s: str) -> str:
    # remove "(optional)" etc
    return re.sub(r"\([^)]*\)", "", s or "").strip()


def _split_garnish_text(garnish_text: str) -> list[str]:
    s = _normalize_spaces(_strip_parenthetical(garnish_text))
    if not s:
        return []
    # Common separators: "+", ",", " and "
    parts: list[str] = []
    for chunk in re.split(r"\+|,| and ", s, flags=re.IGNORECASE):
        p = _normalize_spaces(chunk)
        if p:
            parts.append(p)
    return parts


def _garnish_phrase_to_ingredient_name(phrase: str) -> str:
    p = (phrase or "").strip().lower()
    # Heuristics for your current seeded dataset + common bar garnishes
    if "lime" in p:
        return "Lime"
    if "lemon" in p:
        return "Lemon"
    if "orange" in p:
        return "Orange"
    if "mint" in p:
        return "Mint"
    if "salt" in p:
        return "Salt"

    # Generic cleanup (e.g. "lime wheel" -> "lime", "orange peel" -> "orange")
    cleaned = p
    for w in ["wheel", "peel", "twist", "sprig", "rim", "slice", "wedge"]:
        cleaned = cleaned.replace(w, " ")
    cleaned = _normalize_spaces(cleaned)
    if not cleaned:
        cleaned = p
    # Title case for Ingredient.name convention
    return cleaned.title()


async def _ensure_kind(session, name: str) -> Kind:
    n = _normalize_spaces(name)
    res = await session.execute(select(Kind).where(func.lower(Kind.name) == n.lower()))
    k = res.scalar_one_or_none()
    if k:
        return k
    k = Kind(name=n)
    session.add(k)
    await session.flush()
    return k


async def _get_or_create_ingredient_for_garnish(session, name: str, garnish_kind_id: uuid.UUID | None) -> Ingredient:
    n = _normalize_spaces(name)
    res = await session.execute(select(Ingredient).where(func.lower(Ingredient.name) == n.lower()))
    ing = res.scalar_one_or_none()
    if ing:
        # Don't overwrite existing kind; only set if missing
        if garnish_kind_id and getattr(ing, "kind_id", None) is None:
            ing.kind_id = garnish_kind_id
        return ing

    ing = Ingredient(name=n, kind_id=garnish_kind_id)
    session.add(ing)
    await session.flush()
    return ing


async def seed(
    with_glass: bool = False,
    for_cocktails: bool = False,
    from_garnish_text: bool = False,
    create_missing_garnish_ingredients: bool = True,
):
    created_items = 0
    created_stock = 0

    async with async_session_maker() as session:
        async with session.begin():
            bottle_ids_to_seed: set[uuid.UUID] = set()
            glass_ids_to_seed: set[uuid.UUID] = set()
            garnish_ingredient_ids_to_seed: set[uuid.UUID] = set()
            garnish_ingredient_ids_from_text: set[uuid.UUID] = set()

            if for_cocktails:
                # Bottles referenced by cocktails
                bres = await session.execute(
                    select(RecipeIngredient.bottle_id).where(RecipeIngredient.bottle_id.is_not(None)).distinct()
                )
                bottle_ids_to_seed = {r[0] for r in bres.all() if r[0]}

                # Glass types referenced by cocktails
                gres = await session.execute(
                    select(CocktailRecipe.glass_type_id).where(CocktailRecipe.glass_type_id.is_not(None)).distinct()
                )
                glass_ids_to_seed = {r[0] for r in gres.all() if r[0]}

                # Garnish ingredients referenced by cocktails
                ires = await session.execute(
                    select(RecipeIngredient.ingredient_id)
                    .where(RecipeIngredient.is_garnish == True)  # noqa: E712
                    .distinct()
                )
                garnish_ingredient_ids_to_seed = {r[0] for r in ires.all() if r[0]}

                if from_garnish_text:
                    # Parse garnish_text and map/create Ingredients; then seed those as GARNISH items.
                    garnish_kind = await _ensure_kind(session, "Garnish")
                    tres = await session.execute(
                        select(CocktailRecipe.garnish_text)
                        .where(CocktailRecipe.garnish_text.is_not(None))
                        .distinct()
                    )
                    garnish_texts = [r[0] for r in tres.all() if r[0] and str(r[0]).strip()]
                    for gt in garnish_texts:
                        for phrase in _split_garnish_text(str(gt)):
                            ing_name = _garnish_phrase_to_ingredient_name(phrase)
                            if not ing_name:
                                continue
                            if create_missing_garnish_ingredients:
                                ing = await _get_or_create_ingredient_for_garnish(session, ing_name, garnish_kind.id)
                                garnish_ingredient_ids_from_text.add(ing.id)
                            else:
                                res = await session.execute(
                                    select(Ingredient.id).where(func.lower(Ingredient.name) == ing_name.lower())
                                )
                                iid = res.scalar_one_or_none()
                                if iid:
                                    garnish_ingredient_ids_from_text.add(iid)

            # BOTTLES -> InventoryItem(type=BOTTLE)
            if bottle_ids_to_seed:
                bres = await session.execute(select(Bottle).where(Bottle.id.in_(bottle_ids_to_seed)))
            else:
                bres = await session.execute(select(Bottle))
            bottles = bres.scalars().all()
            for b in bottles:
                existing = await session.execute(select(InventoryItem.id).where(InventoryItem.bottle_id == b.id))
                if existing.scalar_one_or_none():
                    continue
                session.add(
                    InventoryItem(
                        id=uuid.uuid4(),
                        item_type="BOTTLE",
                        bottle_id=b.id,
                        ingredient_id=None,
                        glass_type_id=None,
                        name=b.name,
                        unit="bottle",
                        is_active=True,
                    )
                )
                created_items += 1

            # GLASS types -> InventoryItem(type=GLASS)
            # - with_glass=True => all glass types
            # - for_cocktails=True => only those referenced by cocktail_recipes
            if with_glass or glass_ids_to_seed:
                if glass_ids_to_seed and not with_glass:
                    gres = await session.execute(select(GlassType).where(GlassType.id.in_(glass_ids_to_seed)))
                else:
                    gres = await session.execute(select(GlassType))
                glasses = gres.scalars().all()
                for g in glasses:
                    existing = await session.execute(select(InventoryItem.id).where(InventoryItem.glass_type_id == g.id))
                    if existing.scalar_one_or_none():
                        continue
                    session.add(
                        InventoryItem(
                            id=uuid.uuid4(),
                            item_type="GLASS",
                            bottle_id=None,
                            ingredient_id=None,
                            glass_type_id=g.id,
                            name=g.name,
                            unit="glass",
                            is_active=True,
                        )
                    )
                    created_items += 1

            # GARNISH ingredients -> InventoryItem(type=GARNISH)
            garnish_ids = set(garnish_ingredient_ids_to_seed) | set(garnish_ingredient_ids_from_text)
            if garnish_ids:
                ires = await session.execute(select(Ingredient).where(Ingredient.id.in_(garnish_ids)))
                garnish_ings = ires.scalars().all()
                for ing in garnish_ings:
                    existing_item = (
                        await session.execute(select(InventoryItem).where(InventoryItem.ingredient_id == ing.id))
                    ).scalar_one_or_none()

                    if existing_item:
                        # Normalize older seeds: unit='garnish' -> 'piece'
                        if (existing_item.unit or "").strip().lower() == "garnish":
                            existing_item.unit = "piece"
                        continue

                    session.add(
                        InventoryItem(
                            id=uuid.uuid4(),
                            item_type="GARNISH",
                            bottle_id=None,
                            ingredient_id=ing.id,
                            glass_type_id=None,
                            name=ing.name,
                            unit="piece",
                            is_active=True,
                        )
                    )
                    created_items += 1

            # Ensure stock rows for both locations for all items
            ires = await session.execute(select(InventoryItem.id))
            item_ids = [r[0] for r in ires.all()]
            for item_id in item_ids:
                for loc in LOCATIONS:
                    sid = uuid.uuid4()
                    stmt = (
                        insert(InventoryStock)
                        .values(
                            id=sid,
                            location=loc,
                            inventory_item_id=item_id,
                            quantity=0,
                            reserved_quantity=0,
                        )
                        .on_conflict_do_nothing(index_elements=["location", "inventory_item_id"])
                    )
                    res = await session.execute(stmt)
                    if res.rowcount and res.rowcount > 0:
                        created_stock += 1

        await session.commit()

    print(f"[seed_inventory_v3] created_items={created_items} created_stock_rows={created_stock}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-glass", action="store_true", help="Also create inventory items for glass types")
    parser.add_argument("--for-cocktails", action="store_true", help="Ensure items exist for bottles/glasses/garnishes referenced by cocktails")
    parser.add_argument("--from-garnish-text", action="store_true", help="Create GARNISH items from cocktail_recipes.garnish_text (best-effort)")
    parser.add_argument("--no-create-missing-garnish-ingredients", action="store_true", help="Do not create Ingredient rows for unknown garnish names")
    args = parser.parse_args()

    asyncio.run(
        seed(
            with_glass=bool(args.with_glass),
            for_cocktails=bool(args.for_cocktails),
            from_garnish_text=bool(args.from_garnish_text),
            create_missing_garnish_ingredients=not bool(args.no_create_missing_garnish_ingredients),
        )
    )

