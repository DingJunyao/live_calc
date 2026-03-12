# 食材层级管理系统设计文档

## 1. 问题概述

当前系统中存在的食材管理问题：
- 食材存在不当分立情况（如"米"和"大米"被认为是不同食材）
- 缺乏层级关系管理（如"鸡肉"和"鸡胸肉"之间没有关联）
- 计算菜谱成本和营养值时，因食材匹配不准导致计算错误
- 没有有效的回退机制处理未匹配到的食材

## 2. 解决方案概述

设计一套完整的食材层级管理系统，包含：
- 增强的食材层级关系模型
- 智能的食材匹配算法
- 灵活的回退机制
- 数据层面的食材合并功能
- 前端管理界面

## 3. 数据模型设计

### 3.1 食材层级关系模型增强

```python
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin
from enum import Enum

class RelationshipType(Enum):
    CONTAINS = "contains"  # 包含关系：鸡肉 contains 鸡胸肉
    SUBSTITUTABLE = "substitutable"  # 可替代关系：牛奶 substitutable 豆浆
    FALLBACK = "fallback"   # 回退关系：大米 fallback 米

class IngredientHierarchy(Base, AuditMixin):
    __tablename__ = "ingredient_hierarchy"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("ingredients.id"))  # 父级食材
    child_id = Column(Integer, ForeignKey("ingredients.id"))   # 子级食材
    relationship_type = Column(String(20), default="contains")  # 关系类型
    relationship_strength = Column(Numeric(3, 2), default=1.00)  # 关系强度 0-1
    is_bidirectional = Column(Boolean, default=True)  # 是否双向关系
    is_default_fallback = Column(Boolean, default=False)  # 是否为默认回退选项

    # 关系定义保持不变
    parent = relationship("Ingredient", foreign_keys="IngredientHierarchy.parent_id", back_populates="hierarchy_children")
    child = relationship("Ingredient", foreign_keys="IngredientHierarchy.child_id", back_populates="hierarchy_parents")
```

## 4. 服务层设计

### 4.1 增强食材匹配器

