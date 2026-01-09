from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from schemas.ingredient import (
    IngredientCreate,
    IngredientUpdate,
    IngredientBrandCreate,
    IngredientBrandUpdate,
)
from db.database import (
    get_async_session,
    Ingredient as IngredientModel,
    IngredientBrand as IngredientBrandModel,
)
from typing import List, Dict
from uuid import UUID
from core.auth import current_active_user
from db.users import User

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
    ingredient_model = IngredientModel(name=ingredient.name)
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
    ingredient_model.name = ingredient.name
    await db.commit()
    await db.refresh(ingredient_model)
    return ingredient_model.to_schema

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


@router.get("/{ingredient_id}/brands", response_model=List[Dict])
async def list_ingredient_brands(ingredient_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """List purchasable bottle SKUs (brands) for an ingredient"""
    # Ensure ingredient exists
    ing_result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient = ing_result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with id {ingredient_id} not found",
        )

    result = await db.execute(
        select(IngredientBrandModel).where(IngredientBrandModel.ingredient_id == ingredient_id)
    )
    brands = result.scalars().all()
    return [
        {
            "id": b.id,
            "ingredient_id": b.ingredient_id,
            "brand_name": b.brand_name,
            "bottle_size_ml": b.bottle_size_ml,
            "bottle_price": float(b.bottle_price) if b.bottle_price is not None else None,
        }
        for b in brands
    ]


@router.post("/{ingredient_id}/brands", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_ingredient_brand(
    ingredient_id: UUID,
    brand: IngredientBrandCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new purchasable bottle SKU (brand) for an ingredient"""
    ing_result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient = ing_result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with id {ingredient_id} not found",
        )

    brand_model = IngredientBrandModel(
        ingredient_id=ingredient_id,
        brand_name=brand.brand_name,
        bottle_size_ml=brand.bottle_size_ml,
        bottle_price=brand.bottle_price,
    )
    db.add(brand_model)
    await db.commit()
    await db.refresh(brand_model)
    return {
        "id": brand_model.id,
        "ingredient_id": brand_model.ingredient_id,
        "brand_name": brand_model.brand_name,
        "bottle_size_ml": brand_model.bottle_size_ml,
        "bottle_price": float(brand_model.bottle_price) if brand_model.bottle_price is not None else None,
    }


@router.put("/brands/{brand_id}", response_model=Dict)
async def update_ingredient_brand(
    brand_id: UUID,
    brand: IngredientBrandUpdate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update an existing ingredient brand (superuser only)"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to update ingredient brands",
        )

    result = await db.execute(select(IngredientBrandModel).where(IngredientBrandModel.id == brand_id))
    brand_model = result.scalar_one_or_none()
    if not brand_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found",
        )

    if brand.brand_name is not None:
        brand_model.brand_name = brand.brand_name
    if brand.bottle_size_ml is not None:
        brand_model.bottle_size_ml = brand.bottle_size_ml
    if brand.bottle_price is not None:
        brand_model.bottle_price = brand.bottle_price

    await db.commit()
    await db.refresh(brand_model)
    return {
        "id": brand_model.id,
        "ingredient_id": brand_model.ingredient_id,
        "brand_name": brand_model.brand_name,
        "bottle_size_ml": brand_model.bottle_size_ml,
        "bottle_price": float(brand_model.bottle_price) if brand_model.bottle_price is not None else None,
    }


@router.delete("/brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingredient_brand(
    brand_id: UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete an ingredient brand (superuser only)"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete ingredient brands",
        )

    result = await db.execute(select(IngredientBrandModel).where(IngredientBrandModel.id == brand_id))
    brand_model = result.scalar_one_or_none()
    if not brand_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found",
        )

    await db.delete(brand_model)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)