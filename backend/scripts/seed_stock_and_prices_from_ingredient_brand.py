"""
Seed a small amount of stock for ALL inventory items, and set prices based on bottles.

Inventory assumptions (current setup):
- inventory_items are ingredient-backed (item_type="GARNISH", ingredient_id != null)
- unit is usually "ml" (so price is treated as "price per ml")

Pricing rules:
1) For each ingredient, find a bottle with an active BottlePrice:
   - Prefer Bottle.is_default_cost with an active price
   - Else any bottle with an active price
2) Derive per-ml price:
   - cents_per_ml = round(bottle_price.price_minor / bottle.volume_ml)
   - inventory_items.price_minor = cents_per_ml
   - inventory_items.currency = bottle_price.currency
3) If still missing, leave price as NULL.

Stock rules:
- Ensure BAR + WAREHOUSE stock rows exist for every inventory item.
- If a stock row quantity is 0, set it to defaults (env-configurable).

Run inside docker:
  docker exec -i cocktail-api sh -lc "cd /app && PYTHONPATH=/app uv run python scripts/seed_stock_and_prices_from_ingredient_brand.py"

Env vars:
- BAR_QTY (default: 1000)        # when unit=ml, this is ml
- WAREHOUSE_QTY (default: 3000)  # when unit=ml, this is ml
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

from sqlalchemy import select, func

from db.database import async_session_maker, Ingredient, Bottle, BottlePrice
from db.inventory.item import InventoryItem
from db.inventory.stock import InventoryStock


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip())
    except Exception:
        return float(default)


async def main() -> None:
    bar_qty = _env_float("BAR_QTY", 1000.0)
    wh_qty = _env_float("WAREHOUSE_QTY", 3000.0)
    today = date.today()

    async with async_session_maker() as db:
        # Load all ingredient-backed inventory items
        items_res = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.ingredient_id.is_not(None))
            .order_by(func.lower(InventoryItem.name).asc())
        )
        items = items_res.scalars().all() or []
        ingredient_ids = [it.ingredient_id for it in items if it.ingredient_id]

        if not items:
            print("No ingredient-backed inventory items found.")
            return

        # Load ingredients (to get brand_id)
        ing_res = await db.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
        ingredients = ing_res.scalars().all() or []
        ing_by_id = {i.id: i for i in ingredients}

        # Load bottles for these ingredients
        bottle_res = await db.execute(
            select(Bottle)
            .where(Bottle.ingredient_id.in_(ingredient_ids))
        )
        bottles = bottle_res.scalars().all() or []
        bottles_by_ing: dict = {}
        for b in bottles:
            if not b.ingredient_id:
                continue
            bottles_by_ing.setdefault(b.ingredient_id, []).append(b)

        bottle_ids = [b.id for b in bottles if b.id]

        # Current bottle prices (most recent active per bottle)
        price_by_bottle = {}
        if bottle_ids:
            q = (
                select(BottlePrice)
                .where(BottlePrice.bottle_id.in_(bottle_ids))
                .where(BottlePrice.start_date <= today)
                .where((BottlePrice.end_date == None) | (BottlePrice.end_date >= today))  # noqa: E711
                .distinct(BottlePrice.bottle_id)
                .order_by(
                    BottlePrice.bottle_id,
                    BottlePrice.start_date.desc(),
                    BottlePrice.id.desc(),
                )
            )
            p_res = await db.execute(q)
            for p in p_res.scalars().all() or []:
                price_by_bottle[p.bottle_id] = p

        def _pick_priced_bottle_for_ingredient(ingredient_id):
            candidates = bottles_by_ing.get(ingredient_id) or []
            # prefer default-cost WITH an active price
            for b in candidates:
                if not getattr(b, "is_default_cost", False):
                    continue
                if b.id in price_by_bottle:
                    return b
            # else any bottle with an active price
            for b in candidates:
                if b.id in price_by_bottle:
                    return b
            return None

        # Compute per-ingredient cents_per_ml and currency (STRICTLY from bottles)
        cents_per_ml_by_ing = {}
        currency_by_ing = {}
        for ing_id in ingredient_ids:
            b = _pick_priced_bottle_for_ingredient(ing_id)
            if not b:
                continue
            p = price_by_bottle.get(b.id)
            vol = int(getattr(b, "volume_ml", 0) or 0)
            if not p or not vol:
                continue
            cents_per_ml = int(round(int(p.price_minor) / float(vol)))
            if cents_per_ml <= 0:
                continue
            cents_per_ml_by_ing[ing_id] = cents_per_ml
            currency_by_ing[ing_id] = (p.currency or "ILS").upper()

        # Apply to inventory items + stock
        price_updates = 0
        stock_updates = 0
        stock_creates = 0

        for it in items:
            iid = it.ingredient_id
            cents = cents_per_ml_by_ing.get(iid)
            curr = currency_by_ing.get(iid)

            if cents is not None and cents > 0:
                it.price_minor = int(cents)
                it.currency = (curr or "ILS").upper()
                price_updates += 1

            for loc, default_qty in (("BAR", bar_qty), ("WAREHOUSE", wh_qty)):
                st_res = await db.execute(
                    select(InventoryStock).where(
                        InventoryStock.inventory_item_id == it.id,
                        InventoryStock.location == loc,
                    )
                )
                st = st_res.scalar_one_or_none()
                if st is None:
                    db.add(InventoryStock(location=loc, inventory_item_id=it.id, quantity=default_qty, reserved_quantity=0))
                    stock_creates += 1
                else:
                    if float(st.quantity or 0) == 0.0:
                        st.quantity = default_qty
                        stock_updates += 1

        await db.commit()

        print(
            "Done. "
            f"Price updates applied (from bottles): {price_updates}/{len(items)}. "
            f"Stock rows created: {stock_creates}. Stock rows updated from 0: {stock_updates}."
        )


if __name__ == "__main__":
    asyncio.run(main())

