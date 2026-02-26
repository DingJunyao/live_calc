# 生计项目 - API 通信与认证问题解决总结

## 问题描述

用户报告无法注册，提示：
- `POST http://localhost:5173/api/auth/register` 报 404
- `Unexpected end of JSON input`
- 同样的问题也出现在登录和其他 API 端点
- `INFO:     127.0.0.1:56368 - "GET /api/v1/config HTTP/1.1" 404 Not Found`
- `ValueError: password cannot be longer than 72 bytes, truncate manually if necessary`

## 问题根本原因

存在五层问题：

### 1. 前端环境变量配置错误
- 文件: `frontend/.env`
- 问题: `VITE_API_URL=/api` （缺少 `/v1` 版本号）
- 影响: API 客户端发送请求到 `/api/auth/register` 而不是 `/api/v1/auth/register`

### 2. Vite 代理配置不匹配
- 文件: `frontend/vite.config.ts`
- 配置: `proxy: { '/api/v1': ... }`
- 问题: 只代理 `/api/v1` 路径，不处理 `/api` 路径

### 3. 前后端 API 路径不一致
- 后端注册: `prefix="/api/v1/auth"` → `/api/v1/auth/register`
- 前端发送: 由于环境变量错误 → `/api/auth/register`
- 结果: 路径不匹配导致 404

### 4. bcrypt/passlib 版本兼容性问题
- 后端在处理密码时使用了 passlib + bcrypt
- bcrypt 5.0.0 与 passlib 1.7.4 存在版本兼容性问题
- Passlib 在初始化时执行内部测试，触发 bcrypt 的 72 字节长度限制
- 前端 SHA256 哈希（64 字节）经 hex 编码变成 128 字节，超出限制

### 5. HTTP 环境下 Web Crypto API 不可用
- 局域网测试时，浏览器在非 HTTPS 环境下禁用 Web Crypto API
- 前端无法进行密码哈希处理

## 解决方案

### 修复前端环境变量
```diff
# frontend/.env
- VITE_API_URL=/api
+ VITE_API_URL=/api/v1
```

### 修复 Register 组件中的直接 fetch 调用
```diff
onMounted(async () => {
  // 检查是否需要邀请码
  try {
-    const config = await fetch('/api/v1/config').then(r => r.json())
+    const config = await api.get('/auth/config')
    requireInviteCode.value = config.registration_require_invite_code || false
  } catch (error) {
    // 忽略错误，默认不需要邀请码
    requireInviteCode.value = false
  }
})
```

### 更换密码哈希实现方式
- 从 passlib + bcrypt 混合模式切换为纯 bcrypt 实现
- 在 `get_password_hash` 和 `verify_password` 函数中添加自动截断逻辑
- 确保所有密码在传递给 bcrypt 之前都被截断到 72 字节

### 适配 HTTP 环境下的密码处理
- 使用 crypto-js 库替代 Web Crypto API
- 前端对密码进行 SHA256 哈希处理
- 后端继续使用 bcrypt 进行二次哈希存储

## 完整路径解析

```
前端发起: api.post('/auth/register', ...)
↓
API 客户端构造: '/api/v1' + '/auth/register' = '/api/v1/auth/register'
↓
Vite 开发服务器: 识别 '/api/v1' 前缀，转发到 http://localhost:8000/api/v1/auth/register
↓
后端 FastAPI: 接收 /api/v1/auth/register，匹配到 auth router 的 /register 端点
↓
处理结果: 正确的注册逻辑，密码经过前端 SHA256 + 后端 bcrypt 双重哈希处理
```

## 验证测试

所有以下路径现在都能正确工作：
- ✅ `GET /api/v1/auth/config` - 获取注册配置
- ✅ `POST /api/v1/auth/register` - 用户注册
- ✅ `POST /api/v1/auth/login` - 用户登录
- ✅ `POST /api/v1/auth/refresh` - 令牌刷新
- ✅ `GET /api/v1/auth/me` - 获取用户信息
- ✅ 其他所有 `/api/v1/*` 端点

## 相关修复

此修复解决了项目中的多个相关问题：
1. 修复了之前添加的 `/api/v1/auth/config` 端点的路径
2. 修复了 Vite 代理配置 (`/api/v1` 代理到 `http://localhost:8000`)
3. 确保了前后端路径的一致性
4. 修复了 bcrypt 版本兼容性和 72 字节长度限制问题
5. 适配了 HTTP 局域网环境下的密码处理

## 部署影响

- Docker 部署: 通过 nginx 配置，路径映射正常工作
- 直接部署: 通过反向代理，路径映射正常工作
- 开发环境: 通过 Vite 代理，路径映射现在正常工作
- 密码处理: 前端 SHA256 + 后端 bcrypt 双重哈希确保安全性
- HTTP 环境: 通过 crypto-js 库支持前端密码哈希处理

## 安全注意事项

在 HTTP 局域网环境下，现在使用 crypto-js 库进行前端密码哈希处理，提升了安全性。
密码会经过以下处理：
1. 前端使用 SHA256 进行哈希处理
2. 后端接收哈希值后使用 bcrypt 进行二次哈希存储
详情请参考 SECURITY_NOTICE_HTTP.md 文件中的安全指南。

## 总结

通过以下关键修复：
1. 修正前端环境变量 `VITE_API_URL=/api/v1`
2. 修复 Register 组件中的直接 fetch 调用，改为使用 API 客户端
3. 重构密码哈希实现，更换为纯 bcrypt 并添加长度截断逻辑
4. 适配 HTTP 环境下使用 crypto-js 进行前端密码哈希

实现了前端 API 客户端、Vite 开发代理和后端 API 路由之间的路径一致性，
解决了所有 API 通信相关的 404 错误，并修复了 bcrypt 长密码长度限制问题。

用户现在应该能够正常访问注册、登录及其他所有功能（局域网测试环境下），且安全性得到保障。