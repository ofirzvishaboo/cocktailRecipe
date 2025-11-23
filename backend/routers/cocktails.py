from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from schemas.cocktails import CocktailRecipe, CocktailRecipeCreate, CocktailRecipeUpdate
from db.database import (
    get_async_session,
    CocktailRecipe as CocktailRecipeModel,
    Ingredient as IngredientModel,
    CocktailIngredient as CocktailIngredientModel
)
from typing import List, Dict
from uuid import UUID


router = APIRouter()


@router.get("/", response_model=List[Dict])
async def get_cocktails(db: AsyncSession = Depends(get_async_session)):
    """Get all cocktail recipes"""
    result = await db.execute(
        select(CocktailRecipeModel)
        .options(selectinload(CocktailRecipeModel.cocktail_ingredients).selectinload(CocktailIngredientModel.ingredient))
    )
    cocktails = result.scalars().all()
    return [cocktail.to_schema for cocktail in cocktails]


@router.get("/{cocktail_id}", response_model=Dict)
async def get_cocktail_recipe(cocktail_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """Get a single cocktail recipe by ID"""
    result = await db.execute(
        select(CocktailRecipeModel)
        .options(selectinload(CocktailRecipeModel.cocktail_ingredients).selectinload(CocktailIngredientModel.ingredient))
        .where(CocktailRecipeModel.id == cocktail_id)
    )
    cocktail = result.scalar_one_or_none()

    if not cocktail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail with id {cocktail_id} not found"
        )

    return cocktail.to_schema


@router.post("/", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_cocktail_recipe(
    cocktail: CocktailRecipeCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new cocktail recipe"""
    try:
        # Create cocktail recipe
        cocktail_model = CocktailRecipeModel(
            name=cocktail.name,
            image_url=cocktail.image_url
        )
        db.add(cocktail_model)
        await db.flush()  # Flush to get the ID

        # Process ingredients
        for ingredient_data in cocktail.ingredients:
            # Get or create ingredient
            ingredient_result = await db.execute(
                select(IngredientModel).where(IngredientModel.name == ingredient_data.name)
            )
            ingredient = ingredient_result.scalar_one_or_none()

            if not ingredient:
                ingredient = IngredientModel(name=ingredient_data.name)
                db.add(ingredient)
                await db.flush()

            # Create association with ml amount
            cocktail_ingredient = CocktailIngredientModel(
                cocktail_id=cocktail_model.id,
                ingredient_id=ingredient.id,
                ml=ingredient_data.ml
            )
            db.add(cocktail_ingredient)

        await db.commit()

        # Reload the model with relationships
        result = await db.execute(
            select(CocktailRecipeModel)
            .options(selectinload(CocktailRecipeModel.cocktail_ingredients).selectinload(CocktailIngredientModel.ingredient))
            .where(CocktailRecipeModel.id == cocktail_model.id)
        )
        cocktail_model = result.scalar_one()

        return cocktail_model.to_schema
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating cocktail: {str(e)}"
        )


@router.put("/{cocktail_id}", response_model=Dict)
async def update_cocktail_recipe(
    cocktail_id: UUID,
    cocktail: CocktailRecipeUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """Update an existing cocktail recipe"""
    result = await db.execute(
        select(CocktailRecipeModel).where(CocktailRecipeModel.id == cocktail_id)
    )
    cocktail_model = result.scalar_one_or_none()

    if not cocktail_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail with id {cocktail_id} not found"
        )

    try:
        # Update cocktail name and image
        cocktail_model.name = cocktail.name
        cocktail_model.image_url = cocktail.image_url

        # Delete existing associations
        delete_result = await db.execute(
            select(CocktailIngredientModel).where(
                CocktailIngredientModel.cocktail_id == cocktail_id
            )
        )
        existing_associations = delete_result.scalars().all()
        for assoc in existing_associations:
            await db.delete(assoc)

        await db.flush()

        # Create new associations
        for ingredient_data in cocktail.ingredients:
            # Get or create ingredient
            ingredient_result = await db.execute(
                select(IngredientModel).where(IngredientModel.name == ingredient_data.name)
            )
            ingredient = ingredient_result.scalar_one_or_none()

            if not ingredient:
                ingredient = IngredientModel(name=ingredient_data.name)
                db.add(ingredient)
                await db.flush()

            # Create association with ml amount
            cocktail_ingredient = CocktailIngredientModel(
                cocktail_id=cocktail_id,
                ingredient_id=ingredient.id,
                ml=ingredient_data.ml
            )
            db.add(cocktail_ingredient)

        await db.commit()

        # Reload the model with relationships
        result = await db.execute(
            select(CocktailRecipeModel)
            .options(selectinload(CocktailRecipeModel.cocktail_ingredients).selectinload(CocktailIngredientModel.ingredient))
            .where(CocktailRecipeModel.id == cocktail_id)
        )
        cocktail_model = result.scalar_one()

        return cocktail_model.to_schema
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating cocktail: {str(e)}"
        )


@router.delete("/{cocktail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cocktail_recipe(
    cocktail_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a cocktail recipe by ID"""
    result = await db.execute(
        select(CocktailRecipeModel).where(CocktailRecipeModel.id == cocktail_id)
    )
    cocktail_model = result.scalar_one_or_none()

    if not cocktail_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail with id {cocktail_id} not found"
        )

    try:
        await db.delete(cocktail_model)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting cocktail: {str(e)}"
        )