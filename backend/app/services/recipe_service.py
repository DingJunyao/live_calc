from sqlalchemy.orm import Session
from typing import Dict, List
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient, NutritionData
from decimal import Decimal


async def calculate_recipe_cost(
    recipe_id: int,
    user_id: int,
    db: Session = None
) -> Dict:
    """计算菜谱成本"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_cost = Decimal("0.00")
    cost_breakdown = []

    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient
        if not ingredient or not ingredient.nutrition_id:
            continue

        # 查找用户最新的价格记录
        latest_record = db.query(ProductRecord).filter(
            ProductRecord.user_id == user_id,
            ProductRecord.product_name.contains(ingredient.name)
        ).order_by(ProductRecord.recorded_at.desc()).first()

        if latest_record:
            cost = Decimal(str(latest_record.price))
            total_cost += cost
            cost_breakdown.append({
                "ingredient_name": ingredient.name,
                "cost": float(cost),
                "unit_price": float(latest_record.price)
            })

    return {
        "total_cost": total_cost,
        "currency": "CNY",
        "cost_per_serving": total_cost / (recipe.servings or 1),
        "cost_breakdown": cost_breakdown
    }


async def calculate_recipe_nutrition(
    recipe_id: int,
    db: Session = None
) -> Dict:
    """计算菜谱营养"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_calories = Decimal("0.00")
    total_protein = Decimal("0.00")
    total_fat = Decimal("0.00")
    total_carbs = Decimal("0.00")

    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient
        if not ingredient or not ingredient.nutrition_id:
            continue

        nutrition = db.query(NutritionData).filter(
            NutritionData.id == ingredient.nutrition_id
        ).first()
        if not nutrition:
            continue

        total_calories += Decimal(str(nutrition.calories or 0))
        total_protein += Decimal(str(nutrition.protein or 0))
        total_fat += Decimal(str(nutrition.fat or 0))
        total_carbs += Decimal(str(nutrition.carbs or 0))

    servings = recipe.servings or 1

    return {
        "total_calories": total_calories,
        "total_protein": total_protein,
        "total_fat": total_fat,
        "total_carbs": total_carbs,
        "per_serving": {
            "calories": total_calories / servings,
            "protein": total_protein / servings,
            "fat": total_fat / servings,
            "carbs": total_carbs / servings
        }
    }
