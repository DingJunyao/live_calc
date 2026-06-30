# 实体单位覆盖与密度 接入提议-审核框架

> 分支：`feat/multi-user-permissions`
> 日期：2026-06-30
> 上游：[MULTI_USER_PERMISSIONS.md](MULTI_USER_PERMISSIONS.md)（多用户权限系统）
> 设计：[docs/superpowers/specs/2026-06-29-entity-unit-density-proposals-design.md](../docs/superpowers/specs/2026-06-29-entity-unit-density-proposals-design.md)
> 计划：[docs/superpowers/plans/2026-06-29-entity-unit-density-proposals.md](../docs/superpowers/plans/2026-06-29-entity-unit-density-proposals.md)

## 背景

多用户权限系统 P0~P3 完成后，「实体单位覆盖」（`entity_unit_overrides`，原料/商品的自定义单位换算，如「一盒=12个」「一个鸡蛋55g」）与「实体密度」（`entity_densities`）两类数据的 5 个写端点仍被 P0 一刀切锁成 `get_current_admin_user`，普通用户在原料/商品详情页维护时一提交就 403（属 [MULTI_USER_PERMISSIONS.md](MULTI_USER_PERMISSIONS.md) 已知妥协 §3「未分流端点」）。

本次放开这 5 个写端点给普通用户并接入 `change_proposals` 提议-审核框架。

## 三条关键决策（用户拍板）

1. **审核策略：全 manual**——普通用户的 create/update/delete 全部待管理员审核（治理总表原定「新增 auto」被本次加严）。管理员 `apply_as_admin` 直写即时生效。
2. **范围：实体单位覆盖 + 实体密度**——全局换算关系（UnitConversion）不动（「与克的换算」已由 `EntityUnitOverride.weight_per_unit` 承担）。
3. **删除回滚：软删**——两表加 `is_active`，delete 软删 + revert 复活，与单位/食材体系一致。连带项：唯一约束拆普通索引（同名重建既定套路）+ 下游读取点全过滤。

## 六个 Task 成果

| Task | 内容 |
|---|---|
| 1 | 两表加 `is_active`（含 `server_default=sa.text("1")`）+ 拆唯一约束改复合索引 + alembic 迁移 + 三引擎 SQL + 补开发库（258 覆盖/1 密度保留）+ 模型测试 |
| 2 | 两执行器 `EntityUnitOverrideExecutor`/`EntityDensityExecutor`（继承 CrudExecutorBase，覆写 validate：create 同名查重带 is_active、update/delete 校验活跃）+ 单测 |
| 3 | bootstrap 注册（全 manual）+ 注册验证测试 + density duplicate 测试 |
| 4 | **32 个下游读取点加 is_active 过滤**（unit_conversion_service 9 + recipe_service 1 + inferrer 4 + export reachability/packaging + importer）+ downstream 回归测试 |
| 5 | units.py 5 写端点分流（管理员 apply_as_admin / 普通用户 submit）+ 集成测试 + **P0 修复** |
| 6 | 两个详情页前端按角色提示 + 审核台 entityTypeLabel 补 2 项 + npm run build |

## 关键技术点

### 1. SQLite 唯一约束只能表重建（plan 原方案行不通）
原模型 `UniqueConstraint(name="uq_entity_unit")` 在 SQLite 上落成**匿名** `sqlite_autoindex_<table>_1`（忽略 name），且 SQLite 禁止 DROP 关联 UNIQUE 的 autoindex。`batch_alter_table.drop_constraint("uq_entity_unit")` 报 `No such constraint`，`drop_index` 同样失效。唯一可靠解是**手写表重建**（CREATE 新表无 UNIQUE + INSERT 复制 + DROP + RENAME），与 SQLite 官方 alter-table 推荐一致，参照 [BUGFIX_原料同名重建](BUGFIX_原料同名重建.md) 先例。迁移做引擎分支：SQLite 走 `op.execute` 表重建，MySQL/PG 走 `batch_alter_table.drop_constraint`（约束为真实命名）。

### 2. is_active 软删 + server_default（防原始 INSERT 路径崩）
两表有原始 SQL INSERT 省略 is_active 的路径（`task_templates.py` Agent 模板、`migrate_from_bak.py`），靠 DB 层 DEFAULT 兜底。但 `create_all` 建的库（项目 dev 库历史）列无 DEFAULT 会 NOT NULL 崩。故模型加 `server_default=sa.text("1")`（参照 `merchant.is_open`/`recipe.is_public`），迁移/SQL 表重建也显式 DEFAULT 1，三层覆盖。

