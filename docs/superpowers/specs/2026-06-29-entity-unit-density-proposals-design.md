# 实体单位覆盖与实体密度 接入提议-审核框架 设计

> 日期：2026-06-29
> 分支：`feat/multi-user-permissions`
> 上游设计：[2026-06-27-multi-user-permissions-design.md](./2026-06-27-multi-user-permissions-design.md)
> 概览：[cc/MULTI_USER_PERMISSIONS.md](../../../cc/MULTI_USER_PERMISSIONS.md)

## 1. 背景

多用户权限系统已完成 P0~P3：建立了通用 `change_proposals` 提议-审核框架 + 类型执行器，并将共享数据写端点做了分流改造（管理员 `apply_as_admin` 直写 / 普通用户 `submit` 走审核）。

但「实体单位覆盖」（`entity_unit_overrides`）和「实体密度」（`entity_densities`）两类数据的 5 个写端点，在 P0 堵漏阶段被一刀切锁成 `get_current_admin_user`，**未进分流**（见 [cc/MULTI_USER_PERMISSIONS.md](../../../cc/MULTI_USER_PERMISSIONS.md) 「已知妥协 §3 未分流端点」）。导致普通用户在原料、商品详情页维护自定义单位与密度时，提交即 403。

本次目标：放开这 5 个写端点给普通用户，并接入提议-审核框架——普通用户提交全部经管理员审核，管理员超级权限路径即时生效。

## 2. 现状

### 2.1 端点与权限（[backend/app/api/units.py](../../../backend/app/api/units.py)）

| 端点 | 路径 | 当前权限 |
|---|---|---|
| 列表-单位覆盖 | `GET /entities/{type}/{id}/units` | 所有人可读 |
| 列表-密度 | `GET /entities/{type}/{id}/density` | 所有人可读 |
| 未映射单位 | `GET /entities/{type}/{id}/units/unmapped-units` | 所有人可读 |
| 创建-单位覆盖 | `POST /entities/{type}/{id}/units` | **仅管理员** |
| 更新-单位覆盖 | `PUT /entities/{type}/{id}/units/{override_id}` | **仅管理员** |
| 删除-单位覆盖 | `DELETE /entities/{type}/{id}/units/{override_id}` | **仅管理员** |
| upsert-密度 | `POST /entities/{type}/{id}/density` | **仅管理员** |
| 删除-密度 | `DELETE /entities/{type}/{id}/density/{density_id}` | **仅管理员** |

5 个写端点全部 `Depends(get_current_admin_user)`，普通用户被挡死。

### 2.2 数据模型

- [entity_unit_override.py](../../../backend/app/models/entity_unit_override.py)：`EntityUnitOverride`，无 `is_active`、无 `AuditMixin`，仅有 `created_at/updated_at`。唯一约束 `uq_entity_unit(entity_type, entity_id, unit_name)`。
- [entity_density.py](../../../backend/app/models/entity_density.py)：`EntityDensity`，同样无 `is_active`。唯一约束 `uq_entity_density(entity_type, entity_id, condition)`。
- 两表的 `entity_type` 列是业务级（值为 `ingredient`/`product`），与框架执行器的注册级 `entity_type` 是两个概念（详见 §5.2）。

### 2.3 下游读取点（成本计算核心，共 12+ 处）

