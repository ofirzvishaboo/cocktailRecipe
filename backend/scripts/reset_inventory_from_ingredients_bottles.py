"""
Reset Inventory so items are bottle-based and priced by bottle price.

Goal:
- Inventory item unit = "bottle"
- Inventory price comes from BottlePrice (not manual inventory_items.price_minor)

What this script does:
- DELETE all inventory movements, stock, and items.
- For each Ingredient:
  - Pick a Bottle to represent it:
    1) Prefer a bottle with an ACTIVE BottlePrice today
    2) Prefer Bottle.is_default_cost within priced bottles
    3) Else any bottle with an active price
    4) Else any bottle for that ingredient
  - Create InventoryItem as item_type="BOTTLE" with bottle_id=<picked bottle>
  - Set unit="bottle"
  - Do NOT set inventory_items.price_minor/currency (so API uses BottlePrice)
- Create BAR + WAREHOUSE stock rows with default quantities (in bottles).

Run inside docker:
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/reset_inventory_from_ingredients_bottles.py"

Env vars:
- BAR_QTY_BOTTLES (default: 2)
- WAREHOUSE_QTY_BOTTLES (default: 4)
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

from sqlalchemy import delete, select, func

from db.database import async_session_maker, Ingredient, Bottle, BottlePrice
from db.inventory.item import InventoryItem
from db.inventory.stock import InventoryStock
from db.inventory.movement import InventoryMovement


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip())
    except Exception:
        return float(default)


async def main() -> None:
    bar_qty = _env_float("BAR_QTY_BOTTLES", 2.0)
    wh_qty = _env_float("WAREHOUSE_QTY_BOTTLES", 4.0)
    today = date.today()

    async with async_session_maker() as db:
        # wipe inventory (children first)
        await db.execute(delete(InventoryMovement))
        await db.execute(delete(InventoryStock))
        await db.execute(delete(InventoryItem))
        await db.commit()

        # Load ingredients
        ing_res = await db.execute(select(Ingredient).order_by(func.lower(Ingredient.name).asc()))
        ingredients = ing_res.scalars().all() or []
        ing_ids = [i.id for i in ingredients]

        if not ing_ids:
            print("No ingredients found.")
            return

        # Load bottles for all ingredients
        b_res = await db.execute(select(Bottle).where(Bottle.ingredient_id.in_(ing_ids)))
        bottles = b_res.scalars().all() or []
        bottles_by_ing: dict = {}
        bottle_ids = []
        for b in bottles:
            if not b.ingredient_id:
                continue
            bottles_by_ing.setdefault(b.ingredient_id, []).append(b)
            bottle_ids.append(b.id)

        # Load current prices for bottles
        priced_bottle_ids: set = set()
        if bottle_ids:
            p_stmt = (
                select(BottlePrice.bottle_id)
                .where(BottlePrice.bottle_id.in_(bottle_ids))
                .where(BottlePrice.start_date <= today)
                .where((BottlePrice.end_date == None) | (BottlePrice.end_date >= today))  # noqa: E711
                .distinct()
            )
            p_res = await db.execute(p_stmt)
            priced_bottle_ids = {r[0] for r in (p_res.all() or []) if r and r[0]}

        def pick_bottle(ingredient_id):
            candidates = bottles_by_ing.get(ingredient_id) or []
            if not candidates:
                return None
            priced = [b for b in candidates if b.id in priced_bottle_ids]
            if priced:
                # prefer default-cost among priced
                for b in priced:
                    if getattr(b, "is_default_cost", False):
                        return b
                return priced[0]
            # else prefer default-cost even if unpriced
            for b in candidates:
                if getattr(b, "is_default_cost", False):
                    return b
            return candidates[0]

        items_created = 0
        stock_created = 0
        missing_bottle = 0
        missing_price = 0

        for ing in ingredients:
            b = pick_bottle(ing.id)
            if not b:
                missing_bottle += 1
                continue

            if b.id not in priced_bottle_ids:
                missing_price += 1

            item = InventoryItem(
                item_type="BOTTLE",
                bottle_id=b.id,
                ingredient_id=None,
                glass_type_id=None,
                name=b.name,
                unit="bottle",
                is_active=True,
                min_level=None,
                reorder_level=None,
                price_minor=None,
                currency=None,
            )
            db.add(item)
            await db.flush()
            items_created += 1

            db.add(InventoryStock(location="BAR", inventory_item_id=item.id, quantity=bar_qty, reserved_quantity=0))
            db.add(InventoryStock(location="WAREHOUSE", inventory_item_id=item.id, quantity=wh_qty, reserved_quantity=0))
            stock_created += 2

        await db.commit()

        print(
            "Done. "
            f"Inventory bottle-items created: {items_created}. "
            f"Stock rows created: {stock_created}. "
            f"Ingredients without any bottle: {missing_bottle}. "
            f"Bottles missing an active price: {missing_price}."
        )


if __name__ == "__main__":
    asyncio.run(main())

