# 生计项目 - API 通信问题解决总结

## 问题描述

用户报告无法注册，提示：
- `POST http://localhost:5173/api/auth/register` 报 404
- `Unexpected end of JSON input`
- 同样的问题也出现在登录和其他 API 端点

## 问题根本原因

存在三层路径不匹配问题：

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

## 解决方案

### 修复前端环境变量
```diff
# frontend/.env
- VITE_API_URL=/api
+ VITE_API_URL=/api/v1
```

### 验证配置一致性
- 前端 API 客户端: `baseURL = '/api/v1'` (或环境变量)
- 前端请求: `api.post('/auth/register', ...)` → 发送到 `/api/v1/auth/register`
- Vite 代理: `/api/v1` → 转发到 `http://localhost:8000`
- 后端路由: `/api/v1/auth/register` (通过 `/auth` + `prefix="/api/v1/auth"`)

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
处理结果: 正确的注册逻辑
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

## 部署影响

- Docker 部署: 通过 nginx 配置，路径映射正常工作
- 直接部署: 通过反向代理，路径映射正常工作
- 开发环境: 通过 Vite 代理，路径映射现在正常工作

## 总结

通过将前端环境变量从 `VITE_API_URL=/api` 修正为 `VITE_API_URL=/api/v1`，
实现了前端 API 客户端、Vite 开发代理和后端 API 路由之间的路径一致性，
从而解决了所有 API 通信相关的 404 错误。

用户现在应该能够正常访问注册、登录及其他所有功能。