`EntityUnitOverride`（7 处）：[unit_conversion_service.py](../../../backend/app/services/unit_conversion_service.py) 6 处（L311/330/348/512/554/663）、[recipe_service.py:1834](../../../backend/app/services/recipe_service.py#L1834)。
`EntityDensity`（5+ 处）：unit_conversion_service 3 处（L122/142/161）、[inferrer.py](../../../backend/app/services/importer/ai_inference/inferrer.py) 3 处（L468/562/597）。
导出层：[export/reachability.py](../../../backend/app/services/export/reachability.py)、[export/packaging.py](../../../backend/app/services/export/packaging.py)、[importer/importers/export.py](../../../backend/app/services/importer/importers/export.py)。

### 2.4 写入点（管理员/系统级，保持直写不走框架）

- [inferrer.py:639](../../../backend/app/services/importer/ai_inference/inferrer.py#L639)：Agent 密度推测写入
- [importer/importers/export.py:247](../../../backend/app/services/importer/importers/export.py#L247)：导入写入密度
- [unit_conversion_service.py:632](../../../backend/app/services/unit_conversion_service.py#L632)：自动匹配创建覆盖
- `_batch_insert_wpu.py`：离线批量脚本

这些是管理员/系统级写入，靠 `is_active` 默认值 `True` 保证写入即活数据，不接入提议框架。

### 2.5 前端调用点

[IngredientDetail.vue](../../../frontend/src/views/ingredients/IngredientDetail.vue)（L2365~2526）、[ProductDetail.vue](../../../frontend/src/views/products/ProductDetail.vue)（L1539~1700）各 5 个写函数。[PricesView.vue](../../../frontend/src/views/prices/PricesView.vue)、[QuickPriceRecordDialog.vue](../../../frontend/src/components/prices/QuickPriceRecordDialog.vue) 仅读 `GET .../units`（单位下拉），不受影响。

## 3. 关键决策（3 条）

1. **审核策略：全部 manual**。普通用户提交的 create/update/delete 全部待管理员审核（治理总表原定「新增 auto」被本次需求覆盖加严）。管理员 `apply_as_admin` 即时生效，单用户场景零负担。
2. **范围：实体单位覆盖 + 实体密度两类**。全局换算关系（`UnitConversion`）不动——「与克的换算」已由 `EntityUnitOverride.weight_per_unit` 承担（如「一个鸡蛋多少克」）。
3. **删除回滚：软删**。给两张表加 `is_active`，delete 软删 + revert 复活，与单位/食材体系一致。连带项：唯一约束拆普通索引（同名重建既定套路）+ 12+ 下游读取点加 `is_active` 过滤。

> 方案对比：硬删 + 快照重插不改表、下游零改动，但用户最终选择软删以保持与现有软删体系的一致性。软删的代价（唯一约束重构 + 全量下游过滤）在本设计中完整承担。

## 4. 设计详述

### 4.1 节 A：数据模型变更

两张表各加：
```python
is_active = Column(Boolean, default=True, nullable=False, index=True)
```

去掉数据库唯一约束，改普通复合索引（跨引擎一致，避免软删后同名重建撞约束）：
- `EntityUnitOverride`：去 `uq_entity_unit`，加 `ix_entity_unit_active(entity_type, entity_id, unit_name)`
- `EntityDensity`：去 `uq_entity_density`，加 `ix_entity_density_active(entity_type, entity_id, condition)`

**迁移**：
- alembic 一个版本（ADD COLUMN `is_active` default True + drop unique constraint + create composite index），`down_revision` 接当前 head，具体 revision hash 实现时由 alembic 生成。
- 三引擎 SQL 脚本（SQLite / MySQL / PostgreSQL）。纯字段 + 索引变更，与 PostGIS 无关，PG 不分 PostGIS 版本。
- 开发库 `livecalc.db` schema 漂移补齐方式参照既有先例（备份后手动执行 SQL，不依赖 alembic_version）。

### 4.2 节 B：两个新执行器

加 `is_active` 后，两表能直接复用 [_crud_base.py](../../../backend/app/services/proposals/executors/_crud_base.py) 的默认软删 delete（`is_active=False`）+ revert（`restore_active` 复活）。

新建：
- [executors/entity_unit_override.py](../../../backend/app/services/proposals/executors/entity_unit_override.py)：`EntityUnitOverrideExecutor`，框架 `entity_type="entity_unit_override"`
- [executors/entity_density.py](../../../backend/app/services/proposals/executors/entity_density.py)：`EntityDensityExecutor`，框架 `entity_type="entity_density"`

各自**继承 `CrudExecutorBase`**，覆写 `validate`：
- create：按业务 `entity_type` + `entity_id` + `unit_name`（覆盖）/ `condition`（密度）查重，**带 `is_active=True` 过滤**
- update/delete：校验目标行存在且 `is_active=True`（基类默认 `db.query(model).get(eid)` 不带过滤，子类需补）

apply/revert 吃基类：
- create：apply 新增 `is_active=True`；revert 硬删新建行（create 回滚 = 当没创建过）
- update：apply 快照旧值改新值；revert 按快照还原
- delete：apply 软删 `is_active=False` + 全字段快照；revert 复活 `is_active=True`

**两种 entity_type 区分**（实现关键，避免混淆）：
- **框架级** `entity_type`：执行器注册名（`"entity_unit_override"` / `"entity_density"`），用于 `change_proposals.entity_type` 与注册表查找
- **业务级** `entity_type`：数据表列（`"ingredient"` / `"product"`），来自 URL 路径参数，放入 `change_proposals.payload`，执行器 create 时取出写入数据行

### 4.3 节 C：端点分流（units.py 5 个写端点）

5 个端点统一改：
```python
if current_user.is_admin:
    proposal_service.apply_as_admin(db, entity_type="entity_unit_override",
        entity_id=..., action=..., payload=..., admin=current_user)
else:
    p = proposal_service.submit(db, entity_type="entity_unit_override",
        entity_id=..., action=..., payload=..., proposer=current_user)
db.commit()
```

各端点 action / entity_id / payload 规约：

| 端点 | action | entity_id | payload 关键字段 |
|---|---|---|---|
| create 覆盖 | `create` | `None` | 业务 `entity_type`/`entity_id` + `unit_name` + `conversion_factor`/`weight_per_unit`/... |
| update 覆盖 | `update` | `override.id` | `EntityUnitOverrideUpdate` 部分字段 |
| delete 覆盖 | `delete` | `override.id` | `{}` |
| upsert 密度 | `create` 或 `update` | 见下 | 业务 `entity_type`/`entity_id` + `density`/`condition`/... |
| delete 密度 | `delete` | `density.id` | `{}` |

**密度 upsert 语义**：端点先按业务 `entity_type` + `entity_id` + `condition` 查 `is_active=True` 记录——有则 submit `update`（`entity_id` = 已存记录 id），无则 submit `create`（`entity_id=None`）。

**响应处理**（全 manual，无 auto 路径）：
- 管理员：`apply_as_admin` 即时生效，返回最新对象（与现有行为一致）
- 普通用户：submit 后 status=`pending`，无实际对象，返回占位骨架（参照 [unit.create](../../../backend/app/api/units.py#L172) 的 `id=0` 占位以满足 `response_model`）

bootstrap 注册：`default_policy="manual"`（全 action 默认 manual，无需 set_policy 细分）。

### 4.4 节 D：下游读取点加 is_active 过滤（关键，漏一处即成本算错）

`EntityUnitOverride`（7 处全部加 `.filter(EntityUnitOverride.is_active == True)`）：
- unit_conversion_service.py L311/330/348/512/554/663
- recipe_service.py L1834

`EntityDensity`（5+ 处）：
- unit_conversion_service.py L122/142/161
- inferrer.py L468/562/597

导出层（reachability / packaging / importer）只收集/导出 `is_active=True` 的活数据。

**校验**：实现后逐一核对这些读取点无遗漏（grep `EntityUnitOverride`/`EntityDensity` 全量比对），是本节的验收门槛。

### 4.5 节 E：前端适配

[IngredientDetail.vue](../../../frontend/src/views/ingredients/IngredientDetail.vue) 与 [ProductDetail.vue](../../../frontend/src/views/products/ProductDetail.vue) 的 5 个写函数：
- 非管理员提交后，后端返回 pending（占位），前端弹 toast「已提交，待管理员审核」+ 刷新列表（列表不显示待定值，审核通过后才出现）
- 管理员即时生效，正常刷新
- 利用已有 auth store 判断角色；非管理员保存按钮文案可改为「提交审核」（可选增强）

[ProposalsView.vue](../../../frontend/src/views/admin/ProposalsView.vue) 的 `entityTypeLabel` 补：`entity_unit_override` →「实体单位覆盖」、`entity_density` →「实体密度」。

### 4.6 节 F：测试

新增测试覆盖：
1. 普通用户 create/update/delete 覆盖 + create/update/delete 密度 → 全部 submit → status=`pending`（manual 待审）
2. 管理员同操作 `apply_as_admin` → status=`applied`，即时生效
3. 软删除：delete apply 后 `is_active=False`，`unit_conversion_service` 读不到（换算失效）
4. revert：delete revert 后 `is_active=True` 复活，换算恢复
5. 同名重建：软删后同业务 key create 不撞约束（唯一约束已拆），校验通过

## 5. 关键文件清单

### 后端（新增）
- `backend/app/services/proposals/executors/entity_unit_override.py`
- `backend/app/services/proposals/executors/entity_density.py`
- `backend/alembic/versions/20260629_*_entity_unit_density_soft_delete.py`（revision hash 实现时生成）
- `backend/scripts/sql/20260629_entity_unit_density_soft_delete_sqlite.sql`
- `backend/scripts/sql/20260629_entity_unit_density_soft_delete_mysql.sql`
- `backend/scripts/sql/20260629_entity_unit_density_soft_delete_postgres.sql`

### 后端（修改）
- `backend/app/models/entity_unit_override.py`（+is_active、拆约束）
- `backend/app/models/entity_density.py`（同上）
- `backend/app/api/units.py`（5 端点分流）
- `backend/app/services/proposals/bootstrap.py`（注册 2 执行器）
- `backend/app/services/unit_conversion_service.py`（6+3 处过滤）
- `backend/app/services/recipe_service.py`（1 处过滤）
- `backend/app/services/importer/ai_inference/inferrer.py`（3 处过滤）
- 导出层 reachability/packaging/importer（过滤活数据）

### 前端（修改）
- `frontend/src/views/ingredients/IngredientDetail.vue`
- `frontend/src/views/products/ProductDetail.vue`
- `frontend/src/views/admin/ProposalsView.vue`（entityTypeLabel）

## 6. 风险与权衡

1. **下游过滤遗漏**：12+ 处读取点漏一处即成本计算读到「幽灵数据」。缓解：实现后 grep 全量比对 + 下游单测覆盖换算失效场景。
2. **软删占位**：软删的行留在表内（is_active=False），不参与换算但占空间。可接受（量级小），未来可加清理任务。
3. **create revert 硬删**：create 提议审核通过后回滚走硬删（非软删），语义是「当没创建过」。与 delete 的软删 revert 不同，文档与代码注释明示。
4. **密度无独立 update 端点**：upsert 在端点层判断 create/update，执行器本身只认标准三 action。映射逻辑在端点，执行器保持通用。

## 7. 不在本次范围

- 全局换算关系 `UnitConversion` 的增删（仍是管理员专属）
- 标准/模糊单位的增删改（已分流，不在本次）
- 数据级归属（created_by）：本两类数据属「共享知识库」桶，谁都能提议、管理员把关，无需归属字段
- 自动审核（auto_review）具体判定逻辑：沿用框架预留接口，本次全 manual
