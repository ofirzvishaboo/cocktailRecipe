from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from schemas.cocktails import (
    CocktailRecipe,
    CocktailRecipeCreate,
    CocktailRecipeUpdate,
    CocktailCostResponse,
    EventEstimateRequest,
    EventEstimateResponse,
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
import math

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
                    "ingredient_name_he": getattr(ingredient, "name_he", None) if ingredient else None,
                    "quantity": float(ri.quantity),
                    "unit": ri.unit,
                    "bottle_id": ri.bottle_id,
                    "bottle_name": bottle.name if bottle else None,
                    "bottle_name_he": getattr(bottle, "name_he", None) if bottle else None,
                    "bottle_volume_ml": bottle.volume_ml if bottle else None,
                    "is_garnish": ri.is_garnish,
                    "is_optional": ri.is_optional,
                    "sort_order": ri.sort_order,
                    "subcategory_name": subcategory.name if subcategory else None,
                }
            )

    glass_type = getattr(c, "glass_type", None)

    return {
        "id": c.id,
        "created_by_user_id": c.created_by_user_id,
        "user": user_data,
        "name": c.name,
        "name_he": getattr(c, "name_he", None),
        "description": c.description,
        "description_he": getattr(c, "description_he", None),
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "glass_type_id": c.glass_type_id,
        # Convenience fields (matches `backend/db/cocktail_recipe.py` `to_schema`)
        "glass_type_name": glass_type.name if glass_type else None,
        "glass_type_name_he": getattr(glass_type, "name_he", None) if glass_type else None,
        "picture_url": c.picture_url,
        "garnish_text": c.garnish_text,
        "garnish_text_he": getattr(c, "garnish_text_he", None),
        "base_recipe_id": c.base_recipe_id,
        "is_base": c.is_base,
        "menus": list(c.menus) if getattr(c, "menus", None) else (["classic"] if c.is_base else ["signature"]),
        "preparation_method": c.preparation_method,
        "preparation_method_he": getattr(c, "preparation_method_he", None),
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
            selectinload(CocktailRecipeModel.glass_type),
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
            selectinload(CocktailRecipeModel.glass_type),
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
            name_he=cocktail.name_he,
            description=cocktail.description,
            description_he=cocktail.description_he,
            picture_url=cocktail.picture_url,
            garnish_text=cocktail.garnish_text,
            garnish_text_he=cocktail.garnish_text_he,
            glass_type_id=cocktail.glass_type_id,
            base_recipe_id=cocktail.base_recipe_id,
            is_base=bool(cocktail.is_base),
            menus=list(cocktail.menus) if cocktail.menus else [],
            preparation_method=cocktail.preparation_method,
            preparation_method_he=cocktail.preparation_method_he,
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
                selectinload(CocktailRecipeModel.glass_type),
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
        cocktail_model.name_he = cocktail.name_he
        cocktail_model.description = cocktail.description
        cocktail_model.description_he = cocktail.description_he
        cocktail_model.picture_url = cocktail.picture_url
        cocktail_model.garnish_text = cocktail.garnish_text
        cocktail_model.garnish_text_he = cocktail.garnish_text_he
        cocktail_model.glass_type_id = cocktail.glass_type_id
        cocktail_model.base_recipe_id = cocktail.base_recipe_id
        cocktail_model.is_base = bool(cocktail.is_base)
        cocktail_model.menus = list(cocktail.menus) if cocktail.menus else []
        cocktail_model.preparation_method = cocktail.preparation_method
        cocktail_model.preparation_method_he = cocktail.preparation_method_he
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
                selectinload(CocktailRecipeModel.glass_type),
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
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Compute ingredient and total cost for a cocktail (scaled) excluding juice ingredients."""
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

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
                "ingredient_name_he": getattr(ri.ingredient, "name_he", None) if ri.ingredient else None,
                "quantity": qty,
                "unit": unit,
                "scaled_quantity": scaled_qty,
                "bottle_id": bottle.id if bottle else None,
                "bottle_name": bottle.name if bottle else None,
                "bottle_name_he": getattr(bottle, "name_he", None) if bottle else None,
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
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Compute ingredient and total cost for a cocktail (scaled). Uses bottles + bottle_prices + recipe_ingredients."""
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

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
    # NOTE: /cost should always include ALL ingredients.
    # If the caller wants to exclude juices (e.g. when batching "base"), use /no-juice-cost.
    recipe_ingredients = cocktail.recipe_ingredients

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
                "ingredient_name_he": getattr(ri.ingredient, "name_he", None) if ri.ingredient else None,
                "quantity": qty,
                "unit": unit,
                "scaled_quantity": scaled_qty,
                "bottle_id": bottle.id if bottle else None,
                "bottle_name": bottle.name if bottle else None,
                "bottle_name_he": getattr(bottle, "name_he", None) if bottle else None,
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


@router.post("/event-estimate", response_model=EventEstimateResponse)
async def event_estimate(
    payload: EventEstimateRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Estimate ingredients + bottles needed for an event.

    - Admin-only.
    - Input: 4 cocktail names + people count.
    - Assumption: servings_per_person (default 3) split equally across the 4 cocktail slots.
    - Includes all ingredients (juice + garnish included).
    """
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    names_in = [(n or "").strip() for n in payload.cocktail_names]
    names_lower = [n.lower() for n in names_in if n]
    unique_lower = sorted(set(names_lower))

    stmt = (
        select(CocktailRecipeModel)
        .options(
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.ingredient).selectinload(IngredientModel.subcategory),
            selectinload(CocktailRecipeModel.recipe_ingredients).selectinload(RecipeIngredientModel.bottle),
        )
        .where(
            or_(
                func.lower(CocktailRecipeModel.name).in_(unique_lower),
                func.lower(CocktailRecipeModel.name_he).in_(unique_lower),
            )
        )
    )
    res = await db.execute(stmt)
    found = res.scalars().all() or []

    by_lower: dict[str, CocktailRecipeModel] = {}
    for c in found:
        en = (getattr(c, "name", "") or "").strip().lower()
        he = (getattr(c, "name_he", "") or "").strip().lower()
        if en:
            by_lower.setdefault(en, c)
        if he:
            by_lower.setdefault(he, c)

    missing: List[str] = []
    selected: List[CocktailRecipeModel] = []
    for raw in names_in:
        key = (raw or "").strip().lower()
        c = by_lower.get(key)
        if not c:
            missing.append(raw)
            continue
        selected.append(c)

    total_servings = float(payload.people) * float(payload.servings_per_person)
    servings_per_cocktail = total_servings / float(len(payload.cocktail_names) or 1)

    # Preload default-cost bottles for ingredients that don't have a bottle set on the recipe ingredient.
    ingredient_ids: set[UUID] = set()
    for c in selected:
        for ri in (getattr(c, "recipe_ingredients", None) or []):
            if getattr(ri, "ingredient_id", None):
                ingredient_ids.add(ri.ingredient_id)

    default_bottles_by_ingredient: dict[UUID, BottleModel] = {}
    if ingredient_ids:
        bres = await db.execute(
            select(BottleModel)
            .where(BottleModel.ingredient_id.in_(list(ingredient_ids)))
            .where(BottleModel.is_default_cost == True)  # noqa: E712
        )
        for b in bres.scalars().all():
            default_bottles_by_ingredient.setdefault(b.ingredient_id, b)

    # Aggregation:
    # - ml_agg: per ingredient_id -> total_ml and chosen bottle
    # - qty_agg: per (ingredient_id, unit) -> total_quantity
    ml_agg: dict[UUID, dict] = {}
    qty_agg: dict[tuple[UUID, str], dict] = {}

    def _ensure_ml_bucket(ingredient_id: UUID, ingredient_obj: Optional[IngredientModel]) -> dict:
        if ingredient_id not in ml_agg:
            ml_agg[ingredient_id] = {
                "ingredient": ingredient_obj,
                "total_ml": 0.0,
                "bottle": None,
            }
        else:
            if ml_agg[ingredient_id].get("ingredient") is None and ingredient_obj is not None:
                ml_agg[ingredient_id]["ingredient"] = ingredient_obj
        return ml_agg[ingredient_id]

    def _ensure_qty_bucket(ingredient_id: UUID, unit: str, ingredient_obj: Optional[IngredientModel]) -> dict:
        key = (ingredient_id, unit)
        if key not in qty_agg:
            qty_agg[key] = {
                "ingredient": ingredient_obj,
                "unit": unit,
                "total_quantity": 0.0,
            }
        else:
            if qty_agg[key].get("ingredient") is None and ingredient_obj is not None:
                qty_agg[key]["ingredient"] = ingredient_obj
        return qty_agg[key]

    for c in selected:
        for ri in (getattr(c, "recipe_ingredients", None) or []):
            ingredient = getattr(ri, "ingredient", None)
            ingredient_id = getattr(ri, "ingredient_id", None)
            if not ingredient_id:
                continue

            qty = float(getattr(ri, "quantity", 0) or 0)
            unit = (getattr(ri, "unit", "") or "").strip().lower()
            scaled_qty = qty * servings_per_cocktail

            scaled_ml = _unit_to_ml(scaled_qty, unit)
            if scaled_ml is not None:
                bucket = _ensure_ml_bucket(ingredient_id, ingredient)
                bucket["total_ml"] += float(scaled_ml)

                # Pick bottle for recommendation math
                bottle = getattr(ri, "bottle", None)
                if bottle is None:
                    bottle = default_bottles_by_ingredient.get(ingredient_id)
                if bucket.get("bottle") is None and bottle is not None and getattr(bottle, "volume_ml", None):
                    bucket["bottle"] = bottle
            else:
                qb = _ensure_qty_bucket(ingredient_id, unit or "", ingredient)
                qb["total_quantity"] += float(scaled_qty)

    out_lines: List[dict] = []

    # ml-convertible lines with bottle recommendations
    for ingredient_id, b in ml_agg.items():
        ing = b.get("ingredient")
        total_ml_val = float(b.get("total_ml") or 0.0)
        bottle = b.get("bottle")

        bottle_volume = int(getattr(bottle, "volume_ml", 0) or 0) if bottle is not None else 0
        bottles_needed = None
        leftover_ml = None
        if bottle_volume and total_ml_val > 0:
            bottles_needed = int(math.ceil(total_ml_val / float(bottle_volume)))
            leftover_ml = float(bottles_needed * bottle_volume) - total_ml_val

        out_lines.append(
            {
                "ingredient_id": ingredient_id,
                "ingredient_name": (getattr(ing, "name", None) or "Unknown"),
                "ingredient_name_he": getattr(ing, "name_he", None) if ing is not None else None,
                "total_ml": total_ml_val,
                "bottle_id": getattr(bottle, "id", None) if bottle is not None else None,
                "bottle_name": getattr(bottle, "name", None) if bottle is not None else None,
                "bottle_name_he": getattr(bottle, "name_he", None) if bottle is not None else None,
                "bottle_volume_ml": getattr(bottle, "volume_ml", None) if bottle is not None else None,
                "bottles_needed": bottles_needed,
                "leftover_ml": leftover_ml,
            }
        )

    # non-ml lines (grouped per ingredient + unit)
    for (_ingredient_id, unit), b in qty_agg.items():
        ing = b.get("ingredient")
        out_lines.append(
            {
                "ingredient_id": _ingredient_id,
                "ingredient_name": (getattr(ing, "name", None) or "Unknown"),
                "ingredient_name_he": getattr(ing, "name_he", None) if ing is not None else None,
                "total_quantity": float(b.get("total_quantity") or 0.0),
                "unit": unit,
            }
        )

    # Sort for stable output
    def _sort_key(x: dict) -> tuple:
        name = (x.get("ingredient_name") or "").lower()
        unit = (x.get("unit") or "")
        return (name, unit)

    out_lines.sort(key=_sort_key)

    return {
        "people": int(payload.people),
        "servings_per_person": float(payload.servings_per_person),
        "total_servings": float(total_servings),
        "servings_per_cocktail": float(servings_per_cocktail),
        "missing_cocktails": missing,
        "ingredients": out_lines,
    }