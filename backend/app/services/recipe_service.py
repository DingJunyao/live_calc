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
        if not ingredient:
            continue

        # 首先通过ingredient_id查找商品（这个SB逻辑之前漏了）
        from app.models.product_entity import Product
        product = db.query(Product).filter(
            Product.ingredient_id == ingredient.id,
            Product.is_active == True
        ).first()

        latest_record = None
        unit_price = None

        if product:
            # 通过商品ID查找用户最新的价格记录
            latest_record = db.query(ProductRecord).filter(
                ProductRecord.user_id == user_id,
                ProductRecord.product_id == product.id
            ).order_by(ProductRecord.recorded_at.desc()).first()

            if latest_record:
                # 计算单价：总价 ÷ 数量
                record_price = Decimal(str(latest_record.price))
                record_quantity = Decimal(str(latest_record.standard_quantity))
                unit_price = record_price / record_quantity
        else:
            # 如果找不到商品或者找不到价格记录，尝试通过名称匹配（这个SB数据一致性问题）
            latest_record = db.query(ProductRecord).filter(
                ProductRecord.user_id == user_id,
                ProductRecord.product_name.contains(ingredient.name)
            ).order_by(ProductRecord.recorded_at.desc()).first()

            if latest_record:
                # 同样需要计算单价
                record_price = Decimal(str(latest_record.price))
                record_quantity = Decimal(str(latest_record.standard_quantity))
                unit_price = record_price / record_quantity

        if latest_record:
            # 计算成本：单价 × 菜谱中的数量 = 成本
            ingredient_quantity = recipe_ingredient.quantity
            if ingredient_quantity:
                try:
                    # 尝试解析数量（可能是数字或字符串）
                    quantity = Decimal(str(ingredient_quantity))
                    cost = unit_price * quantity
                    total_cost += cost

                    cost_breakdown.append({
                        "ingredient_name": ingredient.name,
                        "quantity": str(ingredient_quantity),
                        "unit_price": float(unit_price),
                        "cost": float(cost)
                    })
                except Exception as e:
                    # 数量解析失败，使用基础价格
                    cost = Decimal(str(latest_record.price))
                    total_cost += cost
                    cost_breakdown.append({
                        "ingredient_name": ingredient.name,
                        "quantity": "1",  # 默认为1
                        "unit_price": float(latest_record.price),
                        "cost": float(cost)
                    })
            else:
                # 没有数量，直接使用单价
                if unit_price:
                    cost = unit_price
                    total_cost += cost
                    cost_breakdown.append({
                        "ingredient_name": ingredient.name,
                        "quantity": "1",
                        "unit_price": float(unit_price),
                        "cost": float(cost)
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
        if not ingredient:
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
