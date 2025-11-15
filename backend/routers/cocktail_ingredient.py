from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from schemas.cocktail_ingredient import (
    CocktailIngredientCreate,
    CocktailIngredientUpdate,
    CocktailIngredientDelete
)
from db.database import (
    get_async_session,
    CocktailIngredient as CocktailIngredientModel,
    CocktailRecipe as CocktailRecipeModel,
    Ingredient as IngredientModel
)
from typing import List, Dict
from uuid import UUID


router = APIRouter()


@router.get("/", response_model=List[Dict])
async def get_cocktail_ingredients(
    cocktail_id: UUID | None = Query(None, description="Filter by cocktail ID"),
    ingredient_id: UUID | None = Query(None, description="Filter by ingredient ID"),
    db: AsyncSession = Depends(get_async_session)
):
    """Get all cocktail-ingredient associations, optionally filtered by cocktail_id or ingredient_id"""
    # Start with base query
    query = select(CocktailIngredientModel).options(
        selectinload(CocktailIngredientModel.cocktail),
        selectinload(CocktailIngredientModel.ingredient)
    )

    # Apply filters
    conditions = []
    if cocktail_id is not None:
        conditions.append(CocktailIngredientModel.cocktail_id == cocktail_id)
    if ingredient_id is not None:
        conditions.append(CocktailIngredientModel.ingredient_id == ingredient_id)

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    associations = result.scalars().all()

    # Build response
    response = []
    for assoc in associations:
        response.append({
            "cocktail_id": str(assoc.cocktail_id),
            "ingredient_id": str(assoc.ingredient_id),
            "ml": assoc.ml,
            "cocktail_name": assoc.cocktail.name if hasattr(assoc, 'cocktail') and assoc.cocktail else None,
            "ingredient_name": assoc.ingredient.name if hasattr(assoc, 'ingredient') and assoc.ingredient else None
        })

    return response