```python
class EnhancedIngredientMatcher:
    """增强的智能食材匹配器"""

    def __init__(self, db: Session):
        self.db = db

    def enhanced_match_product_to_ingredient(self, product_name: str,
                                           use_hierachy_fallback: bool = True) -> List[Tuple[Ingredient, float, str]]:
        """
        增强的食材匹配算法
        返回: [(ingredient, confidence, match_type), ...]
        """
        matches = []

        # 1. 精确匹配
        exact_match = self.db.query(Ingredient).filter(
            Ingredient.name == product_name
        ).first()

        if exact_match:
            matches.append((exact_match, 1.0, "exact"))

        # 2. 别名匹配
        alias_matches = self._find_alias_matches(product_name)
        matches.extend(alias_matches)

        # 3. 模糊匹配
        partial_matches = self._find_partial_matches(product_name)
        matches.extend(partial_matches)

        # 4. 层级关系匹配
        if use_hierachy_fallback:
            hierarchy_matches = self._find_hierarchy_matches(product_name)
            matches.extend(hierarchy_matches)

        # 5. 去重并按置信度排序
        unique_matches = {}
        for ingredient, confidence, match_type in matches:
            if ingredient.id not in unique_matches or unique_matches[ingredient.id][1] < confidence:
                unique_matches[ingredient.id] = (ingredient, confidence, match_type)

        result = list(unique_matches.values())
        result.sort(key=lambda x: x[1], reverse=True)

        return result

    def _find_alias_matches(self, product_name: str) -> List[Tuple[Ingredient, float, str]]:
        """查找别名匹配"""
        alias_matches = self.db.query(Ingredient).filter(
            Ingredient.aliases.isnot(None)
        ).all()

        matches = []
        for ingredient in alias_matches:
            if ingredient.aliases:
                for alias in ingredient.aliases:
                    if product_name.lower() == alias.lower():
                        matches.append((ingredient, 1.0, "alias"))
                    elif product_name.lower() in alias.lower() or alias.lower() in product_name.lower():
                        confidence = 0.9 if len(alias) > len(product_name) else 0.8
                        matches.append((ingredient, confidence, "alias_partial"))

        return matches

    def _find_hierarchy_matches(self, product_name: str) -> List[Tuple[Ingredient, float, str]]:
        """查找层级关系匹配"""
        matches = []

        # 查找所有父级关系（更宽泛的分类）
        parents = self.db.query(IngredientHierarchy).join(
            Ingredient, IngredientHierarchy.parent_id == Ingredient.id
        ).filter(
            or_(
                Ingredient.name.like(f'%{product_name}%'),
                Ingredient.name.like(f'%{product_name.lower()}%')
            ),
            IngredientHierarchy.relationship_type.in_([
                RelationshipType.CONTAINS.value,
                RelationshipType.SUBSTITUTABLE.value
            ])
        ).all()

        for rel in parents:
            parent_ing = rel.parent
            base_confidence = 0.7
            strength = float(rel.relationship_strength or 1.0)
            final_confidence = base_confidence * strength
            matches.append((parent_ing, final_confidence, "hierarchy_parent"))

        # 查找所有子级关系（更具体的分类）
        children = self.db.query(IngredientHierarchy).join(
            Ingredient, IngredientHierarchy.child_id == Ingredient.id
        ).filter(
            or_(
                Ingredient.name.like(f'%{product_name}%'),
                Ingredient.name.like(f'%{product_name.lower()}%')
            ),
            IngredientHierarchy.relationship_type.in_([
                RelationshipType.CONTAINS.value,
                RelationshipType.FALLBACK.value
            ])
        ).all()

        for rel in children:
            child_ing = rel.child
            base_confidence = 0.8
            strength = float(rel.relationship_strength or 1.0)
            final_confidence = base_confidence * strength
            matches.append((child_ing, final_confidence, "hierarchy_child"))

        return matches

    def get_ingredient_fallback_chain(self, ingredient_name: str) -> List[Tuple[Ingredient, float]]:
        """获取食材的回退链，用于计算成本和营养时找不到精确匹配时使用"""
        # 先找到基础食材
        base_matches = self.enhanced_match_product_to_ingredient(ingredient_name)
        if not base_matches:
            return []

        fallback_chain = []
        processed_ids = set()

        for base_ing, base_conf, match_type in base_matches:
            if base_ing.id in processed_ids:
                continue

            # 添加自身
            fallback_chain.append((base_ing, base_conf))
            processed_ids.add(base_ing.id)

            # 查找所有子级（更具体的食材）- 递归查找多级关系
            children = self._get_all_descendants(base_ing.id, processed_ids)
            for child_id, path_confidence in children:
                if child_id not in processed_ids:
                    child_ing = self.db.query(Ingredient).filter(Ingredient.id == child_id).first()
                    if child_ing:
                        # 根据路径长度调整置信度
                        adjusted_conf = base_conf * path_confidence * 0.9
                        fallback_chain.append((child_ing, adjusted_conf))
                        processed_ids.add(child_id)

            # 查找所有父级（更通用的食材）- 递归查找多级关系
            parents = self._get_all_ancestors(base_ing.id, processed_ids)
            for parent_id, path_confidence in parents:
                if parent_id not in processed_ids:
                    parent_ing = self.db.query(Ingredient).filter(Ingredient.id == parent_id).first()
                    if parent_ing:
                        # 根据路径长度调整置信度
                        adjusted_conf = base_conf * path_confidence * 0.8
                        fallback_chain.append((parent_ing, adjusted_conf))
                        processed_ids.add(parent_id)

        return fallback_chain

    def _get_all_descendants(self, ingredient_id: int, visited: set = None, depth: int = 0, max_depth: int = 5) -> List[Tuple[int, float]]:
        """递归获取所有子级食材（后代）"""
        if visited is None:
            visited = set()
        if ingredient_id in visited or depth >= max_depth:
            return []

        visited.add(ingredient_id)
        descendants = []

        # 获取直接子节点
        direct_children = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == ingredient_id,
            IngredientHierarchy.relationship_type.in_([
                RelationshipType.CONTAINS.value,
                RelationshipType.FALLBACK.value
            ])
        ).all()

        for child_rel in direct_children:
            child_id = child_rel.child_id
            strength = float(child_rel.relationship_strength or 1.0)

            # 添加直接子节点
            descendants.append((child_id, strength))

            # 递归获取间接子节点
            indirect_descendants = self._get_all_descendants(child_id, visited.copy(), depth + 1, max_depth)
            for desc_id, desc_strength in indirect_descendants:
                # 路径越长，置信度越低
                path_strength = strength * desc_strength * 0.9  # 每级降低10%
                descendants.append((desc_id, path_strength))

        return descendants

    def _get_all_ancestors(self, ingredient_id: int, visited: set = None, depth: int = 0, max_depth: int = 5) -> List[Tuple[int, float]]:
        """递归获取所有父级食材（祖先）"""
        if visited is None:
            visited = set()
        if ingredient_id in visited or depth >= max_depth:
            return []

        visited.add(ingredient_id)
        ancestors = []

        # 获取直接父节点
        direct_parents = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == ingredient_id,
            IngredientHierarchy.relationship_type.in_([
                RelationshipType.CONTAINS.value,
                RelationshipType.FALLBACK.value
            ])
        ).all()

        for parent_rel in direct_parents:
            parent_id = parent_rel.parent_id
            strength = float(parent_rel.relationship_strength or 1.0)

            # 添加直接父节点
            ancestors.append((parent_id, strength))

            # 递归获取间接父节点
            indirect_ancestors = self._get_all_ancestors(parent_id, visited.copy(), depth + 1, max_depth)
            for anc_id, anc_strength in indirect_ancestors:
                # 路径越长，置信度越低
                path_strength = strength * anc_strength * 0.9  # 每级降低10%
                ancestors.append((anc_id, path_strength))

        return ancestors

    def get_multi_level_hierachy(self, ingredient_id: int) -> Dict:
        """获取多级层级关系图谱"""
        ingredient = self.db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            return {}

        hierarchy = {
            "id": ingredient.id,
            "name": ingredient.name,
            "children": self._build_children_tree(ingredient_id),
            "parents": self._build_parents_tree(ingredient_id)
        }

        return hierarchy

    def _build_children_tree(self, ingredient_id: int, visited: set = None, depth: int = 0, max_depth: int = 3) -> List[Dict]:
        """构建子级树形结构"""
        if visited is None:
            visited = set()
        if ingredient_id in visited or depth >= max_depth:
            return []

        visited.add(ingredient_id)
        children = []

        direct_children = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == ingredient_id,
            IngredientHierarchy.relationship_type == RelationshipType.CONTAINS.value
        ).all()

        for child_rel in direct_children:
            child_ing = self.db.query(Ingredient).filter(Ingredient.id == child_rel.child_id).first()
            if child_ing:
                child_node = {
                    "id": child_ing.id,
                    "name": child_ing.name,
                    "relationship_strength": float(child_rel.relationship_strength or 1.0),
                    "children": self._build_children_tree(child_rel.child_id, visited.copy(), depth + 1, max_depth)
                }
                children.append(child_node)

        return children

    def _build_parents_tree(self, ingredient_id: int, visited: set = None, depth: int = 0, max_depth: int = 3) -> List[Dict]:
        """构建父级树形结构"""
        if visited is None:
            visited = set()
        if ingredient_id in visited or depth >= max_depth:
            return []

        visited.add(ingredient_id)
        parents = []

        direct_parents = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == ingredient_id,
            IngredientHierarchy.relationship_type == RelationshipType.CONTAINS.value
        ).all()

        for parent_rel in direct_parents:
            parent_ing = self.db.query(Ingredient).filter(Ingredient.id == parent_rel.parent_id).first()
            if parent_ing:
                parent_node = {
                    "id": parent_ing.id,
                    "name": parent_ing.name,
                    "relationship_strength": float(parent_rel.relationship_strength or 1.0),
                    "parents": self._build_parents_tree(parent_rel.parent_id, visited.copy(), depth + 1, max_depth)
                }
                parents.append(parent_node)

        return parents
```

