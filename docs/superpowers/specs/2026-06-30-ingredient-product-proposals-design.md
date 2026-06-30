# 原料/商品 改删 + 层级提示 接入提议-审核框架 设计

> 日期：2026-06-30
> 分支：`feat/multi-user-permissions`
> 上游：[MULTI_USER_PERMISSIONS.md](../../../cc/MULTI_USER_PERMISSIONS.md)、[FEATURE_实体单位密度审核框架.md](../../../cc/FEATURE_实体单位密度审核框架.md)
> 配套计划：[docs/superpowers/plans/2026-06-30-ingredient-product-proposals.md](../plans/2026-06-30-ingredient-product-proposals.md)（下一步生成）

## 1. 背景

多用户权限系统已完成主体改造，但仍有两类遗留问题（用户反馈）：

1. **普通用户修改、删除原料、商品时提示「无权修改」**：原料/商品的 update/delete 端点（[ingredient_extended.py](../../../backend/app/api/ingredient_extended.py) / [products_entity.py](../../../backend/app/api/products_entity.py)）仍是「`created_by` 限制」语义——普通用户只能改/删自己创建的，改他人的返回 403。这与「客观存在共享池，所有人可提议审核」（治理总表 ingredient/product 编辑删除 = manual）的定位不符，是 P2 共享转型的遗漏（端点未分流）。
2. **食材层级关系前端提示误导**：后端 [ingredient_hierarchy.py](../../../backend/app/api/ingredient_hierarchy.py) 的 create/update/delete 已分流（manual），但前端 [IngredientDetail.vue](../../../frontend/src/views/ingredients/IngredientDetail.vue) 的层级维护函数统一提示「成功」，普通用户实际待审却看到「成功」。

本次：放开原料/商品 update+delete 给普通用户走审核框架（manual），并修复层级关系前端提示。

## 2. 现状

### 2.1 原料 update/delete（[ingredient_extended.py](../../../backend/app/api/ingredient_extended.py)）

