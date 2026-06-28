# 多用户权限系统

> 分支：`feat/multi-user-permissions`（29 commit，未合并到 master，待 review）
> 日期：2026-06-28

## 背景

系统需支持多用户，但原实现按「单用户（管理员）」心智编写，权限管控缺失/过松/共享数据归属含糊。本次改造建立完整的多用户权限体系。

- 设计文档：[docs/superpowers/specs/2026-06-27-multi-user-permissions-design.md](../docs/superpowers/specs/2026-06-27-multi-user-permissions-design.md)
- 实现计划：[docs/superpowers/plans/2026-06-27-multi-user-permissions.md](../docs/superpowers/plans/2026-06-27-multi-user-permissions.md)

## 核心决策（8 条）

1. **愿景**：全面社区共建。价格公开聚合，支出/购买私有且不可反推
2. **菜谱**：自创默认私有；发布需管理员审核；发布后共建共编；作者不可撤回/删除，管理员可删
3. **商家**：转共享池，「收藏」替代私有归属；新增自由、改/删走审核
4. **审核者**：仅管理员
5. **审核策略三档**：auto_approve / auto_review / manual，预留 `ProposalAutoReviewer` 接口
6. **合并**：人工审核 + 影响预览 + 待审互斥 + 回滚窗口
7. **价格匿名化**：唯一硬约束——对外输出剥离 `record_type` 与 `user_id`
8. **落地架构**：通用 `change_proposals` 表 + 类型执行器
9. **管理员超级权限**：管理员所有写操作直写、绕过框架、菜谱创建即发布（单用户场景零负担）

## 六桶数据分类

| 桶 | 数据 | 权限 |
|---|---|---|
| ① 个人私密 | 支出、购买记录、地点、偏好、黑名单、商家排序、每日推荐 | 仅本人 |
| ② 价格公开聚合 | ProductRecord（去标识） | 所有人可见，本人录 |
| ③ 客观存在共享池 | 商家、商品、食材、分类 | 所有人可见，提议审核 |
| ④ 共享知识库 | 营养、单位、层级、合并 | 所有人可见，提议审核 |
| ⑤ 公开内容 | 菜谱（发布后） | 所有人可见，共建共编 |
| ⑥ 管理员专属 | 用户管理、邀请码、配置、Agent、导入、USDA、标准单位 | 仅管理员 |

## 四阶段实现

### P0 堵漏（11 commit）
- 收紧共享写：units/nutrition/usda/ingredient_hierarchy/extended/products_entity → `get_current_admin_user`
- 越权读修复：export scope=full 限管理员；recipes images 可见性校验（修了 HTTPException 被 try/except 吞为 500 的 bug）
- 路由遮蔽修复：ingredient_hierarchy.router 提前（merge-history 等曾被 extended 的 GET /{id} 吞）
- 统一手动 is_admin → Depends(get_current_admin_user)
- 测试：`tests/test_permissions_p0.py`（as_admin/as_non_admin fixture 在 conftest）

### P1 通用提议-审核框架（6 commit）
- `models/change_proposal.py`（ChangeProposal 表 + 迁移 + 四引擎 SQL）
- `services/proposals/base.py`（ProposalExecutor ABC + ApplyResult + ProposalAutoReviewer Protocol + AutoReviewResult）
- `services/proposals/auto_reviewer.py`（DefaultAutoReviewer，全 escalate）
- `services/proposals/registry.py`（ExecutorRegistry：register/get/policy_for/risk_for/set_policy/set_risk/reset）
- `services/proposals/service.py`（submit 三档分流 / review / revert / apply_as_admin / revert_all_by_user / _do_apply）
- `api/proposals.py`（6 端点：submit/preview/list/get/review/revert + revert-by-user）
- `schemas/proposal.py`

