"""
Ensure inventory items exist for ingredients that have NO bottles (typically garnishes).

Why:
- Inventory is currently bottle-based, so ingredients without bottles are missing.
- Garnishes like "Lemon peel" often have no bottle, but are needed in Items.

What it does (idempotent):
- For every Ingredient that has zero Bottle rows:
  - ensure an inventory_items row exists:
    - item_type = "GARNISH"
    - ingredient_id = <ingredient>
    - name = ingredient.name
    - unit = "unit"
  - ensure inventory_stock rows exist for BAR and WAREHOUSE (quantity=0)

Run inside docker:
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/seed_garnish_items_from_recipes.py"
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select, func

from db.database import async_session_maker, Ingredient, Bottle
from db.inventory.item import InventoryItem
from db.inventory.stock import InventoryStock


async def main() -> None:
    async with async_session_maker() as db:
        # Find ingredients that have no bottles
        res = await db.execute(
            select(Ingredient)
            .outerjoin(Bottle, Bottle.ingredient_id == Ingredient.id)
            .group_by(Ingredient.id)
            .having(func.count(Bottle.id) == 0)
            .order_by(func.lower(Ingredient.name).asc())
        )
        ingredients = res.scalars().all() or []

        if not ingredients:
            print("No ingredients without bottles found.")
            return

        created_items = 0
        created_stock = 0

        for ing in ingredients:
            existing_res = await db.execute(select(InventoryItem).where(InventoryItem.ingredient_id == ing.id))
            item = existing_res.scalar_one_or_none()
            if item is None:
                item = InventoryItem(
                    item_type="GARNISH",
                    bottle_id=None,
                    ingredient_id=ing.id,
                    glass_type_id=None,
                    name=ing.name,
                    unit="unit",
                    is_active=True,
                    min_level=None,
                    reorder_level=None,
                    price_minor=None,
                    currency=None,
                )
                db.add(item)
                await db.flush()
                created_items += 1

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
        print(f"Done. Ingredient items (no bottles) created: {created_items}. Stock rows created: {created_stock}.")


if __name__ == "__main__":
    asyncio.run(main())

