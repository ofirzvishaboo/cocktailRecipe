from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from schemas.cocktails import (
    CocktailRecipe,
    CocktailRecipeCreate,
    CocktailRecipeUpdate,
    CocktailCostResponse,
)
from db.database import (
    get_async_session,
    CocktailRecipe as CocktailRecipeModel,
    Ingredient as IngredientModel,
    RecipeIngredient as RecipeIngredientModel,
    Bottle as BottleModel,
    BottlePrice as BottlePriceModel,
)
from typing import List, Dict, Optional
from uuid import UUID
from core.auth import current_active_user
from db.users import User
from datetime import date

router = APIRouter()

OZ_TO_ML = 29.5735
DASH_TO_ML = 0.92


def _unit_to_ml(quantity: float, unit: str) -> Optional[float]:
    u = (unit or "").strip().lower()
    if u == "ml":
        return float(quantity)
    if u == "oz":
        return float(quantity) * OZ_TO_ML
    if u == "dash":
        return float(quantity) * DASH_TO_ML
    return None


def _serialize_cocktail(c: CocktailRecipeModel) -> Dict:
    user_data = None
    if getattr(c, "user", None):
        user_data = {"id": c.user.id, "email": c.user.email}

    recipe_ingredients = []
    ris = getattr(c, "recipe_ingredients", None) or []
    if ris:
        for ri in ris:
            bottle = getattr(ri, "bottle", None)
            ingredient = getattr(ri, "ingredient", None)
            subcategory = ingredient.subcategory if (ingredient and getattr(ingredient, "subcategory", None)) else None
            recipe_ingredients.append(
                {
                    "id": ri.id,
                    "ingredient_id": ri.ingredient_id,
                    "ingredient_name": ingredient.name if ingredient else None,
                    "quantity": float(ri.quantity),
                    "unit": ri.unit,
                    "bottle_id": ri.bottle_id,
                    "bottle_name": bottle.name if bottle else None,
                    "bottle_volume_ml": bottle.volume_ml if bottle else None,
                    "is_garnish": ri.is_garnish,
                    "is_optional": ri.is_optional,
                    "sort_order": ri.sort_order,
                    "subcategory_name": subcategory.name if subcategory else None,
                }
            )

    return {
        "id": c.id,
        "created_by_user_id": c.created_by_user_id,
        "user": user_data,
        "name": c.name,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "glass_type_id": c.glass_type_id,
        "picture_url": c.picture_url,
        "garnish_text": c.garnish_text,
        "base_recipe_id": c.base_recipe_id,
        "is_base": c.is_base,
        "preparation_method": c.preparation_method,
        "batch_type": c.batch_type,
        "recipe_ingredients": recipe_ingredients,
    }


@router.get("/", response_model=List[Dict])
async def get_cocktails(db: AsyncSession = Depends(get_async_session)):
    """Get all cocktail recipes"""
    result = await db.execute(
        select(CocktailRecipeModel)
        .options(
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
            selectinload(CocktailRecipeModel.user),
        )
    )
    cocktails = result.scalars().all()
    return [_serialize_cocktail(c) for c in cocktails]


@router.get("/{cocktail_id}", response_model=Dict)
async def get_cocktail_recipe(cocktail_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """Get a single cocktail recipe by ID"""
    result = await db.execute(
        select(CocktailRecipeModel)
        .options(
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
            selectinload(CocktailRecipeModel.user),
        )
        .where(CocktailRecipeModel.id == cocktail_id)
    )
    cocktail = result.scalar_one_or_none()

    if not cocktail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail with id {cocktail_id} not found"
        )

    return _serialize_cocktail(cocktail)


# @router.get(f"/{cocktail_id}/no-juice-recipe")


