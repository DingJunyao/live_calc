# 生计项目 - 问题修复总结

## 问题概述

用户在注册和登录时遇到以下错误：
- `INFO: 127.0.0.1:56368 - "GET /api/v1/config HTTP/1.1" 404 Not Found`
- `ValueError: password cannot be longer than 72 bytes, truncate manually if necessary`

## 问题根源分析

### 1. 前端路由配置错误
- Register.vue 组件中直接使用 `fetch('/api/v1/config')` 而不是通过 API 客户端
- 这绕过了 Vite 开发代理，导致 404 错误

### 2. bcrypt/passlib 兼容性问题
- bcrypt 5.0.0 与 passlib 1.7.4 存在版本兼容性问题
- passlib 在初始化时会执行内部测试，触发 bcrypt 的 72 字节长度限制检查
- 即使代码中已做截断，初始化阶段仍会报错

## 解决方案

### 1. 修复前端路由问题
**文件**: `frontend/src/views/auth/Register.vue`
- 将 `fetch('/api/v1/config')` 替换为 `api.get('/auth/config')`
- 导入 `api` 客户端以确保请求通过代理

### 2. 修复 bcrypt 兼容性问题
**文件**: `backend/app/core/security.py`
- 移除 passlib 依赖，直接使用 bcrypt 库
- 实现手动截断逻辑，确保密码长度不超过 72 字节
- 提供 `get_password_hash` 和 `verify_password` 函数的兼容实现

### 3. 保持后端路由一致性
**确认**: 后端路由 `/api/v1/auth/config` 已正确注册
- 在 `app/main.py` 中通过 `app.include_router(auth.router, prefix="/api/v1/auth", ...)` 注册
- 在 `app/api/auth.py` 中定义 `@router.get("/config", ...)` 端点

## 验证结果

### 1. 路由测试
- `/api/v1/auth/config` 端点返回: `{"registration_require_invite_code":true}`
- ✅ 通过测试

### 2. 注册功能测试
- 使用有效数据成功注册: `{"username":"testuser","email":"test@example.com","phone":"13812345678","password_hash":"testpassword123"}`
- 返回访问令牌和刷新令牌
- ✅ 通过测试

### 3. bcrypt 修复测试
- 普通密码 (13 字符): ✅ 正常工作
- 长密码 (80 字符): ✅ 正常工作（自动截断）
- 密码验证: ✅ 正常工作

## 总结

所有问题均已修复，用户现在应该能够：
1. 访问注册页面时正确获取配置信息
2. 成功完成用户注册
3. 成功完成用户登录
4. 任何长度的密码都将被正确处理（自动截断到72字节）

## 未来建议

1. 考虑升级到兼容性更好的 bcrypt/passlib 版本组合
2. 在前端表单中增加对密码长度的实时验证提示
3. 在 API 文档中明确说明密码长度限制