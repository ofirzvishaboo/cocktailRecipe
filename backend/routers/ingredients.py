from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas.ingredient import IngredientCreate, IngredientUpdate
from db.database import (
    get_async_session,
    Ingredient as IngredientModel
)
from typing import List, Dict
from uuid import UUID


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
async def create_ingredient(ingredient: IngredientCreate, db: AsyncSession = Depends(get_async_session)):
    """Create a new ingredient"""
    ingredient_model = IngredientModel(name=ingredient.name)
    db.add(ingredient_model)
    await db.commit()
    await db.refresh(ingredient_model)
    return ingredient_model.to_schema

@router.put("/{ingredient_id}", response_model=Dict)
async def update_ingredient(ingredient_id: UUID, ingredient: IngredientUpdate, db: AsyncSession = Depends(get_async_session)):
    """Update an existing ingredient"""
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
async def delete_ingredient(ingredient_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """Delete an existing ingredient"""
    result = await db.execute(select(IngredientModel).where(IngredientModel.id == ingredient_id))
    ingredient_model = result.scalar_one_or_none()
    if not ingredient_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with id {ingredient_id} not found"
        )
    await db.delete(ingredient_model)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)