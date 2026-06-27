"""执行器注册入口。

P1：无真实执行器（仅测试中注册 stub）。
P2：在此 import 并 register 各业务执行器（ingredient/nutrition/unit/merchant/hierarchy/merge/recipe_publish），
    并由 main.py lifespan 调用 register_all()。
P3：管理员后台可调用 ExecutorRegistry.set_policy 动态改策略（持久化到 system_config 另行实现）。
"""
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.executors.recipe_publish import RecipePublishExecutor


def register_all() -> None:
    """注册所有业务执行器。P2.4 起逐步填充。"""
    ExecutorRegistry.register(
        RecipePublishExecutor(), default_policy="manual", default_risk="mid")
    # P2.5 继续追加 ingredient/nutrition/unit/hierarchy/merge/merchant
