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
from app.services.proposals.executors.merchant_merge import MerchantMergeExecutor
from app.services.proposals.executors.recipe_edit import RecipeEditExecutor
from app.services.proposals.executors.entity_unit_override import EntityUnitOverrideExecutor
from app.services.proposals.executors.entity_density import EntityDensityExecutor
from app.services.proposals.executors.product import ProductExecutor
from app.services.proposals.executors.product_split import ProductSplitExecutor
from app.services.proposals.executors.product_merge import ProductMergeExecutor
from app.services.proposals.executors.usda_ingredient_match import UsdaIngredientMatchExecutor
from app.services.proposals.executors.usda_product_match import UsdaProductMatchExecutor
from app.services.proposals.executors.product_nutrition import ProductNutritionExecutor


def register_all(db=None) -> None:
    """注册所有业务执行器并设默认策略（治理总表 §5.5）。

    若提供 db（SQLAlchemy Session），则在默认策略生效后从 system_config
    加载持久化策略覆盖之，使管理员配置在重启后保持。
    """
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

    # 商家合并：清理共享池重复商家（manual + high risk）
    ExecutorRegistry.register(MerchantMergeExecutor(), default_policy="manual", default_risk="high")

    # 菜谱发布：manual
    ExecutorRegistry.register(RecipePublishExecutor(), default_policy="manual", default_risk="mid")

    # 菜谱编辑：已发布菜谱的修改走提议（manual）
    ExecutorRegistry.register(RecipeEditExecutor(), default_policy="manual", default_risk="mid")

    # 实体单位覆盖：全 manual（新增/编辑/删除均需审核，用户加严要求）
    ExecutorRegistry.register(EntityUnitOverrideExecutor(), default_policy="manual", default_risk="mid")

    # 实体密度：全 manual
    ExecutorRegistry.register(EntityDensityExecutor(), default_policy="manual", default_risk="mid")

    # 商品实体：全 manual（update/delete 均需审核）
    ExecutorRegistry.register(ProductExecutor(), default_policy="manual", default_risk="mid")

    # 商品拆分：全 manual（创建新原料，迁移营养，高风险）
    ExecutorRegistry.register(ProductSplitExecutor(), default_policy="manual", default_risk="high")

    # 商品合并：全 manual（迁移价格记录，软删源商品，高风险）
    ExecutorRegistry.register(ProductMergeExecutor(), default_policy="manual", default_risk="high")

    # USDA 匹配：替换语义（清旧写新），全 manual（覆盖营养数据，用户已确认需审核）
    ExecutorRegistry.register(UsdaIngredientMatchExecutor(), default_policy="manual", default_risk="mid")
    ExecutorRegistry.register(UsdaProductMatchExecutor(), default_policy="manual", default_risk="mid")

    # 商品营养数据：全 manual（补空 auto 由端点 policy_override 覆盖）
    ExecutorRegistry.register(ProductNutritionExecutor(), default_policy="manual", default_risk="mid")

    # 加载持久化策略覆盖默认（system_config）
    if db is not None:
        try:
            n = ExecutorRegistry.load_persisted_policies(db)
            if n:
                # 仅日志用，调用方可在 lifespan 记录；这里静默返回
                pass
        except Exception:
            # 持久化加载失败不应阻断启动（沿用默认策略）
            pass