- `update_ingredient`（[ingredient_extended.py:527](../../../backend/app/api/ingredient_extended.py#L527)）：前端 `PUT /ingredients/{id}` 调用。`get_current_user` + 手写 `created_by` 检查（非创建者非管理员 → 403「无权修改此食材」）+ `is_imported` 限制。**直接改库，未走框架**。端点是个超大端点，除基本字段外内嵌 nutrition 营养数据处理（L590+）——但前端基本信息编辑 payload 不含 nutrition（走独立营养编辑区块）。
- 原料删除：前端实际调用 **[nutrition.py:531](../../../backend/app/api/nutrition.py#L531) `soft_delete_ingredient`**（`DELETE /nutrition/ingredients/{id}`）——`created_by` 检查 + 403「无权删除此原料」，**级联软删**（菜谱引用检查 + 软删其下 Product + 软删 IngredientHierarchy parent/child + 软删 ingredient），未走框架。`ingredient_extended.py:948` 也有同名端点（`/ingredients/{id}`）但前端不用。
- `hard_delete_ingredient`（[ingredient_extended.py:714](../../../backend/app/api/ingredient_extended.py#L714)）：`get_current_admin_user` 仅管理员，硬删，**保持不变**（高危不可逆，不进框架）。

### 2.2 商品 update/delete（[products_entity.py](../../../backend/app/api/products_entity.py)）

- `update_product`（L358）：`created_by` 检查 + 403「无权修改此商品」。barcode 唯一检查、tags 序列化、updated_by。**直接改库，未走框架**。
- `delete_product`（L410）：`created_by` 检查 + 403「无权删除此商品」。**唯一商品检查**（原料的唯一商品不能删）+ 软删 Product + **级联软删其 ProductRecord**。未走框架。

### 2.3 执行器现状

- `IngredientExecutor`（[ingredient.py](../../../backend/app/services/proposals/executors/ingredient.py)）：继承 CrudExecutorBase，支持 create/update/delete/merge。**delete 走基类（软删 is_active=False），不级联**——与现状 soft_delete_ingredient 的级联不一致。bootstrap 已注册（update/delete/merge = manual）。
- **无 ProductExecutor**：`executors/` 目录无 product.py，bootstrap 未注册 product entity_type。Product 模型（`Product(Base, AuditMixin)`）有 is_active。

### 2.4 前端提示现状

- 原料基本信息编辑（[IngredientDetail.vue saveBasicInfo](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3549)）：payload 只含基本信息（name/default_unit_id/category_id/aliases/serving_weight/serving_weight_unit_id），**不含 nutrition**（nutrition 走独立的「营养成分内联编辑」区块）。成功提示「基本信息已保存」。
- 商品基本信息编辑（[ProductDetail.vue saveBasicInfo](../../../frontend/src/views/products/ProductDetail.vue#L2309)）：payload 含 name/brand/barcode/ingredient_id/tags/aliases，不含 nutrition。成功提示「基本信息已保存」。
- 层级关系（[IngredientDetail.vue](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3194) add/edit/delete）：成功提示「关系添加/更新/删除成功」，**不区分角色**（后端已分流，前端误报成功）。

## 3. 关键决策（2 条）

1. **update 只基本信息走提议**：原料/商品的 update 提议只承载基本信息字段。nutrition 不走这个提议——营养数据已有独立的 `NutritionExecutor`（营养审核），普通用户改营养走那条路。前端基本信息编辑 payload 天然不含 nutrition，**前端 payload 零改动**。
2. **delete 完整反级联**：delete 走框架后，执行器 apply 复刻现状级联（原料→商品+层级关系；商品→价格记录），revert 时按 snapshot 反级联复活（主记录 + 子记录）。现状是软删（is_active=False），反级联即复活（is_active=True），不丢数据，保证回滚一致性。

## 4. 设计详述

### 4.1 节 A：后端执行器

**新建 `ProductExecutor`**（`executors/product.py`，继承 CrudExecutorBase）：
- `entity_type = "product"`，`model_class = Product`
- validate：update/delete 校验目标存在且 `is_active=True`（参照 entity_unit_override）
- update：吃基类（setattr 基本字段）
- delete：**覆写 apply**——唯一商品检查（原料的唯一活跃商品拒删）+ 软删 Product + 级联软删其 ProductRecord（is_active=False）+ snapshot（含主记录全列 + 级联 ProductRecord 的 id 列表）；**覆写 revert**——按 snapshot 复活 Product（is_active=True）+ 复活级联 ProductRecord

**`IngredientExecutor` 覆写 delete**（加级联）：
- 现状 delete 吃 CrudExecutorBase（不级联），需覆写
- apply：菜谱引用检查（有引用拒删）+ 软删 ingredient + 级联软删其 Product + IngredientHierarchy（parent/child）+ snapshot（主记录 + 级联 Product id + Hierarchy id）
- revert：反级联复活 ingredient + Product + Hierarchy
- update/merge 逻辑不变（update 吃基类 setattr 基本字段）

**bootstrap 注册 ProductExecutor**：`default_policy="manual"`（update/delete 全 manual）。ingredient 已注册（update/delete=manual），无需改策略。

### 4.2 节 B：端点分流（4 个，去掉 created_by 限制）

通用模式：`if current_user.is_admin: apply_as_admin else: submit`（参照单位 CRUD、entity_unit_override/density）。

| 端点 | 提议 | payload | 备注 |
|---|---|---|---|
| `update_ingredient`（ingredient_extended:527） | ingredient update | 基本信息字段（model_dump(mode="json") 防 Decimal） | nutrition 参数保留但不进提议（前端不传）；去掉 created_by/is_imported 限制；name 唯一在端点提交时查 |
| `soft_delete_ingredient`（**nutrition:531**，前端实际调用） | ingredient delete | `{}` | 去掉 created_by；菜谱引用检查在端点提交时 + 执行器 apply 时双层查 |
| `update_product`（products_entity:358） | product update | 基本信息字段 | 去掉 created_by；barcode 唯一、tags 序列化在端点提交时做，payload 带 updated_by |
| `delete_product`（products_entity:410） | product delete | `{}` | 去掉 created_by；唯一商品检查在端点提交时 + 执行器 apply 时双层查 |

- `hard_delete_ingredient` 保持 `get_current_admin_user`（仅管理员，不进框架）。
- `updated_by`：payload 带 `updated_by=current_user.id`（普通用户提交时即 proposer，管理员即 admin），执行器 setattr。
- **双层业务检查**：菜谱引用（原料删除）、唯一商品（商品删除）等「业务前置条件」在端点提交时 **和** 执行器 apply 时都查，防审核期间状态变化。
- 响应：管理员 apply_as_admin 即时返回对象；普通用户 submit（manual 待审）返回占位/原对象（参考 entity_unit_override 模式）。

### 4.3 节 C：前端提示（任务 1 + 任务 2）

参考刚做的 entity_unit_override/density 模式（`userStore.user?.is_admin` 分支）：

- **任务 1**：
  - [IngredientDetail saveBasicInfo](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3549)（基本信息保存）+ 删除原料函数：按角色提示
  - [ProductDetail saveBasicInfo](../../../frontend/src/views/products/ProductDetail.vue#L2309)（基本信息保存）+ 删除商品函数：按角色提示
- **任务 2**：
  - [IngredientDetail 层级 add/edit/delete](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3194)：按角色提示
- 统一文案：管理员「保存/删除成功」+刷新；普通用户「已提交，待管理员审核」/「删除提议已提交，待管理员审核」+不刷新列表（待审数据不在列表）

### 4.4 节 D：测试

- ProductExecutor delete 级联（ProductRecord 软删）+ revert 反级联（复活）
- IngredientExecutor delete 级联（Product + Hierarchy 软删）+ revert 反级联
- 4 端点分流：管理员 apply_as_admin 即时；普通用户 submit → manual 待审（列表不出现待定值）
- 双层业务检查（菜谱引用/唯一商品）
- 前端 npm run build

## 5. 关键文件

### 后端新增
- `backend/app/services/proposals/executors/product.py`

### 后端修改
- `backend/app/services/proposals/executors/ingredient.py`（delete 覆写加级联）
- `backend/app/services/proposals/bootstrap.py`（注册 ProductExecutor）
- `backend/app/api/ingredient_extended.py`（原料 update 分流）
- `backend/app/api/nutrition.py`（原料 delete 分流，L531 soft_delete_ingredient）
- `backend/app/api/products_entity.py`（商品 update/delete 分流）

### 前端修改
- `frontend/src/views/ingredients/IngredientDetail.vue`（基本信息+删除+层级提示）
- `frontend/src/views/products/ProductDetail.vue`（基本信息+删除提示）

## 6. 不在范围

- 原料/商品的 **create**：现状普通用户可创建（created_by=自己），治理总表 create=auto。本次不动 create（用户只提修改/删除）。
- nutrition 营养数据编辑：走独立的 NutritionExecutor，不在本次 update 提议范围。
- 原料 hard_delete：保持仅管理员（高危不可逆）。
- 商品 barcode/tags 的独立管理端点：不动（本次只 update/delete 主体）。

## 7. 风险与权衡

1. **审核期间状态变化**：manual 审核有延迟，提交时无冲突但审核时可能冲突（如别人先改了同名/同 barcode）。双层检查（提交 + apply）兜底；极端冲突时 apply 抛错，管理员在审核台看到失败。可接受。
2. **delete 反级联复杂度**：snapshot 级联行 + revert 复活，工作量中等。但软删/复活不丢数据，保证回滚一致性。
3. **放开 created_by 的语义变化**：现状普通用户只能改自己创建的；改后任何普通用户可提议改任何原料/商品（管理员审核把关）。符合「共享池」语义。数据 created_by 不因提议改变（提议者记在 change_proposals.proposer_id）。
