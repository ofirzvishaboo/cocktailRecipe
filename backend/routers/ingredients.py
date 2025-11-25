from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from schemas.ingredient import IngredientCreate, IngredientUpdate
from db.database import (
    get_async_session,
    Ingredient as IngredientModel
)
from typing import List, Dict
from uuid import UUID
from core.auth import current_active_user
from db.users import User

router = APIRouter()

@router.get("/", response_model=List[Dict])
async def get_ingredients(db: AsyncSession = Depends(get_async_session)):
    """Get all ingredients"""
    result = await db.execute(select(IngredientModel))
    ingredients = result.scalars().all()
    return [ingredient.to_schema for ingredient in ingredients]

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