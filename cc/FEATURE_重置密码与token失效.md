# FEATURE：用户重置密码与 Token 失效

- 日期：2026-06-22
- 关联设计：`docs/superpowers/specs/2026-06-22-用户重置密码与token失效-design.md`
- 关联计划：`docs/superpowers/plans/2026-06-22-用户重置密码与token失效.md`

## 背景与目标

后台「用户管理」编辑用户的对话框中，密码原作为一个普通输入框（编辑时非必填、提示「留空则不修改密码」），存在两个问题：

1. **交互/安全**：管理员每次打开编辑框都看到密码框，易误改；密码修改混在通用编辑流程里，缺少独立、明确的「重置密码」动作。
2. **重置后旧会话仍有效**：access token 有效期 7 天（`jwt_access_token_expire_minutes = 10080`），refresh token 同样 7 天，且前端 401 会自动用 refresh token 续命——仅改密码不废旧 token 的话，被重置的用户最长还能逍遥 7 天。

目标：编辑表单去密码、改为「重置密码」按钮 + 独立对话框；重置密码后**立即作废该用户所有 access / refresh token**。

## 方案

### 1. Token 版本号机制（作废旧 token）

给 `users` 表加 `token_version`（Integer, default 0, not null）：

- **签发**：`login` / `register` / `refresh` 三处在 JWT payload 加 `"ver": user.token_version`。
- **校验**：`resolve_user_from_token`（access 校验入口，HTTPBearer 与 SSE query token 鉴权共享）在 `is_active` 之后比对 `payload.get("ver", 0) != user.token_version` → 401「凭证已失效，请重新登录」；`refresh` 端点同样比对（旧 refresh token 刷不出新 access）。
- **作废**：`update_user`（`PUT /auth/users/{id}`）在改密码分支内 `target.token_version += 1`，**仅**在传了 `password_hash` 时 bump（改用户名/邮箱/手机不动 token）。

### 2. 前端 UI

- 编辑对话框：密码 `v-text-field` 改 `v-if="!isEditing"`（仅新增显示），编辑态 `v-else` 显示「🔑 重置密码」按钮 + 说明文字。
- 新增独立「重置密码」对话框：新密码 + 确认新密码（`confirmPasswordRule` 校验一致），提交 `PUT /auth/users/{id}` 仅带 `password_hash`。
- `saveUser` 编辑分支去掉密码拼装。
- `api/client.ts` **零改动**：被重置用户下次请求 401 → 自动 refresh（也 401）→ 清 token 跳 `/login`，闭环天然成立。

## 改动清单

### 后端
- `app/models/user.py`：新增 `token_version = Column(Integer, default=0, nullable=False)`。
- `app/core/security.py`：`resolve_user_from_token` 增加版本比对（`is_active` 之后）。
- `app/api/auth.py`：`register`/`login`/`refresh` 签发带 `ver`；`refresh` 增加版本校验；`update_user` 改密码时 `token_version += 1`。
- `alembic/versions/20260622_0003_add_token_version_to_users.py`：新迁移（`batch_alter_table`，SQLite 友好，`server_default='0'`）。
- `scripts/sql/20260622_add_token_version_to_users_{sqlite,mysql,postgresql}.sql`：三套手工 SQL（PostGIS 无关，故无第四套）。
- `tests/test_auth.py`：新增 `_admin_token` helper + `test_reset_password_invalidates_old_tokens` + `test_update_other_fields_keeps_token_valid`。

### 前端
- `src/views/admin/UserManagementView.vue`：编辑态去密码框换按钮、加重置对话框、加状态与方法、瘦身 `saveUser` 编辑分支。

## 关键设计决策

- **为何用 token 版本号而非黑名单**：黑名单要存 access+refresh、要处理过期清理、表单调增长；版本号零额外存储、access/refresh 同时失效、自动随 token 过期清理。
- **默认 0 兼容存量**：迁移给所有现有用户 `token_version=0`；存量老 token 无 `ver` claim，校验时 `payload.get("ver", 0)` 取 0 == 库中 0，**不误伤在线用户**；重置密码后才 bump 到 1，老 token 失效。
- **bump 仅限改密**：非密码字段更新（用户名/邮箱/手机）不 bump，避免误踢。
- **前端零改动闭环**：复用既有 401 自动 refresh 逻辑，被重置用户自然被送回登录页。

## 验证结论

- 后端 `pytest tests/test_auth.py`：**5 passed**（原有 3 + 新增 2），覆盖「重置后旧 access 401、旧 refresh 401、新密码可登录、改邮箱不影响 token」。
- 实现者另用 uuid 唯一用户名内联验证端到端 8 断言全过。
- 前端 `npm run build` 通过（`✓ built`，无 TS/模板错误）。
- 两阶段审查（spec + 质量）均通过。

## 已知事项 / 未来改进

- **`tests/test_auth.py` 测试隔离缺陷（既有）**：该文件用 `TestClient(app)` 打真实开发库、硬编码用户名（testuser 等）、无清理 fixture，每次跑都会留下测试用户导致重跑时 `test_register` 等因用户名冲突失败。本次为验证清理过一次，但根因未修。建议未来引入事务回滚 fixture 或内存库隔离。
- **`tests/agent/test_agent_api.py:143` helper 前瞻提示**：该 helper 自建 token 不带 `ver`，靠默认 0 兼容当前正常工作；若未来 agent 测试场景 bump `token_version`，需同步给该 helper 补 `ver`。
- **开发库 alembic 版本曾滞后**：本任务执行时发现开发库 `alembic_version` 停在 `20260618_0001`（schema 实际已最新，疑为平时用 MCP 维护所致），已通过 `alembic stamp 20260622_0002` + `upgrade head` 对齐到 `20260622_0003`，`favorite_merchants` 旧表按现状保留（用户确认 alembic 未发版未启用）。
