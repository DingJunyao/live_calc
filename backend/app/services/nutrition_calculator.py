"""
营养计算引擎

基于 USDA 营养数据和 NRV（营养素参考值）百分比进行计算
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.nutrition_data import NutritionData, NRVStandard
from app.models.nutrition import Ingredient
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product_entity import Product


class NutritionCalculator:
    """
    营养计算器

    提供基于 NRV 百分比的营养计算功能
    """

    # 核心营养素列表
    CORE_NUTRIENTS = [
        "energy_kcal", "protein", "fat", "carbohydrate", "fiber",
        "calcium", "iron", "sodium", "potassium",
        "vitamin_a_rae", "vitamin_c", "vitamin_b1", "vitamin_b2",
        "vitamin_b12", "vitamin_d", "vitamin_e", "vitamin_k"
    ]

    # 营养素显示名称
    NUTRIENT_NAMES = {
        "energy_kcal": "能量",
        "protein": "蛋白质",
        "fat": "脂肪",
        "carbohydrate": "碳水化合物",
        "fiber": "膳食纤维",
        "calcium": "钙",
        "iron": "铁",
        "sodium": "钠",
        "potassium": "钾",
        "vitamin_a_rae": "维生素A",
        "vitamin_c": "维生素C",
        "vitamin_b1": "维生素B1",
        "vitamin_b2": "维生素B2",
        "vitamin_b12": "维生素B12",
        "vitamin_d": "维生素D",
        "vitamin_e": "维生素E",
        "vitamin_k": "维生素K",
        "saturated_fat": "饱和脂肪",
        "cholesterol": "胆固醇",
        "folate": "叶酸"
    }

    def __init__(self, db: Session):
        self.db = db

    def calculate_ingredient_nutrition(
        self,
        ingredient_id: int,
        quantity: float = 100.0,
        unit: str = "g"
    ) -> Optional[Dict]:
        """
        计算指定数量食材的营养成分

        Args:
            ingredient_id: 食材 ID
            quantity: 数量
            unit: 单位

        Returns:
            计算后的营养数据
        """
        # 获取营养数据
        nutrition = self.db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id,
            NutritionData.is_verified == True
        ).first()

        if not nutrition:
            return None

        # 转换单位到基准单位（g 或 ml）
        base_quantity = self._convert_to_base(quantity, unit)

        # 计算缩放比例
        scale_factor = base_quantity / nutrition.reference_amount

        # 计算各营养素的值
        calculated_nutrients = self._calculate_scaled_nutrients(
            nutrition.nutrients,
            scale_factor
        )

        return {
            "ingredient_id": ingredient_id,
            "quantity": quantity,
            "unit": unit,
            "base_quantity": base_quantity,
            "nutrition": calculated_nutrients
        }

    def calculate_recipe_nutrition(
        self,
        recipe_id: int,
        servings: Optional[int] = None
    ) -> Optional[Dict]:
        """
        计算菜谱的营养成分

        Args:
            recipe_id: 菜谱 ID
            servings: 份数（如果为 None，使用菜谱默认份数）

        Returns:
            计算后的营养数据
        """
        # 获取菜谱
        recipe = self.db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return None

        # 使用指定的份数或默认份数
        servings = servings or recipe.servings or 1

        # 获取菜谱的所有原料
        recipe_ingredients = self.db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()

        if not recipe_ingredients:
            return None

        # 累计所有原料的营养成分
        total_nutrition = {
            "core_nutrients": {},
            "all_nutrients": {},
            "nrp_totals": {}
        }

        ingredient_details = []

        for ri in recipe_ingredients:
            # 解析原料数量
            quantity = self._parse_quantity(ri.quantity, ri.quantity_range)

            if quantity is None:
                continue

            unit = ri.unit.abbreviation if ri.unit else "g"

            # 计算该原料的营养成分
            ingredient_nutrition = self.calculate_ingredient_nutrition(
                ri.ingredient_id,
                quantity,
                unit
            )

            if not ingredient_nutrition:
                continue

            # 累加到总营养
            self._accumulate_nutrients(
                total_nutrition,
                ingredient_nutrition["nutrition"]
            )

            # 记录原料详情
            ingredient_details.append({
                "ingredient_id": ri.ingredient_id,
                "ingredient_name": ri.ingredient.name if ri.ingredient else "未知",
                "quantity": quantity,
                "unit": unit,
                "nutrition": ingredient_nutrition["nutrition"]
            })

        # 计算每份营养
        per_serving_nutrition = self._calculate_per_serving(
            total_nutrition,
            servings
        )

        return {
            "recipe_id": recipe_id,
            "recipe_name": recipe.name,
            "total_nutrition": total_nutrition,
            "per_serving_nutrition": per_serving_nutrition,
            "servings": servings,
            "ingredient_details": ingredient_details
        }

    def calculate_product_nutrition(
        self,
        product_id: int,
        quantity: Optional[float] = None,
        unit: Optional[str] = None
    ) -> Optional[Dict]:
        """
        计算商品的营养成分

        Args:
            product_id: 商品 ID
            quantity: 数量（如果为 None，使用商品默认数量）
            unit: 单位（如果为 None，使用商品默认单位）

        Returns:
            计算后的营养数据
        """
        # 获取商品
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None

        # 优先使用商品自定义营养数据
        if product.has_custom_nutrition and product.custom_nutrition_data:
            # 直接使用自定义数据
            if quantity is None:
                quantity = product.default_quantity or 100.0
            if unit is None:
                unit = product.default_unit or "g"

            scale_factor = quantity / (product.custom_nutrition_data.get("reference_amount", 100.0))

            return {
                "product_id": product_id,
                "product_name": product.name,
                "quantity": quantity,
                "unit": unit,
                "source": "custom",
                "nutrition": self._calculate_scaled_nutrients(
                    product.custom_nutrition_data,
                    scale_factor
                )
            }

        # 使用关联食材的 USDA 数据
        if product.ingredient_id:
            return self.calculate_ingredient_nutrition(
                product.ingredient_id,
                quantity or 100.0,
                unit or "g"
            )

        return None

    def _convert_to_base(self, quantity: float, unit: str) -> float:
        """
        转换单位到基准单位

        使用 app.utils.unit_converter 的转换函数
        """
        from app.utils.unit_converter import convert_to_standard

        quantity_decimal = Decimal(str(quantity))
        converted_quantity, standard_unit = convert_to_standard(quantity_decimal, unit)

        # 转换为标准单位后再转换为克或毫升
        if standard_unit in ["g", "ml"]:
            return float(converted_quantity)
        elif standard_unit == "ml":
            # 假设 1ml = 1g（简化处理）
            return float(converted_quantity)
        else:
            # 其他单位不转换
            return quantity

    def _parse_quantity(
        self,
        quantity: str,
        quantity_range: Optional[Dict] = None
    ) -> Optional[float]:
        """
        解析数量字符串

        支持格式:
        - "100" -> 100.0
        - "100-200" -> 150.0 (取平均值)
        - {"min": 100, "max": 200} -> 150.0
        """
        try:
            if quantity_range and isinstance(quantity_range, dict):
                min_q = float(quantity_range.get("min", 0))
                max_q = float(quantity_range.get("max", 0))
                if min_q > 0 and max_q > 0:
                    return (min_q + max_q) / 2

            if quantity and isinstance(quantity, str):
                # 尝试解析 "100-200" 格式
                if "-" in quantity:
                    parts = quantity.split("-")
                    if len(parts) == 2:
                        min_q = float(parts[0].strip())
                        max_q = float(parts[1].strip())
                        return (min_q + max_q) / 2

                # 尝试直接转换为 float
                return float(quantity.strip())

            if quantity:
                return float(quantity)

            return None

        except (ValueError, TypeError):
            return None

    def _calculate_scaled_nutrients(
        self,
        nutrients: Dict,
        scale_factor: float
    ) -> Dict:
        """
        计算按比例缩放后的营养值
        """
        result = {
            "core_nutrients": {},
            "all_nutrients": {},
            "nrp_totals": {}
        }

        # 处理核心营养素
        core_nutrients = nutrients.get("core_nutrients", {})
        for name, data in core_nutrients.items():
            result["core_nutrients"][name] = {
                **data,
                "value": round(data["value"] * scale_factor, 2),
                "nrp_pct": round(data["nrp_pct"] * scale_factor, 2)
            }

        # 处理所有营养素
        all_nutrients = nutrients.get("all_nutrients", {})
        for key, data in all_nutrients.items():
            result["all_nutrients"][key] = {
                **data,
                "value": round(data["value"] * scale_factor, 2),
                "nrp_pct": round(data["nrp_pct"] * scale_factor, 2)
            }

        # 计算 NRV 总和
        for name, data in result["core_nutrients"].items():
            if "nrp_pct" in data:
                result["nrp_totals"][name] = data["nrp_pct"]

        return result

    def _accumulate_nutrients(
        self,
        total: Dict,
        addition: Dict
    ):
        """
        累加营养数据
        """
        # 累加核心营养素
        for name, data in addition.get("core_nutrients", {}).items():
            if name not in total["core_nutrients"]:
                total["core_nutrients"][name] = data.copy()
            else:
                total["core_nutrients"][name]["value"] += data["value"]
                total["core_nutrients"][name]["nrp_pct"] += data["nrp_pct"]

        # 累加所有营养素
        for key, data in addition.get("all_nutrients", {}).items():
            if key not in total["all_nutrients"]:
                total["all_nutrients"][key] = data.copy()
            else:
                total["all_nutrients"][key]["value"] += data["value"]
                total["all_nutrients"][key]["nrp_pct"] += data["nrp_pct"]

    def _calculate_per_serving(
        self,
        total_nutrition: Dict,
        servings: int
    ) -> Dict:
        """
        计算每份营养
        """
        if servings <= 0:
            servings = 1

        per_serving = {
            "core_nutrients": {},
            "all_nutrients": {},
            "nrp_totals": {}
        }

        # 计算核心营养素每份值
        for name, data in total_nutrition.get("core_nutrients", {}).items():
            per_serving["core_nutrients"][name] = {
                **data,
                "value": round(data["value"] / servings, 2),
                "nrp_pct": round(data["nrp_pct"] / servings, 2)
            }

        # 计算所有营养素每份值
        for key, data in total_nutrition.get("all_nutrients", {}).items():
            per_serving["all_nutrients"][key] = {
                **data,
                "value": round(data["value"] / servings, 2),
                "nrp_pct": round(data["nrp_pct"] / servings, 2)
            }

        # 计算 NRV 每份总和
        for name, data in per_serving["core_nutrients"].items():
            if "nrp_pct" in data:
                per_serving["nrp_totals"][name] = data["nrp_pct"]

        return per_serving


async def calculate_recipe_nutrition(
    recipe_id: int,
    db: Session,
    servings: Optional[int] = None
) -> Optional[Dict]:
    """
    计算菜谱营养的便捷函数
    """
    calculator = NutritionCalculator(db)
    return calculator.calculate_recipe_nutrition(recipe_id, servings)
