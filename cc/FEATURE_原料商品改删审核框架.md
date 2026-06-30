# 原料/商品 改删 + 层级提示 接入提议-审核框架

> 分支：`feat/multi-user-permissions`
> 日期：2026-06-30
> 上游：[MULTI_USER_PERMISSIONS.md](MULTI_USER_PERMISSIONS.md)、[FEATURE_实体单位密度审核框架.md](FEATURE_实体单位密度审核框架.md)
> 设计：[docs/superpowers/specs/2026-06-30-ingredient-product-proposals-design.md](../docs/superpowers/specs/2026-06-30-ingredient-product-proposals-design.md)
> 计划：[docs/superpowers/plans/2026-06-30-ingredient-product-proposals.md](../docs/superpowers/plans/2026-06-30-ingredient-product-proposals.md)

## 背景

多用户权限系统主体完成后，两类遗留（用户反馈）：
1. 普通用户修改、删除原料、商品时提示「无权修改」（403）——原料/商品 update/delete 端点仍是 `created_by` 限制（只能改自己创建的），未走审核框架，与「客观存在共享池，所有人可提议审核」（治理总表 ingredient/product 编辑删除 = manual）不符，是 P2 遗漏。
2. 食材层级关系前端提示误导——后端已分流（manual），前端统一提示「成功」，普通用户实际待审却看到「成功」。

本次：放开原料/商品 update+delete 给普通用户走审核（全 manual + 管理员直写即时 + delete 完整反级联），修复层级关系前端提示。

## 两条关键决策

1. **update 只基本信息走提议**：原料/商品 update 提议只承载基本信息字段（前端基本信息编辑 payload 天然不含 nutrition），nutrition 走独立的 NutritionExecutor。`update_ingredient` 的 nutrition 处理段保留不动（前端不传，实际不触发）。
2. **delete 完整反级联**：执行器 apply 复刻现状级联（原料→商品+层级关系；商品→价格记录），revert 按 snapshot 反级联复活（主记录 + 子记录）。软删/复活不丢数据。

## 五个 Task 成果

| Task | 内容 |
|---|---|
| 1 | 新建 `ProductExecutor`（继承 CrudExecutorBase，update 吃基类，delete 覆写：唯一商品检查 + 软删 Product + 级联软删 ProductRecord + snapshot + revert 反级联） |
| 2 | `IngredientExecutor` delete 覆写加级联（菜谱引用检查 + 软删 ingredient + 级联 Product + IngredientHierarchy parent/child + snapshot + revert 反级联）+ 顺手对齐 product.py snapshot 时序 |
| 3 | bootstrap 注册 ProductExecutor（全 manual） |
| 4 | 4 端点分流去 created_by（商品 update/delete + 原料 update/delete）+ ingredient_extended:949 旧 soft_delete 对齐接入分流 + 清理重复 import |
| 5 | 前端 7 处按角色提示（基本信息/删除/层级）+ build |

## 关键技术点

### 1. delete 级联 + 反级联（snapshot/revert）
- 商品 delete：软删 Product + 级联软删其 ProductRecord；snapshot 存 `_cascade_record_ids`；revert 按 id 复活两者
- 原料 delete：菜谱引用检查（有引用拒删）+ 软删 ingredient + 级联软删 Product + Hierarchy（parent/child 双向）；snapshot 存 `_cascade_product_ids`/`_cascade_hierarchy_ids`；revert 按 id 反级联复活
- snapshot 用 `_json_safe`（防 Decimal/date 入 JSON 列）+ **在置 is_active=False 之前**（对齐基类 _crud_base.py:81 顺序）

### 2. 双层业务检查
唯一商品（商品删除）、菜谱引用（原料删除）在**端点提交时**和**执行器 apply 时**都查——端点提交时拒（400）不产生 pending 提议（防审核期间状态变化绕过）。

### 3. 两个 soft_delete_ingredient 对齐
历史遗留：`ingredient_extended.py:949`（路由 `DELETE /api/v1/ingredients/{id}`）和 `nutrition.py:531`（`DELETE /api/v1/nutrition/ingredients/{id}`，前端实际调用）两个同名函数。本次两个都接入分流（去 created_by + 走提议 + 去内联级联由执行器做），逻辑一致，消除漂移。

### 4. update_ingredient nutrition 段保留
`update_ingredient`（ingredient_extended）是超大端点（基本信息 + nutrition 处理）。分流只改基本信息段（构造 payload + submit/apply_as_admin），**nutrition 处理段完整保留**（前端不传，不触发）。分流后 `db.refresh(ingredient)` 让 nutrition 段读最新。

