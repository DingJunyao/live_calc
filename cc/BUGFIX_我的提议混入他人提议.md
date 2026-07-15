# BUGFIX：管理员「我的提议」混入他人提议

## 现象
admin/123456 登录后，「我的提议」（个人中心 → 我的提议）列表里仍有内容，且这些内容并非管理员添加——管理员写操作本应直写即时生效、不该在「我的提议」里看到别家的东西。

## 根因
一个端点扛了两个语义，分流逻辑只认 `is_admin`。

后端 `GET /proposals` 的 [list_proposals](../backend/app/api/proposals.py#L194) 按角色分流：
```python
q = db.query(ChangeProposal)
if not current_user.is_admin:
    q = q.filter(ChangeProposal.proposer_id == current_user.id)
```
管理员分支**完全不过滤** `proposer_id`，直接看整张 `change_proposals` 表。

而前端两个页面共用同一个接口、同一个函数，前端不传任何区分参数：
- 审核台 [ProposalsView.vue:695](../frontend/src/views/admin/ProposalsView.vue#L695)：`listProposals(status, 100)`
- 我的提议 [MyProposalsView.vue:226](../frontend/src/views/profile/MyProposalsView.vue#L226)：`listProposals(status, 100)`

于是对管理员来说，两个页面返回同一份数据：`change_proposals` 全表。

表里同时存在两类记录：
1. admin 自己直写留痕的（[service.py:177-181](../backend/app/services/proposals/service.py#L177) `apply_as_admin` 插 `proposer_id=admin、status=applied`）——这部分出现在「我的提议」**正常**，符合设计。
2. 别的普通用户 `submit` 进来的 `pending` 提议——这部分**不该**出现在 admin 的「我的提议」，却因管理员分支无过滤全混进来。用户看到的「并非管理员添加的内容」就是这类。

## 修复
给 `GET /proposals` 加 `scope` query 参数区分两种语义（用户决策：admin「我的提议」= `proposer_id` 为自己的全部记录，含直写留痕）。

- 后端 [list_proposals](../backend/app/api/proposals.py#L194) 加 `scope: Optional[str] = Query(None)`；过滤条件改为 `if scope == "mine" or not current_user.is_admin: filter(proposer_id == current_user.id)`。
  - `scope=mine`：无论角色都只看自己（「我的提议」用）
  - 不传：保持原行为（管理员全部、普通用户自己），审核台向后兼容
- 前端 [api/proposals.ts listProposals](../frontend/src/api/proposals.ts) 加可选 `scope?: 'mine'` 透传。
- 前端 [MyProposalsView.vue loadList](../frontend/src/views/profile/MyProposalsView.vue#L226) 调用传 `'mine'`。
- 审核台 [ProposalsView.vue](../frontend/src/views/admin/ProposalsView.vue) **不动**（保持默认看全部，正是审核台所需）。

## 验证
- 新增 [test_proposals_scope.py](../backend/tests/test_proposals_scope.py) 3 测试 passed：
  - `test_admin_default_list_returns_all`（admin 不带 scope 看全部，向后兼容）
  - `test_admin_scope_mine_excludes_others`（admin scope=mine 只看自己，核心断言）
  - `test_non_admin_scope_mine_still_own_only`（普通用户 scope=mine 仍只看自己，不泄漏）
- TDD 流程：先写测试 → 核心断言红灯（后端不认 scope）→ 加参数 → 转绿。
- proposals 全量回归 71 passed, 1 failed（`test_merchant_executor_delete_and_revert_with_references`）；该失败经 `git stash` 回基线 `a5d695a` 验证为**预存基线失败**（商家执行器 delete 未把 ProductRecord.merchant_id 置 NULL），与本次改动无关。
- `py_compile app/api/proposals.py` 通过；前端 `npm run build` 通过（31.59s）。

## 影响面
无表结构变更。改动 3 文件 + 1 测试：后端端点加可选查询参数（向后兼容，旧调用方零影响）、前端 API 封装加可选参数、我的提议页调用点带 `mine`。

## 遗留
商家执行器 `MerchantExecutor.apply`（delete 路径）未把关联 `ProductRecord.merchant_id` 置 NULL，是预存基线 bug（非本次引入），可另查。
