# USDA 匹配 接入提议-审核框架 设计

> 日期：2026-06-30
> 分支：`feat/multi-user-permissions`
> 上游：[MULTI_USER_PERMISSIONS.md](../../../cc/MULTI_USER_PERMISSIONS.md)、[FEATURE_原料商品改删审核框架.md](../../../cc/FEATURE_原料商品改删审核框架.md)
> 治理总表依据：[2026-06-27-multi-user-permissions-design.md](./2026-06-27-multi-user-permissions-design.md)「营养数据/映射 | USDA 匹配写入：有数据→人工」

## 1. 背景

USDA 匹配（把 USDA 食材营养数据写入原料/商品）的两个端点在 P0 堵漏阶段被锁成 `get_current_admin_user`，普通用户 403。但治理总表定的是「USDA 匹配写入：有数据→人工」——应放开走审核。这是 P2 共享转型的遗漏（端点未分流），同 entity_unit_override/density、原料/商品改删。

## 2. 现状

### 2.1 端点（[usda.py](../../../backend/app/api/usda.py)）
- `match_ingredient_endpoint`（L84，`POST /usda/match/ingredient/{id}`）：`get_current_admin_user` 仅管理员 → 普通用户 403
- `match_product_endpoint`（L95，`POST /usda/match/product/{id}`）：同

### 2.2 写入逻辑（[matcher.py](../../../backend/app/services/usda/matcher.py)）
- `match_ingredient(db, ingredient_id, fdc_id)`（L183）：**替换语义**——清空该原料所有 NutritionData + 写一条新的（source=usda_manual_match, is_verified=True, nutrients, usda_id, usda_name）。内部 `db.commit()`。
- `match_product(db, product_id, fdc_id)`（L213）：写 `Product.custom_nutrition_data`（复制原料骨架 + USDA 覆盖）。内部 `db.commit()`。

