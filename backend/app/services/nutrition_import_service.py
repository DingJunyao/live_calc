"""
从 HowToCook_json 仓库导入营养数据的服务

数据来源: https://github.com/DingJunyao/HowToCook_json/out/nutritions.json

数据结构:
{
  "usda_id": "169291",
  "ingredient_name": "西葫芦",
  "usda_name": "Squash, summer, zucchini, includes skin, raw",
  "nutrients": {
    "energy_kcal": {"value": 70.0, "unit": "kJ", "nrp_pct": 0.84, "standard": "中国GB标准", "note": "..."},
    "protein": {"value": 1.21, "unit": "g", "nrp_pct": 2.02, "standard": "中国GB标准"},
    ...
  }
}
"""

import json
import os
import requests
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData, AIIngredientMatch  # NutritionData 和 AIIngredientMatch 从 nutrition_data 导入
from sqlalchemy.exc import IntegrityError


class NutritionImportService:
    """从 nutritions.json 导入营养数据"""

    # 仓库 URL
    REPO_URL = "https://github.com/DingJunyao/HowToCook_json"
    REPO_RAW_BASE = "https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out"
    NUTRITION_FILE_URL = f"{REPO_RAW_BASE}/nutritions.json"

    # 核心营养素列表（优先显示和计算）
    CORE_NUTRIENTS = [
        "energy_kcal", "protein", "fat", "carbohydrate", "fiber",
        "calcium", "iron", "sodium", "potassium",
        "vitamin_a_rae", "vitamin_c", "vitamin_b1", "vitamin_b2",
        "vitamin_b12", "vitamin_d", "vitamin_e", "vitamin_k"
    ]

    # 营养素显示名称映射
    NUTRIENT_DISPLAY_NAMES = {
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

    def import_all(
        self,
        mode: str = "incremental",
        force_update: bool = False,
        repo_dir: Optional[str] = None
    ) -> Dict[str, any]:
        """
        导入所有营养数据

        Args:
            mode: 导入模式
                - "incremental": 仅导入新食材的营养数据
                - "full": 导入所有食材的营养数据，更新已存在的
                - "force": 强制重新导入所有数据
            force_update: 是否强制更新已有数据
            repo_dir: 本地仓库目录路径（如果提供，从本地文件读取）

        Returns:
            导入结果统计
        """
        print("开始从 nutritions.json 导入营养数据...")

        results = {
            "total": 0,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
            "mode": mode
        }

        try:
            # 1. 读取 nutritions.json（从本地或网络）
            if repo_dir and os.path.exists(repo_dir):
                # 从本地仓库读取
                nutrition_file = os.path.join(repo_dir, "out", "nutritions.json")
                print(f"正在从本地仓库读取营养数据: {nutrition_file}")
                with open(nutrition_file, "r", encoding="utf-8") as f:
                    nutrition_data_list = json.load(f)
            else:
                # 从网络下载
                print(f"正在下载 {self.NUTRITION_FILE_URL}...")
                response = requests.get(self.NUTRITION_FILE_URL, timeout=60)
                response.raise_for_status()
                nutrition_data_list = response.json()

            results["total"] = len(nutrition_data_list)
            print(f"读取完成，共 {len(nutrition_data_list)} 个食材的营养数据")

            # 2. 获取所有现有食材
            existing_ingredients = {
                ing.name: ing
                for ing in self.db.query(Ingredient).all()
            }

            # 3. 遍历并导入营养数据
            for item in nutrition_data_list:
                try:
                    ingredient_name = item.get("ingredient_name", "").strip()

                    if not ingredient_name:
                        results["failed"] += 1
                        continue

                    # 查找食材
                    ingredient = existing_ingredients.get(ingredient_name)

                    if not ingredient:
                        print(f"  跳过未注册的食材: {ingredient_name}")
                        results["skipped"] += 1
                        continue

                    # 检查是否已有营养数据
                    existing_nutrition = self.db.query(NutritionData).filter(
                        NutritionData.ingredient_id == ingredient.id,
                        NutritionData.source == "usda_import"
                    ).first()

                    # 根据模式决定是否导入
                    if mode == "incremental" and existing_nutrition and not force_update:
                        results["skipped"] += 1
                        continue

                    # 准备营养数据
                    nutrients_dict = self._prepare_nutrients_dict(item.get("nutrients", {}))

                    # 创建或更新营养数据
                    if existing_nutrition:
                        if mode in ["full", "force"] or force_update:
                            # 更新已有数据
                            existing_nutrition.nutrients = nutrients_dict
                            existing_nutrition.usda_id = item.get("usda_id")
                            existing_nutrition.usda_name = item.get("usda_name")
                            results["updated"] += 1
                            print(f"  更新营养数据: {ingredient_name}")
                    else:
                        # 创建新数据
                        nutrition = NutritionData(
                            ingredient_id=ingredient.id,
                            source="usda_import",
                            usda_id=item.get("usda_id"),
                            usda_name=item.get("usda_name"),
                            nutrients=nutrients_dict,
                            reference_amount=100.0,  # 默认为每100g
                            reference_unit="g",
                            match_confidence=1.0,  # 直接匹配，置信度100%
                            is_verified=True  # 来自官方数据源
                        )
                        self.db.add(nutrition)
                        results["imported"] += 1
                        print(f"  导入营养数据: {ingredient_name}")

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"导入失败: {item.get('ingredient_name')} - {str(e)}")

            # 4. 创建 AI 匹配记录
            self._create_ai_matches(nutrition_data_list, existing_ingredients)

            # 5. 提交事务
            self.db.commit()

            results["success"] = True
            results["message"] = (
                f"导入完成：新增 {results['imported']}，更新 {results['updated']}，"
                f"跳过 {results['skipped']}，失败 {results['failed']}"
            )

        except Exception as e:
            self.db.rollback()
            results["success"] = False
            results["message"] = f"导入失败: {str(e)}"
            results["errors"].append(str(e))

        return results

    def _prepare_nutrients_dict(self, nutrients: Dict) -> Dict:
        """
        准备营养数据字典

        将原始的 nutritions.json 格式转换为内部格式
        """
        nutrients_dict = {
            "core_nutrients": {},
            "all_nutrients": {},
            "nutrient_details": {}
        }

        for nutrient_name, nutrient_data in nutrients.items():
            nutrient_info = {
                "value": nutrient_data.get("value", 0),
                "unit": nutrient_data.get("unit", ""),
                "nrp_pct": nutrient_data.get("nrp_pct", 0),
                "standard": nutrient_data.get("standard", "无标准"),
                "note": nutrient_data.get("note", "")
            }

            # 添加到所有营养素
            nutrients_dict["all_nutrients"][nutrient_name] = nutrient_info

            # 如果是核心营养素，添加到核心列表
            if nutrient_name in self.CORE_NUTRIENTS:
                display_name = self.NUTRIENT_DISPLAY_NAMES.get(
                    nutrient_name,
                    nutrient_name.replace("_", " ").title()
                )
                nutrients_dict["core_nutrients"][display_name] = {
                    **nutrient_info,
                    "key": nutrient_name
                }

            # 存储详细信息
            nutrients_dict["nutrient_details"][nutrient_name] = nutrient_info

        return nutrients_dict

    def _create_ai_matches(
        self,
        nutrition_data_list: List[Dict],
        existing_ingredients: Dict[str, Ingredient]
    ):
        """
        创建 AI 匹配记录

        为所有成功导入的食材创建匹配记录
        """
        match_count = 0

        for item in nutrition_data_list:
            ingredient_name = item.get("ingredient_name", "").strip()
            ingredient = existing_ingredients.get(ingredient_name)

            if not ingredient:
                continue

            # 检查是否已有匹配记录
            existing_match = self.db.query(AIIngredientMatch).filter(
                AIIngredientMatch.ingredient_id == ingredient.id,
                AIIngredientMatch.source == "usda"
            ).first()

            if existing_match:
                continue

            # 创建新的匹配记录
            ai_match = AIIngredientMatch(
                ingredient_id=ingredient.id,
                source="usda",
                source_name=item.get("usda_name", ""),
                source_id=item.get("usda_id", ""),
                confidence=1.0,
                match_method="exact_name",
                nutrition_data=item.get("nutrients", {}),
                is_verified=True
            )
            self.db.add(ai_match)
            match_count += 1

        print(f"创建了 {match_count} 个 AI 匹配记录")

    def get_nutrient_statistics(self) -> Dict[str, any]:
        """
        获取营养数据统计信息
        """
        # 总食材数
        total_ingredients = self.db.query(Ingredient).count()

        # 有营养数据的食材数
        ingredients_with_nutrition = self.db.query(NutritionData).filter(
            NutritionData.source == "usda_import"
        ).count()

        # 核心营养素覆盖率
        coverage = {}
        for nutrient in self.CORE_NUTRIENTS:
            count = self.db.query(NutritionData).filter(
                NutritionData.source == "usda_import",
                NutritionData.nutrients["core_nutrients"].has_key(nutrient)
            ).count()
            coverage[nutrient] = {
                "count": count,
                "percentage": (count / ingredients_with_nutrition * 100)
                if ingredients_with_nutrition > 0 else 0
            }

        return {
            "total_ingredients": total_ingredients,
            "ingredients_with_nutrition": ingredients_with_nutrition,
            "coverage_percentage": (
                ingredients_with_nutrition / total_ingredients * 100
                if total_ingredients > 0 else 0
            ),
            "nutrient_coverage": coverage
        }

    def get_ingredient_nutrition(
        self,
        ingredient_id: int
    ) -> Optional[Dict]:
        """
        获取指定食材的营养数据
        """
        nutrition = self.db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id,
            NutritionData.source == "usda_import"
        ).first()

        if not nutrition:
            return None

        return {
            "ingredient_id": ingredient_id,
            "source": nutrition.source,
            "usda_id": nutrition.usda_id,
            "usda_name": nutrition.usda_name,
            "nutrients": nutrition.nutrients,
            "reference_amount": nutrition.reference_amount,
            "reference_unit": nutrition.reference_unit
        }


def check_and_import_nutrition(
    db: Session,
    mode: str = "incremental",
    force_update: bool = False,
    repo_dir: Optional[str] = None
) -> Dict[str, any]:
    """
    检查并导入营养数据

    Args:
        db: 数据库会话
        mode: 导入模式
        force_update: 是否强制更新
        repo_dir: 本地仓库目录路径（如果提供，从本地文件读取）

    Returns:
        导入结果
    """
    service = NutritionImportService(db)
    return service.import_all(mode=mode, force_update=force_update, repo_dir=repo_dir)
