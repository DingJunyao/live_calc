# 食材层级管理与合并系统

## 概述

本系统实现了食材的层级管理与合并功能，解决以下问题：
- 食材不当分立（如"米"和"大米"被认为是不同食材）
- 处理层级关系（如"鸡肉"、"鸡胸肉"、"鸡翅"等）
- 实现食材合并功能，将多个相似食材合并为一个
- 支持回退机制，在计算成本和营养值时找不到精确食材时向上查找
- 数据操作层面的合并，将相关记录（菜谱、价格记录等）自动重定向到合并后的食材

## 核心功能

### 1. 食材层级关系管理

通过IngredientHierarchy模型实现食材之间的层级关系，支持三种关系类型：
- CONTAINS: 包含关系（如"鸡肉"包含"鸡胸肉"）
- SUBSTITUTABLE: 可替代关系（如"精盐"可替代"盐"）
- FALLBACK: 回退关系（如计算时找不到"鸡胸肉"可用"鸡肉"替代）

### 2. 食材合并功能

通过IngredientMerger服务实现数据层面的食材合并，包括：
- 将源食材的所有关联记录迁移到目标食材
- 自动处理重复数据冲突
- 记录合并历史

### 3. 智能匹配与回退机制

通过EnhancedIngredientMatcher实现：
- 精确匹配
- 同义词匹配
- 模糊匹配
- 层级回退匹配
- 处理已合并的食材

## 数据模型

### Ingredient 模型扩展

在`app/models/nutrition.py`中为Ingredient模型增加了以下字段：

```python
# 合并相关字段
is_merged = Column(Boolean, default=False, nullable=False)  # 标记是否已被合并
merged_into_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True)  # 合并到的目标食材ID

# 关系
merged_to_target = relationship("Ingredient", remote_side=[id], back_populates="merged_from_sources")
merged_from_sources = relationship("Ingredient", back_populates="merged_to_target", foreign_keys=[merged_into_id])
merge_records_as_source = relationship("IngredientMergeRecord", foreign_keys="IngredientMergeRecord.source_ingredient_id", back_populates="source_ingredient")
merge_records_as_target = relationship("IngredientMergeRecord", foreign_keys="IngredientMergeRecord.target_ingredient_id", back_populates="target_ingredient")
```

### IngredientHierarchy 模型

```python
class HierarchyRelationType(Enum):
    CONTAINS = "contains"          # 包含关系（父类包含子类）
    SUBSTITUTABLE = "substitutable" # 可替代关系（可以相互替代）
    FALLBACK = "fallback"          # 回退关系（找不到子类时可用父类替代）

class IngredientHierarchy(Base, AuditMixin):
    __tablename__ = "ingredient_hierarchies"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    child_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    relation_type = Column(String(20), nullable=False)  # 关系类型
    strength = Column(Integer, default=50)  # 关系强度（0-100）
```

### IngredientMergeRecord 模型

记录食材合并的历史：

```python
class IngredientMergeRecord(Base, AuditMixin):
    __tablename__ = "ingredient_merge_records"

    id = Column(Integer, primary_key=True, index=True)
    source_ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    target_ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    merged_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
```

## 服务层实现

### IngredientMerger 服务

位于`app/services/ingredient_merger.py`，提供食材合并功能：

```python
class IngredientMerger:
    def merge_ingredients(self, source_ingredient_ids: List[int], target_ingredient_id: int, merged_by_user_id: int) -> Dict[str, Any]:
        """
        将多个源食材合并到目标食材
        """
```

合并操作包括：
- 更新菜谱中的食材引用
- 更新商品价格记录中的食材引用
- 更新营养数据映射
- 更新层级关系中的食材引用
- 处理营养数据合并
- 标记源食材为已合并状态
- 记录合并历史

### EnhancedIngredientMatcher 服务

扩展了原有的IngredientMatcher服务，增加了对合并食材的处理能力。

## API 接口

### 食材合并接口

在`app/api/ingredient_merge.py`中提供合并接口：

```
POST /api/v1/ingredients/merge
```

请求体：
```json
{
  "source_ingredient_ids": [1, 2, 3],
  "target_ingredient_id": 4
}
```

## 数据库迁移

数据库迁移脚本`alembic/versions/20260312_0002_add_fields_for_ingredient_merge_functionality.py`会自动执行以下更改：

1. 为ingredients表添加合并相关的字段
2. 创建ingredient_merge_records表记录合并历史
3. 创建ingredient_hierarchies表管理层级关系
4. 为新表添加适当的索引

## 使用示例

### 合并食材

```python
from app.services.ingredient_merger import IngredientMerger

merger = IngredientMerger(db_session)
result = merger.merge_ingredients(
    source_ingredient_ids=[1, 2],  # "大米", "泰米"
    target_ingredient_id=3,        # "米"
    merged_by_user_id=1
)
```

### 智能匹配

```python
from app.services.ingredient_matcher import IngredientMatcher

matcher = IngredientMatcher(db_session)
best_match = matcher.find_best_match_with_fallback("泰米")
```

## 注意事项

1. 合并操作是不可逆的，合并后的源食材会被标记为已合并状态
2. 合并会自动处理关联数据的重定向
3. 合并前请确保目标食材是正确的聚合目标
4. 合并后仍可通过别名找到原食材名，以保留历史记录
5. 所有菜谱、价格记录等关联数据会自动迁移到目标食材

## 前端适配

前端需要更新以下组件以支持新的功能：
- 食材选择下拉框（处理合并后的食材）
- 食材管理页面（提供合并功能）
- 价格录入界面（自动处理合并食材）
- 菜谱编辑页面（使用合并后的食材进行成本和营养计算）