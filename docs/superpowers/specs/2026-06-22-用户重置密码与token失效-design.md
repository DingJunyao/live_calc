# 用户重置密码与 Token 失效 — 设计文档

- 日期：2026-06-22
- 范围：后台「用户管理」编辑流程 + JWT 失效机制
- 状态：已与用户确认设计，待编写实现计划

## 1. 背景与目标

当前后台「用户管理」的编辑用户对话框中，密码作为一个普通输入框存在，编辑时非必填，提示「留空则不修改密码」。这带来两个问题：

1. **交互/安全隐患**：管理员每次打开编辑框都看到密码框，容易误改；密码修改混在通用编辑流程里，没有独立、明确的「重置密码」动作。
2. **重置后旧会话仍有效**：access token 有效期长达 7 天（`jwt_access_token_expire_minutes = 10080`），refresh token 同样 7 天。即便管理员重置了某用户的密码，该用户手持的旧 token 在最长 7 天内依然可用。

本次目标：

- 将编辑用户表单中的密码字段替换为一个独立的「重置密码」按钮，点击后弹出一个独立对话框输入新密码。
- 重置密码后，**立即作废该用户所有已签发的 access / refresh token**，迫使其重新登录。

## 2. 现状分析

### 2.1 前端

- 页面：[frontend/src/views/admin/UserManagementView.vue](frontend/src/views/admin/UserManagementView.vue)
  - 同一个 `v-dialog` 同时承担「新增用户」与「编辑用户」。编辑时密码 `v-text-field` 非必填，提示「留空则不修改密码」。
  - `saveUser()` 编辑分支：仅当 `formData.password` 非空时才把 `password_hash`（前端 SHA256）拼进 payload。
  - 打开编辑对话框时 `formData.password = ''`。
- 加密：[frontend/src/utils/crypto.ts](frontend/src/utils/crypto.ts) `hashPassword()` 用 SHA256。
- API 客户端：[frontend/src/api/client.ts](frontend/src/api/client.ts)
  - 请求拦截器：附带 `Authorization: Bearer <access_token>`。
  - 响应拦截器（关键）：收到 **401 → 用 refresh_token 调 `/auth/refresh` → 成功则重试原请求；失败则清 token 跳 `/login`**。
  - 含义：**仅废 access token 无效**，前端会自动用 refresh token 续命。要让用户真正下线，必须连 refresh token 一起废。

### 2.2 后端

- 路由：[backend/app/api/auth.py](backend/app/api/auth.py)
  - `PUT /auth/users/{user_id}`（`update_user`）：管理员更新用户，`password_hash` 可选，传了才改。
  - `POST /auth/login`、`POST /auth/register`、`POST /auth/refresh`：签发 token，payload 仅含 `{"sub": <user_id>, "exp": ..., "type": ...}`，**无版本号**。
- 安全：[backend/app/core/security.py](backend/app/core/security.py)
  - `create_access_token` / `create_refresh_token`：签发 JWT。
  - `resolve_user_from_token`：access token 校验入口（被 `get_current_user` 与 SSE query token 鉴权共享）。流程：空 token → 401；解码失败 → 401；类型非 access → 401；`sub` 缺失 → 401；用户不存在 → 404；`is_active=False` → 403。
- 配置：[backend/app/config.py](backend/app/config.py)
  - `jwt_access_token_expire_minutes = 10080`（7 天），`jwt_refresh_token_expire_days = 7`。
- 模型：[backend/app/models/user.py](backend/app/models/user.py)
  - 字段：`id, username, email, phone, password_hash, is_admin, is_active, email_verified, created_at, updated_at`。**无 token 版本字段**。

### 2.3 关键结论

- 后端 `PUT /auth/users/{id}` 已支持「只传 password_hash 改密码」，可直接复用，无需新接口。
- 前端 401 闭环已具备；只要后端让 access 与 refresh 同时失效，前端零改动即可达到「踢下线」效果。
- 目前没有任何 token 失效机制（无黑名单、无版本号）。