### P2 共享转型（7 commit + 前端）
- 模型变更：Merchant.user_id nullable、Recipe.is_public、Unit.is_standard、UserMerchantFavorite、ProductMerchantPriceSummary
- 价格去标识：`services/price_aggregator.py`（recompute_summary 聚合单价 ¥/斤）；latest-price 读 ProductRecord 跨用户公开（响应无 user_id/record_type，保留单位转换/fallback/total_cost 业务逻辑）
- 商家共享池：merchants.py 列表/详情/坐标去 user_id 过滤 + 收藏端点
- 菜谱发布：RecipePublishExecutor + POST /recipes/{id}/publish（管理员直发/普通用户审核）+ 已发布守卫
- 5 业务执行器：ingredient（含合并完整 snapshot/revert）/ nutrition（补空 auto/覆盖 manual）/ unit（拒标准单位）/ hierarchy / merchant（软停用）+ CrudExecutorBase DRY 基类
- bootstrap.register_all 注册 7 执行器 + 治理总表策略（main.py lifespan 调用）
- 分流改造：共享写端点统一 `if is_admin: apply_as_admin else: submit`
- 前端：MerchantsView（收藏/筛选/提议 toast）+ RecipesView/RecipeDetail（发布按钮/守卫/chip）+ RecipeResponse.is_public

### P3 增强（2 commit）
- 商家合并执行器（merchant_merge，清理重复商家）
- 反垃圾：service.revert_all_by_user + POST /proposals/revert-by-user

## 治理总表（策略）

| 数据 | 新增 | 编辑 | 删除 | 特殊 |
|---|---|---|---|---|
| 食材 | auto | manual | manual+回滚 | 合并：manual+预览+互斥+回滚（high） |
| 营养数据 | 补空auto/有数据manual | manual | manual | USDA 匹配：manual |
| 标准单位 | 管理员直写 | 管理员直写 | 管理员直写 | 不进框架 |
| 模糊量单位 | auto | manual | manual | — |
| 实体单位覆盖/密度 | auto | manual | manual | — |
| 食材层级关系 | manual | manual | manual | 涉成本全审 |
| 商家 | auto | manual（坐标high） | manual+回滚 | 收藏私有 |
| 商品实体 | auto | manual | manual+回滚 | 条码：manual |
| 菜谱·发布前 | 私有 | 作者自由 | 作者自由 | — |
| 菜谱·发布 | — | manual | — | 通过变公开共建 |
| 菜谱·发布后 | — | manual（任何人） | 作者不可删/管理员可删 | — |

## 关键文件

- 框架：`backend/app/services/proposals/`（base/registry/service/auto_reviewer/bootstrap + executors/）
- 执行器：`executors/{ingredient,nutrition,unit,hierarchy,merchant,merchant_merge,recipe_publish}.py` + `_crud_base.py`
- API：`api/proposals.py`、`api/merchants.py`、`api/recipes.py`、`api/ingredient_hierarchy.py` 等
- 测试：`tests/test_permissions_p0.py`、`tests/test_proposals_framework.py`、`tests/test_shared_data.py`

## 已知妥协 / 后续

1. **合并 quantity 追加无法精确 revert**：合并时 quantity 加到目标行，revert 只还原源行快照，目标行数量变更丢失（代码注释明示）。建议后续快照补目标行 quantity。
2. **nutrition set_policy 权宜**：补空场景由执行器 apply 内动态 set_policy 转 auto，运行时改、重启回 manual。建议落 system_config。
3. **未分流端点**：units 换算、条码批量导入、商品营养/修正、ingredient 硬删除保留管理员直写（执行器语义不符或高危）。
4. **auto_review 预留**：DefaultAutoReviewer 全 escalate，具体判定逻辑待填（规则/AI）。
5. **registry 策略进程级**：类变量，重启回默认。后台动态改策略持久化（system_config）未实现。
6. **revert_all_by_user 突破回滚窗口**：反垃圾场景刻意放开 revertable_until，单条失败不阻断。
7. **基线测试失败**（16 个，master 同样失败，与本次无关）：test_auth/test_locations/test_nutrition/test_recipes/test_reports/test_inferrer/test_user_merchant_product_order/test_downloader/test_format_detector，待单独清理。

## 测试

- 新增 51 个权限/框架/共享测试全过
- 全量 373 passed / 16 failed（16 全是预存基线）
- 前端 npm run build 通过
