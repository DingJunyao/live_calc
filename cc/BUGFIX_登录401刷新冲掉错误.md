# BUGFIX：登录失败页面刷新冲掉错误提示

## 症状
登录输错密码，页面快速刷新，错误信息一闪而过看不到。

## 根因
[client.ts](frontend/src/api/client.ts) 响应拦截器的 401 处理无差别：

```ts
if (error.response?.status === 401) {
  const refreshToken = localStorage.getItem('refresh_token')
  if (refreshToken) { try { /* 刷新 token 重试 */ } catch { location.href='/login' } }
  else { window.location.href = '/login' }  // ← 登录失败命中这条
}
```

登录请求 `/auth/login` 返回 401（凭证错误）时，用户未登录、`refreshToken` 为空 → 走 else 分支 `window.location.href='/login'`。但用户**本就在 /login**，等于整页刷新，把 [Login.vue:111](frontend/src/views/auth/Login.vue#L111) catch 里刚设的 `errorMessage`（读 `response.data.detail` 显示 v-alert）冲掉。

## 修复
401 拦截器加 `isLoginRequest` 判断，登录请求的 401 跳过 token 刷新/跳登录，直接走 extractErrorDetail + reject（带 userMessage）给调用方显示：

```ts
const isLoginRequest = error.config?.url?.includes('/auth/login')
if (!isLoginRequest) { /* 原 刷新 token / 跳登录 逻辑 */ }
```

[Login.vue](frontend/src/views/auth/Login.vue) 的 catch 逻辑本就正确（读 `response.data.detail` 显示 v-alert），无需改。

## 验证
build 通过，密码错误应稳定显示 v-alert「用户名或密码错误」、不再整页刷新。普通 tab + PWA 都受益。无表结构变更。