## 3. 方案选型

### Token 失效机制：两条路

| 方案 | 做法 | 评价 |
| --- | --- | --- |
| Token 黑名单 | 把被作废的 token / jti 存表，每次请求查 | access + refresh 都要存；要处理过期清理；表单调增长。脏且累，不推荐。 |
| **Token 版本号**（采用） | User 加 `token_version` 整数列；签发时写进 payload；校验时比对；重置密码 `+1` | 无额外存储；access / refresh 同时失效；老用户不受影响；附带可复用于未来其他「踢下线」场景。 |

### UI 交互：采用「编辑框内按钮 + 独立弹窗」（方案 A）

- 编辑用户对话框内，用「🔑 重置密码」按钮替换原密码字段（仅编辑模式显示）。
- 点击后弹出一个独立 `v-dialog`，含「新密码」「确认新密码」两个输入框。
- 确认后调 `PUT /auth/users/{id}`，仅传 `password_hash`。

## 4. 详细设计

### 4.1 后端

#### 4.1.1 模型：新增 `token_version`

[backend/app/models/user.py](backend/app/models/user.py)：

```python
token_version = Column(Integer, default=0, nullable=False)
```

默认 `0` 的兼容性意义见 §5。

#### 4.1.2 安全：签发带版本、校验比对版本

[backend/app/core/security.py](backend/app/core/security.py)：

- `create_access_token` / `create_refresh_token`：本身不改签名，由**调用方**在 `data` 字典中传入 `"ver": user.token_version`（与 `"sub"` 同级）。函数体保持不动，`data.copy()` 会自动带上。
- `resolve_user_from_token`：在查到 user 之后、`return user` 之前（建议紧接 `is_active` 校验之后），新增版本比对：

```python
token_ver = payload.get("ver", 0)
if token_ver != user.token_version:
    raise HTTPException(status_code=401, detail="凭证已失效，请重新登录")
```

> 老token无 `ver` → `payload.get("ver", 0)` = 0；存量用户 `token_version` = 0；相等，不误踢（见 §5）。

#### 4.1.3 路由：签发传 ver、重置密码 bump 版本

[backend/app/api/auth.py](backend/app/api/auth.py)：

- `login`：`create_access_token(data={"sub": str(user.id), "ver": user.token_version})`，refresh 同理。
- `register`：用户刚创建，`token_version` 为默认 0，签发时同样带上 `"ver": user.token_version`。
- `refresh`：
  - 解码后、查到 user 后，新增 `if payload.get("ver", 0) != user.token_version: raise 401`（旧 refresh token 直接拒）。
  - 重新签发 access token 时带上当前 `"ver": user.token_version`。
- `update_user`（`PUT /auth/users/{user_id}`）：在更新 `password_hash` 的分支内，**同时** `target.token_version += 1`：

```python
if user_update.password_hash is not None:
    target.password_hash = get_password_hash(user_update.password_hash)
    target.token_version += 1   # 重置密码 → 作废该用户所有现有 token
```

> 仅在确实改密码时 bump，其他字段更新（用户名/邮箱/手机）不影响 token 有效性。

#### 4.1.4 数据库迁移

- alembic 迁移：新增 `users.token_version`（`Integer, default=0, nullable=False`）。现有行自动填 0。
- 按项目规范提供 SQL 脚本三套（与 PostGIS 无关，故不需要第四套）：
  - SQLite
  - MySQL
  - PostgreSQL

### 4.2 前端

[frontend/src/views/admin/UserManagementView.vue](frontend/src/views/admin/UserManagementView.vue)：

