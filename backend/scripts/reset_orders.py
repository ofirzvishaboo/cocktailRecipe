"""
Delete ALL orders + order items from the database.

Run inside docker (recommended):
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/reset_orders.py"
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete

from db.database import async_session_maker, Order, OrderItem


async def main() -> None:
    async with async_session_maker() as db:
        # Delete children first (FK)
        res_items = await db.execute(delete(OrderItem))
        res_orders = await db.execute(delete(Order))
        await db.commit()

        items_n = int(getattr(res_items, "rowcount", 0) or 0)
        orders_n = int(getattr(res_orders, "rowcount", 0) or 0)
        print(f"Deleted order_items: {items_n}, orders: {orders_n}")


if __name__ == "__main__":
    asyncio.run(main())

