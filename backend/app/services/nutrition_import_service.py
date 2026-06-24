"""
从 HowToCook_json 仓库导入营养数据的服务

新版数据结构（corr 分支）:
  nutritions.json 为列表格式:
  [
    {
      "usda_id": "2685568",
      "ingredient_name": "西葫芦",
      "usda_name": "Squash, summer, green, zucchini, includes skin, raw",
      "nutrients": [
        {"name": "蛋白质", "name_en": "Protein", "value": 0.984, "unit": "g", "nrp_pct": 1.64, "standard": "中国GB标准"},
        ...
      ]
    },
    ...
  ]
"""

import json
import os
import requests
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData, AIIngredientMatch
from sqlalchemy.exc import IntegrityError


def _get_repo_config():
    """从环境变量读取数据仓库配置"""
    return {
        "url": os.getenv("DATA_REPO_URL", "https://github.com/DingJunyao/HowToCook_json.git"),
        "branch": os.getenv("DATA_REPO_BRANCH", "corr"),
        "data_dir": os.getenv("DATA_REPO_DIR", "out"),
    }


class NutritionImportService:
    """从 nutritions.json 导入营养数据"""

    # 核心营养素英文名（用于匹配 name_en 字段）
    CORE_NUTRIENTS_EN = {
        # 能量
        "Energy (Atwater General Factors)",
        "Energy (Atwater Specific Factors)",
        "Energy",
        # 宏量营养素
        "Protein",
        "Total lipid (fat)",
        "Carbohydrate, by difference",
        "Fiber, total dietary",
        # 矿物质
        "Calcium, Ca",
        "Iron, Fe",
        "Sodium, Na",
        "Potassium, K",
        # 维生素
        "Vitamin A, RAE",
        "Vitamin C, total ascorbic acid",
        "Thiamin",
        "Riboflavin",
        "Vitamin B-12",
        "Vitamin D (D2 + D3)",
        "Vitamin E (alpha-tocopherol)",
        "Vitamin K (phylloquinone)",
        # 其他
        "Fatty acids, total saturated",
        "Cholesterol",
        "Folate, total",
    }

    # 中文名 -> 显示名（用于核心营养素展示）
    CORE_DISPLAY_MAP = {
        # 能量（新版有多种中文名）
        "热量（Atwater 通用系数）": "能量",
        "热量（Atwater 特定系数）": "能量",
        "热量": "能量",
        "能量": "能量",
        # 宏量营养素
        "蛋白质": "蛋白质",
        "脂肪": "脂肪",
        "碳水化合物": "碳水化合物",
        "膳食纤维": "膳食纤维",
        # 矿物质
        "钙": "钙",
        "铁": "铁",
        "钠": "钠",
        "钾": "钾",
        # 维生素
        "维生素A": "维生素A",
        "维生素A (RAE)": "维生素A",
        "维生素C": "维生素C",
        "维生素B1": "维生素B1",
        "维生素B1（硫胺素）": "维生素B1",
        "维生素B2": "维生素B2",
        "维生素B2（核黄素）": "维生素B2",
        "维生素B12": "维生素B12",
        "维生素D": "维生素D",
        "维生素E": "维生素E",
        "维生素K": "维生素K",
        # 其他
        "饱和脂肪酸": "饱和脂肪酸",
        "胆固醇": "胆固醇",
        "叶酸": "叶酸",
    }

    # 中文名到 key 的映射（用于生成一致的英文 key）
    CN_TO_KEY = {
        # 能量（统一为 energy，涵盖 USDA 的"能量/Energy"主字段及 Atwater 通用/特定系数）
        "热量（Atwater 通用系数）": "energy",
        "热量（Atwater 特定系数）": "energy",
        "热量": "energy",
        "能量": "energy",
        # 宏量营养素
        "蛋白质": "protein",
        "脂肪": "fat",
        "碳水化合物": "carbohydrate",
        "膳食纤维": "fiber",
        # 矿物质
        "钙": "calcium",
        "铁": "iron",
        "钠": "sodium",
        "钾": "potassium",
        "镁": "magnesium",
        "磷": "phosphorus",
        "锌": "zinc",
        "铜": "copper",
        "锰": "manganese",
        "硒": "selenium",
        "氟": "fluoride_f",
        # 维生素
        "维生素A": "vitamin_a_rae",
        "维生素A (RAE)": "vitamin_a_rae",
        "维生素A (IU)": "vitamin_a_iu",
        "维生素C": "vitamin_c",
        "维生素B1": "vitamin_b1",
        "维生素B1（硫胺素）": "vitamin_b1",
        "维生素B2": "vitamin_b2",
        "维生素B2（核黄素）": "vitamin_b2",
        "维生素B3（烟酸）": "niacin",
        "维生素B5（泛酸）": "pantothenic_acid",
        "维生素B6": "vitamin_b6",
        "维生素B12": "vitamin_b12",
        "维生素B12（添加）": "vitamin_b_12_added",
        "维生素D": "vitamin_d",
        "维生素D (IU)": "vitamin_d_(d2_+_d3)_international_units",
        "维生素D3": "vitamin_d3",
        "维生素D2（麦角钙化醇）": "vitamin_d2",
        "维生素E": "vitamin_e",
        "维生素E（添加）": "vitamin_e_added",
        "维生素K": "vitamin_k",
        "维生素K（二氢叶绿醌）": "vitamin_k_(dihydrophylloquinone)",
        "生物素": "biotin",
        # 其他
        "饱和脂肪酸": "saturated_fat",
        "单不饱和脂肪酸": "monounsaturated_fat",
        "多不饱和脂肪酸": "polyunsaturated_fat",
        "反式脂肪酸": "fatty_acids_total_trans",
        "反式单烯脂肪酸": "fatty_acids_total_trans_monoenoic",
        "反式多烯脂肪酸": "fatty_acids_total_trans_polyenoic",
        "胆固醇": "cholesterol",
        "叶酸": "folate",
        "叶酸（合成）": "folic_acid",
        "食物叶酸": "folate_food",
        "叶酸 (DFE)": "folate_dfe",
        "胆碱": "choline_total",
        "甜菜碱": "betaine",
        "水分": "water",
        "灰分": "ash",
        "酒精": "alcohol_ethyl",
        "咖啡因": "caffeine",
        "可可碱": "theobromine",
        "总糖": "total_sugars",
        "蔗糖": "sucrose",
        "葡萄糖": "glucose",
        "果糖": "fructose",
        "乳糖": "lactose",
        "麦芽糖": "maltose",
        "半乳糖": "galactose",
        "淀粉": "starch",
        "视黄醇": "retinol",
        "β-胡萝卜素": "carotene_beta",
        "α-胡萝卜素": "carotene_alpha",
        "β-隐黄素": "cryptoxanthin_beta",
        "番茄红素": "lycopene",
        "叶黄素+玉米黄质": "lutein_plus_zeaxanthin",
        "植物甾醇": "phytosterols",
        "氮": "nitrogen",
    }

    # 英文名到 key 的映射（作为 CN_TO_KEY 的补充）
    EN_NAME_TO_KEY = {
        "Energy (Atwater General Factors)": "energy",
        "Energy (Atwater Specific Factors)": "energy",
        "Protein": "protein",
        "Total lipid (fat)": "fat",
        "Carbohydrate, by difference": "carbohydrate",
        "Fiber, total dietary": "fiber",
        "Calcium, Ca": "calcium",
        "Iron, Fe": "iron",
        "Sodium, Na": "sodium",
        "Potassium, K": "potassium",
        "Magnesium, Mg": "magnesium",
        "Phosphorus, P": "phosphorus",
        "Zinc, Zn": "zinc",
        "Copper, Cu": "copper",
        "Manganese, Mn": "manganese",
        "Selenium, Se": "selenium",
        "Fluoride, F": "fluoride_f",
        "Vitamin A, RAE": "vitamin_a_rae",
        "Vitamin A, IU": "vitamin_a_iu",
        "Vitamin C, total ascorbic acid": "vitamin_c",
        "Thiamin": "vitamin_b1",
        "Riboflavin": "vitamin_b2",
        "Niacin": "niacin",
        "Pantothenic acid": "pantothenic_acid",
        "Vitamin B-6": "vitamin_b6",
        "Vitamin B-12": "vitamin_b12",
        "Vitamin B-12, added": "vitamin_b_12_added",
        "Vitamin D (D2 + D3)": "vitamin_d",
        "Vitamin D (D2 + D3), International Units": "vitamin_d_(d2_+_d3)_international_units",
        "Vitamin D3 (cholecalciferol)": "vitamin_d3",
        "Vitamin D2 (ergocalciferol)": "vitamin_d2",
        "Vitamin E (alpha-tocopherol)": "vitamin_e",
        "Vitamin E, added": "vitamin_e_added",
        "Vitamin K (phylloquinone)": "vitamin_k",
        "Vitamin K (Dihydrophylloquinone)": "vitamin_k_(dihydrophylloquinone)",
        "Vitamin K (Menaquinone-4)": "vitamin_k_(menaquinone_4)",
        "Fatty acids, total saturated": "saturated_fat",
        "Fatty acids, total monounsaturated": "monounsaturated_fat",
        "Fatty acids, total polyunsaturated": "polyunsaturated_fat",
        "Fatty acids, total trans": "fatty_acids_total_trans",
        "Fatty acids, total trans-monoenoic": "fatty_acids_total_trans_monoenoic",
        "Fatty acids, total trans-polyenoic": "fatty_acids_total_trans_polyenoic",
        "Cholesterol": "cholesterol",
        "Folate, total": "folate",
        "Folate, food": "folate_food",
        "Folate, DFE": "folate_dfe",
        "Folic acid": "folic_acid",
        "Choline, total": "choline_total",
        "Betaine": "betaine",
        "Alcohol, ethyl": "alcohol_ethyl",
        "Caffeine": "caffeine",
        "Theobromine": "theobromine",
        "Water": "water",
        "Ash": "ash",
        "Retinol": "retinol",
        "Carotene, beta": "carotene_beta",
        "Carotene, alpha": "carotene_alpha",
        "Cryptoxanthin, beta": "cryptoxanthin_beta",
        "Lycopene": "lycopene",
        "Lutein + zeaxanthin": "lutein_plus_zeaxanthin",
        "Phytosterols": "phytosterols",
        "Total Sugars": "total_sugars",
        "Sugars, Total": "total_sugars",
        "Nitrogen": "nitrogen",
    }

    # 单位规范化映射（HowToCook_json 中使用中文单位名）
    UNIT_NORMALIZE = {
        "毫克": "mg",
        "毫g": "mg",
        "微克": "μg",
        "ug": "μg",
        "mcg": "μg",
        "千卡": "kcal",
        "大卡": "kcal",
        "卡路里": "kcal",
        "千焦": "kJ",
        "千焦耳": "kJ",
        "克": "g",
        "千克": "kg",
    }

    def __init__(self, db: Session):
        self.db = db
        self._repo_config = _get_repo_config()

    @property
    def NUTRITION_FILE_URL(self):
        """根据配置动态生成远程文件 URL"""
        repo_url = self._repo_config["url"].rstrip("/").removesuffix(".git")
        branch = self._repo_config["branch"]
        data_dir = self._repo_config["data_dir"]
        return f"https://raw.githubusercontent.com/{repo_url.split('github.com/')[-1]}/{branch}/{data_dir}/nutritions.json"

    def import_all(
        self,
        mode: str = "incremental",
        force_update: bool = False,
        repo_dir: Optional[str] = None
    ) -> Dict[str, any]:
        """
        导入所有营养数据

        Args:
            mode: 导入模式 (incremental / full / force)
            force_update: 是否强制更新已有数据
            repo_dir: 本地仓库目录路径

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
            # 1. 读取 nutritions.json
            nutrition_data_list = self._load_nutrition_data(repo_dir)
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

                    ingredient = existing_ingredients.get(ingredient_name)
                    if not ingredient:
                        results["skipped"] += 1
                        continue

                    existing_nutrition = self.db.query(NutritionData).filter(
                        NutritionData.ingredient_id == ingredient.id,
                        NutritionData.source == "usda_import"
                    ).first()

                    if mode == "incremental" and existing_nutrition and not force_update:
                        results["skipped"] += 1
                        continue

                    # 准备营养数据（新版 list 格式）
                    nutrients_dict = self._prepare_nutrients_dict(item.get("nutrients", []))

                    if existing_nutrition:
                        if mode in ["full", "force"] or force_update:
                            existing_nutrition.nutrients = nutrients_dict
                            existing_nutrition.usda_id = item.get("usda_id")
                            existing_nutrition.usda_name = item.get("usda_name")
                            results["updated"] += 1
                            print(f"  更新营养数据: {ingredient_name}")
                    else:
                        nutrition = NutritionData(
                            ingredient_id=ingredient.id,
                            source="usda_import",
                            usda_id=item.get("usda_id"),
                            usda_name=item.get("usda_name"),
                            nutrients=nutrients_dict,
                            reference_amount=100.0,
                            reference_unit="g",
                            match_confidence=1.0,
                            is_verified=True
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

    def _load_nutrition_data(self, repo_dir: Optional[str] = None) -> List[Dict]:
        """从本地仓库或远程加载营养数据"""
        data_dir = self._repo_config["data_dir"]

        if repo_dir and os.path.exists(repo_dir):
            nutrition_file = os.path.join(repo_dir, data_dir, "nutritions.json")
            print(f"正在从本地仓库读取营养数据: {nutrition_file}")
            with open(nutrition_file, "r", encoding="utf-8") as f:
                return json.load(f)

        print(f"正在下载 {self.NUTRITION_FILE_URL}...")
        from app.config import get_settings
        response = requests.get(self.NUTRITION_FILE_URL, timeout=get_settings().import_http_timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_unit(unit: str) -> str:
        """规范化单位：中文单位名 -> 标准英文缩写"""
        if not unit:
            return unit
        unit_key = unit.strip()
        if unit_key in NutritionImportService.UNIT_NORMALIZE:
            return NutritionImportService.UNIT_NORMALIZE[unit_key]
        return unit

    def _prepare_nutrients_dict(self, nutrients: List[Dict]) -> Dict:
        """
        准备营养数据字典

        新版 nutrients 格式为列表:
        [
            {"name": "蛋白质", "name_en": "Protein", "value": 0.984, "unit": "g", "nrp_pct": 1.64, "standard": "中国GB标准"},
            ...
        ]
        """
        nutrients_dict = {
            "core_nutrients": {},
            "all_nutrients": {},
            "nutrient_details": {}
        }

        has_energy_kcal = False  # 记录 all_nutrients 中是否已有 kcal 版能量

        for nutrient_item in nutrients:
            cn_name = nutrient_item.get("name", "")
            en_name = nutrient_item.get("name_en", "")

            # 规范化单位
            raw_unit = nutrient_item.get("unit", "")
            normalized_unit = self._normalize_unit(raw_unit)

            nutrient_info = {
                "value": nutrient_item.get("value", 0),
                "unit": normalized_unit,
                "nrp_pct": nutrient_item.get("nrp_pct", 0),
                "standard": nutrient_item.get("standard", "无标准"),
                "note": nutrient_item.get("note", ""),
                "name_en": en_name,
            }

            # 用英文名作为 key 存储（与旧版格式对齐，便于前端查询）
            key = self._get_nutrient_key(cn_name, en_name)

            # Energy kJ/kcal 去重：同一个食材可能同时有千卡和千焦两个 Energy 条目，
            # 都生成 key="energy"，后面的覆盖前面的。优先保留千卡版。
            if key == "energy" and normalized_unit == "kJ":
                if has_energy_kcal:
                    continue  # 已有千卡版，跳过千焦版
                # 如果还没有千卡版，暂时记录位置但继续处理，
                # 等后面遇到千卡版时再覆盖
            elif key == "energy" and normalized_unit == "kcal":
                has_energy_kcal = True

            nutrients_dict["all_nutrients"][key] = nutrient_info
            nutrients_dict["nutrient_details"][key] = nutrient_info

            # 判断是否为核心营养素
            if self._is_core_nutrient(cn_name, en_name):
                display_name = self.CORE_DISPLAY_MAP.get(cn_name, cn_name)
                # 避免重复能量项（优先用 Atwater 通用系数）
                if display_name == "能量" and display_name in nutrients_dict["core_nutrients"]:
                    if "通用" not in cn_name:
                        continue
                nutrients_dict["core_nutrients"][display_name] = {
                    **nutrient_info,
                    "key": key
                }

        return nutrients_dict

    def _get_nutrient_key(self, cn_name: str, en_name: str) -> str:
        """
        获取营养素的 key

        优先级：
        1. 中文名 -> key 映射（CN_TO_KEY）
        2. 英文名 -> key 映射（EN_NAME_TO_KEY，覆盖 USDA 原始 name_en）
        3. 用英文名自动生成 key
        """
        if cn_name in self.CN_TO_KEY:
            return self.CN_TO_KEY[cn_name]
        if en_name in self.EN_NAME_TO_KEY:
            return self.EN_NAME_TO_KEY[en_name]
        # 用英文名生成 key：小写、替换空格和特殊字符为下划线
        key = en_name.lower()
        key = key.replace(", ", "_").replace(" ", "_").replace("(", "").replace(")", "")
        key = key.replace("+", "_plus_").replace("-", "_")
        # 去掉连续下划线
        while "__" in key:
            key = key.replace("__", "_")
        return key.strip("_")

    def _is_core_nutrient(self, cn_name: str, en_name: str) -> bool:
        """判断是否为核心营养素"""
        if cn_name in self.CORE_DISPLAY_MAP:
            return True
        if en_name in self.CORE_NUTRIENTS_EN:
            return True
        return False

    def _create_ai_matches(
        self,
        nutrition_data_list: List[Dict],
        existing_ingredients: Dict[str, Ingredient]
    ):
        """创建 AI 匹配记录"""
        match_count = 0

        for item in nutrition_data_list:
            ingredient_name = item.get("ingredient_name", "").strip()
            ingredient = existing_ingredients.get(ingredient_name)
            if not ingredient:
                continue

            existing_match = self.db.query(AIIngredientMatch).filter(
                AIIngredientMatch.ingredient_id == ingredient.id,
                AIIngredientMatch.source == "usda"
            ).first()

            if existing_match:
                continue

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
        """获取营养数据统计信息"""
        total_ingredients = self.db.query(Ingredient).count()
        ingredients_with_nutrition = self.db.query(NutritionData).filter(
            NutritionData.source == "usda_import"
        ).count()

        return {
            "total_ingredients": total_ingredients,
            "ingredients_with_nutrition": ingredients_with_nutrition,
            "coverage_percentage": (
                ingredients_with_nutrition / total_ingredients * 100
                if total_ingredients > 0 else 0
            ),
        }

    def get_ingredient_nutrition(self, ingredient_id: int) -> Optional[Dict]:
        """获取指定食材的营养数据"""
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
    """检查并导入营养数据"""
    service = NutritionImportService(db)
    return service.import_all(mode=mode, force_update=force_update, repo_dir=repo_dir)
