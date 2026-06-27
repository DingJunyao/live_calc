"""执行器注册入口。

P2：注册全部业务执行器（ingredient/nutrition/unit/hierarchy/merchant/recipe_publish）
    并按治理总表（设计文档 §5.5）设默认策略。由 main.py lifespan 调用 register_all()。
P3：管理员后台可调用 ExecutorRegistry.set_policy 动态改策略（持久化到 system_config 另行实现）。
"""
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.executors.recipe_publish import RecipePublishExecutor
from app.services.proposals.executors.ingredient import IngredientExecutor
from app.services.proposals.executors.nutrition import NutritionExecutor
from app.services.proposals.executors.unit import UnitExecutor
from app.services.proposals.executors.hierarchy import HierarchyExecutor
from app.services.proposals.executors.merchant import MerchantExecutor


def register_all() -> None:
    """注册所有业务执行器并设默认策略（治理总表 §5.5）。"""
    # 食材：新增 auto、编辑/删除/合并 manual（合并/删除 high）
    ExecutorRegistry.register(IngredientExecutor(), default_policy="auto_approve", default_risk="mid")
    ExecutorRegistry.set_policy("ingredient", "update", "manual")
    ExecutorRegistry.set_policy("ingredient", "delete", "manual")
    ExecutorRegistry.set_policy("ingredient", "merge", "manual")
    ExecutorRegistry.set_risk("ingredient", "merge", "high")
    ExecutorRegistry.set_risk("ingredient", "delete", "high")

    # 营养：默认 manual（补空由执行器 apply 内动态 set_policy 转 auto）
    ExecutorRegistry.register(NutritionExecutor(), default_policy="manual", default_risk="mid")

    # 单位：新增 auto、编辑/删除 manual
    ExecutorRegistry.register(UnitExecutor(), default_policy="auto_approve", default_risk="mid")
    ExecutorRegistry.set_policy("unit", "update", "manual")
    ExecutorRegistry.set_policy("unit", "delete", "manual")

    # 层级：全 manual
    ExecutorRegistry.register(HierarchyExecutor(), default_policy="manual", default_risk="mid")

    # 商家：新增 auto、编辑/删除 manual（编辑/删除 high，含坐标高危）
    ExecutorRegistry.register(MerchantExecutor(), default_policy="auto_approve", default_risk="mid")
    ExecutorRegistry.set_policy("merchant", "update", "manual")
    ExecutorRegistry.set_policy("merchant", "delete", "manual")
    ExecutorRegistry.set_risk("merchant", "update", "high")
    ExecutorRegistry.set_risk("merchant", "delete", "high")

    # 菜谱发布：manual
    ExecutorRegistry.register(RecipePublishExecutor(), default_policy="manual", default_risk="mid")
