from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from schemas.ingredient import (
    IngredientCreate,
    IngredientUpdate,
    BottleCreate,
    BottleUpdate,
    BottlePriceCreate,
    BottlePriceUpdate,
)
import logging
from db.database import (
    get_async_session,
    Ingredient as IngredientModel,
    Bottle as BottleModel,
    BottlePrice as BottlePriceModel,
    CocktailRecipe as CocktailRecipeModel,
    RecipeIngredient as RecipeIngredientModel,
    Brand as BrandModel,
    Supplier as SupplierModel,
)
from db.inventory.item import InventoryItem as InventoryItemModel
from typing import List, Dict
from uuid import UUID
from core.auth import current_active_user
from db.users import User
from datetime import date

router = APIRouter()


async def _ensure_brand_id_from_name(db: AsyncSession, name: str):
    """Create (or reuse) a Brand by name (case-insensitive). Returns brand_id or None."""
    n = (name or "").strip()
    if not n:
        return None
    res = await db.execute(select(BrandModel).where(func.lower(BrandModel.name) == n.lower()))
    existing = res.scalar_one_or_none()
    if existing:
        return existing.id
    m = BrandModel(name=n)
    db.add(m)
    # Flush so we can use the id in the same transaction without committing yet.
    await db.flush()
    return m.id

@router.get("/", response_model=List[Dict])
async def get_ingredients(db: AsyncSession = Depends(get_async_session)):
    """Get all ingredients"""
    try:
        result = await db.execute(select(IngredientModel))
        ingredients = result.scalars().all()
        return [ingredient.to_schema for ingredient in ingredients]
    except Exception as e:
        print(f"Error fetching ingredients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ingredients: {str(e)}"
        )

@router.get("/{ingredient_id}", response_model=Dict)
async def get_ingredient(ingredient_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """Get an ingredient by ID"""
    result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with id {ingredient_id} not found"
        )
    return ingredient.to_schema

