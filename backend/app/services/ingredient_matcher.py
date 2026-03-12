from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Tuple, Optional, Dict, Any
from app.models.nutrition import Ingredient
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.product_ingredient_link import ProductIngredientLink
import re


class IngredientMatcher:
    """智能食材匹配器"""

    def __init__(self, db: Session):
        self.db = db

    def match_product_to_ingredient(self, product_name: str) -> List[Tuple[Ingredient, float]]:
        """
        将产品名称匹配到可能的食材及其置信度
        例如："金龙鱼高筋小麦粉" -> [(高筋面粉, 0.95), (小麦粉, 0.85), (面粉, 0.75)]
        """
        matches = []

        # 精确匹配
        exact_match = self.db.query(Ingredient).filter(
            and_(
                Ingredient.name == product_name,
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).first()

        if exact_match:
            matches.append((exact_match, 1.0))

        # 模糊匹配
        # 首先尝试直接包含匹配
        partial_matches = self.db.query(Ingredient).filter(
            and_(
                or_(
                    Ingredient.name.like(f'%{product_name}%'),
                    Ingredient.name.like(f'%{product_name.lower()}%'),
                    Ingredient.name.like(f'%{product_name.upper()}%')
                ),
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).all()

        for ingredient in partial_matches:
            if ingredient not in [match[0] for match in matches]:  # 避免重复
                confidence = self._calculate_match_confidence(product_name, ingredient)
                matches.append((ingredient, confidence))

        # 别名匹配
        alias_matches = self.db.query(Ingredient).filter(
            and_(
                Ingredient.aliases.isnot(None),
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).all()

        for ingredient in alias_matches:
            if ingredient.aliases:
                for alias in ingredient.aliases:
                    if product_name.lower() in alias.lower() or alias.lower() in product_name.lower():
                        if ingredient not in [match[0] for match in matches]:
                            confidence = self._calculate_match_confidence(product_name, ingredient, True)
                            matches.append((ingredient, confidence))

        # 按置信度排序
        matches.sort(key=lambda x: x[1], reverse=True)

        # 处理合并的食材：如果匹配到一个已被合并的食材，将其替换为其目标食材
        processed_matches = []
        for ingredient, confidence in matches:
            if ingredient.is_merged and ingredient.merged_into_id:
                # 如果当前食材已被合并，获取其合并到的目标食材
                target_ingredient = self._get_active_ingredient(ingredient.merged_into_id)
                if target_ingredient:
                    # 检查目标食材是否已经在匹配列表中，避免重复
                    if target_ingredient not in [match[0] for match in processed_matches]:
                        processed_matches.append((target_ingredient, confidence))
            else:
                processed_matches.append((ingredient, confidence))

        return processed_matches

    def _get_active_ingredient(self, ingredient_id: int) -> Optional[Ingredient]:
        """获取活跃的食材（如果不是已合并的食材）"""
        ingredient = self.db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient:
            # 如果目标食材本身也是被合并的，则递归查找最终目标
            if ingredient.is_merged and ingredient.merged_into_id:
                return self._get_active_ingredient(ingredient.merged_into_id)
            return ingredient
        return None

    def _calculate_match_confidence(self, product_name: str, ingredient: Ingredient, is_variant: bool = False) -> float:
        """计算匹配置信度"""
        confidence = 0.0

        # 基本匹配分数
        if product_name.lower() == ingredient.name.lower():
            confidence = 1.0
        elif ingredient.name.lower() in product_name.lower() or product_name.lower() in ingredient.name.lower():
            # 完整包含匹配
            confidence = 0.9
        elif product_name.lower() in ingredient.name.lower().replace(' ', '') or \
             ingredient.name.lower().replace(' ', '') in product_name.lower():
            # 忽略空格的匹配
            confidence = 0.8
        else:
            # 更复杂的部分匹配
            product_words = set(product_name.lower().split())
            ingredient_words = set(ingredient.name.lower().split())

            common_words = product_words.intersection(ingredient_words)
            if common_words:
                confidence = min(0.7, len(common_words) / len(ingredient_words))

        # 如果是变体匹配，降低一点分数
        if is_variant:
            confidence *= 0.9

        return confidence

    def resolve_ingredient_hierarchy(self, base_ingredient: str, grade_requirement: str = None) -> Optional[Ingredient]:
        """
        解析食材层级关系
        例如：基础食材="面粉"，等级要求="高筋" -> 返回"高筋面粉"
        """
        # 首先查找基础食材
        base_ing = self.db.query(Ingredient).filter(
            and_(
                or_(
                    Ingredient.name == base_ingredient,
                    Ingredient.name.like(f'%{base_ingredient}%')
                ),
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).first()

        if not base_ing:
            return None

        # 如果有等级要求，尝试查找更具体的食材
        if grade_requirement:
            # 构造具体的食材名称
            specific_names = [
                f"{grade_requirement}{base_ingredient}",
                f"{base_ingredient}{grade_requirement}",
                f"{grade_requirement} {base_ingredient}",
                f"{base_ingredient} {grade_requirement}"
            ]

            for name in specific_names:
                specific_ing = self.db.query(Ingredient).filter(
                    and_(
                        Ingredient.name == name,
                        Ingredient.is_merged == False  # 只考虑未被合并的食材
                    )
                ).first()
                if specific_ing:
                    # 检查是否已被合并
                    if specific_ing.is_merged and specific_ing.merged_into_id:
                        return self._get_active_ingredient(specific_ing.merged_into_id)
                    return specific_ing

            # 尝试在层级关系中查找
            children = self.db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == base_ing.id
            ).all()

            for child_rel in children:
                child_ing = self.db.query(Ingredient).filter(Ingredient.id == child_rel.child_id).first()
                if child_ing and grade_requirement.lower() in child_ing.name.lower():
                    # 检查是否已被合并
                    if child_ing.is_merged and child_ing.merged_into_id:
                        return self._get_active_ingredient(child_ing.merged_into_id)
                    return child_ing

        # 检查基础食材是否已被合并
        if base_ing.is_merged and base_ing.merged_into_id:
            return self._get_active_ingredient(base_ing.merged_into_id)

        return base_ing

    def suggest_alternatives(self, unavailable_ingredient: Ingredient) -> List[Ingredient]:
        """
        提供可替代的食材选项
        """
        alternatives = []

        # 检查输入的食材是否已被合并，如果是，使用合并后的目标食材
        if unavailable_ingredient.is_merged and unavailable_ingredient.merged_into_id:
            unavailable_ingredient = self._get_active_ingredient(unavailable_ingredient.merged_into_id)
            if not unavailable_ingredient:
                return []

        # 从层级关系查找替代品
        # 查找父级（更通用的类别）
        parent_relations = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == unavailable_ingredient.id
        ).all()

        for parent_rel in parent_relations:
            parent_ing = self.db.query(Ingredient).filter(Ingredient.id == parent_rel.parent_id).first()
            if parent_ing and parent_ing not in alternatives:
                # 检查父级食材是否已被合并
                if parent_ing.is_merged and parent_ing.merged_into_id:
                    active_parent = self._get_active_ingredient(parent_ing.merged_into_id)
                    if active_parent and active_parent not in alternatives:
                        alternatives.append(active_parent)
                elif parent_ing not in alternatives:
                    alternatives.append(parent_ing)

        # 查找同级别的其他子项（类似的产品）
        if parent_relations:
            for parent_rel in parent_relations:
                sibling_rels = self.db.query(IngredientHierarchy).filter(
                    IngredientHierarchy.parent_id == parent_rel.parent_id
                ).all()

                for sibling_rel in sibling_rels:
                    if sibling_rel.child_id != unavailable_ingredient.id:
                        sibling_ing = self.db.query(Ingredient).filter(Ingredient.id == sibling_rel.child_id).first()
                        if sibling_ing:
                            # 检查兄弟食材是否已被合并
                            if sibling_ing.is_merged and sibling_ing.merged_into_id:
                                active_sibling = self._get_active_ingredient(sibling_ing.merged_into_id)
                                if active_sibling and active_sibling not in alternatives:
                                    alternatives.append(active_sibling)
                            elif sibling_ing not in alternatives:
                                alternatives.append(sibling_ing)

        # 从营养数据查找功能类似的食材
        if unavailable_ingredient.nutrition_id:
            similar_nutrition = self.db.query(Ingredient).join(
                Ingredient.nutrition_data
            ).filter(
                and_(
                    Ingredient.nutrition_id == unavailable_ingredient.nutrition_id,
                    Ingredient.id != unavailable_ingredient.id,
                    Ingredient.is_merged == False  # 只考虑未被合并的食材
                )
            ).all()

            for similar_ing in similar_nutrition:
                # 检查相似食材是否已被合并
                if similar_ing.is_merged and similar_ing.merged_into_id:
                    active_similar = self._get_active_ingredient(similar_ing.merged_into_id)
                    if active_similar and active_similar not in alternatives:
                        alternatives.append(active_similar)
                elif similar_ing not in alternatives:
                    alternatives.append(similar_ing)

        return alternatives

    def link_product_to_ingredient(self, product_id: int, ingredient_id: int) -> ProductIngredientLink:
        """
        创建产品记录与食材之间的链接
        """
        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        ingredient = self.db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            ingredient_id = ingredient.merged_into_id

        link = ProductIngredientLink(
            product_id=product_id,
            ingredient_id=ingredient_id
        )

        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)

        return link

    def find_best_match_with_fallback(self, ingredient_name: str, user_id: int = None) -> Optional[Ingredient]:
        """
        使用回退机制查找最佳匹配的食材

        Args:
            ingredient_name: 输入的食材名称
            user_id: 用户ID，可用于个性化匹配

        Returns:
            匹配到的食材对象，如果没有找到则返回None
        """
        # 步骤1: 精确匹配
        exact_match = self._exact_match(ingredient_name)
        if exact_match:
            return exact_match

        # 步骤2: 同义词匹配
        synonym_match = self._synonym_match(ingredient_name)
        if synonym_match:
            return synonym_match

        # 步骤3: 模糊匹配
        fuzzy_match = self._fuzzy_match(ingredient_name)
        if fuzzy_match:
            return fuzzy_match

        # 步骤4: 层级回退 - 查找更通用的父级食材
        fallback_match = self._hierarchy_fallback_match(ingredient_name)
        if fallback_match:
            return fallback_match

        # 步骤5: 如果都找不到，尝试更宽松的模糊匹配
        loose_fuzzy_match = self._loose_fuzzy_match(ingredient_name)
        if loose_fuzzy_match:
            return loose_fuzzy_match

        return None

    def _exact_match(self, name: str) -> Optional[Ingredient]:
        """精确匹配食材名称"""
        ingredient = self.db.query(Ingredient).filter(
            and_(
                Ingredient.name == name,
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).first()

        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            return self._get_active_ingredient(ingredient.merged_into_id)
        return ingredient

    def _synonym_match(self, name: str) -> Optional[Ingredient]:
        """同义词匹配"""
        # 查找别名中包含该名称的食材
        ingredients = self.db.query(Ingredient).filter(
            and_(
                Ingredient.aliases.isnot(None),
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).all()

        for ingredient in ingredients:
            if ingredient.aliases and name in ingredient.aliases:
                if ingredient.is_merged and ingredient.merged_into_id:
                    return self._get_active_ingredient(ingredient.merged_into_id)
                return ingredient

        return None

    def _fuzzy_match(self, name: str) -> Optional[Ingredient]:
        """模糊匹配（相似度较高的匹配）"""
        # 简单的子串匹配，优先匹配较长的名称
        potential_matches = self.db.query(Ingredient).filter(
            and_(
                Ingredient.name.contains(name),
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).order_by(func.length(Ingredient.name)).all()

        # 也查找别名中包含该子串的食材
        alias_matches = self.db.query(Ingredient).filter(
            and_(
                Ingredient.aliases.op('?')(name),  # JSON字段包含查询
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).all()

        potential_matches.extend(alias_matches)

        # 如果找到了多个匹配项，选择名称最接近的那个
        if potential_matches:
            # 简单按名称长度排序，优先选择较短但包含输入名称的
            match = min(potential_matches, key=lambda x: abs(len(x.name) - len(name)))

            if match.is_merged and match.merged_into_id:
                return self._get_active_ingredient(match.merged_into_id)
            return match

        return None

    def _hierarchy_fallback_match(self, name: str) -> Optional[Ingredient]:
        """层级回退匹配 - 查找更通用的父级食材"""
        # 首先尝试找到输入名称对应的食材
        child_ingredient = self.db.query(Ingredient).filter(
            and_(
                Ingredient.name == name,
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).first()

        if not child_ingredient:
            # 如果找不到，尝试模糊匹配
            child_ingredient = self._fuzzy_match(name)

        if child_ingredient:
            # 查找该食材的父级食材（更通用的类别）
            parent_relation = self.db.query(IngredientHierarchy).filter(
                and_(
                    IngredientHierarchy.child_id == child_ingredient.id,
                    IngredientHierarchy.relation_type == "fallback"  # 使用fallback关系
                )
            ).first()

            if parent_relation:
                parent_ingredient = self.db.query(Ingredient).filter(
                    Ingredient.id == parent_relation.parent_id
                ).first()

                if parent_ingredient and not parent_ingredient.is_merged:
                    return parent_ingredient
                elif parent_ingredient and parent_ingredient.is_merged and parent_ingredient.merged_into_id:
                    # 如果父级食材已被合并，返回其合并后的目标
                    return self._get_active_ingredient(parent_ingredient.merged_into_id)

        return None

    def _loose_fuzzy_match(self, name: str) -> Optional[Ingredient]:
        """宽松的模糊匹配（较低相似度但仍可能相关）"""
        # 使用正则表达式或其他高级匹配技术
        # 这里使用简单的相似度计算作为示例
        potential_matches = self.db.query(Ingredient).filter(
            and_(
                func.lower(Ingredient.name).contains(func.lower(name)),
                Ingredient.is_merged == False  # 只考虑未被合并的食材
            )
        ).all()

        if potential_matches:
            match = potential_matches[0]  # 返回第一个匹配项
            if match.is_merged and match.merged_into_id:
                return self._get_active_ingredient(match.merged_into_id)
            return match

        return None

    def get_ingredient_with_all_related_names(self, ingredient_id: int) -> Dict[str, Any]:
        """获取食材及其所有相关名称（包括别名、父子关系名称等）"""
        ingredient = self.db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            return {}

        # 如果食材已被合并，返回其目标食材的相关信息
        if ingredient.is_merged and ingredient.merged_into_id:
            ingredient = self._get_active_ingredient(ingredient.merged_into_id)
            if not ingredient:
                return {}

        result = {
            "primary_name": ingredient.name,
            "aliases": ingredient.aliases or [],
            "related_names": set(),
            "hierarchy_info": {
                "parents": [],  # 父级食材（更通用的类别）
                "children": []  # 子级食材（更具体的类别）
            }
        }

        # 获取别名
        if ingredient.aliases:
            result["related_names"].update(ingredient.aliases)

        # 获取层级关系
        # 查找作为子级的关系（获取父级）
        parent_relations = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == ingredient.id
        ).all()

        for rel in parent_relations:
            parent_ing = self.db.query(Ingredient).filter(Ingredient.id == rel.parent_id).first()
            if parent_ing:
                # 检查父级食材是否已被合并
                if parent_ing.is_merged and parent_ing.merged_into_id:
                    parent_ing = self._get_active_ingredient(parent_ing.merged_into_id)

                if parent_ing:
                    result["hierarchy_info"]["parents"].append({
                        "name": parent_ing.name,
                        "relation_type": rel.relation_type,
                        "id": parent_ing.id
                    })
                    result["related_names"].add(parent_ing.name)

        # 查找作为父级的关系（获取子级）
        child_relations = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == ingredient.id
        ).all()

        for rel in child_relations:
            child_ing = self.db.query(Ingredient).filter(Ingredient.id == rel.child_id).first()
            if child_ing:
                # 检查子级食材是否已被合并
                if child_ing.is_merged and child_ing.merged_into_id:
                    child_ing = self._get_active_ingredient(child_ing.merged_into_id)

                if child_ing:
                    result["hierarchy_info"]["children"].append({
                        "name": child_ing.name,
                        "relation_type": rel.relation_type,
                        "id": child_ing.id
                    })
                    result["related_names"].add(child_ing.name)

        result["related_names"] = list(result["related_names"])
        return result