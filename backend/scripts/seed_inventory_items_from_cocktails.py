"""
Ensure Inventory Items exist for ALL ingredients used in cocktails.

This script is idempotent:
- It DOES NOT delete existing inventory.
- It creates missing inventory_items for:
  - bottle-backed ingredients (InventoryItem.item_type="BOTTLE") using an existing Bottle
  - non-bottle ingredients (InventoryItem.item_type="GARNISH") using ingredient_id
- It creates missing inventory_stock rows (BAR/WAREHOUSE) with quantity=0 for new items.

Run inside docker:
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/seed_inventory_items_from_cocktails.py"
"""

from __future__ import annotations

import asyncio
from typing import Optional

from sqlalchemy import select, func

from db.database import async_session_maker, RecipeIngredient, Ingredient, Bottle
from db.inventory.item import InventoryItem
from db.inventory.stock import InventoryStock


def _unit_for_ingredient(units_seen: set[str]) -> str:
    u = {x.strip().lower() for x in units_seen if x}
    if any(x in u for x in ("ml", "oz")):
        return "ml"
    return "unit"


async def main() -> None:
    async with async_session_maker() as db:
        # All ingredients referenced by any recipe ingredient
        res = await db.execute(select(RecipeIngredient.ingredient_id).distinct())
        ingredient_ids = [r[0] for r in res.all() if r and r[0]]

        if not ingredient_ids:
            print("No recipe ingredients found. Nothing to seed.")
            return

        # Load ingredients
        ing_res = await db.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
        ingredients = ing_res.scalars().all() or []
        ing_by_id = {i.id: i for i in ingredients}

        # Units seen per ingredient (to pick garnish unit if needed)
        units_res = await db.execute(select(RecipeIngredient.ingredient_id, RecipeIngredient.unit))
        units_seen: dict = {}
        for (iid, unit) in units_res.all() or []:
            if iid is None:
                continue
            units_seen.setdefault(iid, set()).add(unit or "")

        # Candidate bottle per ingredient:
        # - Prefer a bottle_id explicitly set on any recipe_ingredient row
        # - Else prefer Bottle.is_default_cost
        # - Else any Bottle for the ingredient
        bottle_by_ingredient: dict = {}

        override_res = await db.execute(
            select(RecipeIngredient.ingredient_id, RecipeIngredient.bottle_id)
            .where(RecipeIngredient.bottle_id.is_not(None))
        )
        for iid, bid in override_res.all() or []:
            if iid and bid and iid not in bottle_by_ingredient:
                bottle_by_ingredient[iid] = bid

        # Load all bottles for these ingredients
        b_res = await db.execute(select(Bottle).where(Bottle.ingredient_id.in_(ingredient_ids)))
        bottles = b_res.scalars().all() or []
        bottles_by_ing: dict = {}
        for b in bottles:
            bottles_by_ing.setdefault(b.ingredient_id, []).append(b)

        def _pick_bottle_id(iid) -> Optional[str]:
            if iid in bottle_by_ingredient:
                return bottle_by_ingredient[iid]
            candidates = bottles_by_ing.get(iid) or []
            for b in candidates:
                if getattr(b, "is_default_cost", False):
                    return b.id
            return candidates[0].id if candidates else None

        created_items = 0
        created_stock = 0

        for iid in ingredient_ids:
            ing = ing_by_id.get(iid)
            if not ing:
                continue

            bottle_id = _pick_bottle_id(iid)
            if bottle_id:
                # Ensure BOTTLE inventory item exists for bottle_id (unique index enforces 1)
                ex = await db.execute(select(InventoryItem).where(InventoryItem.bottle_id == bottle_id))
                item = ex.scalar_one_or_none()
                if item is None:
                    # Load bottle for naming
                    b = next((x for x in (bottles_by_ing.get(iid) or []) if x.id == bottle_id), None)
                    if b is None:
                        bq = await db.execute(select(Bottle).where(Bottle.id == bottle_id))
                        b = bq.scalar_one_or_none()

                    item = InventoryItem(
                        item_type="BOTTLE",
                        bottle_id=bottle_id,
                        ingredient_id=None,
                        glass_type_id=None,
                        name=(getattr(b, "name", None) or getattr(ing, "name", None) or "Bottle"),
                        unit="bottle",
                        is_active=True,
                        min_level=None,
                        reorder_level=None,
                        price_minor=None,
                        currency=None,
                    )
                    db.add(item)
                    await db.flush()
                    created_items += 1
            else:
                # Ensure GARNISH inventory item exists for ingredient_id (unique index enforces 1)
                ex = await db.execute(select(InventoryItem).where(InventoryItem.ingredient_id == iid))
                item = ex.scalar_one_or_none()
                if item is None:
                    item = InventoryItem(
                        item_type="GARNISH",
                        bottle_id=None,
                        ingredient_id=iid,
                        glass_type_id=None,
                        name=getattr(ing, "name", None) or "Ingredient",
                        unit=_unit_for_ingredient(units_seen.get(iid, set())),
                        is_active=True,
                        min_level=None,
                        reorder_level=None,
                        price_minor=None,
                        currency=None,
                    )
                    db.add(item)
                    await db.flush()
                    created_items += 1

            # Ensure stock rows exist for both locations (do not overwrite existing quantities)
            for loc in ("BAR", "WAREHOUSE"):
                st_res = await db.execute(
                    select(InventoryStock).where(
                        InventoryStock.inventory_item_id == item.id,
                        InventoryStock.location == loc,
                    )
                )
                st = st_res.scalar_one_or_none()
                if st is None:
                    db.add(InventoryStock(location=loc, inventory_item_id=item.id, quantity=0, reserved_quantity=0))
                    created_stock += 1

        await db.commit()

        total = await db.execute(select(func.count()).select_from(InventoryItem))
        total_items = int(total.scalar() or 0)

        print(
            f"Done. Inventory items created: {created_items}. "
            f"Stock rows created: {created_stock}. "
            f"Total inventory items now: {total_items}."
        )


if __name__ == "__main__":
    asyncio.run(main())

