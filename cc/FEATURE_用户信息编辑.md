# 用户信息编辑

个人中心新增「用户信息编辑」（设置列表第一项，主题切换上方），用户自助改用户名/邮箱/手机/密码。此前改账号信息只能找管理员。

spec：[docs/superpowers/specs/2026-07-16-用户信息编辑-design.md](../docs/superpowers/specs/2026-07-16-用户信息编辑-design.md)
plan：[docs/superpowers/plans/2026-07-16-用户信息编辑.md](../docs/superpowers/plans/2026-07-16-用户信息编辑.md)

## 后端

- 新增 `PUT /auth/me/account`（[auth.py](../backend/app/api/auth.py) `update_my_account`）：字段全可选（传了才改）。用户名/邮箱/手机查重（`User.id != current_user.id`，命中 400）；改密码（`new_password` 非空）必须带 `current_password`（`verify_password` 校验，错 401），成功后 `token_version += 1` 并签发新 access+refresh token 一并返回；不改密码则 token_version 不动、不签发 token。
- 新增 schema `UserAccountUpdate` / `UserAccountResponse`（[schemas/auth.py](../backend/app/schemas/auth.py)）。
- 抽 `_user_to_response(user, db)` helper（[auth.py](../backend/app/api/auth.py)），`get_me`/`patch_me`/`update_my_account` 三处共用，消除三份 `UserResponse(...)` 构造重复（DRY）。
- 端点内 `current_user` 是 `get_current_user` 独立 session 返回的 detached 对象，在本请求 db 重新 load 后再 setattr+commit（与 `patch_me` 一致）。

## 前端

- [ProfileView.vue](../frontend/src/views/profile/ProfileView.vue) 列表首项加「用户信息编辑」入口 + 用户信息编辑对话框（用户名/邮箱/手机）；对话框内「修改密码」按钮打开独立的修改密码对话框（当前/新/确认）。`saveAccount` 只提交有变化的基本信息字段；`saveChangePassword` 单独提交 current_password/new_password，改密返回新 token 则 `userStore.setTokens` 静默替换 + `fetchUser`；密码用 `hashPassword`（@/utils/crypto，与 Register/Login 一致）SHA256 后传。
- [user.ts](../frontend/src/stores/user.ts) 加 `setTokens(access, refresh)`，`login`/`register` 改复用（消除各自三行重复）。

## 设计要点

- 改密码强制校验当前密码（防登录态被劫持时改密）。
- 改密 `token_version+1` → 旧 token 全失效（含其他设备，安全预期）；同时签发新 token 给发起方，本机不掉线。
- 改用户名/邮箱/手机不碰 `token_version`，登录态不受影响，也不要求密码（已登录即可信）。
- 邮箱不做验证流程（`email_verified` 维持原值）；用户名长度 3–50、手机号正则沿用注册约束。

## 测试与验证

- [test_account_update.py](../backend/tests/test_account_update.py) 7 例全绿（uuid 唯一用户名避免开发库残留撞名）：改用户名成功/重复、改邮箱重复、改密码旧密错/缺旧密/成功（新 token + 旧 token 失效 + 新密码可登录）、不改密码旧 token 仍有效。
- helper 提取未破坏 `get_me`：既有 `test_update_other_fields_keeps_token_valid`（走 `GET /me`）回归通过佐证。
- 前端 `npm run build` 通过（30.23s，ProfileView chunk 29.23 kB）。
- 无表结构变更（User 字段全已具备），无 alembic/SQL 脚本。

## 测试运行环境备注

后端测试用根 `.venv`（CLAUDE.md 所指），从项目根跑需 `PYTHONPATH=backend` + `DATABASE_URL=sqlite:///D:/code/live_calc/backend/data/livecalc.db` 钉死——否则相对路径 `./data/livecalc.db` 解析到根/data 找不到；同时覆盖 .env 里的 PG，免得测试往开发 PG 写数据。`uv run --directory backend` 会误用 backend/.venv（实际装在根 .venv）导致 `import app` 失败，故直接用根 .venv 的 python。
