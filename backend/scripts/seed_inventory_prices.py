import argparse
import asyncio
import sys
from pathlib import Path

"""
Seed manual inventory prices (inventory_items.price_minor/currency).

Why this exists:
- Bottles can be priced via bottle_prices.
- Glass and Garnish do not have a dedicated price table in the current schema.

Run inside the api container:
  docker compose exec -T api uv run python scripts/seed_inventory_prices.py --overwrite
"""

# Allow running from repo root by ensuring `backend/` is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from db.database import async_session_maker  # noqa: E402
from db.inventory.item import InventoryItem  # noqa: E402


def _minor(price: float) -> int:
    return int(round(float(price) * 100))


def _guess_price(item: InventoryItem, glass_price: float, garnish_piece_price: float, garnish_default_price: float) -> float:
    if item.item_type == "GLASS":
        return glass_price
    # GARNISH
    unit = (item.unit or "").strip().lower()
    if unit in ("piece", "pcs", "pc"):
        return garnish_piece_price
    return garnish_default_price


async def seed_prices(
    currency: str,
    glass_price: float,
    garnish_piece_price: float,
    garnish_default_price: float,
    overwrite: bool,
    dry_run: bool,
):
    currency = (currency or "ILS").strip().upper()
    if len(currency) != 3:
        raise ValueError("currency must be a 3-letter code (e.g. ILS)")

    async with async_session_maker() as session:
        res = await session.execute(
            select(InventoryItem).where(InventoryItem.item_type.in_(["GLASS", "GARNISH"]))
        )
        items = res.scalars().all()

        updated = 0
        for it in items:
            if not overwrite and it.price_minor is not None:
                continue
            price = _guess_price(it, glass_price, garnish_piece_price, garnish_default_price)
            it.price_minor = _minor(price)
            it.currency = currency
            updated += 1

        if dry_run:
            print(f"[seed_inventory_prices] DRY RUN: would update {updated} items")
            return

        await session.commit()
        print(f"[seed_inventory_prices] Updated {updated} items (currency={currency})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--currency", default="ILS")
    p.add_argument("--glass-price", type=float, default=8.0, help="Default price per glass item")
    p.add_argument("--garnish-piece-price", type=float, default=1.0, help="Default price for garnish items with unit=piece")
    p.add_argument("--garnish-default-price", type=float, default=3.0, help="Default price for garnish items with other units")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing manual prices")
    p.add_argument("--dry-run", action="store_true", help="Do not commit, just print what would change")
    args = p.parse_args()

    asyncio.run(
        seed_prices(
            currency=args.currency,
            glass_price=args.glass_price,
            garnish_piece_price=args.garnish_piece_price,
            garnish_default_price=args.garnish_default_price,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()