@router.get("/{cocktail_name}/{ingredient_name}", response_model=Dict)
async def get_cocktail_ingredient(
    cocktail_name: str,
    ingredient_name: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific cocktail-ingredient association by cocktail and ingredient names"""
    # Look up cocktail by name
    cocktail_result = await db.execute(
        select(CocktailRecipeModel).where(CocktailRecipeModel.name == cocktail_name)
    )
    cocktail = cocktail_result.scalar_one_or_none()
    if not cocktail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail '{cocktail_name}' not found"
        )

    # Look up ingredient by name
    ingredient_result = await db.execute(
        select(IngredientModel).where(IngredientModel.name == ingredient_name)
    )
    ingredient = ingredient_result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient '{ingredient_name}' not found"
        )

    # Find the association
    result = await db.execute(
        select(CocktailIngredientModel)
        .options(
            selectinload(CocktailIngredientModel.cocktail),
            selectinload(CocktailIngredientModel.ingredient)
        )
        .where(
            CocktailIngredientModel.cocktail_id == cocktail.id,
            CocktailIngredientModel.ingredient_id == ingredient.id
        )
    )
    association = result.scalar_one_or_none()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Association between cocktail '{cocktail_name}' and ingredient '{ingredient_name}' not found"
        )

    return {
        "cocktail_id": str(association.cocktail_id),
        "ingredient_id": str(association.ingredient_id),
        "ml": association.ml,
        "cocktail_name": association.cocktail.name,
        "ingredient_name": association.ingredient.name
    }


@router.post("/", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_cocktail_ingredient(
    association: CocktailIngredientCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new cocktail-ingredient association"""
    try:
        # Verify cocktail exists
        cocktail_result = await db.execute(
            select(CocktailRecipeModel).where(CocktailRecipeModel.id == association.cocktail_id)
        )
        cocktail = cocktail_result.scalar_one_or_none()
        if not cocktail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cocktail with id {association.cocktail_id} not found"
            )

        # Verify ingredient exists
        ingredient_result = await db.execute(
            select(IngredientModel).where(IngredientModel.id == association.ingredient_id)
        )
        ingredient = ingredient_result.scalar_one_or_none()
        if not ingredient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingredient with id {association.ingredient_id} not found"
            )

        # Check if association already exists
        existing_result = await db.execute(
            select(CocktailIngredientModel).where(
                CocktailIngredientModel.cocktail_id == association.cocktail_id,
                CocktailIngredientModel.ingredient_id == association.ingredient_id
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Association between cocktail {association.cocktail_id} and ingredient {association.ingredient_id} already exists"
            )

        # Create association
        association_model = CocktailIngredientModel(
            cocktail_id=association.cocktail_id,
            ingredient_id=association.ingredient_id,
            ml=association.ml
        )
        db.add(association_model)
        await db.commit()

        # Reload with relationships
        result = await db.execute(
            select(CocktailIngredientModel)
            .options(
                selectinload(CocktailIngredientModel.cocktail),
                selectinload(CocktailIngredientModel.ingredient)
            )
            .where(
                CocktailIngredientModel.cocktail_id == association.cocktail_id,
                CocktailIngredientModel.ingredient_id == association.ingredient_id
            )
        )
        association_model = result.scalar_one()

        return {
            "cocktail_id": association_model.cocktail_id,
            "ingredient_id": association_model.ingredient_id,
            "ml": association_model.ml,
            "cocktail_name": association_model.cocktail.name,
            "ingredient_name": association_model.ingredient.name
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating association: {str(e)}"
        )


@router.put("/{cocktail_name}/{ingredient_name}", response_model=Dict)
async def update_cocktail_ingredient(
    cocktail_name: str,
    ingredient_name: str,
    association: CocktailIngredientUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """Update an existing cocktail-ingredient association"""
    # Look up cocktail by name
    cocktail_result = await db.execute(
        select(CocktailRecipeModel).where(CocktailRecipeModel.name == cocktail_name)
    )
    cocktail = cocktail_result.scalar_one_or_none()
    if not cocktail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail '{cocktail_name}' not found"
        )

    # Look up ingredient by name
    ingredient_result = await db.execute(
        select(IngredientModel).where(IngredientModel.name == ingredient_name)
    )
    ingredient = ingredient_result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient '{ingredient_name}' not found"
        )

    # Find the association
    result = await db.execute(
        select(CocktailIngredientModel).where(
            CocktailIngredientModel.cocktail_id == cocktail.id,
            CocktailIngredientModel.ingredient_id == ingredient.id
        )
    )
    association_model = result.scalar_one_or_none()

    if not association_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Association between cocktail '{cocktail_name}' and ingredient '{ingredient_name}' not found"
        )

    try:
        # Note: cocktail_id and ingredient_id are part of the composite primary key,
        # so they cannot be updated. Only ml can be updated.
        # If you need to change the IDs, delete and recreate the association.

        # Update ml field
        if association.ml is not None:
            association_model.ml = association.ml
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ml field is required for update"
            )

        await db.commit()

        # Reload with relationships
        result = await db.execute(
            select(CocktailIngredientModel)
            .options(
                selectinload(CocktailIngredientModel.cocktail),
                selectinload(CocktailIngredientModel.ingredient)
            )
            .where(
                CocktailIngredientModel.cocktail_id == cocktail.id,
                CocktailIngredientModel.ingredient_id == ingredient.id
            )
        )
        association_model = result.scalar_one()

        return {
            "cocktail_id": str(association_model.cocktail_id),
            "ingredient_id": str(association_model.ingredient_id),
            "ml": association_model.ml,
            "cocktail_name": association_model.cocktail.name,
            "ingredient_name": association_model.ingredient.name
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating association: {str(e)}"
        )


@router.delete("/{cocktail_name}/{ingredient_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cocktail_ingredient(
    association: CocktailIngredientDelete,
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a cocktail-ingredient association"""
    # Look up cocktail by name
    cocktail_result = await db.execute(
        select(CocktailRecipeModel).where(CocktailRecipeModel.name == association.cocktail_name)
    )
    cocktail = cocktail_result.scalar_one_or_none()
    if not cocktail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail '{association.cocktail_name}' not found"
        )

    # Look up ingredient by name
    ingredient_result = await db.execute(
        select(IngredientModel).where(IngredientModel.name == association.ingredient_name)
    )
    ingredient = ingredient_result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient '{association.ingredient_name}' not found"
        )

    # Find the association
    result = await db.execute(
        select(CocktailIngredientModel).where(
            CocktailIngredientModel.cocktail_id == cocktail.id,
            CocktailIngredientModel.ingredient_id == ingredient.id
        )
    )
    association_model = result.scalar_one_or_none()

    if not association_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Association between cocktail '{association.cocktail_name}' and ingredient '{association.ingredient_name}' not found"
        )

    try:
        await db.delete(association_model)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting association: {str(e)}"
        )