## 5. 营养和成本计算增强

修改 `recipe_service.py` 中的营养计算方法以利用层级关系：

```python
def calculate_recipe_nutrition(recipe_id: int, db: Session):
    """计算菜谱营养（利用食材层级关系进行回退）"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise ValueError(f"Recipe {recipe_id} not found")

    matcher = EnhancedIngredientMatcher(db)

    for recipe_ing in recipe.ingredients:
        # 首先尝试使用精确匹配的食材
        ingredient = db.query(Ingredient).filter(
            Ingredient.name == recipe_ing.ingredient_name
        ).first()

        # 如果找不到精确匹配，或者食材没有营养数据，则使用回退机制
        if not ingredient or not ingredient.nutrition_data:
            # 获取食材的回退链，包括层级关系中的父级食材
            fallback_chain = matcher.get_ingredient_fallback_chain(recipe_ing.ingredient_name)

            # 按照回退链顺序查找可用的营养数据
            ingredient = None
            used_fallback = False

            for fallback_ing, confidence in fallback_chain:
                if fallback_ing.nutrition_data:
                    ingredient = fallback_ing
                    used_fallback = True
                    print(f"Using fallback ingredient '{ingredient.name}' for '{recipe_ing.ingredient_name}' (confidence: {confidence})")
                    break

        # 如果找到了有营养数据的食材，使用其数据进行计算
        if ingredient and ingredient.nutrition_data:
            nutrition_data = ingredient.nutrition_data
            # ... 执行营养计算逻辑 ...
        else:
            # 如果最终还是找不到可用的营养数据，记录警告并使用默认值
            print(f"Warning: No nutrition data found for {recipe_ing.ingredient_name} or its fallbacks")
            # 使用默认值或标记为待完善
```

