# Task 2.5b：共享写端点分流改造

## 背景

多用户权限计划 P0 阶段把共享数据写端点统一收紧为 `get_current_admin_user`（管理员直写、普通 403）。
P1 通用提议—审核框架就绪（Task 1.x）、P2 业务执行器注册（Task 2.5a）后，本 task 把这些「限管理员」端点升级为分流模式：

- **管理员** → `proposal_service.apply_as_admin`：经框架执行器 `apply`，绕过审核，立即生效；同时在 `change_proposals` 表留痕（status=applied）。
- **普通用户** → `proposal_service.submit`：按治理总表策略分流（auto_approve 立即 / manual 待审 / auto_review 走默认 escalate）。

`apply_as_admin` 与 `submit` 均在 service 层不 commit，由 API 层 `db.commit()` 兜底；异常路径不 commit（事务随请求结束丢弃）。

## 改造端点清单（5 文件）

### 1. `backend/app/api/ingredient_hierarchy.py`
- **merge_ingredients**（POST `/ingredients/merge`）→ 分流（entity_type="ingredient", action="merge"）。普通用户的所有权预检保留（源与目标均须由本人创建），不满足先 403 再走 submit。管理员 `apply_as_admin` 调 `IngredientExecutor._apply_merge`（复用 IngredientMerger + 全量快照）。治理总表 ingredient.merge=manual+high → 普通用户 pending。
- **create_hierarchy_relation**（POST `/ingredients/hierarchy`）→ 分流（entity_type="hierarchy", action="create"）。API 层做关系类型校验 + fallback 交换 + 唯一性校验后，把最终 `parent_id/child_id/relation_type/strength` 作为 payload 传给执行器（CrudExecutorBase.create 直接 `IngredientHierarchy(**payload)`）。治理总表 hierarchy 全 manual → 普通 pending。
- **update_hierarchy_relation**（PUT `/ingredients/hierarchy/{id}`）→ 分流（action="update"），payload={"strength": N}。普通用户待审期间返回当前值。
- **delete_hierarchy_relation**（DELETE `/ingredients/hierarchy/{id}`）→ 分流（action="delete"）。**注：执行器 delete 为软删（is_active=False），原端点是硬删 `db.delete`**；改软删是为了支持 revert 回滚。查询侧应统一按 is_active=True 过滤。
- GET `/merge-history`（管理员）、`/{id}/hierarchy`、`/{id}/merge-status` 不动（只读）。

### 2. `backend/app/api/units.py`
- **create_unit**（POST `/`）→ 分流（entity_type="unit", action="create"）。API 层做名称/缩写唯一性预检，payload=UnitCreate.model_dump()。治理总表 unit.create=auto_approve → 普通用户提交即 applied。
- **update_unit**（PUT `/{id}`）→ 分流（action="update"）。payload=update_data。执行器 validate 拒绝改 is_standard=True 的标准单位（仅管理员可改/删）。治理总表 unit.update=manual → 普通 pending，返回当前单位（值未变）。
- **delete_unit**（DELETE `/{id}`）→ 分流（action="delete"）。执行器 delete 软删 is_active=False（原硬删的 FK 引用兜底已移除——软删不会触发 FK 错误）。
- 换算关系 / 实体单位覆盖 / 实体密度写端点：**本次未进分流**，保留 `get_current_admin_user`（同模式待续，前端无直接调用且涉及多表关联，执行器未覆盖 UnitConversion/EntityUnitOverride/EntityDensity）。
- 所有 GET 端点不动（保留 `get_current_user`）。

### 3. `backend/app/api/nutrition.py`
- **edit_ingredient_nutrition**（POST `/ingredients/{id}/nutrition`）→ 分流（entity_type="nutrition", action="update"）。抽 `_build_structured_nutrients(request)` 把请求 NutrientItem 列表 + NRV 百分比计算转为 `{core_nutrients, all_nutrients, nutrient_details}` 结构化字典（管理员/提议路径共用），作为 payload["nutrients"] 传给执行器。执行器写入 `NutritionData.nutrients`（补空则新建、覆盖则更新），并在 apply 内动态 set_policy（补空→auto_approve，覆盖→manual）。普通用户路径返回 200，message 区分「自动通过」与「待审」。
- **edit_product_nutrition**（POST `/products/{id}/nutrition`）、**correct_nutrition_mapping**（POST `/correct`）：**本次未进分流**，保留 `get_current_admin_user`。原因：前者写 `Product.custom_nutrition_data`（不是 NutritionData.ingredient_id），后者改 `IngredientNutritionMapping`，两者与 NutritionExecutor（仅写 NutritionData.ingredient_id）的语义不匹配。同模式待续。
- 所有 GET 端点不动。

### 4. `backend/app/api/merchants.py`
- **update_merchant**（PUT `/{id}`）→ 分流（entity_type="merchant", action="update"）。原端点用 `Merchant.user_id == current_user.id` 过滤（共享池转型后 user_id 已 nullable 失效），改为按 id 查到后走分流。治理总表 merchant.update=manual+high → 普通 pending。
- **delete_merchant**（DELETE `/{id}`）→ 分流（action="delete"）。**执行器 delete 行为变了**：原端点硬性拒绝有价格记录的商家（404/400）；执行器软停用（is_open=False + 名称加 `[已停用]` 前缀）+ 把 ProductRecord.merchant_id 引用置 NULL，不再拒绝。这是有意的行为变更——共享池商家被引用时硬删本就不可能，软停用 + 置空引用是更合理的共享治理。
- 其他端点（create / GET / 收藏 / 排序 / 价格）不动。