### 5. 两个执行器都继承 CrudExecutorBase
update 吃基类 setattr；delete 覆写（级联 + snapshot + 反级联）。`_json_safe` 复用（与实体单位覆盖/密度一致）。

## 文件清单

### 后端新增
- `app/services/proposals/executors/product.py`（ProductExecutor）
- `tests/test_product_ingredient_proposals.py`（执行器+端点测试）
- `tests/test_product_ingredient_e2e.py`（端到端 11 测试）

### 后端修改
- `app/services/proposals/executors/ingredient.py`（delete 覆写加级联）
- `app/services/proposals/executors/product.py`（snapshot 时序对齐——Task 2 顺手）
- `app/services/proposals/bootstrap.py`（注册 ProductExecutor）
- `app/api/products_entity.py`（商品 update/delete 分流）
- `app/api/ingredient_extended.py`（原料 update 分流 + :949 soft_delete 对齐）
- `app/api/nutrition.py`（原料 delete 分流 + 清理重复 import）

### 前端修改
- `views/ingredients/IngredientDetail.vue`（saveBasicInfo/deleteIngredient/层级 add/edit/delete 5 处）
- `views/products/ProductDetail.vue`（saveBasicInfo/deleteProduct 2 处）

## 测试

- 执行器 4（Product/Ingredient cascade+revert/拒删）+ 端点 5（admin 即时/non-admin 待审）+ 注册 1 + e2e 11 = 相关测试 **90 passed, 0 failed**
- 端到端链路：普通用户改/删→pending→管理员审核通过→applied（级联生效）→管理员回滚→reverted（反级联复活）；双层检查端点即拒
- 前端 `npm run build` 通过

## 已知遗留（非阻断）

- `nutrition.py:482` 的旧 `update_ingredient`（`PUT /api/v1/nutrition/ingredients/{id}`）是影子路由——前端走 `ingredient_extended.update_ingredient`（`PUT /ingredients/{id}`，已分流），这条不用，仍旧 created_by 直接写。不影响功能（前端不调），若要彻底清洁可后续删除或接入分流。

## 后续修复与增强（2026-06-30 用户反馈）