### 2.3 nutrition 的「补空 auto」未真正生效
[edit_ingredient_nutrition](../../../backend/app/api/nutrition.py#L1421) 注释称「执行器 apply 内动态 set_policy（补空→auto）」，但 `service.submit` 在 validate 前就读取 policy（默认 manual），manual 提议不 apply，故 set_policy 不执行——补空实际也 manual pending。属 CLAUDE.md 标注的已知妥协（「nutrition set_policy 权宜…建议落 system_config」）。USDA 匹配需用正确机制实现补空 auto。

## 3. 关键决策（3 条）

1. **范围：原料 + 商品都放开**。match_ingredient（写 NutritionData）+ match_product（写 custom_nutrition_data）两个端点都接入审核，与治理总表「营养数据/映射」一致。
2. **策略：有数据 manual / 没数据 auto**（沿用治理总表）。原料/商品已有营养数据 → 覆盖走人工审核；无数据 → 补空自动通过。
3. **补空 auto 用 `service.submit` 的 `policy_override` 参数实现**（而非 nutrition 的 apply 内 set_policy 权宜）。端点判断有无数据，传 policy_override 控制。

## 4. 设计详述

### 4.1 节 A：matcher 去 commit

[matcher.py](../../../backend/app/services/usda/matcher.py) 的 `match_ingredient` / `match_product` 去掉内部 `db.commit()`（保留 `db.flush()` 拿新建行的 id）。由调用方（端点/执行器）commit。这样执行器 apply 不违反框架「只 flush，API 层 commit」约定，也避免 apply 内 commit 导致 proposal 提前落库的混乱。

> 现有端点（管理员直写路径）调用后需自行 `db.commit()`。

### 4.2 节 B：两个新执行器

**`UsdaIngredientMatchExecutor`**（`entity_type="usda_ingredient_match"`，继承 ProposalExecutor）：
- validate：原料存在 + fdc_id 对应 USDA food 存在
- apply：snapshot 该原料所有旧 NutritionData（全字段）→ 调 `match_ingredient`（清空+写新）→ revert_payload（旧数据列表 + 新行 usda_id）
- revert：删新行（按 usda_id=fdc_id）+ 插旧行（snapshot 全字段，新 id；NutritionData 是叶表无外键引用，id 变化无影响）
- entity_label：「原料「{name}」USDA 匹配」

**`UsdaProductMatchExecutor`**（`entity_type="usda_product_match"`，继承 ProposalExecutor）：
- validate：商品存在 + fdc_id 有效
- apply：snapshot 旧 `Product.custom_nutrition_data`（JSON 值）→ 调 `match_product`（覆盖）→ revert_payload（旧值）
- revert：还原 `Product.custom_nutrition_data` = 旧值
- entity_label：「商品「{name}」USDA 匹配」

> 两执行器不继承 CrudExecutorBase（USDA 匹配是「替换」语义，非标准 CRUD；apply 调 matcher，snapshot/revert 自定义）。snapshot 用 `_json_safe`（Decimal/date 入 JSON 列兜底）。

### 4.3 节 C：service.submit 加 policy_override

[service.py](../../../backend/app/services/proposals/service.py) 的 `submit` 加可选参数：
```python
def submit(db, *, entity_type, entity_id, action, payload, proposer, policy_override=None):
    ...
    policy = policy_override or ExecutorRegistry.policy_for(entity_type, action)
    ...
```
可选参数，默认 None 走 registry（**不破坏现有调用**）。端点据此实现补空 auto（无数据传 "auto_approve" → submit 内立即 apply；有数据传 "manual" 或不传 → pending）。

> apply_as_admin 不需要 policy_override（管理员直写，固定 auto_approve + applied）。

### 4.4 节 D：端点分流（[usda.py](../../../backend/app/api/usda.py)）

两个端点去 `get_current_admin_user`，改 `get_current_user` + 分流：
- 管理员：`apply_as_admin`（即时生效）+ db.commit
- 普通用户：判断原料/商品有无现有营养数据：
  - 有数据 → `submit(policy_override="manual")` → pending 待审
  - 无数据 → `submit(policy_override="auto_approve")` → 立即 applied（补空自动通过）
- 返回消息区分（applied / pending）

### 4.5 节 E：bootstrap 注册两执行器

[bootstrap.py](../../../backend/app/services/proposals/bootstrap.py) 注册 `UsdaIngredientMatchExecutor` + `UsdaProductMatchExecutor`，`default_policy="manual"`（补空 auto 由端点 policy_override 覆盖，不走 registry 默认）。

### 4.6 节 F：前端 UsdaMatchDialog 按角色提示

[UsdaMatchDialog.vue](../../../frontend/src/components/usda/UsdaMatchDialog.vue) 匹配成功后按角色提示：管理员「匹配成功」+ 刷新；普通用户按后端返回 status——applied（补空）「匹配成功（补空自动通过）」/ pending「已提交，待管理员审核」。读后端返回的 message 或 status 区分。

### 4.7 节 G：测试

- 执行器 apply/revert：ingredient（替换 NutritionData + 回滚还原）、product（覆盖 custom_nutrition_data + 回滚）
- 端点分流：管理员即时；普通用户有数据 → manual pending；普通用户无数据 → auto applied
- bootstrap 注册验证
- entity_label 含原料/商品名

## 5. 关键文件

### 后端新增
- `backend/app/services/proposals/executors/usda_ingredient_match.py`
- `backend/app/services/proposals/executors/usda_product_match.py`
- `backend/tests/test_usda_match_proposals.py`

### 后端修改
- `backend/app/services/usda/matcher.py`（match_ingredient/match_product 去 commit）
- `backend/app/services/proposals/service.py`（submit 加 policy_override）
- `backend/app/api/usda.py`（两端点分流）
- `backend/app/services/proposals/bootstrap.py`（注册两执行器）

### 前端修改
- `frontend/src/components/usda/UsdaMatchDialog.vue`（按角色提示）

## 6. 不在范围

- nutrition 端点的补空 auto 修复（已知妥协，本次只给 USDA 匹配用 policy_override 正确实现；nutrition 可后续统一）
- USDA 数据下载/上传/翻译（已是管理员级，不动）
- 商品营养的其他写入路径（correct 等，CLAUDE.md 标注未分流，本次不动）

## 7. 风险与权衡

1. **matcher 去 commit 影响现有调用方**：match_ingredient/match_product 去 commit 后，所有调用方（端点管理员直写 + 执行器）需自行 commit。本期改造覆盖两端点 + 执行器；若有其他调用方（如导入脚本）需排查补 commit。
2. **替换语义 revert 的 id 变化**：ingredient revert 重插旧 NutritionData 会用新 id（旧 id 被 delete）。NutritionData 是叶表无外键引用，安全。但若未来有表引用 NutritionData.id 需重新评估。
3. **policy_override 是框架小改**：给 submit 加可选参数，默认 None 不影响现有。比 nutrition 的 apply 内 set_policy 权宜干净，但改了核心 service 签名（向后兼容）。
4. **补空 auto 的判断时机**：端点在提交时查「有无数据」。提交到审核期间若数据变化（别的提议），apply 时执行器不再复查（USDA 匹配是替换，不依赖现有数据状态）。可接受。
