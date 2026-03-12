"""
食材合并服务 - 实现数据层面的食材合并操作
将源食材的所有关联记录迁移到目标食材，并在源食材上标记已合并状态
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.nutrition import Ingredient, IngredientNutritionMapping
from app.models.recipe import RecipeIngredient
from app.models.product_ingredient_link import ProductIngredientLink  # 修正导入路径
from app.models.ingredient_merge_record import IngredientMergeRecord  # 从正确的位置导入
from app.models.ingredient_hierarchy import IngredientHierarchy  # 从正确的位置导入
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class IngredientMerger:
    """食材合并服务类，负责将多个食材的数据合并为一个"""

    def __init__(self, db: Session):
        self.db = db

    def merge_ingredients(self, source_ingredient_ids: List[int], target_ingredient_id: int, merged_by_user_id: int) -> Dict[str, Any]:
        """
        将多个源食材合并到目标食材

        Args:
            source_ingredient_ids: 源食材ID列表
            target_ingredient_id: 目标食材ID
            merged_by_user_id: 执行合并的用户ID

        Returns:
            Dict: 合并结果统计
        """
        if not source_ingredient_ids:
            return {"success": False, "message": "源食材列表不能为空"}

        if target_ingredient_id in source_ingredient_ids:
            return {"success": False, "message": "目标食材不能同时是源食材"}

        # 验证所有食材ID都存在
        all_ingredient_ids = source_ingredient_ids + [target_ingredient_id]
        existing_ingredients = self.db.query(Ingredient).filter(
            Ingredient.id.in_(all_ingredient_ids)
        ).all()
        existing_ids = [ing.id for ing in existing_ingredients]

        missing_ids = set(all_ingredient_ids) - set(existing_ids)
        if missing_ids:
            return {"success": False, "message": f"以下食材ID不存在: {list(missing_ids)}"}

        # 检查目标食材是否已经被合并（即它是其他食材合并的目标）
        existing_merge = self.db.query(IngredientMergeRecord).filter(
            IngredientMergeRecord.target_ingredient_id == target_ingredient_id
        ).first()
        if existing_merge:
            return {"success": False, "message": f"目标食材 {target_ingredient_id} 已经是其他食材的合并目标，不能再次作为目标"}

        # 验证所有源食材都没有被其他合并操作使用
        source_merged = self.db.query(IngredientMergeRecord).filter(
            IngredientMergeRecord.source_ingredient_id.in_(source_ingredient_ids)
        ).first()
        if source_merged:
            return {"success": False, "message": f"源食材之一已被其他合并操作使用，无法合并"}

        # 检查目标食材是否已经是其他食材的合并目标（反向检查）
        target_as_source = self.db.query(IngredientMergeRecord).filter(
            and_(
                IngredientMergeRecord.source_ingredient_id == target_ingredient_id,
                IngredientMergeRecord.is_active == True
            )
        ).first()
        if target_as_source:
            return {"success": False, "message": f"目标食材 {target_ingredient_id} 已被标记为合并操作的源，不能作为目标"}

        try:
            # 记录合并前的统计信息
            stats_before = self._get_ingredients_stats(source_ingredient_ids + [target_ingredient_id])

            # 1. 更新菜谱中的食材引用
            updated_recipes_count = self._update_recipe_ingredients(source_ingredient_ids, target_ingredient_id)

            # 2. 更新商品价格记录中的食材引用
            updated_products_count = self._update_product_ingredients(source_ingredient_ids, target_ingredient_id)

            # 3. 更新营养数据映射
            updated_mappings_count = self._update_nutrition_mappings(source_ingredient_ids, target_ingredient_id)

            # 4. 更新层级关系中的食材引用
            updated_hierarchies_count = self._update_ingredient_hierarchies(source_ingredient_ids, target_ingredient_id)

            # 5. 处理营养数据合并
            merged_nutrition_count = self._merge_nutrition_data(source_ingredient_ids, target_ingredient_id)

            # 6. 标记源食材为已合并状态
            for source_id in source_ingredient_ids:
                source_ing = self.db.query(Ingredient).filter(Ingredient.id == source_id).first()
                if source_ing:
                    # 添加到别名列表，保留原名以便历史记录查询
                    if source_ing.name != source_ing.name.lower():
                        if source_ing.aliases:
                            if source_ing.name.lower() not in source_ing.aliases:
                                source_ing.aliases.append(source_ing.name.lower())
                        else:
                            source_ing.aliases = [source_ing.name.lower()]

                    # 标记为已合并
                    source_ing.is_merged = True
                    source_ing.merged_into_id = target_ingredient_id

            # 7. 记录合并历史
            self._record_merge_history(source_ingredient_ids, target_ingredient_id, merged_by_user_id)

            # 提交事务
            self.db.commit()

            # 记录合并后的统计信息
            stats_after = self._get_ingredients_stats([target_ingredient_id])

            # 计算合并结果
            result = {
                "success": True,
                "message": f"成功将 {len(source_ingredient_ids)} 个食材合并到目标食材 {target_ingredient_id}",
                "merged_count": len(source_ingredient_ids),
                "updated_recipes_count": updated_recipes_count,
                "updated_products_count": updated_products_count,
                "updated_mappings_count": updated_mappings_count,
                "updated_hierarchies_count": updated_hierarchies_count,
                "merged_nutrition_count": merged_nutrition_count,
                "stats_change": {
                    "before": stats_before,
                    "after": stats_after
                }
            }

            logger.info(f"成功合并食材: {result}")
            return result

        except Exception as e:
            self.db.rollback()
            logger.error(f"合并食材时发生错误: {str(e)}", exc_info=True)
            return {"success": False, "message": f"合并食材时发生错误: {str(e)}"}

    def _update_recipe_ingredients(self, source_ingredient_ids: List[int], target_ingredient_id: int) -> int:
        """更新菜谱中的食材引用"""
        updated_count = 0

        # 更新RecipeIngredient表中的引用
        recipe_ingredients = self.db.query(RecipeIngredient).filter(
            RecipeIngredient.ingredient_id.in_(source_ingredient_ids)
        ).all()

        for rec_ing in recipe_ingredients:
            # 检查是否已存在相同菜谱和目标食材的记录
            existing = self.db.query(RecipeIngredient).filter(
                and_(
                    RecipeIngredient.recipe_id == rec_ing.recipe_id,
                    RecipeIngredient.ingredient_id == target_ingredient_id
                )
            ).first()

            if existing:
                # 如果已存在相同菜谱和目标食材的记录，需要合并数量
                # 尝试解析现有和新的数量，合并它们
                try:
                    # 假设quantity是数字字符串，需要解析并相加
                    existing_qty = float(existing.quantity) if existing.quantity and existing.quantity.replace('.', '').isdigit() else 0
                    new_qty = float(rec_ing.quantity) if rec_ing.quantity and rec_ing.quantity.replace('.', '').isdigit() else 0
                    combined_qty = existing_qty + new_qty
                    existing.quantity = str(combined_qty)
                except:
                    # 如果无法解析为数字，则保留原始的逻辑（简单覆盖）
                    # 或者将数量组合为文本表示
                    if existing.quantity and rec_ing.quantity:
                        existing.quantity = f"{existing.quantity} + {rec_ing.quantity}"
                    elif rec_ing.quantity:
                        existing.quantity = rec_ing.quantity

                # 删除重复的记录
                self.db.delete(rec_ing)
            else:
                # 直接更新食材引用
                rec_ing.ingredient_id = target_ingredient_id
            updated_count += 1

        return updated_count

    def _update_product_ingredients(self, source_ingredient_ids: List[int], target_ingredient_id: int) -> int:
        """更新商品价格记录中的食材引用"""
        updated_count = 0

        # 更新ProductIngredientLink表中的引用
        product_links = self.db.query(ProductIngredientLink).filter(
            ProductIngredientLink.ingredient_id.in_(source_ingredient_ids)
        ).all()

        for prod_link in product_links:
            # 检查是否已存在相同商品和目标食材的记录
            existing = self.db.query(ProductIngredientLink).filter(
                and_(
                    ProductIngredientLink.product_id == prod_link.product_id,
                    ProductIngredientLink.ingredient_id == target_ingredient_id
                )
            ).first()

            if existing:
                # 如果已存在相同的商品-食材链接，保留原有链接，删除重复的
                self.db.delete(prod_link)
            else:
                # 直接更新食材引用
                prod_link.ingredient_id = target_ingredient_id
            updated_count += 1

        return updated_count

    def _update_nutrition_mappings(self, source_ingredient_ids: List[int], target_ingredient_id: int) -> int:
        """更新营养数据映射"""
        updated_count = 0

        # 更新IngredientNutritionMapping表中的引用
        mappings = self.db.query(IngredientNutritionMapping).filter(
            IngredientNutritionMapping.ingredient_id.in_(source_ingredient_ids)
        ).all()

        for mapping in mappings:
            # 检查是否已存在相同营养数据和目标食材的映射
            existing = self.db.query(IngredientNutritionMapping).filter(
                and_(
                    IngredientNutritionMapping.nutrition_id == mapping.nutrition_id,
                    IngredientNutritionMapping.ingredient_id == target_ingredient_id
                )
            ).first()

            if existing:
                # 如果已存在相同的营养数据映射，比较优先级和置信度，保留更高者
                if mapping.priority > existing.priority or \
                   (mapping.priority == existing.priority and mapping.confidence > existing.confidence):
                    # 更新现有映射的优先级和置信度
                    existing.priority = mapping.priority
                    existing.confidence = mapping.confidence
                # 删除重复的映射
                self.db.delete(mapping)
            else:
                # 直接更新食材引用
                mapping.ingredient_id = target_ingredient_id
            updated_count += 1

        return updated_count

    def _update_ingredient_hierarchies(self, source_ingredient_ids: List[int], target_ingredient_id: int) -> int:
        """更新层级关系中的食材引用"""
        updated_count = 0

        # 1. 更新作为父节点的层级关系
        parent_relations = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id.in_(source_ingredient_ids)
        ).all()

        for rel in parent_relations:
            # 检查是否已存在相同子节点和目标父节点的关系
            existing = self.db.query(IngredientHierarchy).filter(
                and_(
                    IngredientHierarchy.parent_id == target_ingredient_id,
                    IngredientHierarchy.child_id == rel.child_id
                )
            ).first()

            if not existing:
                # 更新父节点引用
                rel.parent_id = target_ingredient_id
                updated_count += 1
            else:
                # 已存在相同关系，删除重复的
                self.db.delete(rel)

        # 2. 更新作为子节点的层级关系
        child_relations = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id.in_(source_ingredient_ids)
        ).all()

        for rel in child_relations:
            # 检查是否已存在相同父节点和目标子节点的关系
            existing = self.db.query(IngredientHierarchy).filter(
                and_(
                    IngredientHierarchy.parent_id == rel.parent_id,
                    IngredientHierarchy.child_id == target_ingredient_id
                )
            ).first()

            if not existing:
                # 更新子节点引用
                rel.child_id = target_ingredient_id
                updated_count += 1
            else:
                # 已存在相同关系，删除重复的
                self.db.delete(rel)

        return updated_count

    def _merge_nutrition_data(self, source_ingredient_ids: List[int], target_ingredient_id: int) -> int:
        """合并营养数据"""
        merged_count = 0

        # 这里可以添加更复杂的营养数据合并逻辑
        # 比如平均化营养值、保留最高置信度的数值等
        # 目前简单地保留目标食材的营养数据

        return merged_count

    def _record_merge_history(self, source_ingredient_ids: List[int], target_ingredient_id: int, merged_by_user_id: int):
        """记录合并历史"""
        for source_id in source_ingredient_ids:
            merge_record = IngredientMergeRecord(
                source_ingredient_id=source_id,
                target_ingredient_id=target_ingredient_id,
                merged_by_user_id=merged_by_user_id
            )
            self.db.add(merge_record)

    def _get_ingredients_stats(self, ingredient_ids: List[int]) -> Dict[str, Any]:
        """获取食材统计信息"""
        ingredients = self.db.query(Ingredient).filter(
            Ingredient.id.in_(ingredient_ids)
        ).all()

        stats = {
            "total_ingredients": len(ingredients),
            "total_recipes": 0,
            "total_products": 0,
            "total_nutrition_mappings": 0
        }

        for ing in ingredients:
            stats["total_recipes"] += len(ing.recipe_ingredients)
            stats["total_products"] += len(ing.products) + len(ing.product_links)
            stats["total_nutrition_mappings"] += len(ing.nutrition_mappings)

        return stats