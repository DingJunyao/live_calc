from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Tuple, Optional
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
            Ingredient.name == product_name
        ).first()

        if exact_match:
            matches.append((exact_match, 1.0))

        # 模糊匹配
        # 首先尝试直接包含匹配
        partial_matches = self.db.query(Ingredient).filter(
            or_(
                Ingredient.name.like(f'%{product_name}%'),
                Ingredient.name.like(f'%{product_name.lower()}%'),
                Ingredient.name.like(f'%{product_name.upper()}%')
            )
        ).all()

        for ingredient in partial_matches:
            if ingredient not in [match[0] for match in matches]:  # 避免重复
                confidence = self._calculate_match_confidence(product_name, ingredient)
                matches.append((ingredient, confidence))

        # 别名匹配
        alias_matches = self.db.query(Ingredient).filter(
            Ingredient.aliases.isnot(None)
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
        return matches

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
            or_(
                Ingredient.name == base_ingredient,
                Ingredient.name.like(f'%{base_ingredient}%')
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
                specific_ing = self.db.query(Ingredient).filter(Ingredient.name == name).first()
                if specific_ing:
                    return specific_ing

            # 尝试在层级关系中查找
            children = self.db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == base_ing.id
            ).all()

            for child_rel in children:
                child_ing = self.db.query(Ingredient).filter(Ingredient.id == child_rel.child_id).first()
                if grade_requirement.lower() in child_ing.name.lower():
                    return child_ing

        return base_ing

    def suggest_alternatives(self, unavailable_ingredient: Ingredient) -> List[Ingredient]:
        """
        提供可替代的食材选项
        """
        alternatives = []

        # 从层级关系查找替代品
        # 查找父级（更通用的类别）
        parent_relations = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == unavailable_ingredient.id
        ).all()

        for parent_rel in parent_relations:
            parent_ing = self.db.query(Ingredient).filter(Ingredient.id == parent_rel.parent_id).first()
            if parent_ing and parent_ing not in alternatives:
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
                        if sibling_ing and sibling_ing not in alternatives:
                            alternatives.append(sibling_ing)

        # 从营养数据查找功能类似的食材
        if unavailable_ingredient.nutrition_id:
            similar_nutrition = self.db.query(Ingredient).join(
                Ingredient.nutrition_data
            ).filter(
                and_(
                    Ingredient.nutrition_id == unavailable_ingredient.nutrition_id,
                    Ingredient.id != unavailable_ingredient.id
                )
            ).all()

            for similar_ing in similar_nutrition:
                if similar_ing not in alternatives:
                    alternatives.append(similar_ing)

        return alternatives

    def link_product_to_ingredient(self, product_record_id: int, ingredient_id: int,
                                   match_confidence: float = 1.0,
                                   match_method: str = "manual") -> ProductIngredientLink:
        """
        创建产品记录与食材之间的链接
        """
        link = ProductIngredientLink(
            product_record_id=product_record_id,
            ingredient_id=ingredient_id,
            match_confidence=match_confidence,
            match_method=match_method
        )

        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)

        return link