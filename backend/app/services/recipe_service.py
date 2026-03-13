from sqlalchemy.orm import Session
from typing import Dict, List
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData  # NutritionData 从 nutrition_data 导入，避免冲突
from decimal import Decimal


async def batch_calculate_recipes_cost_nutrition(
    recipe_ids: List[int],
    user_id: int,
    db: Session = None
) -> Dict[int, Dict]:
    """批量计算多个菜谱的成本和营养信息"""
    # 首先获取所有菜谱
    recipes = db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()

    results = {}

    for recipe in recipes:
        cost_result = await calculate_recipe_cost(recipe.id, user_id, db)
        nutrition_result = await calculate_recipe_nutrition(recipe.id, db)

        # 合并结果
        combined_result = {
            "cost": cost_result,
            "nutrition": nutrition_result
        }

        results[recipe.id] = combined_result

    return results


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

        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            # 获取合并后的目标食材
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient.merged_into_id).first()

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

    # NRV（营养素参考值）- 中国标准值（成人每日摄入量）
    # 来源：GB 28050-2011《食品安全国家标准 预包装食品营养标签通则》
    NRV_REFERENCE_VALUES = {
        "能量": 2000,  # kcal
        "蛋白质": 60,   # g
        "脂肪": 60,     # g
        "碳水化合物": 300,  # g
        "膳食纤维": 25,   # g
        "钙": 800,      # mg
        "铁": 15,       # mg
        "钠": 2000,     # mg
        "钾": 2000,     # mg
        "维生素A": 800,  # μg
        "维生素C": 100,   # mg
        "维生素B1": 1.2, # mg
        "维生素B2": 1.4, # mg
        "维生素B12": 2.4, # μg
        "维生素D": 5,     # μg
        "维生素E": 14,    # mg
        "维生素K": 80     # μg
    }

    # 初始化所有核心营养素的总量
    total_core_nutrients = {
        "能量": {"value": 0, "unit": "kcal", "key": "energy_kcal"},
        "蛋白质": {"value": 0, "unit": "g", "key": "protein"},
        "脂肪": {"value": 0, "unit": "g", "key": "fat"},
        "碳水化合物": {"value": 0, "unit": "g", "key": "carbohydrate"},
        "膳食纤维": {"value": 0, "unit": "g", "key": "fiber"},
        "钙": {"value": 0, "unit": "mg", "key": "calcium"},
        "铁": {"value": 0, "unit": "mg", "key": "iron"},
        "钠": {"value": 0, "unit": "mg", "key": "sodium"},
        "钾": {"value": 0, "unit": "mg", "key": "potassium"},
        "维生素A": {"value": 0, "unit": "μg", "key": "vitamin_a_rae"},
        "维生素C": {"value": 0, "unit": "mg", "key": "vitamin_c"},
        "维生素B1": {"value": 0, "unit": "mg", "key": "vitamin_b1"},
        "维生素B2": {"value": 0, "unit": "mg", "key": "vitamin_b2"},
        "维生素B12": {"value": 0, "unit": "μg", "key": "vitamin_b12"},
        "维生素D": {"value": 0, "unit": "μg", "key": "vitamin_d"},
        "维生素E": {"value": 0, "unit": "mg", "key": "vitamin_e"},
        "维生素K": {"value": 0, "unit": "μg", "key": "vitamin_k"}
    }

    from app.utils.unit_converter import convert_to_standard

    # 存储食材贡献详情
    ingredient_details = []

    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient

        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient.merged_into_id).first()

        if not ingredient:
            continue

        # 使用 ingredient_id 查找营养数据（而不是 nutrition_id）
        nutrition = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient.id
        ).order_by(NutritionData.id.desc()).first()

        if not nutrition:
            continue

        # 获取营养数据（从 JSON 字段）
        nutrients = nutrition.nutrients or {}
        core_nutrients = nutrients.get("core_nutrients", {})
        all_nutrients = nutrients.get("all_nutrients", {})

        # 提取参考基准
        reference_amount = Decimal(str(nutrition.reference_amount or 100.0))
        reference_unit = nutrition.reference_unit or "g"

        # 获取菜谱中的原料数量，并转换为标准单位
        ingredient_quantity_str = recipe_ingredient.quantity or "0"
        ingredient_unit = ""

        # 尝试解析数量和单位
        try:
            # 如果数量是纯数字字符串
            if ingredient_quantity_str.replace(".", "").replace("-", "").isdigit():
                quantity = Decimal(str(ingredient_quantity_str))
                # 如果有单位信息，尝试使用原始数量和单位
                if recipe_ingredient.unit:
                    ingredient_unit = recipe_ingredient.unit.abbreviation
                    # 转换为标准单位
                    standard_quantity, standard_unit = convert_to_standard(quantity, ingredient_unit)
                else:
                    # 没有单位信息，假设使用参考基准单位
                    standard_quantity = quantity
                    standard_unit = reference_unit
            else:
                # 数量可能包含单位（如 "250g"），需要解析
                import re
                match = re.match(r"([\d.]+)\s*([a-zA-Z\u4e00-\u9fff]+)", ingredient_quantity_str)
                if match:
                    quantity = Decimal(match.group(1))
                    ingredient_unit = match.group(2)
                    standard_quantity, standard_unit = convert_to_standard(quantity, ingredient_unit)
                else:
                    # 无法解析，使用默认值
                    standard_quantity = Decimal("100")
                    standard_unit = reference_unit
        except Exception as e:
            # 解析失败，使用默认值
            standard_quantity = Decimal("100")
            standard_unit = reference_unit

        # 计算比例因子（菜谱中的数量 / 参考基准数量）
        # 确保单位一致才能比较

        # 首先处理容量单位的密度转换
        if standard_unit.lower() == "ml" and recipe_ingredient.unit:
            # 如果是容量单位，尝试使用密度转换为重量
            from app.models.ingredient_density import IngredientDensity

            # 查找密度数据（mL → g）
            density = db.query(IngredientDensity).filter(
                IngredientDensity.ingredient_id == ingredient.id,
                IngredientDensity.from_unit_id == recipe_ingredient.unit.id,
                IngredientDensity.to_unit_id == 3  # g 的 ID
            ).first()

            if density and density.density_value:
                # 使用密度转换：重量 = 容量 × 密度
                standard_quantity = standard_quantity * Decimal(str(density.density_value))
                standard_unit = "g"  # 转换为克
            else:
                # 没有密度数据，假设密度为 1.0 g/mL
                standard_quantity = standard_quantity
                standard_unit = "g"

        if standard_unit.lower() in ["g", "ml"] and reference_unit.lower() in ["g", "ml"]:
            # 如果都是重量或容量单位，可以计算比例
            ratio = standard_quantity / reference_amount
        elif recipe_ingredient.unit and recipe_ingredient.unit.unit_type == "count":
            # 如果是计数单位（如"个"），尝试使用 piece_weight 转换
            if ingredient.piece_weight and ingredient.piece_weight_unit_id:
                # 使用食材的标准重量转换（如：1个鸡蛋=50g）
                piece_weight = Decimal(str(ingredient.piece_weight))
                piece_weight_unit = ingredient.piece_weight_unit.abbreviation

                # 转换为标准重量单位
                converted_weight, converted_unit = convert_to_standard(piece_weight, piece_weight_unit)
                # 计算总重量（数量 × 每个的重量）
                total_weight = quantity * converted_weight

                if converted_unit.lower() == reference_unit.lower():
                    # 单位一致，计算比例
                    ratio = total_weight / reference_amount
                else:
                    # 单位不一致，尝试转换
                    from app.models.unit import Unit
                    weight_unit_obj = db.query(Unit).filter(Unit.abbreviation == converted_unit).first()
                    if weight_unit_obj and weight_unit_obj.unit_type == "mass":
                        ratio = total_weight / reference_amount
                    else:
                        # 无法转换，使用默认值
                        ratio = Decimal("1.0")
            else:
                # 没有设置标准重量，假设比例是1:1
                ratio = Decimal("1.0")
        else:
            # 单位不一致，假设比例是1:1（使用参考值）
            ratio = Decimal("1.0")

        # 累加所有核心营养素值
        for nutrient_name, nutrient_data in core_nutrients.items():
            if nutrient_name in total_core_nutrients:
                value = float(nutrient_data.get("value", 0) or 0)
                source_unit = nutrient_data.get("unit", "")

                # 如果是能量，检查单位并转换为 kcal
                if nutrient_name == "能量" and source_unit == "kJ":
                    # 先将 kJ 转换为 kcal（1 kJ = 0.239006 kcal）
                    value_kcal = value * 0.239006
                    total_core_nutrients[nutrient_name]["value"] += value_kcal * float(ratio)
                    total_core_nutrients[nutrient_name]["unit"] = "kcal"
                else:
                    total_core_nutrients[nutrient_name]["value"] += value * float(ratio)
                    total_core_nutrients[nutrient_name]["unit"] = source_unit

        # 添加食材贡献详情
        ingredient_details.append({
            "ingredient_id": ingredient.id,
            "ingredient_name": ingredient.name,
            "quantity": float(standard_quantity),
            "unit": standard_unit,
            "nutrition_contribution": {
                nutrient_name: {
                    "value": float(nutrient_data.get("value", 0) or 0) * float(ratio),
                    "unit": nutrient_data.get("unit", ""),
                    "nrp_pct": round(((float(nutrient_data.get("value", 0) or 0) * float(ratio)) / NRV_REFERENCE_VALUES.get(nutrient_name, 1)) * 100, 2) if NRV_REFERENCE_VALUES.get(nutrient_name, 0) > 0 else 0
                }
                for nutrient_name, nutrient_data in core_nutrients.items()
                if nutrient_name in total_core_nutrients
            }
        })

    servings = recipe.servings or 1

    # 计算每份营养值和 NRV 百分比
    per_serving_core_nutrients = {}
    for name, data in total_core_nutrients.items():
        per_serving_value = round(data["value"] / servings, 2)
        per_serving_unit = data["unit"]

        # 使用 NRV 标准参考值计算 NRV 百分比
        nrv_reference = NRV_REFERENCE_VALUES.get(name, 0)
        if nrv_reference > 0:
            # NRV 百分比 = （每份营养值 / NRV 标准值）× 100
            per_serving_nrp_pct = round((per_serving_value / nrv_reference) * 100, 2)
        else:
            # 没有参考值，使用默认值
            per_serving_nrp_pct = 0

        per_serving_core_nutrients[name] = {
            "value": per_serving_value,
            "unit": per_serving_unit,
            "key": data["key"],
            "nrp_pct": per_serving_nrp_pct
        }

    # 提取简化的核心值用于兼容性
    energy_data = total_core_nutrients.get("能量", {})
    protein_data = total_core_nutrients.get("蛋白质", {})
    fat_data = total_core_nutrients.get("脂肪", {})
    carb_data = total_core_nutrients.get("碳水化合物", {})

    # 如果能量单位是 kJ，转换为 kcal
    total_calories = float(energy_data["value"])
    if energy_data["unit"] == "kJ":
        total_calories *= 0.239006

    return {
        "total_calories": total_calories,
        "total_protein": float(protein_data["value"]),
        "total_fat": float(fat_data["value"]),
        "total_carbs": float(carb_data["value"]),
        "per_serving": {
            "calories": total_calories / servings,
            "protein": float(protein_data["value"]) / servings,
            "fat": float(fat_data["value"]) / servings,
            "carbs": float(carb_data["value"]) / servings
        },
        "total_nutrition": {
            "core_nutrients": {
                name: {
                    **data,
                    "value": round(data["value"], 2)
                }
                for name, data in total_core_nutrients.items()
            }
        },
        "per_serving_nutrition": {
            "core_nutrients": per_serving_core_nutrients
        },
        "ingredient_details": ingredient_details  # 添加食材贡献详情
    }