1. **编辑对话框模板**：删除密码 `v-text-field`，替换为一个「🔑 重置密码」按钮（`v-btn`，`prepend-icon="mdi-lock-reset"`，`variant="outlined"`），以 `v-if="isEditing"` 仅在编辑模式显示（新增模式下密码字段保持原样，建号必须有密码）。
2. **新增「重置密码」独立对话框**：
   - 状态：`resetDialog`（bool）、`resetUserId`（number）、`resetUsername`（string，用于标题展示）、`resetForm`（`{ newPassword, confirmPassword }`）。
   - 模板：两个 `v-text-field`（`type="password"`），「新密码」套用 `rules.required` + `rules.minPassword`，「确认新密码」增加「与上一致」的自定义校验。
   - 打开：新增 `openResetPasswordDialog(item)`，记录 id/username、清空表单、打开 dialog。
   - 提交：新增 `submitResetPassword()`，校验通过后 `api.put(\`/auth/users/${resetUserId.value}\`, { password_hash: hashPassword(resetForm.newPassword) })`，成功提示「密码已重置，该用户需重新登录」、关闭 dialog。
3. **`saveUser()` 编辑分支**：删除 `if (formData.password) { payload.password_hash = ... }` 这段（编辑流程不再碰密码）。新增分支不动。

[frontend/src/api/client.ts](frontend/src/api/client.ts)：**零改动**。被重置用户下一次请求 → access token 拿 401 → 自动 refresh → refresh 也 401 → 清 token → 跳 `/login`，闭环天然成立。

### 4.3 改动清单总览

| 层 | 文件 | 改动 |
| --- | --- | --- |
| 后端模型 | `models/user.py` | 加 `token_version` 列 |
| 后端安全 | `core/security.py` | `resolve_user_from_token` 增加版本比对 |
| 后端路由 | `api/auth.py` | login/register/refresh 签发带 `ver`；refresh 校验版本；update_user 改密码时 bump |
| 后端迁移 | `alembic/` | 新增迁移文件 |
| 后端 SQL | SQL 脚本目录 | SQLite / MySQL / PostgreSQL 三套 |
| 前端 | `views/admin/UserManagementView.vue` | 删密码框、加重置按钮、加重置对话框、瘦身 saveUser 编辑分支 |
| 前端 | `api/client.ts` | 零改动 |

## 5. 存量兼容性

- 迁移给所有现有用户 `token_version = 0`。
- 现有在有效期内的老 token 没有 `ver` claim → 校验时 `payload.get("ver", 0)` 取 0 → 等于 `user.token_version`（0）→ **不失效，现有在线用户不受影响**。
- 自本次上线起新签发的 token 都带 `ver`。
- 管理员重置某用户密码 → 该用户 `token_version` 变为 1 → 其所有旧 token（无论 access 还是 refresh，无论是否带 `ver`）的版本号（0）都不再匹配 → 全部立即失效。

## 6. 范围外（YAGNI）

- 不新增独立的 `POST /auth/users/{id}/reset-password` 接口，复用现有 `PUT /auth/users/{id}`。
- 不引入 token 黑名单。
- 不新增专门的审计日志表记录「谁重置了谁的密码」（如未来有合规需求再议）。
- 不改动「切换激活状态」「切换管理员」的 token 行为（`is_active=False` 已能让被禁用用户立即 403，无需版本号介入）。
- 不改动新增用户流程（创建时密码字段保留）。

## 7. 测试要点

- **编辑表单**：编辑模式下不再出现密码输入框，出现「重置密码」按钮；新增模式下密码字段仍在且必填。
- **重置流程**：输两次新密码、不一致时校验拦截、提交后后端密码更新、提示语出现。
- **踢下线（核心）**：
  - 用被重置用户的旧 access token 请求任意鉴权接口 → 401。
  - 用其旧 refresh token 调 `/auth/refresh` → 401。
  - 前端表现：下一次请求后自动跳转登录页。
- **存量不受影响**：上线后未被动过的老用户，其上线前签发的 token 仍可用至自然过期。
- **其他字段更新不踢人**：仅改用户名/邮箱/手机时，不 bump 版本，该用户 token 仍有效。
