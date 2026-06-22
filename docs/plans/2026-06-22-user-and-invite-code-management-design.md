# 用户管理与邀请码管理增强 — 设计方案

日期：2026-06-22

---

## 一、后端权限依赖重构

在 `backend/app/core/security.py` 新增可复用依赖：

```python
async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")
    return current_user
```

- 所有现有端点的散落 `if not current_user.is_admin: raise 403` 替换为 `Depends(get_current_admin_user)`
- 涉及文件：`auth.py`、`invite_codes.py`、`admin.py`
- `get_current_user` 加活性检查：`is_active=False` 时抛 403 "账户已被禁用"

---

## 二、动态配置机制

### 模型

新增 `system_config` 表（key-value）：

```python
class SystemConfig(Base):
    __tablename__ = "system_config"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(tz=True), onupdate=func.now())
```

### 逻辑

- `Settings` 初始化时读数据库，`.env` 值作为默认值（数据库有则用数据库，无则 fallback 并写入初始记录）
- 目前配置项：`registration_require_invite_code`

### API

- `GET /api/v1/admin/config` — 获取动态配置（仅管理员）
- `PUT /api/v1/admin/config` — 批量更新配置 `{ "registration_require_invite_code": true }`（仅管理员）

---

## 三、用户管理 API

在 `backend/app/api/admin.py` 新增（全部使用 `Depends(get_current_admin_user)`）：

| 端点 | 说明 |
|---|---|
| `GET /api/v1/admin/users` | 分页列表，支持搜索（用户名/邮箱） |
| `GET /api/v1/admin/users/{id}` | 单个用户详情 |
| `POST /api/v1/admin/users` | 管理员创建用户（跳过邀请码校验，密码已前端 SHA256） |
| `PUT /api/v1/admin/users/{id}` | 修改用户信息，密码选填 |
| `PUT /api/v1/admin/users/{id}/admin` | 切换管理员身份 `{ "is_admin": bool }` |
| `PUT /api/v1/admin/users/{id}/active` | 切换激活状态 `{ "is_active": bool }` |

### 安全规则

- **不能动自己**：`id == current_user.id` 禁止改 `is_admin` 和 `is_active`
- **不能动首个用户**：`id == 1` 禁止取消管理员或失效，返回 403
- 管理员创建用户时 `is_admin` 默认 false

### Schema

- `UserAdminCreate`：username(必填)、email(必填)、password(必填，SHA256)、phone(可选)、is_admin(默认 false)
- `UserAdminUpdate`：全部可选，密码传了才更新

---

## 四、前端用户管理页面

### 入口

仪表盘「用户总数」卡片 → 可点击 → `/admin/users`

### 页面结构

- **工具栏**：搜索框（用户名/邮箱） + 新增用户按钮
- **列表**：`v-data-table`，列 = ID、用户名、邮箱、手机号、管理员、状态、注册时间、操作
- **操作列**：编辑 / 切换管理员 / 切换激活。自己和 id=1 的按钮禁用 + tooltip
- **新增/编辑对话框**：表单含用户名、邮箱、手机号、密码、管理员 checkbox

### 路由

`/admin/users`，`meta: { adminOnly: true }`，懒加载 `UserManagementView.vue`

---

## 五、邀请码模型 & API 增强

### 模型变更

- `used`（Boolean）→ `used_count`（Integer, default=0）
- 新增 `max_uses`（Integer, nullable），NULL = 不限次数
- `validate_invite_code()` 改判据：未过期 + max_uses 为 NULL 或 used_count < max_uses
- 注册成功后 `used_count += 1`

### API 增强

| 端点 | 变更 |
|---|---|
| `GET /api/v1/invite-codes` | 响应增加 `max_uses`、`used_count` |
| `POST /api/v1/invite-codes` | 请求体增加 `code`(可选)、`max_uses`(可选) |
| `PUT /api/v1/invite-codes/{id}` | **新增**，修改 expires_at 和 max_uses |
| `DELETE /api/v1/invite-codes/{id}` | 不变 |

### 注册配置

`GET /api/v1/auth/config` 的 `require_invite_code` 从数据库动态读取

---

## 六、前端邀请码管理页面改造

基于现有 `InviteCodesView.vue` 增强：

### 顶部配置区（新增）

- Switch toggle：「开启邀请码注册」，调用 `PUT /api/v1/admin/config`
- 下方提示文字说明当前状态
- 失败回弹 + loading 状态

### 创建对话框增强

- 邀请码输入框：可手动输入（重复报错），留空自动随机生成
- 骰子按钮：前端随机预填 8 位码
- 过期时间：日期选择器，可为空
- 最大使用次数：数字输入框，可为空（不限），范围 1-9999

### 列表增强

- 新增列：最大使用次数（∞）、已使用次数、剩余次数
- 已用完/过期行灰显
- 编辑按钮（修改过期时间和最大次数）+ 删除按钮

### 编辑对话框（新增）

- 仅可修改过期时间和最大次数，code 只读
- 调用 `PUT /api/v1/invite-codes/{id}`

---

## 七、注册页面 & 仪表盘改造

### 注册页面

- 加载时请求 `GET /api/v1/auth/config`，按 `require_invite_code` 决定：
  - true：显示邀请码输入框，必填，注册带 `invite_code`
  - false：隐藏邀请码输入框，注册不带 `invite_code`
- 表单校验规则动态绑定

### 仪表盘

- 「用户总数」卡片加 `@click` → `/admin/users`，hover 效果 + 箭头图标
- 功能入口列表加「用户管理」项
- 后台导航补全入口

---

## 数据库迁移

- 新增 `system_config` 表
- `invite_codes` 表：`used` → `used_count`，新增 `max_uses`
- 提供 SQLite / MySQL / PostgreSQL 三套迁移脚本
