# BUGFIX：注册前后端校验对齐与错误信息透传

- 日期：2026-06-22
- 触发：注册时 `username="a"` 前端放过、后端 422 拒；且报错只显示「请求参数验证失败」，不指明哪个字段。

## 症状

1. **前后端校验不一致**：前端放行 `username="a"`（1 字符），后端 `UserRegister` 要求 `min_length=3`，返回 422。
2. **错误信息不具体**：前端只显示笼统的「请求参数验证失败」，不告诉用户哪个字段、什么问题。

## 根因（Phase 1 调查结论）

误以为是后端没给详情，**实测后端给了**——关键澄清：

- 后端 [main.py:445-483](backend/app/main.py#L445) 的 `RequestValidationError` 处理器返回 `{"detail": "请求参数验证失败", "errors": [{"field","message","type"}]}`，字段级详情都在 `errors` 里。
- 前端 [client.ts:30-49](frontend/src/api/client.ts#L30) 的 `extractErrorDetail` 已正确解析该格式，拼成 `"请求参数验证失败: body.username: ..."` 挂到 `error.userMessage`。

真正根因全在前端 [Register.vue](frontend/src/views/auth/Register.vue)，两处：

1. **校验缺失**：`handleRegister` 里 username/email 只校验「非空」，缺后端要求的「username 3-50 字符」「email 合法格式」。
2. **错误没用上**：`catch` 读的是 `error.response.data.detail`（笼统标题），没用拦截器拼好的 `error.userMessage`（含字段详情）。

> 「读 detail 不读 userMessage」是项目里的**全局模式**（UserManagementView 等也这样），本次聚焦注册。

## 修复（纯前端，后端零改动）

[Register.vue](frontend/src/views/auth/Register.vue) 两处：

1. `handleRegister` 校验段补齐：
   - username：非空 + `3-50 字符`（对齐后端 `min_length=3, max_length=50`）
   - email：非空 + 格式正则 `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`（复用 UserManagementView 同款，对齐后端 `EmailStr`）
2. `catch` 改读：`error.userMessage || error.response?.data?.detail || '注册失败，请稍后重试'`（优先拦截器拼好的详情）。

## 验证

- `npm run build`：✓ 通过（26.75s）。
- edge-devtools MCP 实测 `username="a"` + 合法 email/password/confirm 后点注册：
  - 用户名输入框下显示「用户名需 3-50 个字符」（中文 field-level 错误）✓
  - 无顶部 alert（前端拦截，无后端错误）✓
  - 网络面板**无 `POST /api/v1/auth/register`**（根本未发后端）✓
  - 停在 `/register` 未跳转 ✓

## 备注 / 未来改进

- 症状 2 的修复（读 `userMessage`）是兜底——前端校验补齐后，能漏到后端触发 422 的场景已极罕见（后端额外校验只剩比前端正则更严的 `EmailStr`）。后端 `errors` 的 `field` 仍带 `body.` 前缀、`message` 仍为英文（如 `String should have at least 3 characters`），若未来要彻底中文化，需建 `type→中文` 映射表 + 清理 `body.` 前缀，跨端改动，暂不做（YAGNI）。
- 其他页面（Login、UserManagementView 等）同样的「读 detail 不读 userMessage」模式若遇到可按本方案同法修复。