## 6. 食材/商品合并功能设计

### 6.1 合并功能概述

食材/商品合并功能允许将多个相似的食材或商品合并为一个，将所有相关的引用（包括菜谱中的使用、价格记录等）迁移到合并后的主食材上。这通过直接修改数据引用实现，而不是创建新的关系。

### 6.2 合并服务实现

```python
from typing import List, Tuple, Optional
from sqlalchemy.exc import IntegrityError
from contextlib import contextmanager

class IngredientMerger:
    """食材合并服务 - 实现数据层面的合并"""

    def __init__(self, db: Session):
        self.db = db

    def merge_ingredients(self, source_id: int, target_id: int, reason: str = "",
                         update_recipe_ingredients: bool = True,
                         update_products: bool = True,
                         update_nutrition_mappings: bool = True) -> bool:
        """
        合并食材 - 将 source_id 食材合并到 target_id 食材
        这是一个数据操作：将所有指向 source 的引用改为指向 target

        Args:
            source_id: 被合并的源食材ID
            target_id: 合并到的目标食材ID
            reason: 合并原因
            update_recipe_ingredients: 是否更新菜谱中的食材引用
            update_products: 是否更新商品记录中的食材引用
            update_nutrition_mappings: 是否更新营养数据映射

        Returns:
            bool: 合并是否成功
        """
        try:
            # 检查食材是否存在
            source_ing = self.db.query(Ingredient).filter(Ingredient.id == source_id).first()
            target_ing = self.db.query(Ingredient).filter(Ingredient.id == target_id).first()

            if not source_ing or not target_ing:
                raise ValueError("Source or target ingredient not found")

            if source_id == target_id:
                raise ValueError("Cannot merge ingredient to itself")

            # 开始事务
            with self._transaction_context():
                # 1. 更新菜谱中的食材引用
                if update_recipe_ingredients:
                    self._update_recipe_ingredients(source_id, target_id)

                # 2. 更新商品记录中的食材引用
                if update_products:
                    self._update_product_ingredients(source_id, target_id)

                # 3. 更新营养数据映射关系
                if update_nutrition_mappings:
                    self._update_nutrition_mappings(source_id, target_id)

                # 4. 更新层级关系表中的父子关系
                self._update_hierarchy_references(source_id, target_id)

                # 5. 合并营养数据（如果目标没有营养数据而源有）
                self._merge_nutrition_data(source_id, target_id)

                # 6. 记录合并操作
                merge_record = IngredientMergeRecord(
                    source_ingredient_id=source_id,
                    target_ingredient_id=target_id,
                    merge_reason=reason,
                    created_by=self._get_current_user_id()  # 需要根据实际情况实现
                )
                self.db.add(merge_record)

                # 7. 标记源食材为已合并状态（软删除）
                source_ing.is_merged = True
                source_ing.merged_to_id = target_id
                source_ing.is_active = False  # 标记为非活跃
                source_ing.name = f"[已合并] {source_ing.name}"  # 添加标识

                # 8. 提交事务
                self.db.commit()

                print(f"Successfully merged ingredient {source_id} ({source_ing.name}) into {target_id} ({target_ing.name})")
                return True

        except Exception as e:
            self.db.rollback()
            print(f"Failed to merge ingredients: {str(e)}")
            return False

    def _update_recipe_ingredients(self, source_id: int, target_id: int):
        """更新菜谱中的食材引用 - 将所有指向source的引用改为指向target"""
        # 查找所有使用源食材的菜谱项
        recipe_ingredients_using_source = self.db.query(RecipeIngredient).filter(
            RecipeIngredient.ingredient_id == source_id
        ).all()

        for rec_ing in recipe_ingredients_using_source:
            # 检查目标食材是否已经在同一个菜谱中存在
            existing_in_same_recipe = self.db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id == rec_ing.recipe_id,
                RecipeIngredient.ingredient_id == target_id
            ).first()

            if existing_in_same_recipe:
                # 如果目标食材已在同一菜谱中存在，合并数量
                existing_in_same_recipe.quantity += rec_ing.quantity
                # 删除源食材记录
                self.db.delete(rec_ing)
            else:
                # 否则，简单地更新食材ID
                rec_ing.ingredient_id = target_id

    def _update_product_ingredients(self, source_id: int, target_id: int):
        """更新商品记录中的食材引用"""
        # 查找所有使用源食材的商品
        products_using_source = self.db.query(Product).filter(
            Product.ingredient_id == source_id
        ).all()

        for product in products_using_source:
            # 检查是否已存在使用目标食材的同名商品
            existing_product = self.db.query(Product).filter(
                Product.ingredient_id == target_id,
                Product.name == product.name
            ).first()

            if existing_product:
                # 如果存在同名商品，将价格记录合并过去
                price_records = self.db.query(ProductRecord).filter(
                    ProductRecord.product_id == product.id
                ).all()

                for record in price_records:
                    # 将价格记录转移到目标商品
                    record.product_id = existing_product.id

                # 删除源商品
                self.db.delete(product)
            else:
                # 否则，直接更新食材ID
                product.ingredient_id = target_id

    def _update_nutrition_mappings(self, source_id: int, target_id: int):
        """更新营养数据映射关系"""
        # 查找所有指向源食材的营养数据映射
        mappings_using_source = self.db.query(IngredientNutritionMapping).filter(
            IngredientNutritionMapping.ingredient_id == source_id
        ).all()

        for mapping in mappings_using_source:
            # 检查目标食材是否已存在相同的营养数据映射
            existing_mapping = self.db.query(IngredientNutritionMapping).filter(
                IngredientNutritionMapping.ingredient_id == target_id,
                IngredientNutritionMapping.nutrition_id == mapping.nutrition_id
            ).first()

            if existing_mapping:
                # 如果存在，合并映射信息
                existing_mapping.priority = max(existing_mapping.priority, mapping.priority)
                existing_mapping.confidence = max(existing_mapping.confidence, mapping.confidence)
                # 删除源映射
                self.db.delete(mapping)
            else:
                # 否则，更新食材ID
                mapping.ingredient_id = target_id

    def _update_hierarchy_references(self, source_id: int, target_id: int):
        """更新层级关系表中的父子关系引用"""
        # 更新作为子级的引用（即其他食材指向源食材的关系）
        child_relationships = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == source_id
        ).all()

        for rel in child_relationships:
            # 检查是否已存在相同的父子关系
            existing_rel = self.db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == rel.parent_id,
                IngredientHierarchy.child_id == target_id
            ).first()

            if existing_rel:
                # 如果存在，合并关系强度
                existing_rel.relationship_strength = max(existing_rel.relationship_strength, rel.relationship_strength)
                # 删除重复关系
                self.db.delete(rel)
            else:
                # 否则，更新子级ID
                rel.child_id = target_id

        # 更新作为父级的引用（即源食材指向其他食材的关系）
        parent_relationships = self.db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == source_id
        ).all()

        for rel in parent_relationships:
            # 检查是否已存在相同的父子关系
            existing_rel = self.db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == target_id,
                IngredientHierarchy.child_id == rel.child_id
            ).first()

            if existing_rel:
                # 如果存在，合并关系强度
                existing_rel.relationship_strength = max(existing_rel.relationship_strength, rel.relationship_strength)
                # 删除重复关系
                self.db.delete(rel)
            else:
                # 否则，更新父级ID
                rel.parent_id = target_id

    def _merge_nutrition_data(self, source_id: int, target_id: int):
        """合并营养数据 - 将源食材的营养数据合并到目标食材"""
        source_ing = self.db.query(Ingredient).filter(Ingredient.id == source_id).first()
        target_ing = self.db.query(Ingredient).filter(Ingredient.id == target_id).first()

        # 如果目标食材没有营养数据但源有，则复制过来
        if target_ing.nutrition_id is None and source_ing.nutrition_id is not None:
            target_ing.nutrition_id = source_ing.nutrition_id

        # 合并密度值（如果有）
        if target_ing.density is None and source_ing.density is not None:
            target_ing.density = source_ing.density

        # 合并默认单位
        if target_ing.default_unit_id is None and source_ing.default_unit_id is not None:
            target_ing.default_unit_id = source_ing.default_unit_id

        # 合并piece_weight（单品重量）
        if target_ing.piece_weight is None and source_ing.piece_weight is not None:
            target_ing.piece_weight = source_ing.piece_weight
            target_ing.piece_weight_unit_id = source_ing.piece_weight_unit_id

        # 合并别名
        if source_ing.aliases:
            if not target_ing.aliases:
                target_ing.aliases = source_ing.aliases
            else:
                # 合并两个别名列表，去重
                all_aliases = set(target_ing.aliases + source_ing.aliases)
                target_ing.aliases = list(all_aliases)

    def _get_current_user_id(self) -> int:
        """获取当前用户ID - 需要根据实际应用实现"""
        # 这里应该根据实际的用户认证机制实现
        return 1  # 示例值

    @contextmanager
    def _transaction_context(self):
        """事务上下文管理器"""
        yield
        # 提交由调用者处理
```

