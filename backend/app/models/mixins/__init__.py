"""
营养数据混合类

提供营养数据获取和合并的逻辑，处理：
1. 商品自定义营养值优先
2. 食材层级 fallback 机制
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.ingredient_hierarchy import IngredientHierarchy, HierarchyRelationType
from app.models.nutrition_data import NutritionData


class NutritionMixin:
    """营养数据混合类，处理商品自定义营养值与食材营养值的优先级"""

    # 可信营养数据源（优先级排序）
    _TRUSTED_SOURCES = ['custom', 'usda_import', 'usda_manual_match']

    @staticmethod
    def get_best_nutrition_data(db: Session, ingredient_id: int):
        """
        获取指定食材的最佳可用营养数据

        优先级：custom > usda_import / usda_manual_match > 其他已验证

        Args:
            db: 数据库会话
            ingredient_id: 食材 ID

        Returns:
            NutritionData 或 None
        """
        # 1. 自定义数据（用户编辑，最高优先级）
        nutrition = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id,
            NutritionData.source == 'custom'
        ).first()
        if nutrition:
            return nutrition

        # 2. USDA 数据（usda_import / usda_manual_match）
        nutrition = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id,
            NutritionData.source.in_(['usda_import', 'usda_manual_match'])
        ).order_by(NutritionData.match_confidence.desc()).first()
        if nutrition:
            return nutrition

        # 3. 其他已验证数据（兜底）
        return db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id,
            NutritionData.is_verified == True
        ).first()

    @staticmethod
    def get_nutrient_value(
        db: Session,
        product_custom_data: Optional[dict],
        ingredient,
        nutrient_key: str,
        fallback_chain: Optional[list] = None
    ) -> tuple[Optional[dict], str, str]:
        """
        获取指定营养素的值，考虑商品自定义和食材层级 fallback

        Args:
            db: 数据库会话
            product_custom_data: 商品自定义营养数据
            ingredient: 食材对象
            nutrient_key: 营养素键名（如 "能量", "蛋白质"）
            fallback_chain: 已访问的 fallback 链（用于避免循环）

        Returns:
            (value, source, source_detail)
            - value: 营养素值字典 {value, unit, ...} 或 None
            - source: 来源标识 (product_custom | ingredient | fallback | not_defined)
            - source_detail: 来源详细说明
        """
        # 初始化 fallback_chain
        if fallback_chain is None:
            fallback_chain = []

        # 1. 商品自定义值优先
        if product_custom_data:
            value = product_custom_data.get(nutrient_key)
            if value is not None:
                return value, "product_custom", "商品自定义营养值"

        # 2. 沿食材 fallback 链向上查找
        return NutritionMixin._lookup_fallback_nutrition(
            db, ingredient, nutrient_key, fallback_chain
        )

    @staticmethod
    def _lookup_fallback_nutrition(
        db: Session,
        ingredient,
        nutrient_key: str,
        visited: list
    ) -> tuple[Optional[dict], str, str]:
        """
        沿食材的 fallback 链向上查找营养值

        Args:
            db: 数据库会话
            ingredient: 当前食材对象
            nutrient_key: 营养素键名
            visited: 已访问的食材ID列表（避免循环）

        Returns:
            (value, source, source_detail)
        """
        if not ingredient:
            return None, "not_defined", "食材不存在"

        # 防止循环引用
        if ingredient.id in visited:
            return None, "not_defined", "食材 fallback 链循环引用"

        visited = visited + [ingredient.id]

        # 2.1 检查当前食材的营养数据
        nutrition_data = NutritionMixin.get_best_nutrition_data(db, ingredient.id)

        if nutrition_data and nutrition_data.nutrients:
            nutrition = nutrition_data.nutrients
            if nutrition:
                # 兼容两种格式：core_nutrients 或 all_nutrients
                value = None

                # 尝试从 core_nutrients 获取
                if isinstance(nutrition, dict):
                    core = nutrition.get("core_nutrients", {})
                    if nutrient_key in core:
                        value = core[nutrient_key]
                    else:
                        # 尝试从 all_nutrients 获取
                        all_nut = nutrition.get("all_nutrients", {})
                        # 尝试用中文名匹配
                        value = all_nut.get(nutrient_key)

                if value is not None:
                    return value, "ingredient", f"食材: {ingredient.name}"

        # 2.2 查找 fallback 父级
        parent = NutritionMixin._get_fallback_parent(db, ingredient)
        if parent:
            return NutritionMixin._lookup_fallback_nutrition(
                db, parent, nutrient_key, visited
            )

        # 没有找到
        return None, "not_defined", f"食材 {ingredient.name} 及其祖先均无营养数据"

    @staticmethod
    def _get_fallback_parent(db: Session, ingredient) -> Optional[any]:
        """
        获取食材的 fallback 父级

        通过 IngredientHierarchy 表查询关系类型为 FALLBACK 的父级，
        返回置信度最高的父级

        Args:
            db: 数据库会话
            ingredient: 食材对象

        Returns:
            父级食材对象或 None
        """
        hierarchy = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == ingredient.id,
            IngredientHierarchy.relation_type == HierarchyRelationType.FALLBACK.value
        ).order_by(IngredientHierarchy.strength.desc()).first()

        return hierarchy.parent if hierarchy else None

    @staticmethod
    def merge_nutrition_data(
        db: Session,
        product_custom_data: Optional[dict],
        ingredient,
        nutrition_template: Optional[dict] = None
    ) -> tuple[dict, dict]:
        """
        合并营养数据，返回完整的营养素值和来源信息

        Args:
            db: 数据库会话
            product_custom_data: 商品自定义营养数据
            ingredient: 食材对象
            nutrition_template: 营养素模板（定义需要包含哪些营养素）

        Returns:
            (merged_nutrients, sources)
            - merged_nutrients: 合并后的营养素数据
            - sources: 每个营养素的来源信息
        """
        merged_nutrients = {}
        sources = {}
        ingredient_name = ingredient.name if ingredient else "未知食材"

        if ingredient:
            nutrition_data = NutritionMixin.get_best_nutrition_data(db, ingredient.id)
            if nutrition_data and nutrition_data.nutrients:
                nuts = nutrition_data.nutrients

                # 1. 获取 core_nutrients（中文键名）
                core = nuts.get("core_nutrients", {})
                for k, v in core.items():
                    merged_nutrients[k] = v
                    sources[k] = {"source": "ingredient", "source_detail": f"食材: {ingredient_name}"}

                # 2. 获取 all_nutrients（英文键名）
                # 只添加不在 core_nutrients 中的营养素
                all_nut = nuts.get("all_nutrients", {})
                core_english_keys = {v.get('key') for v in core.values() if isinstance(v, dict) and 'key' in v}
                for k, v in all_nut.items():
                    if isinstance(v, dict) and 'value' in v:
                        # 跳过已在 core 中的英文 key
                        if k not in core_english_keys:
                            merged_nutrients[k] = v
                            sources[k] = {"source": "ingredient", "source_detail": f"食材: {ingredient_name}"}

        # 商品自定义营养素优先覆盖
        if product_custom_data:
            # 兼容嵌套格式 {all_nutrients: {...}, core_nutrients: {...}}
            # 和扁平格式 {energy: {...}, 能量: {...}}
            nested_all = product_custom_data.get("all_nutrients", {})
            nested_core = product_custom_data.get("core_nutrients", {})
            # 合并嵌套的两层（core_nutrients 优先，因为它是显示层查找来源）
            overrides = {**nested_all, **nested_core}
            if overrides:
                for key, value in overrides.items():
                    if value is not None and isinstance(value, dict):
                        # 字段级合并：商品值覆盖原料值（NRV 由上层重算）
                        if key in merged_nutrients and isinstance(merged_nutrients[key], dict):
                            merged = dict(merged_nutrients[key])
                            merged.update(value)
                            merged_nutrients[key] = merged
                        else:
                            merged_nutrients[key] = value
                        sources[key] = {"source": "product_custom", "source_detail": "商品自定义营养值"}
            else:
                # 扁平格式
                for key, value in product_custom_data.items():
                    if key in ("all_nutrients", "core_nutrients", "nutrient_details"):
                        continue
                    if value is not None and isinstance(value, dict):
                        if key in merged_nutrients and isinstance(merged_nutrients[key], dict):
                            merged = dict(merged_nutrients[key])
                            merged.update(value)
                            merged_nutrients[key] = merged
                        else:
                            merged_nutrients[key] = value
                        sources[key] = {"source": "product_custom", "source_detail": "商品自定义营养值"}

        # 如果没有营养素，返回默认值
        if not merged_nutrients:
            merged_nutrients = {
                "能量": {"value": 0, "unit": "kcal"},
                "蛋白质": {"value": 0, "unit": "g"},
                "脂肪": {"value": 0, "unit": "g"},
                "碳水化合物": {"value": 0, "unit": "g"},
            }
            for key in merged_nutrients:
                sources[key] = {"source": "not_defined", "source_detail": "无营养数据"}

        return merged_nutrients, sources