### 修复 1+2：IngredientDetail 商品编辑/删除按角色提示（Task 5 遗漏）
Task 5 只改了 ProductDetail 的商品编辑，**漏了 IngredientDetail 里编辑/删除关联商品的入口**（[saveProduct:1876](../frontend/src/views/ingredients/IngredientDetail.vue#L1876)「商品已更新」、[deleteProduct:1914](../frontend/src/views/ingredients/IngredientDetail.vue#L1914)「商品已删除」+ 提前移除列表）。后端分流本就对（普通用户 submit 待审），但前端误报「已更新/已删除」、且 deleteProduct 普通用户待审却移除了列表。修复：两函数按 `userStore.user?.is_admin` 分支（管理员原行为，普通用户「已提交待审」+ 不更新/不移除列表）。

### 增强 3：审核台变更内容改 diff
审核 delete 提议看不到原内容（payload 是 `{}` + snapshot 仅 apply 时填、pending 为空）。增强：
- **后端 framework**：`CrudExecutorBase` 加 `build_snapshot(db, proposal)`（update 算 payload 字段旧值、delete 算全列、create/其他返回 `{}`）；`service.submit` 在 validate 后用 `getattr(executor, "build_snapshot", None)` 预填 `proposal.snapshot`（try/except 兜底，特殊执行器如 NutritionExecutor 不继承 CrudExecutorBase 自动跳过）；`ProposalResponse` 加 `snapshot` 字段返回。apply 时 `_do_apply` 仍覆盖（保证 apply 前最新值），manual pending 保持提交时预填的 before。
- **前端审核台**：[ProposalsView.vue](../frontend/src/views/admin/ProposalsView.vue) 详情区从单 payload pre 块改成 before→after 字段对比 diff 表（`diffRows` 合并 snapshot+payload 键、过滤 `_` 前缀内部字段、分类 added/removed/changed/unchanged 着色；update 旧→新高亮、delete 显示原内容标「将删除」、create 标「将新增」）。
- 测试：snapshot 预填（delete/update）+ ProposalResponse 序列化 3 测试，13 passed；前端 build 通过。

### 增强 4：审核台显示目标实体名称（entity_label）
审核 diff 时 `entity_type/entity_id` 看不出是什么实体（如 entity_unit_override 的 `payload.entity_id=123` 是哪个原料/商品）。增强：
- **执行器 entity_label**：`ProposalExecutor` ABC 加 `entity_label(db, proposal) -> Optional[str]`（默认 None）；`CrudExecutorBase` 覆写（按 entity_id 查 model 的 name/title/username）；特殊执行器覆写——entity_unit_override（业务实体 ingredient/product 名 + unit_name）、entity_density（业务实体名 + condition）、hierarchy（父子食材名）、nutrition（食材名）、merchant_merge/ingredient merge（源/目标名）、recipe_publish/recipe_edit（菜谱名）。
- **ProposalResponse** 加 `entity_label` 字段；`proposals.py` 的 `_to_response` 序列化时调执行器 entity_label 填充（try/except 兜底，list/get/submit/review/revert 都填）。
- **前端审核台**：列表 `payloadSummary` 前置 entity_label（如「原料「鸡蛋」单位「盒」 · name: 鸡蛋」）+ 详情顶部 v-alert 醒目显示「目标实体」。null 时优雅降级（不显示）。
- 测试：entity_label（product/unit_override）+ ProposalResponse 序列化 3 测试，16 passed；前端 build 通过。

### 修复 5：密度数值不显示（Decimal 序列化为 string）
商品/原料详情页密度数值不显示。根因：后端 `EntityDensityResponse.density` 是 Decimal，**Pydantic v2 序列化到 JSON 默认输出为 string**（实测 `{"density":"2254.273","confidence":"1.0",...}`），前端 `displayDensityValue` 严格 `typeof density !== 'number'` → 永远返回空字符串。修复：前端 `loadDensity` 加载时 `Number(d.density)` 转换 + `displayDensityValue`/`openDensityDialog` 用 `Number()` 兜底（兼容 string/number，isNaN 返回空）。两文件（[IngredientDetail](../frontend/src/views/ingredients/IngredientDetail.vue) / [ProductDetail](../frontend/src/views/products/ProductDetail.vue)）各 3 处，build 通过。
> 注：其他 Decimal 字段（confidence 等）同理序列化为 string。本次仅修密度显示路径；若别处有 typeof 严格检查需同样兜底。更彻底的做法是后端把 Decimal 字段序列化为 number（float），但影响所有 Decimal 字段、范围大，未做。

### 修复 6：营养/商家编辑前端提示遗漏（2026-07-01 用户反馈）
普通用户编辑原料营养数据（走 manual 审核）时，前端固定「营养数据已保存」误报成功。排查「走审核写操作 + 前端固定成功」的同款遗漏：
- **[IngredientDetail saveNutritionEdit](../frontend/src/views/ingredients/IngredientDetail.vue#L3762)**：读后端 `edit_ingredient_nutrition` 返回的 message 区分——pending（有数据）→ info「已提交，待管理员审核」+ 不刷新（营养未落地）；管理员直写 / 补空自动通过 → success「已保存」+ 刷新。
- **[MerchantsView saveItem 商家编辑](../frontend/src/views/data/MerchantsView.vue#L594)**：同款遗漏，修。按 `userStore.user?.is_admin` 区分（管理员 success 刷新 / 普通用户 info「编辑提议已提交，待审核」不刷新）。注：`update_merchant` 后端对管理员/普通用户都返回商家对象（无 message），故用角色判断而非 message。
- **已正确不用动**：食材层级 create/update/delete、商品实体 edit/create/delete、食材合并、商品拆分（都读审核状态/message 分流）；商家删除（已读 message）；admin-only 页面（单位 UnitsView、USDA admin，普通用户不访问）。
- **遗留**：商品营养端点 `edit_product_nutrition`（[nutrition.py:1489](../backend/app/api/nutrition.py#L1489)）锁 `get_current_admin_user`，普通用户编辑商品营养 → 403（不是「审核时误报成功」，是根本不能编辑）。若要放开需单独改造（端点分流 + 商品营养执行器）。

## 执行方式

subagent-driven-development：每 task 派 implementer + 两阶段 review（spec + 质量）。Task 4 review 抓出 ingredient_extended:949 旧 soft_delete 漂移（Important）后 fix 对齐；Task 2 review 提出 snapshot 时序防御性建议，顺手对齐 product.py。全程不 commit，每 task 以测试通过 + py_compile/build 为准。
