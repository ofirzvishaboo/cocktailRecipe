"""
Reset Inventory so that ALL inventory items come from Ingredients.

This will:
- DELETE all inventory movements, stock, and items.
- CREATE one inventory item per ingredient:
  - item_type="GARNISH" (because inventory_items requires exactly one backing FK)
  - ingredient_id=<ingredient.id>
  - name=<ingredient.name>
  - unit="ml" (default; you can later edit per item)
- CREATE stock rows for BAR + WAREHOUSE with quantity=0

Run inside docker:
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/reset_inventory_from_ingredients.py"
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete, select, func

from db.database import async_session_maker, Ingredient
from db.inventory.item import InventoryItem
from db.inventory.stock import InventoryStock
from db.inventory.movement import InventoryMovement


async def main() -> None:
    async with async_session_maker() as db:
        # wipe inventory (children first)
        await db.execute(delete(InventoryMovement))
        await db.execute(delete(InventoryStock))
        await db.execute(delete(InventoryItem))
        await db.commit()

        res = await db.execute(select(Ingredient).order_by(func.lower(Ingredient.name).asc()))
        ingredients = res.scalars().all() or []

        items_created = 0
        stock_created = 0

        for ing in ingredients:
            item = InventoryItem(
                item_type="GARNISH",
                bottle_id=None,
                ingredient_id=ing.id,
                glass_type_id=None,
                name=ing.name,
                unit="ml",
                is_active=True,
                min_level=None,
                reorder_level=None,
                price_minor=None,
                currency=None,
            )
            db.add(item)
            await db.flush()
            items_created += 1

            db.add(InventoryStock(location="BAR", inventory_item_id=item.id, quantity=0, reserved_quantity=0))
            db.add(InventoryStock(location="WAREHOUSE", inventory_item_id=item.id, quantity=0, reserved_quantity=0))
            stock_created += 2

        await db.commit()

        print(f"Done. Inventory items: {items_created}. Stock rows: {stock_created}.")


if __name__ == "__main__":
    asyncio.run(main())