@router.post("/", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_cocktail_recipe(
    cocktail: CocktailRecipeCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new cocktail recipe"""
    try:
        # Create cocktail recipe
        cocktail_model = CocktailRecipeModel(
            name=cocktail.name,
            description=cocktail.description,
            picture_url=cocktail.picture_url,
            garnish_text=cocktail.garnish_text,
            glass_type_id=cocktail.glass_type_id,
            base_recipe_id=cocktail.base_recipe_id,
            is_base=bool(cocktail.is_base),
            preparation_method=cocktail.preparation_method,
            batch_type=cocktail.batch_type,
            created_by_user_id=user.id,
        )
        db.add(cocktail_model)
        await db.flush()  # Flush to get the ID

        # Process recipe_ingredients only (clean break)
        for ri in cocktail.recipe_ingredients:
            db.add(
                RecipeIngredientModel(
                    recipe_id=cocktail_model.id,
                    ingredient_id=ri.ingredient_id,
                    quantity=ri.quantity,
                    unit=ri.unit,
                    bottle_id=ri.bottle_id,
                    is_garnish=ri.is_garnish,
                    is_optional=ri.is_optional,
                    sort_order=ri.sort_order,
                )
            )

        await db.commit()

        # Reload the model with relationships
        result = await db.execute(
            select(CocktailRecipeModel)
            .options(
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
                selectinload(CocktailRecipeModel.user),
            )
            .where(CocktailRecipeModel.id == cocktail_model.id)
        )
        cocktail_model = result.scalar_one()

        return _serialize_cocktail(cocktail_model)
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
    user: User = Depends(current_active_user),
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
    if cocktail_model.created_by_user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to update this cocktail"
        )

    try:
        # Update cocktail name, description, and image
        cocktail_model.name = cocktail.name
        cocktail_model.description = cocktail.description
        cocktail_model.picture_url = cocktail.picture_url
        cocktail_model.garnish_text = cocktail.garnish_text
        cocktail_model.glass_type_id = cocktail.glass_type_id
        cocktail_model.base_recipe_id = cocktail.base_recipe_id
        cocktail_model.is_base = bool(cocktail.is_base)
        cocktail_model.preparation_method = cocktail.preparation_method
        cocktail_model.batch_type = cocktail.batch_type

        # Replace normalized recipe ingredients
        existing_ris = await db.execute(
            select(RecipeIngredientModel).where(RecipeIngredientModel.recipe_id == cocktail_id)
        )
        for ri in existing_ris.scalars().all():
            await db.delete(ri)
        await db.flush()

        for ri in cocktail.recipe_ingredients:
            db.add(
                RecipeIngredientModel(
                    recipe_id=cocktail_id,
                    ingredient_id=ri.ingredient_id,
                    quantity=ri.quantity,
                    unit=ri.unit,
                    bottle_id=ri.bottle_id,
                    is_garnish=ri.is_garnish,
                    is_optional=ri.is_optional,
                    sort_order=ri.sort_order,
                )
            )

        await db.commit()

        # Reload the model with relationships
        result = await db.execute(
            select(CocktailRecipeModel)
            .options(
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
                selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
                selectinload(CocktailRecipeModel.user),
            )
            .where(CocktailRecipeModel.id == cocktail_id)
        )
        cocktail_model = result.scalar_one()

        return _serialize_cocktail(cocktail_model)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating cocktail: {str(e)}"
        )


@router.delete("/{cocktail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cocktail_recipe(
    cocktail_id: UUID,
    user: User = Depends(current_active_user),
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

    # Allow users to delete their own cocktails, or superusers to delete any
    if cocktail_model.created_by_user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this cocktail"
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


@router.get("/{cocktail_id}/no-juice-cost", response_model=CocktailCostResponse)
async def get_no_juice_cocktail(
    cocktail_id: UUID,
    scale_factor: float = 1.0,
    db: AsyncSession = Depends(get_async_session),
):
    """Compute ingredient and total cost for a cocktail (scaled) excluding juice ingredients."""
    result = await db.execute(
        select(CocktailRecipeModel)
        .options(
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
        )
        .where(CocktailRecipeModel.id == cocktail_id)
    )
    cocktail = result.scalar_one_or_none()
    if not cocktail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail with id {cocktail_id} not found",
        )

    lines = []
    total_cocktail_cost = 0.0
    scaled_total_cost = 0.0

    as_of = date.today()
    # Always filter out juice ingredients
    recipe_ingredients = [
        ri for ri in cocktail.recipe_ingredients
        if ri.ingredient and ri.ingredient.subcategory
        and ri.ingredient.subcategory.name.lower() != 'juice'
    ]

    for ri in recipe_ingredients:
        qty = float(ri.quantity or 0)
        unit = ri.unit
        scaled_qty = qty * float(scale_factor or 0)

        ml = _unit_to_ml(qty, unit)
        scaled_ml = _unit_to_ml(scaled_qty, unit)

        bottle = ri.bottle
        if bottle is None:
            # fallback to default bottle
            bottle_result = await db.execute(
                select(BottleModel)
                .where(BottleModel.ingredient_id == ri.ingredient_id, BottleModel.is_default_cost == True)  # noqa: E712
                .limit(1)
            )
            bottle = bottle_result.scalar_one_or_none()

        price_minor = None
        currency = None
        cost_per_ml = 0.0
        if bottle and bottle.volume_ml and bottle.volume_ml > 0:
            price_result = await db.execute(
                select(BottlePriceModel)
                .where(
                    BottlePriceModel.bottle_id == bottle.id,
                    BottlePriceModel.start_date <= as_of,
                    (BottlePriceModel.end_date.is_(None) | (BottlePriceModel.end_date >= as_of)),
                )
                .order_by(BottlePriceModel.start_date.desc())
                .limit(1)
            )
            price = price_result.scalar_one_or_none()
            if price:
                price_minor = int(price.price_minor)
                currency = price.currency
                cost_per_ml = (price_minor / 100.0) / float(bottle.volume_ml)

        ingredient_cost = (scaled_ml or 0.0) * cost_per_ml
        total_cocktail_cost += (ml or 0.0) * cost_per_ml
        scaled_total_cost += ingredient_cost

        lines.append(
            {
                "ingredient_name": ri.ingredient.name if ri.ingredient else "Unknown",
                "quantity": qty,
                "unit": unit,
                "scaled_quantity": scaled_qty,
                "bottle_id": bottle.id if bottle else None,
                "bottle_name": bottle.name if bottle else None,
                "bottle_volume_ml": bottle.volume_ml if bottle else None,
                "price_minor": price_minor,
                "currency": currency,
                "cost_per_ml": cost_per_ml,
                "ingredient_cost": ingredient_cost,
            }
        )

    return {
        "lines": lines,
        "total_cocktail_cost": total_cocktail_cost,
        "scaled_total_cost": scaled_total_cost,
        "scale_factor": float(scale_factor or 0),
    }


@router.get("/{cocktail_id}/cost", response_model=CocktailCostResponse)
async def get_cocktail_cost(
    cocktail_id: UUID,
    scale_factor: float = 1.0,
    db: AsyncSession = Depends(get_async_session),
):
    """Compute ingredient and total cost for a cocktail (scaled). Uses bottles + bottle_prices + recipe_ingredients."""
    result = await db.execute(
        select(CocktailRecipeModel)
        .options(
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
        )
        .where(CocktailRecipeModel.id == cocktail_id)
    )
    cocktail = result.scalar_one_or_none()
    if not cocktail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cocktail with id {cocktail_id} not found",
        )

    lines = []
    total_cocktail_cost = 0.0
    scaled_total_cost = 0.0

    as_of = date.today()
    # Filter out juice ingredients if batch_type is 'base'
    recipe_ingredients = cocktail.recipe_ingredients
    if cocktail.batch_type == 'base':
        recipe_ingredients = [
            ri for ri in recipe_ingredients
            if ri.ingredient and ri.ingredient.subcategory
            and ri.ingredient.subcategory.name.lower() != 'juice'
        ]

    for ri in recipe_ingredients:
        qty = float(ri.quantity or 0)
        unit = ri.unit
        scaled_qty = qty * float(scale_factor or 0)

        ml = _unit_to_ml(qty, unit)
        scaled_ml = _unit_to_ml(scaled_qty, unit)

        bottle = ri.bottle
        if bottle is None:
            # fallback to default bottle
            bottle_result = await db.execute(
                select(BottleModel)
                .where(BottleModel.ingredient_id == ri.ingredient_id, BottleModel.is_default_cost == True)  # noqa: E712
                .limit(1)
            )
            bottle = bottle_result.scalar_one_or_none()

        price_minor = None
        currency = None
        cost_per_ml = 0.0
        if bottle and bottle.volume_ml and bottle.volume_ml > 0:
            price_result = await db.execute(
                select(BottlePriceModel)
                .where(
                    BottlePriceModel.bottle_id == bottle.id,
                    BottlePriceModel.start_date <= as_of,
                    (BottlePriceModel.end_date.is_(None) | (BottlePriceModel.end_date >= as_of)),
                )
                .order_by(BottlePriceModel.start_date.desc())
                .limit(1)
            )
            price = price_result.scalar_one_or_none()
            if price:
                price_minor = int(price.price_minor)
                currency = price.currency
                cost_per_ml = (price_minor / 100.0) / float(bottle.volume_ml)

        ingredient_cost = (scaled_ml or 0.0) * cost_per_ml
        total_cocktail_cost += (ml or 0.0) * cost_per_ml
        scaled_total_cost += ingredient_cost

        lines.append(
            {
                "ingredient_name": ri.ingredient.name if ri.ingredient else "Unknown",
                "quantity": qty,
                "unit": unit,
                "scaled_quantity": scaled_qty,
                "bottle_id": bottle.id if bottle else None,
                "bottle_name": bottle.name if bottle else None,
                "bottle_volume_ml": bottle.volume_ml if bottle else None,
                "price_minor": price_minor,
                "currency": currency,
                "cost_per_ml": cost_per_ml,
                "ingredient_cost": ingredient_cost,
            }
        )

    return {
        "lines": lines,
        "total_cocktail_cost": total_cocktail_cost,
        "scaled_total_cost": scaled_total_cost,
        "scale_factor": float(scale_factor or 0),
    }