### 6.3 数据模型扩展

新增合并记录表：

```python
class IngredientMergeRecord(Base, AuditMixin):
    """食材合并操作记录"""
    __tablename__ = "ingredient_merge_records"

    id = Column(Integer, primary_key=True, index=True)
    source_ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)  # 被合并的源食材
    target_ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)  # 合并到的目标食材
    merge_reason = Column(String(500))  # 合并原因
    status = Column(String(20), default="completed")  # completed, failed, rolled_back

    # 关系
    source_ingredient = relationship("Ingredient", foreign_keys=[source_ingredient_id])
    target_ingredient = relationship("Ingredient", foreign_keys=[target_ingredient_id])

class ProductMergeRecord(Base, AuditMixin):
    """商品合并操作记录"""
    __tablename__ = "product_merge_records"

    id = Column(Integer, primary_key=True, index=True)
    source_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # 被合并的源商品
    target_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # 合并到的目标商品
    merge_reason = Column(String(500))  # 合并原因
    status = Column(String(20), default="completed")  # completed, failed, rolled_back

    # 关系
    source_product = relationship("Product", foreign_keys=[source_product_id])
    target_product = relationship("Product", foreign_keys=[target_product_id])
```

### 6.4 API 端点实现

```python
@router.post("/ingredients/merge", response_model=dict)
async def merge_ingredients(
    merge_request: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """合并食材 - 数据层面的合并操作"""
    # 验证权限
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admin can merge ingredients")

    source_id = merge_request.get("source_id")
    target_id = merge_request.get("target_id")
    reason = merge_request.get("reason", "")

    if not source_id or not target_id:
        raise HTTPException(status_code=400, detail="Both source_id and target_id are required")

    if source_id == target_id:
        raise HTTPException(status_code=400, detail="Source and target IDs cannot be the same")

    merger = IngredientMerger(db)
    success = merger.merge_ingredients(
        source_id=source_id,
        target_id=target_id,
        reason=reason,
        update_recipe_ingredients=True,
        update_products=True,
        update_nutrition_mappings=True
    )

    if success:
        return {"success": True, "message": f"Ingredient {source_id} merged into {target_id} successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to merge ingredients")
```

### 6.5 实施优势

1. **真正的数据合并**：将多个食材完全合并为一个，而不是建立关系
2. **自动重定向**：所有相关记录（菜谱、价格、营养等）自动指向合并后的食材
3. **数据完整性**：保持数据完整性和一致性
4. **可追溯性**：记录合并历史，便于追踪数据变化
5. **性能提升**：减少重复数据，提升查询性能
6. **智能处理**：自动处理重复数据，合并相关信息

这种合并机制真正实现了数据层面的合并，当合并完成后，原先指向多个相似食材的数据都会统一指向合并后的单一食材，彻底解决数据重复问题。