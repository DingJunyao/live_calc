from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.schemas.recipe import (
    RecipeCreate,
    RecipeResponse,
    RecipeDetailResponse,
    RecipeCostResponse,
    RecipeNutritionResponse
)
from app.services.recipe_service import calculate_recipe_cost, calculate_recipe_nutrition

router = APIRouter()


@router.post("/", response_model=RecipeResponse)
async def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建菜谱"""
    try:
        db_recipe = Recipe(
            name=recipe.name,
            source=recipe.source,
            user_id=current_user.id,
            tags=recipe.tags,
            cooking_steps=[s.model_dump() for s in recipe.cooking_steps],
            total_time_minutes=recipe.total_time_minutes,
            difficulty=recipe.difficulty,
            servings=recipe.servings,
            tips=recipe.tips
        )
        db.add(db_recipe)
        db.flush()

        for ingredient_data in recipe.ingredients:
            # 查找食材
            ingredient = db.query(Ingredient).filter(
                Ingredient.name == ingredient_data.ingredient_name
            ).first()
            if not ingredient:
                continue

            recipe_ingredient = RecipeIngredient(
                recipe_id=db_recipe.id,
                ingredient_id=ingredient.id,
                quantity=ingredient_data.quantity,
                unit=ingredient_data.unit
            )
            db.add(recipe_ingredient)

        db.commit()
        db.refresh(db_recipe)
        return db_recipe
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建菜谱失败: {str(e)}")


@router.get("/", response_model=List[RecipeResponse])
async def get_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱列表"""
    try:
        query = db.query(Recipe).filter(Recipe.user_id == current_user.id)

        if tag:
            # JSON 查询
            query = query.filter(Recipe.tags.contains([tag]))

        recipes = query.order_by(Recipe.created_at.desc()).offset(skip).limit(limit).all()
        return recipes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱列表失败: {str(e)}")


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
async def get_recipe_detail(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱详情"""
    try:
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.user_id == current_user.id
        ).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        ingredients_detail = []
        for recipe_ingredient in recipe.ingredients:
            ingredient = recipe_ingredient.ingredient
            ingredients_detail.append({
                "ingredient_id": ingredient.id,
                "name": ingredient.name,
                "quantity": recipe_ingredient.quantity,
                "unit": recipe_ingredient.unit
            })

        return {
            "id": recipe.id,
            "name": recipe.name,
            "source": recipe.source,
            "tags": recipe.tags,
            "cooking_steps": recipe.cooking_steps,
            "total_time_minutes": recipe.total_time_minutes,
            "difficulty": recipe.difficulty,
            "servings": recipe.servings,
            "tips": recipe.tips,
            "created_at": recipe.created_at,
            "updated_at": recipe.updated_at,
            "ingredients": ingredients_detail
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱详情失败: {str(e)}")


@router.get("/{recipe_id}/cost", response_model=RecipeCostResponse)
async def get_recipe_cost(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱成本"""
    try:
        result = await calculate_recipe_cost(recipe_id, current_user.id, db=db)
        if not result:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        return RecipeCostResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算成本失败: {str(e)}")


@router.get("/{recipe_id}/nutrition", response_model=RecipeNutritionResponse)
async def get_recipe_nutrition(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱营养"""
    try:
        result = await calculate_recipe_nutrition(recipe_id, db=db)
        if not result:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        return RecipeNutritionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算营养失败: {str(e)}")
