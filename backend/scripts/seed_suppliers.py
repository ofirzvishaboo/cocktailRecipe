"""
Seed suppliers + auto-assign supplier_id for bottles (suppliers supply bottles, not ingredients).

Run locally:
  python backend/scripts/seed_suppliers.py

It uses the same DATABASE_* env vars as the backend (dotenv supported by db.database).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from db.database import async_session_maker, Supplier, Ingredient
from db.bottle import Bottle


@dataclass(frozen=True)
class SeedSupplier:
    name: str
    contact: Optional[str] = None
    notes: Optional[str] = None


SEED_SUPPLIERS: list[SeedSupplier] = [
    SeedSupplier(name="Spirits & Wines", notes="Default for spirits/liqueurs/vermouth/etc."),
    SeedSupplier(name="Fresh Produce", notes="Default for juices, herbs, fresh items, garnishes."),
    SeedSupplier(name="Mixers", notes="Default for soda/sparkling/tonic/soft drinks."),
]


def _pick_supplier_name_for_ingredient(ing: Ingredient) -> str:
    name = (getattr(ing, "name", "") or "").strip().lower()
    kind_name = (getattr(getattr(ing, "kind", None), "name", "") or "").strip().lower()
    subcat_name = (getattr(getattr(ing, "subcategory", None), "name", "") or "").strip().lower()

    combined = " ".join([name, kind_name, subcat_name])

    fresh_tokens = [
        "juice",
        "lime",
        "lemon",
        "orange",
        "grapefruit",
        "pineapple",
        "mint",
        "basil",
        "rosemary",
        "cucumber",
        "ginger",
        "herb",
        "fresh",
        "garnish",
    ]
    mixer_tokens = [
        "soda",
        "sparkling",
        "tonic",
        "water",
        "cola",
        "ginger ale",
        "ginger beer",
        "sprite",
        "7up",
    ]

    if any(t in combined for t in fresh_tokens):
        return "Fresh Produce"
    if any(t in combined for t in mixer_tokens):
        return "Mixers"
    return "Spirits & Wines"


async def main() -> None:
    async with async_session_maker() as db:
        # 1) Create suppliers (idempotent)
        created = 0
        for s in SEED_SUPPLIERS:
            res = await db.execute(select(Supplier).where(func.lower(Supplier.name) == s.name.lower()))
            existing = res.scalar_one_or_none()
            if existing:
                continue
            db.add(Supplier(name=s.name, contact=s.contact, notes=s.notes))
            created += 1
        await db.commit()

        # Load suppliers into a map
        res = await db.execute(select(Supplier))
        suppliers = res.scalars().all()
        by_name = {sup.name: sup for sup in suppliers}

        # 2) Auto-assign supplier_id for bottles that don't have it (based on ingredient)
        res = await db.execute(
            select(Bottle)
            .options(
                selectinload(Bottle.ingredient).selectinload(Ingredient.kind),
                selectinload(Bottle.ingredient).selectinload(Ingredient.subcategory),
            )
        )
        bottles = res.scalars().all()

        assigned = 0
        for bottle in bottles:
            if bottle.supplier_id:
                continue
            ing = bottle.ingredient
            if not ing:
                continue
            pick = _pick_supplier_name_for_ingredient(ing)
            sup = by_name.get(pick)
            if not sup:
                continue
            bottle.supplier_id = sup.id
            assigned += 1

        await db.commit()

        print(
            f"Done. Suppliers created: {created}. "
            f"Bottles assigned supplier_id: {assigned}."
        )


if __name__ == "__main__":
    asyncio.run(main())