### 5. `backend/app/api/ingredient_extended.py`
- **hard_delete_ingredient**（DELETE `/ingredients/{id}/hard`）：**保留管理员直写**（不进分流）。硬删除不可逆、高危，执行器 delete 只软删 is_active=False，语义不符。任务说明允许「hard-delete 保留管理员直写」。

## 未改造项（同模式待续）

| 端点 | 原因 |
|---|---|
| units: conversions / entity_unit_override / entity_density CRUD | 执行器仅覆盖 Unit 模型，未覆盖 UnitConversion/EntityUnitOverride/EntityDensity 多表 |
| nutrition: edit_product_nutrition | 写 Product.custom_nutrition_data，非 NutritionData |
| nutrition: correct_nutrition_mapping | 改 IngredientNutritionMapping，非 NutritionData |
| ingredient_extended: 食材 create/update/delete | 这些端点已有「所有权 + 管理员超级」校验，属个人/半个人数据；按计划菜谱/原料 CRUD 走个人数据语义不进分流 |
| products_entity: 条码/别名/商品营养写入 | 同理，且商品多为用户私有 |

## 测试

### 改造既有测试（`backend/tests/test_permissions_p0.py`）
- 加模块级 autouse fixture `_register_executors`：TestClient 不触发 main.py lifespan，故显式调 `register_all()` 注册业务执行器（重复 register 用 setdefault 不覆盖策略，多次调用安全）。
- `test_units_create_forbidden_for_non_admin` → 改为 `test_units_create_dispatch_non_admin_submits`：unit.create=auto_approve，普通用户提交即生效（200，非 403）。
- `test_nutrition_ingredient_write_forbidden_for_non_admin` → `test_..._dispatch_..._submits`：ingredient 999 不存在 → 执行器 validate 抛 404（校验发生在 submit 之前），合法空 nutrients 列表避免 422。
- hierarchy create/update/delete 三条：普通用户改 submit（manual → 200/pending 或 404 校验先跑），不再 403。
- `test_merge_history_forbidden_for_non_admin`（GET）、`test_nutrition_correct_forbidden`、`test_ingredient_hard_delete_forbidden`：保留管理员直写，仍 403。

### 新增分流测试（`backend/tests/test_shared_data.py`，8 条）
- `test_dispatch_ingredient_merge_admin_applies_directly`：管理员合并 → applied + change_proposals 留痕。
- `test_dispatch_ingredient_merge_non_admin_submits_proposal`：普通用户合并自己食材 → pending，proposer_id=2。
- `test_dispatch_unit_create_admin_applies` / `_non_admin_auto_approve`：管理员直写 / 普通 auto_approve。
- `test_dispatch_hierarchy_create_admin_applies` / `_non_admin_pending`：管理员直写 / 普通 manual 待审。
- `test_dispatch_merchant_update_admin_applies` / `_non_admin_pending`：管理员直写 / 普通 manual 待审。
- 共用 `_clean_proposals` fixture 前后清空 change_proposals；`_seed_ingredients_for_merge` / `_seed_ingredients_for_hierarchy` / `_cleanup_*` 构造/清理前置数据。

### 结果
- `pytest tests/test_permissions_p0.py tests/test_proposals_framework.py tests/test_shared_data.py -v`：**46 passed**（18 P0 + 17 framework + 11 shared）。
- 全量回归 `pytest tests/`：**16 failed / 368 passed**（失败数与改造前基线完全一致——全是 auth/import/locations/recipes/reports/inferrer/sort_score/downloader/format_detector 的预存失败，无新增失败；通过数从基线 360 升到 368，即本次 +8 新测试）。
- py_compile 全部通过。

## 关键设计点

1. **apply_as_admin vs P0 直接改**：管理员路径不再直接 `db.add` + commit，而是经框架 `apply_as_admin` → 执行器 `apply`。好处：管理员操作也进 `change_proposals` 表留痕（status=applied, proposer_id=reviewer_id=admin.id），审计可追；revert 窗口（high risk）7 天内可回滚。代价：多一次 INSERT + 执行器内部 db.flush。
2. **payload 与执行器期望一致**：合并 `{source_ids, target_id}`；CRUD `{field: value}` 或 `{}` delete；hierarchy create 完整列值；nutrition `{nutrients: structured_dict}`。所有 payload 经 API 层预检（唯一性/存在性/fallback 交换）后传给执行器，执行器只做无状态变更。
3. **GET 端点不动**：保持 `get_current_user` 登录可读，符合「共享数据读公开」原则。
4. **个人数据端点不动**：价格记录、菜谱、支出等 user_id 隔离的端点不在本 task 范围。
5. **执行器限制**：CRUD 执行器只覆盖对应 model_class 的简单 CRUD；多表关联操作（换算/覆盖/密度/商品营养）未覆盖，相关端点保留管理员直写。

## 改了哪些文件

- `backend/app/api/ingredient_hierarchy.py`
- `backend/app/api/units.py`
- `backend/app/api/nutrition.py`
- `backend/app/api/merchants.py`
- `backend/tests/test_permissions_p0.py`
- `backend/tests/test_shared_data.py`

无表结构变更，无 alembic / SQL 脚本。
