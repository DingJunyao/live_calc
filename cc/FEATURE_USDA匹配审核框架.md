# USDA 匹配 接入提议-审核框架

> 分支：`feat/multi-user-permissions`
> 日期：2026-07-01
> 上游：[MULTI_USER_PERMISSIONS.md](MULTI_USER_PERMISSIONS.md)、[FEATURE_原料商品改删审核框架.md](FEATURE_原料商品改删审核框架.md)
> 设计：[docs/superpowers/specs/2026-06-30-usda-match-proposals-design.md](../docs/superpowers/specs/2026-06-30-usda-match-proposals-design.md)
> 治理总表依据：「营养数据/映射 | USDA 匹配写入：有数据→人工」

## 背景

USDA 匹配（把 USDA 食材营养数据写入原料/商品）两端点（[usda.py](../backend/app/api/usda.py) match_ingredient/match_product）在 P0 堵漏阶段锁成 `get_current_admin_user`，普通用户 403。治理总表定的是「USDA 匹配写入：有数据→人工」——应放开走审核。本次接入提议-审核框架。

## 三条关键决策

1. **范围：原料 + 商品都放开**。match_ingredient（写 NutritionData）+ match_product（写 custom_nutrition_data）。
2. **策略：有数据 manual / 没数据 auto**（沿用治理总表）。原料/商品已有营养数据→覆盖走人工；无数据→补空自动通过。
3. **补空 auto 用 `service.submit` 的 `policy_override` 参数实现**（端点判断有无数据传 policy）。**不用** nutrition 的 apply 内 set_policy 权宜（那个其实没生效——submit 在 validate 前读 policy，manual 不 apply，set_policy 不执行）。

## 五个 Task 成果

| Task | 内容 |
|---|---|
| 1 | matcher.py 的 match_ingredient/match_product 去 `db.commit()`（改 flush），由调用方 commit。grep 调用方：usda.py 两端点补 commit（保持工作），测试不需（同 session flush 够） |
| 2 | service.submit 加可选 `policy_override` 参数（默认 None 走 registry，向后兼容），端点据此控制补空 auto |
| 3 | 新建 UsdaIngredientMatchExecutor（替换 NutritionData：snapshot 旧全行→调 matcher→revert 删新+插旧）+ UsdaProductMatchExecutor（覆盖 custom_nutrition_data：snapshot 旧值→revert 还原）+ bootstrap 注册（全 manual，补空 auto 由端点 policy_override 覆盖） |
| 4 | usda.py 两端点分流：去 admin 锁，管理员 apply_as_admin / 普通用户 submit（判断有无数据→manual/auto policy_override）+ 集成测试 |
| 5 | UsdaMatchDialog 按角色/status 提示（管理员成功 / 普通用户 pending 蓝色不误报 / 补空 success，pending 不刷新营养）+ ProposalsView entityTypeLabel 补 2 项 + 清理 usda.py dead import |

## 关键技术点

### 1. 替换语义 snapshot/revert（区别于 CRUD update）
USDA 匹配是「替换」（match_ingredient 清空所有 NutritionData + 写一条 USDA 的），不是 update。执行器 apply：snapshot 旧全行 → 调 matcher → revert_payload（旧数据 + fdc_id）；revert：删 USDA 新行（usda_id=fdc_id）+ 插旧行（新 id，NutritionData 叶表无 FK 引用，安全）。

### 2. _restore_row：全行重插的 DateTime 转换
snapshot 用 `_json_safe`（DateTime→isoformat string，入 JSON 列）。但 ingredient revert **重插全行**时，SQLite DateTime 列拒收 isoformat string。加 `_restore_row` 把 timestamp 列（created_at/updated_at/verified_at/edited_at）`datetime.fromisoformat` 转回。**任何「全列 snapshot + 重插」的执行器都会踩这个坑**（ingredient merge 等手写字段 snapshot 不含 DateTime 故不受影响）。

### 3. policy_override：补空 auto 的正确实现
service.submit 加 `policy_override: Optional[str] = None`。端点判断原料/商品有无数据：有→`policy_override="manual"`（pending）；无→`"auto_approve"`（立即 apply）。可选参数默认 None 走 registry，**不破坏现有调用**。比 nutrition 的 apply 内 set_policy（不生效的权宜）干净。

### 4. matcher 去 commit
match_ingredient/match_product 去 db.commit（改 flush），执行器 apply 不违反框架「只 flush」约定，调用方（端点/API）commit。

## 文件清单

### 后端新增
- `app/services/proposals/executors/usda_ingredient_match.py`
- `app/services/proposals/executors/usda_product_match.py`
- `tests/test_usda_match_proposals.py`

### 后端修改
- `app/services/usda/matcher.py`（match_ingredient/match_product 去 commit）
- `app/services/proposals/service.py`（submit 加 policy_override）
- `app/services/proposals/bootstrap.py`（注册两执行器）
- `app/api/usda.py`（两端点分流 + 清 dead import）

### 前端修改
- `components/usda/UsdaMatchDialog.vue`（按角色提示）
- `views/admin/ProposalsView.vue`（entityTypeLabel 补 USDA 原料/商品匹配）

## 测试

- policy_override 3 + 执行器 apply/revert 6 + 端点分流 4（admin 即时 / 补空 auto / 有数据 manual / 商品）= 相关测试 **13 + 全量回归 80 passed**
- 端到端：管理员即时；普通用户无数据→补空 auto applied；普通用户有数据→manual pending（不覆盖旧数据）
- 前端 `npm run build` 通过

## 不在范围 / 已知妥协

- **nutrition 端点的补空 auto 仍未真正生效**（apply 内 set_policy 权宜，CLAUDE.md 已标注）。本次 USDA 匹配用 policy_override 正确实现，nutrition 可后续统一迁移到 policy_override。
- USDA 数据下载/上传/翻译（管理员级，不动）。
- 商品营养的其他写入路径（correct 等，未分流）。
