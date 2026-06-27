"""食材层级关系执行器：CRUD。

payload（create）：{parent_id, child_id, relation_type, strength?}
update：{strength?} 等；delete：软删。
"""
from app.services.proposals.executors._crud_base import CrudExecutorBase
from app.models.ingredient_hierarchy import IngredientHierarchy


class HierarchyExecutor(CrudExecutorBase):
    entity_type = "hierarchy"
    model_class = IngredientHierarchy