@router.post("/", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_ingredient(ingredient: IngredientCreate, user: User = Depends(current_active_user), db: AsyncSession = Depends(get_async_session)):
    """Create a new ingredient"""
    # Check if ingredient already exists (case-insensitive)
    result = await db.execute(
        select(IngredientModel).where(
            func.lower(IngredientModel.name) == ingredient.name.lower()
        )
    )
    existing_ingredient = result.scalar_one_or_none()
    if existing_ingredient:
        # If the ingredient already exists, allow "enriching" it with missing normalized fields
        # (especially Hebrew translations) instead of silently dropping the provided data.
        changed = False
        if (ingredient.name_he or "").strip() and not (getattr(existing_ingredient, "name_he", None) or "").strip():
            existing_ingredient.name_he = ingredient.name_he
            changed = True
        # Only fill other optional fields if they're currently unset.
        if getattr(ingredient, "brand_id", None) and getattr(existing_ingredient, "brand_id", None) is None:
            existing_ingredient.brand_id = ingredient.brand_id
            changed = True
        if getattr(ingredient, "kind_id", None) and getattr(existing_ingredient, "kind_id", None) is None:
            existing_ingredient.kind_id = ingredient.kind_id
            changed = True
        if getattr(ingredient, "subcategory_id", None) and getattr(existing_ingredient, "subcategory_id", None) is None:
            existing_ingredient.subcategory_id = ingredient.subcategory_id
            changed = True
        if getattr(ingredient, "abv_percent", None) is not None and getattr(existing_ingredient, "abv_percent", None) is None:
            existing_ingredient.abv_percent = ingredient.abv_percent
            changed = True
        if getattr(ingredient, "notes", None) and getattr(existing_ingredient, "notes", None) is None:
            existing_ingredient.notes = ingredient.notes
            changed = True

        if changed:
            await db.commit()
            await db.refresh(existing_ingredient)
        return existing_ingredient.to_schema

    # Create new ingredient (preserve original casing)
    ingredient_model = IngredientModel(
        name=ingredient.name,
        name_he=ingredient.name_he,
        brand_id=ingredient.brand_id,
        kind_id=ingredient.kind_id,
        subcategory_id=ingredient.subcategory_id,
        abv_percent=ingredient.abv_percent,
        notes=ingredient.notes,
        default_supplier_id=getattr(ingredient, "default_supplier_id", None),
    )
    db.add(ingredient_model)
    await db.flush()

    supplier_ids = getattr(ingredient, "supplier_ids", None) or []
    if supplier_ids:
        sup_res = await db.execute(select(SupplierModel).where(SupplierModel.id.in_(supplier_ids)))
        ingredient_model.suppliers = sup_res.scalars().all()

    await db.commit()
    await db.refresh(ingredient_model)
    return ingredient_model.to_schema

@router.put("/{ingredient_id}", response_model=Dict)
async def update_ingredient(ingredient_id: UUID, ingredient: IngredientUpdate, user: User = Depends(current_active_user), db: AsyncSession = Depends(get_async_session)):
    """Update an existing ingredient"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to update this ingredient"
        )
    result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient_model = result.scalar_one_or_none()
    if not ingredient_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with id {ingredient_id} not found"
        )
    # Pydantic v2: allow explicit nulls (e.g. subcategory_id=null to clear) by checking fields_set.
    fields = getattr(ingredient, "model_fields_set", set())

    if "name" in fields and ingredient.name is not None:
        ingredient_model.name = ingredient.name
    if "name_he" in fields:
        ingredient_model.name_he = ingredient.name_he
    if "brand_id" in fields:
        ingredient_model.brand_id = ingredient.brand_id
    if "kind_id" in fields:
        ingredient_model.kind_id = ingredient.kind_id
    if "subcategory_id" in fields:
        ingredient_model.subcategory_id = ingredient.subcategory_id
    if "abv_percent" in fields:
        ingredient_model.abv_percent = ingredient.abv_percent
    if "notes" in fields:
        ingredient_model.notes = ingredient.notes
    if "default_supplier_id" in fields:
        ingredient_model.default_supplier_id = ingredient.default_supplier_id
    if "supplier_ids" in fields:
        supplier_ids = ingredient.supplier_ids or []
        if supplier_ids:
            sup_res = await db.execute(select(SupplierModel).where(SupplierModel.id.in_(supplier_ids)))
            ingredient_model.suppliers = sup_res.scalars().all()
        else:
            ingredient_model.suppliers = []
    await db.commit()
    await db.refresh(ingredient_model)
    return ingredient_model.to_schema


@router.get("/{ingredient_id}/used-by", response_model=List[Dict])
async def get_ingredient_used_by(ingredient_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """List cocktails that use this ingredient (via recipe_ingredients)."""
    res = await db.execute(
        select(CocktailRecipeModel.id, CocktailRecipeModel.name)
        .join(RecipeIngredientModel, RecipeIngredientModel.recipe_id == CocktailRecipeModel.id)
        .where(RecipeIngredientModel.ingredient_id == ingredient_id)
        .distinct()
        .order_by(CocktailRecipeModel.name.asc())
    )
    rows = res.all()
    logging.info(f"Ingredient {ingredient_id} used by {rows}")
    return [{"id": r[0], "name": r[1]} for r in rows]


@router.get("/{ingredient_id}/bottles", response_model=List[Dict])
async def list_bottles_for_ingredient(
    ingredient_id: UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List bottles (SKUs) for an ingredient, with current price if present."""
    ing_result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient = ing_result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")

    bottles_result = await db.execute(select(BottleModel).where(BottleModel.ingredient_id == ingredient_id))
    bottles = bottles_result.scalars().all()
    today = date.today()
    out = []
    for b in bottles:
        price_result = await db.execute(
            select(BottlePriceModel)
            .where(
                BottlePriceModel.bottle_id == b.id,
                BottlePriceModel.start_date <= today,
                (BottlePriceModel.end_date.is_(None) | (BottlePriceModel.end_date >= today)),
            )
            .order_by(BottlePriceModel.start_date.desc())
            .limit(1)
        )
        p = price_result.scalar_one_or_none()
        row_out = {
                "id": b.id,
                "ingredient_id": b.ingredient_id,
                "name": b.name,
                "name_he": getattr(b, "name_he", None),
                "volume_ml": b.volume_ml,
                "importer_id": b.importer_id,
                "description": b.description,
                "description_he": getattr(b, "description_he", None),
                "is_default_cost": bool(b.is_default_cost),
                "current_price": (
                    {
                        "id": p.id,
                        "bottle_id": p.bottle_id,
                        "price_minor": int(p.price_minor),
                        "price": float(p.price_minor) / 100.0,
                        "currency": p.currency,
                        "start_date": p.start_date.isoformat(),
                        "end_date": p.end_date.isoformat() if p.end_date else None,
                        "source": p.source,
                    }
                    if p
                    else None
                ),
            }

        if not user.is_superuser:
            row_out["current_price"] = None

        out.append(row_out)
    return out


@router.post("/{ingredient_id}/bottles", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_bottle_for_ingredient(
    ingredient_id: UUID,
    bottle: BottleCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a bottle SKU for an ingredient."""
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    ing_result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient_model = ing_result.scalar_one_or_none()
    if not ingredient_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")

    # Ensure the Brand exists and link it to the ingredient.
    brand_id = await _ensure_brand_id_from_name(db, bottle.name)
    if brand_id:
        ingredient_model.brand_id = brand_id

    if bottle.is_default_cost:
        # unset other defaults
        others = await db.execute(select(BottleModel).where(BottleModel.ingredient_id == ingredient_id))
        for b in others.scalars().all():
            b.is_default_cost = False

    bottle_model = BottleModel(
        ingredient_id=ingredient_id,
        name=bottle.name,
        name_he=bottle.name_he,
        volume_ml=bottle.volume_ml,
        importer_id=bottle.importer_id,
        description=bottle.description,
        description_he=bottle.description_he,
        is_default_cost=bool(bottle.is_default_cost),
    )
    db.add(bottle_model)
    await db.flush()

    # Create an inventory item for this bottle so it appears in Inventory
    existing = await db.execute(
        select(InventoryItemModel).where(InventoryItemModel.bottle_id == bottle_model.id)
    )
    if existing.scalar_one_or_none() is None:
        inv_item = InventoryItemModel(
            item_type="BOTTLE",
            bottle_id=bottle_model.id,
            name=bottle_model.name or "",
            unit="bottles",
            is_active=True,
        )
        db.add(inv_item)

    await db.commit()
    await db.refresh(bottle_model)
    return {
        "id": bottle_model.id,
        "ingredient_id": bottle_model.ingredient_id,
        "name": bottle_model.name,
        "name_he": bottle_model.name_he,
        "volume_ml": bottle_model.volume_ml,
        "importer_id": bottle_model.importer_id,
        "description": bottle_model.description,
        "description_he": bottle_model.description_he,
        "is_default_cost": bool(bottle_model.is_default_cost),
    }


@router.put("/bottles/{bottle_id}", response_model=Dict)
async def update_bottle(
    bottle_id: UUID,
    bottle: BottleUpdate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update bottle fields (superuser only)."""
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    result = await db.execute(select(BottleModel).where(BottleModel.id == bottle_id))
    bottle_model = result.scalar_one_or_none()
    if not bottle_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bottle not found")

    if bottle.name is not None:
        bottle_model.name = bottle.name
        # Also ensure the Brand exists and link it to the ingredient.
        ing_res = await db.execute(select(IngredientModel).where(IngredientModel.id == bottle_model.ingredient_id))
        ingredient_model = ing_res.scalar_one_or_none()
        if ingredient_model:
            brand_id = await _ensure_brand_id_from_name(db, bottle.name)
            if brand_id:
                ingredient_model.brand_id = brand_id
    if bottle.name_he is not None:
        bottle_model.name_he = bottle.name_he
    if bottle.volume_ml is not None:
        bottle_model.volume_ml = bottle.volume_ml
    if bottle.importer_id is not None:
        bottle_model.importer_id = bottle.importer_id
    if bottle.description is not None:
        bottle_model.description = bottle.description
    if bottle.description_he is not None:
        bottle_model.description_he = bottle.description_he
    if bottle.is_default_cost is not None:
        if bottle.is_default_cost:
            others = await db.execute(select(BottleModel).where(BottleModel.ingredient_id == bottle_model.ingredient_id))
            for b in others.scalars().all():
                b.is_default_cost = False
        bottle_model.is_default_cost = bool(bottle.is_default_cost)

    await db.commit()
    await db.refresh(bottle_model)
    return {
        "id": bottle_model.id,
        "ingredient_id": bottle_model.ingredient_id,
        "name": bottle_model.name,
        "name_he": bottle_model.name_he,
        "volume_ml": bottle_model.volume_ml,
        "importer_id": bottle_model.importer_id,
        "description": bottle_model.description,
        "description_he": bottle_model.description_he,
        "is_default_cost": bool(bottle_model.is_default_cost),
    }


@router.delete("/bottles/{bottle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bottle(
    bottle_id: UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result = await db.execute(select(BottleModel).where(BottleModel.id == bottle_id))
    bottle_model = result.scalar_one_or_none()
    if not bottle_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bottle not found")
    await db.delete(bottle_model)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/bottles/{bottle_id}/prices", response_model=List[Dict])
async def list_bottle_prices(bottle_id: UUID, db: AsyncSession = Depends(get_async_session)):
    res = await db.execute(select(BottlePriceModel).where(BottlePriceModel.bottle_id == bottle_id).order_by(BottlePriceModel.start_date.desc()))
    prices = res.scalars().all()
    return [
        {
            "id": p.id,
            "bottle_id": p.bottle_id,
            "price_minor": int(p.price_minor),
            "price": float(p.price_minor) / 100.0,
            "currency": p.currency,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "source": p.source,
        }
        for p in prices
    ]


@router.post("/bottles/{bottle_id}/prices", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_bottle_price(
    bottle_id: UUID,
    price: BottlePriceCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    bottle_res = await db.execute(select(BottleModel).where(BottleModel.id == bottle_id))
    bottle_model = bottle_res.scalar_one_or_none()
    if not bottle_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bottle not found")

    start = price.start_date or date.today()
    price_minor = int(round(float(price.price) * 100))
    model = BottlePriceModel(
        bottle_id=bottle_id,
        price_minor=price_minor,
        currency=price.currency,
        start_date=start,
        end_date=price.end_date,
        source=price.source,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return {
        "id": model.id,
        "bottle_id": model.bottle_id,
        "price_minor": int(model.price_minor),
        "price": float(model.price_minor) / 100.0,
        "currency": model.currency,
        "start_date": model.start_date.isoformat(),
        "end_date": model.end_date.isoformat() if model.end_date else None,
        "source": model.source,
    }

@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingredient(ingredient_id: UUID, user: User = Depends(current_active_user), db: AsyncSession = Depends(get_async_session)):
    """Delete an existing ingredient"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this ingredient"
        )
    result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient_model = result.scalar_one_or_none()
    if not ingredient_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with id {ingredient_id} not found"
        )
    # Remove from cocktails first (ingredient FK is RESTRICT on recipe_ingredients)
    await db.execute(delete(RecipeIngredientModel).where(RecipeIngredientModel.ingredient_id == ingredient_id))
    await db.delete(ingredient_model)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

