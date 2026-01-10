from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from schemas.ingredient import (
    IngredientCreate,
    IngredientUpdate,
    BottleCreate,
    BottleUpdate,
    BottlePriceCreate,
    BottlePriceUpdate,
)
from db.database import (
    get_async_session,
    Ingredient as IngredientModel,
    Bottle as BottleModel,
    BottlePrice as BottlePriceModel,
)
from typing import List, Dict
from uuid import UUID
from core.auth import current_active_user
from db.users import User
from datetime import date

router = APIRouter()

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
        return existing_ingredient.to_schema

    # Create new ingredient (preserve original casing)
    ingredient_model = IngredientModel(
        name=ingredient.name,
        brand_id=ingredient.brand_id,
        kind_id=ingredient.kind_id,
        subcategory_id=ingredient.subcategory_id,
        abv_percent=ingredient.abv_percent,
        notes=ingredient.notes,
    )
    db.add(ingredient_model)
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
    if ingredient.name is not None:
        ingredient_model.name = ingredient.name
    if ingredient.brand_id is not None:
        ingredient_model.brand_id = ingredient.brand_id
    if ingredient.kind_id is not None:
        ingredient_model.kind_id = ingredient.kind_id
    if ingredient.subcategory_id is not None:
        ingredient_model.subcategory_id = ingredient.subcategory_id
    if ingredient.abv_percent is not None:
        ingredient_model.abv_percent = ingredient.abv_percent
    if ingredient.notes is not None:
        ingredient_model.notes = ingredient.notes
    await db.commit()
    await db.refresh(ingredient_model)
    return ingredient_model.to_schema


@router.get("/{ingredient_id}/bottles", response_model=List[Dict])
async def list_bottles_for_ingredient(ingredient_id: UUID, db: AsyncSession = Depends(get_async_session)):
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
        out.append(
            {
                "id": b.id,
                "ingredient_id": b.ingredient_id,
                "name": b.name,
                "volume_ml": b.volume_ml,
                "importer_id": b.importer_id,
                "description": b.description,
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
        )
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
    if not ing_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")

    if bottle.is_default_cost:
        # unset other defaults
        others = await db.execute(select(BottleModel).where(BottleModel.ingredient_id == ingredient_id))
        for b in others.scalars().all():
            b.is_default_cost = False

    bottle_model = BottleModel(
        ingredient_id=ingredient_id,
        name=bottle.name,
        volume_ml=bottle.volume_ml,
        importer_id=bottle.importer_id,
        description=bottle.description,
        is_default_cost=bool(bottle.is_default_cost),
    )
    db.add(bottle_model)
    await db.commit()
    await db.refresh(bottle_model)
    return {
        "id": bottle_model.id,
        "ingredient_id": bottle_model.ingredient_id,
        "name": bottle_model.name,
        "volume_ml": bottle_model.volume_ml,
        "importer_id": bottle_model.importer_id,
        "description": bottle_model.description,
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
    if bottle.volume_ml is not None:
        bottle_model.volume_ml = bottle.volume_ml
    if bottle.importer_id is not None:
        bottle_model.importer_id = bottle.importer_id
    if bottle.description is not None:
        bottle_model.description = bottle.description
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
        "volume_ml": bottle_model.volume_ml,
        "importer_id": bottle_model.importer_id,
        "description": bottle_model.description,
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
    # Only superusers can delete ingredients (ingredients are shared resources)
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this ingredient"
        )
    await db.delete(ingredient_model)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