### 3. 32 个下游读取点过滤（漏一处成本算错）
这两张表是成本计算核心数据源，被 unit_conversion_service/recipe_service/inferrer/export 多处读。逐个加 `is_active.is_(True)` 过滤，软删行（幽灵数据）不再被读到。**plan 原清单漏了 units.py 的 7 个管理读取点**（list/查重/查找），靠 grep 全量比对抓出补全。packaging.py 的共用 `_query` 辅助函数用 `if model in (EntityDensity, EntityUnitOverride)` 条件分支精准过滤，不影响其他 13 个共用模型。

### 4. 两个执行器 + 两种 entity_type 区分
执行器继承 CrudExecutorBase 复用软删/复活，覆写 validate。区分：**框架级** entity_type（"entity_unit_override"/"entity_density"，注册名、进 change_proposals.entity_type）vs **业务级**（"ingredient"/"product"，URL 路径参数、进 payload）。

### 5. Decimal 三处 JSON 序列化（5 处端点分流触发）
`change_proposals.payload/snapshot/revert_payload` 是 JSON 列，无法序列化 Decimal。三处都要处理：
- **payload**：端点用 `data.model_dump(mode="json")`（Decimal→str 无损，Numeric 列 setter 接受 str 转回）
- **占位响应**：密度 create 占位补 `confidence=data.confidence`（未 flush 对象 confidence=None 撞 ResponseValidationError）
- **snapshot**：见下方 P0

### 6. ⚠️ P0：CrudExecutorBase snapshot JSON-safe（惠及所有 CRUD 执行器）
review 抓出的严重框架 bug：`_crud_base.py` 的 update snapshot（`{k: getattr(obj,k)...}`）和 delete snapshot（全列）把 ORM Decimal 塞进 `change_proposals.snapshot` JSON 列 → TypeError → 管理员直写 update/delete 带 Numeric 字段必 500。潜伏在 P1 框架代码（既有执行器测试没碰 Numeric 字段的 update/delete、且执行器单测直接 `p.snapshot=result.snapshot` 赋值内存对象从不持久化到 JSON 列），Task 5 让管理员直写走执行器才激活。修复：加 `_json_safe(v)`（Decimal→str、datetime/date→isoformat）应用到两处 snapshot 构造，revert 时 str 经 Numeric 列 setter 自动转回 Decimal（无损）。**修一处惠及所有继承 CrudExecutorBase 的执行器**（ingredient/unit/hierarchy/merchant/override/density）。

## 文件清单

### 后端新增
- `app/services/proposals/executors/entity_unit_override.py` / `entity_density.py`
- `alembic/versions/20260629_c0e1d2f3a4b5_entity_unit_density_soft_delete.py`
- `scripts/sql/20260629_entity_unit_density_soft_delete_{sqlite,mysql,postgres}.sql`
- `tests/models/test_entity_soft_delete.py`、`tests/test_entity_executors.py`、`tests/test_entity_unit_density_proposals.py`、`tests/test_entity_e2e_lifecycle.py`

### 后端修改
- `app/models/entity_unit_override.py` / `entity_density.py`（+is_active server_default、拆约束）
- `app/api/units.py`（5 写端点分流）
- `app/services/proposals/bootstrap.py`（注册 2 执行器全 manual）
- `app/services/proposals/executors/_crud_base.py`（P0：_json_safe）
- `app/services/unit_conversion_service.py`（9 处过滤）、`recipe_service.py`（1）、`importer/ai_inference/inferrer.py`（4）、`export/reachability.py`/`packaging.py`、`importer/importers/export.py`

### 前端修改
- `views/ingredients/IngredientDetail.vue` / `views/products/ProductDetail.vue`（8 写函数按角色提示）
- `views/admin/ProposalsView.vue`（entityTypeLabel 补 2 项）

## 测试

- 模型 4 + 执行器 6 + 端点 6 + e2e 4 + downstream 2 + 框架/共享/权限基线 = 相关测试 **77 passed, 0 failed**
- 端到端链路验证：普通用户提交→pending→管理员审核通过→applied 生效→管理员回滚→reverted（create 硬删/delete 复活）；下游 pending 期间隔离、applied 后生效
- 前端 `npm run build` 通过

## 执行方式

subagent-driven-development：每 task 派 implementer + 两阶段 review（spec 符合 + 代码质量），Task 5 review 抓出 P0 后 fix + 复审。全程不 git commit（项目 CLAUDE.md 规矩），每 task 以测试通过 + py_compile/build 为准。
