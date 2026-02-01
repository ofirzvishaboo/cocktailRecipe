"""
Reset inventory to contain only a few bottle items.

This script:
- Deletes ALL inventory movements, stock rows, and items.
- Creates a small set of BOTTLE inventory items using existing Bottle rows.
- Seeds BAR + WAREHOUSE quantities for each bottle item.

Run inside docker (recommended):
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/reset_inventory_seed_few_bottles.py"

Optional env vars:
- KEEP_BOTTLES_COUNT (default: 8)
- BAR_QTY (default: 2)
- WAREHOUSE_QTY (default: 4)
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import delete, select, func

from db.database import async_session_maker, Bottle
from db.inventory.item import InventoryItem
from db.inventory.stock import InventoryStock
from db.inventory.movement import InventoryMovement


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default


async def main() -> None:
    keep = _env_int("KEEP_BOTTLES_COUNT", 8)
    bar_qty = float(os.getenv("BAR_QTY", "2"))
    wh_qty = float(os.getenv("WAREHOUSE_QTY", "4"))

    async with async_session_maker() as db:
        # wipe inventory (children first)
        await db.execute(delete(InventoryMovement))
        await db.execute(delete(InventoryStock))
        await db.execute(delete(InventoryItem))
        await db.commit()

        # Pick bottles to keep (prefer default-cost bottles)
        res = await db.execute(
            select(Bottle)
            .where(Bottle.is_default_cost == True)  # noqa: E712
            .order_by(func.lower(Bottle.name).asc())
            .limit(keep)
        )
        bottles = res.scalars().all() or []

        # Fallback: if none are marked default, just take first bottles
        if not bottles:
            res2 = await db.execute(select(Bottle).order_by(func.lower(Bottle.name).asc()).limit(keep))
            bottles = res2.scalars().all() or []

        created_items = 0
        created_stock = 0

        for b in bottles:
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
            created_items += 1

            db.add(InventoryStock(location="BAR", inventory_item_id=item.id, quantity=bar_qty, reserved_quantity=0))
            db.add(InventoryStock(location="WAREHOUSE", inventory_item_id=item.id, quantity=wh_qty, reserved_quantity=0))
            created_stock += 2

        await db.commit()

        print(
            f"Inventory reset complete. "
            f"Items created: {created_items}. Stock rows created: {created_stock} "
            f"(BAR={bar_qty}, WAREHOUSE={wh_qty})."
        )


if __name__ == "__main__":
    asyncio.run(main())

