# 待审状态显示、我的提议页面、邮件配置与发送 设计文档

## 概述

在多用户权限体系下，普通用户变更共享数据需经人工审核（manual policy）。当前系统对"提交后"的体验不够完整：
1. 用户提交审核后，页面上没有持续的视觉反馈标明"该条目变更待审核"；
2. 用户没有便捷的入口查看自己提交的所有提议及审核进度；
3. 审核流转完全依赖管理员主动进入后台查看，缺乏邮件通知机制。

本文档设计三个功能填补上述体验断点。

---

## 功能一：待审状态显示（服务端草稿回填）

### 目标

普通用户对某实体提交了 update/delete 提议（manual 待审）后：
- 该实体详情页上显示"修改待审核"或"删除待审核"状态标签；
- update 场景：普通用户自身看到的是**提议 payload 中的已修改内容**（服务端草稿回填）；
- delete 场景：普通用户页面顶部显示删除待审横幅，但保留原内容可浏览；
- 管理员或未对该实体提过审的用户不受影响，仍看到数据库当前值。

### 后端设计

#### 通用查询工具

```python
# backend/app/services/proposals/pending.py
def get_pending_proposal(db, entity_type, entity_id, user_id):
    return db.query(ChangeProposal).filter(
        ChangeProposal.entity_type == entity_type,
        ChangeProposal.entity_id == entity_id,
        ChangeProposal.proposer_id == user_id,
        ChangeProposal.status == "pending",
    ).first()
```

#### 影响的实体详情响应追加 `pending_proposal` 字段

在以下端点中，当前用户是普通用户且存在待审提议时，响应中追加 `pending_proposal`（含 action、payload、status、id）。

| 端点 | entity_type | 草稿字段（payload 中） | 特殊情况 |
|---|---|---|---|
| `GET /ingredients/{id}` | ingredient | name, category_id, aliases, etc. | — |
| `GET /products/{id}` | product | name, brand, barcode, etc. | — |
| `GET /merchants/{id}` | merchant | name, address, phone, coordinates | — |
| `GET /recipes/{id}` | recipe | 各类菜谱编辑字段 | — |
| `GET /nutrition/ingredients/{id}/nutrition` | nutrition | nutrients 数组 | — |
| `GET /nutrition/products/{id}/nutrition` | product_nutrition | structured_nutrients | — |

**delete 提议**：payload 仍返回原内容（用户查看时不覆盖渲染），前端据此显示删除横幅。

#### 具体修改位置

每个实体详情 API 的响应 schema 或 controller 中：

1. **ingredient**: `backend/app/api/ingredient_extended.py` `get_ingredient`
2. **product**: `backend/app/api/products_entity.py` `get_product`
3. **merchant**: `backend/app/api/merchants.py` `get_merchant`
4. **recipe**: `backend/app/api/recipes.py` `get_recipe`
5. **nutrition (ingredient)**: `backend/app/api/nutrition.py` `get_ingredient_nutrition`
6. **nutrition (product)**: `backend/app/api/nutrition.py` `get_product_nutrition`

每个端点在返回前：
```python
pending = get_pending_proposal(db, "ingredient", id, current_user.id)
if pending:
    response["pending_proposal"] = {
        "id": pending.id,
        "action": pending.action,
        "payload": pending.payload,
    }
```

create 操作的提议：实体尚未存在（entity_id 为 None），不涉及详情页覆盖渲染。"我的提议"页面可查看状态。

### 前端设计

#### 新增组件 `PendingProposalBanner.vue`

```
位置: frontend/src/components/proposals/PendingProposalBanner.vue
功能: 根据 pending_proposal.action 显示不同横幅
```

- `action === 'delete'` → 顶部警告横幅："该条目已提交删除申请，待管理员审核"
- `action === 'update'` → 信息横幅 + 标签："修改待审核，您看到的是已提交的修改内容"

#### 修改详情页

受影响页面：
- `IngredientDetail.vue` — 标题旁 + 基本信息字段覆盖
- `ProductDetail.vue` — 同上
- `MerchantDetail.vue` — 同上
- `RecipeDetail.vue` — 同上
- `IngredientNutrition.vue` — 营养数据覆盖
- `ProductNutrition.vue` — 同上

每个页面：
1. 从 API 响应解构 `pending_proposal`
2. 如果存在，在页面顶部渲染 `PendingProposalBanner`
3. 如果 `action === 'update'`，用 `pending_proposal.payload` 中的字段覆盖渲染值
4. 如果 `action === 'delete'`，仅展示横幅，不修改内容渲染

**字段覆盖优先级**：`pending_proposal.payload[field] ?? original[field]`

创建提议提交后：根据后端返回的 `proposal_id` 和 `message` 区分：
- 管理员直写（applied）→ 正常跳转
- 普通用户待审（pending）→ 留在当前页，显示"已提交审核申请"

---

## 功能二：我的提议页面（My Proposals）

### 目标

个人中心新增入口，展示当前用户发起的所有提议及审核状态。

### 后端

无新增 API。`GET /proposals` 已支持普通用户只查自己的提议（`list_proposals` 端点按 `current_user.is_admin` 分流）。
`GET /proposals/{id}` 已支持普通用户查看自己提交的提议详情。

### 前端

#### 个人中心新增入口

`ProfileView.vue` 列表中添加：

```vue
<v-list-item @click="router.push('/profile/proposals')">
  <template #prepend>
    <v-icon>mdi-clipboard-text-clock</v-icon>
  </template>
  <v-list-item-title>我的提议</v-list-item-title>
  <v-list-item-subtitle>查看提交的变更提议及审核状态</v-list-item-subtitle>
  <template #append>
    <v-chip v-if="pendingCount" color="warning" size="small">
      {{ pendingCount }} 条待审
    </v-chip>
    <v-icon>mdi-chevron-right</v-icon>
  </template>
</v-list-item>
```

#### 路由

```typescript
{
  path: 'profile/proposals',
  name: 'profile-proposals',
  component: () => import('@/views/profile/MyProposalsView.vue'),
  meta: { title: '我的提议' },
}
```

#### 新页面 `MyProposalsView.vue`

复用 `ProposalsView.vue` 的列表、状态筛选、详情对话框等逻辑，但：
- 无审核/回滚/反垃圾按钮（只有详情查看）
- 无策略配置 tab
- 状态筛选：全部 / 待审 / 已生效 / 已驳回 / 已回滚
- 列表列：状态、类型·动作、摘要、时间、详情按钮
- 详情对话框：完整的 diff 展示（与 ProposalsView 共享 proposalRenderers）
- 顶部可选提示：待审提议会在审核后收到邮件通知（如果配置了邮件）

---

## 功能三：邮件配置与发送

### 目标

管理员可在后台配置 SMTP 参数，系统在三类审核事件中异步发送邮件通知。

### 数据存储

#### 新增表 `smtp_config`

```sql
CREATE TABLE smtp_config (
    id INTEGER PRIMARY KEY DEFAULT 1,  -- 固定一行，id=1
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INTEGER NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls BOOLEAN NOT NULL DEFAULT 1,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 新增表 `email_templates`

```sql
CREATE TABLE email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) NOT NULL UNIQUE,           -- proposal_submitted / proposal_approved / proposal_rejected
    name VARCHAR(100) NOT NULL,                -- 中文显示名
    subject VARCHAR(255) NOT NULL,             -- 邮件主题模板（支持 ${variable} 替换）
    body_html TEXT NOT NULL,                   -- HTML 正文模板（支持 ${variable} 替换）
    description VARCHAR(500) DEFAULT '',       -- 说明，如"通知管理员有新提议需要审核"
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 邮件服务

```python
# backend/app/services/email_service.py

"""
SMTP 邮件发送服务。
异步发送：smtplib 调用封装在 threading.Thread 中，不阻塞请求响应。
"""

import smtplib
import threading
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from string import Template
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务。使用前检查 enabled 和 config 完整性。"""

    def __init__(self, config: Optional["SmtpConfig"] = None):
        self._config = config

    @property
    def ready(self) -> bool:
        return self._config is not None and self._config.enabled and bool(self._config.host)

    def send_template_async(self, template_key: str, to_email: str, variables: dict, db) -> None:
        """根据模板 key 渲染并异步发送。如果服务未就绪或模板不存在，静默跳过。"""
        if not self.ready:
            logger.warning("邮件服务未就绪，跳过发送")
            return
        from app.models.email_template import EmailTemplate
        template = db.query(EmailTemplate).filter(EmailTemplate.key == template_key).first()
        if not template:
            logger.warning("邮件模板 %s 不存在，跳过发送", template_key)
            return
        subject = Template(template.subject).safe_substitute(variables)
        body = Template(template.body_html).safe_substitute(variables)
        self._send_async(to_email, subject, body)

    def send_test_async(self, to_email: str) -> None:
        """发送测试邮件（用于 SMTP 配置页面的测试按钮）。"""
        self._send_async(to_email, "测试邮件", "<h1>SMTP 配置测试</h1><p>这是一封测试邮件，来自 LiveCalc。</p>")

    def _send_async(self, to_email: str, subject: str, body_html: str) -> None:
        thread = threading.Thread(target=self._send_sync, args=(to_email, subject, body_html), daemon=True)
        thread.start()

    def _send_sync(self, to_email: str, subject: str, body_html: str) -> None:
        config = self._config
        if not config or not config.host:
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{config.from_name} <{config.from_address}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            if config.use_tls:
                server = smtplib.SMTP(config.host, config.port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(config.host, config.port, timeout=10)

            if config.username:
                server.login(config.username, config.password)
            server.sendmail(config.from_address, [to_email], msg.as_string())
            server.quit()
            logger.info("邮件发送成功: to=%s subject=%s", to_email, subject)
        except Exception as e:
            logger.error("邮件发送失败: to=%s subject=%s error=%s", to_email, subject, e)
```

### 三个模板的默认值与可用变量

| key | name | 默认主题 | 可用变量 | 接收者 |
|---|---|---|---|---|
| `proposal_submitted` | 新提议通知 | `[LiveCalc] 新提议 #{proposal_id}` | `${proposer_name}, ${proposal_id}, ${entity_type_label}, ${action_label}, ${entity_label}` | 所有管理员 |
| `proposal_approved` | 提议通过通知 | `[LiveCalc] 提议 #{proposal_id} 已通过` | `${proposal_id}, ${entity_type_label}, ${action_label}, ${entity_label}` | 发起者 |
| `proposal_rejected` | 提议驳回通知 | `[LiveCalc] 提议 #{proposal_id} 未通过` | `${proposal_id}, ${entity_type_label}, ${action_label}, ${entity_label}, ${review_note}` | 发起者 |

### 三个邮件触发点

**触发点 1：用户提交提议 → 通知管理员**

位置：`backend/app/api/proposals.py` `submit_proposal` 端点，`db.commit()` 之后。

```python
if proposal.review_policy == "manual":
    _notify_admins_on_submit(db, proposal)
```

实现：
```python
def _notify_admins_on_submit(db, proposal):
    from app.services.email_service import EmailService
    from app.models.user import User
    service = EmailService(db.query(SmtpConfig).first())
    if not service.ready:
        return
    admins = db.query(User).filter(User.is_admin.is_(True)).all()
    variables = {
        "proposer_name": proposal.proposer.username if proposal.proposer else f"#{proposal.proposer_id}",
        "proposal_id": str(proposal.id),
        "entity_type_label": entity_type_label(proposal.entity_type),
        "action_label": action_label(proposal.action),
        "entity_label": _get_entity_label(db, proposal) or "",
    }
    for admin in admins:
        if admin.email:
            service.send_template_async("proposal_submitted", admin.email, variables, db)
```

**触发点 2：提议审核通过 → 通知发起者**

位置：`review_proposal` 端点，`db.commit()` 之后，`approved=True` 时。

```python
if body.approved:
    _notify_proposer_on_approve(db, proposal)
```

**触发点 3：提议审核拒绝 → 通知发起者**

位置：`review_proposal` 端点，`db.commit()` 之后，`approved=False` 时。

```python
else:
    _notify_proposer_on_reject(db, proposal, body.note)
```

`_notify_proposer_on_reject` 将 `review_note` 注入变量。

**注意**：三个触发点都是在 `db.commit()` **之后**异步发送。发送失败仅记日志，不阻断请求。

### 管理后台页面

#### 路由

```typescript
{
  path: 'admin/email-config',
  name: 'admin-email-config',
  meta: { adminOnly: true, title: '邮件配置' },
  component: () => import('@/views/admin/EmailConfigView.vue'),
}
```

#### 页面 `EmailConfigView.vue`

参考 `AiConfigView.vue` 的折叠面板模式：

**面板一：SMTP 配置**
- host (text field)
- port (number, 默认 587)
- username (text field)
- password (password field, 可切换显示)
- use TLS (switch, 默认开启)
- from address (email field)
- from name (text field, 默认"LiveCalc")
- enabled (switch)
- 保存按钮
- 测试发送按钮（输入测试邮箱后发送测试邮件）

**面板二：邮件模板**
- 三个模板分别展示在一个子卡片中
- 每个卡片：模板 key（只读）、name、subject、body_html（`<v-textarea>`，monospace 字体）
- 可用的变量提示（用 info alert 展示："可用变量: ${proposer_name}, ${proposal_id}..."）
- 保存按钮（每个卡片独立保存）

#### 后端 API

`backend/app/api/email_config.py` — 新增独立 router：

| 方法 | 路径 | 权限 | 功能 |
|---|---|---|---|
| GET | `/admin/email-config/smtp` | 管理员 | 获取 SMTP 配置（密码 masked） |
| PUT | `/admin/email-config/smtp` | 管理员 | 更新 SMTP 配置 |
| POST | `/admin/email-config/smtp/test` | 管理员 | 发送测试邮件 |
| GET | `/admin/email-config/templates` | 管理员 | 获取所有模板 |
| GET | `/admin/email-config/templates/{key}` | 管理员 | 获取单模板 |
| PUT | `/admin/email-config/templates/{key}` | 管理员 | 更新单模板 |

密码处理：GET 返回时 password 置为 `"******"` 或空字符串（前端保存时如果没改密码，不更新密码字段）。

#### 后台导航

`AdminDashboard.vue` 列表新增：
```vue
<v-list-item
  prepend-icon="mdi-email-cog"
  title="邮件配置"
  subtitle="SMTP 设置与邮件模板管理"
  to="/admin/email-config"
>
  <template #append>
    <v-icon>mdi-chevron-right</v-icon>
  </template>
</v-list-item>
```

---

## 数据库变更

### 新增表（三平台 SQL）

#### SQLite

```sql
CREATE TABLE smtp_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INTEGER NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls INTEGER NOT NULL DEFAULT 1,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    description VARCHAR(500) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### MySQL

```sql
CREATE TABLE smtp_config (
    id INT PRIMARY KEY DEFAULT 1,
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INT NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls TINYINT(1) NOT NULL DEFAULT 1,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE email_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    `key` VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    description VARCHAR(500) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### PostgreSQL（通用）

```sql
CREATE TABLE smtp_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INTEGER NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls BOOLEAN NOT NULL DEFAULT TRUE,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_templates (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    description VARCHAR(500) DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Alembic 迁移

新增迁移脚本，顺序：
1. 创建 `smtp_config` 表
2. 创建 `email_templates` 表
3. 插入三条默认模板数据（proposal_submitted / proposal_approved / proposal_rejected）

### 默认模板 HTML

**proposal_submitted**:
```html
<h2>新变更提议</h2>
<p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p>
<table>
  <tr><td>提议编号</td><td>#${proposal_id}</td></tr>
  <tr><td>实体类型</td><td>${entity_type_label}</td></tr>
  <tr><td>操作</td><td>${action_label}</td></tr>
  <tr><td>目标</td><td>${entity_label}</td></tr>
</table>
<p>请登录后台管理系统前往审核台处理。</p>
```

**proposal_approved**:
```html
<h2>提议已通过</h2>
<p>您的变更提议已通过审核并生效。</p>
<table>
  <tr><td>提议编号</td><td>#${proposal_id}</td></tr>
  <tr><td>实体类型</td><td>${entity_type_label}</td></tr>
  <tr><td>操作</td><td>${action_label}</td></tr>
  <tr><td>目标</td><td>${entity_label}</td></tr>
</table>
```

**proposal_rejected**:
```html
<h2>提议未通过</h2>
<p>您的变更提议未通过审核。</p>
<table>
  <tr><td>提议编号</td><td>#${proposal_id}</td></tr>
  <tr><td>实体类型</td><td>${entity_type_label}</td></tr>
  <tr><td>操作</td><td>${action_label}</td></tr>
  <tr><td>目标</td><td>${entity_label}</td></tr>
</table>
<p>审核备注：${review_note}</p>
```

---

## 文件清单

### 后端新增

| 文件 | 说明 |
|---|---|
| `backend/app/services/proposals/pending.py` | `get_pending_proposal` 通用查询 |
| `backend/app/services/email_service.py` | EmailService 异步邮件发送 |
| `backend/app/api/email_config.py` | SMTP 配置与模板 CRUD API |
| `backend/app/models/smtp_config.py` | SmtpConfig 模型 |
| `backend/app/models/email_template.py` | EmailTemplate 模型 |
| `backend/app/schemas/email_config.py` | 配置与模板的 Pydantic schema |
| `backend/alembic/versions/20260704_0001_add_email_tables.py` | 迁移脚本 |

### 后端修改

| 文件 | 改动 |
|---|---|
| `backend/app/api/proposals.py` | submit 后 + 审核后，触发邮件 |
| `backend/app/api/ingredient_extended.py` | `get_ingredient` 追加 `pending_proposal` |
| `backend/app/api/products_entity.py` | `get_product` 追加 `pending_proposal` |
| `backend/app/api/merchants.py` | `get_merchant` 追加 `pending_proposal` |
| `backend/app/api/recipes.py` | `get_recipe` 追加 `pending_proposal` |
| `backend/app/api/nutrition.py` | 营养详情追加 `pending_proposal` |
| `backend/app/main.py` | `include_router(email_config.router)` |
| `backend/app/services/proposals/bootstrap.py` | 启动时插入默认模板（if not exists） |

### 前端新增

| 文件 | 说明 |
|---|---|
| `frontend/src/components/proposals/PendingProposalBanner.vue` | 待审状态横幅组件 |
| `frontend/src/views/profile/MyProposalsView.vue` | 我的提议页面 |
| `frontend/src/views/admin/EmailConfigView.vue` | 邮件配置页面 |
| `frontend/src/api/emailConfig.ts` | 邮件配置 API 客户端 |

### 前端修改

| 文件 | 改动 |
|---|---|
| `frontend/src/views/profile/ProfileView.vue` | 添加"我的提议"入口 + pending 计数 |
| `frontend/src/views/ingredients/IngredientDetail.vue` | 集成 PendingProposalBanner + 草稿覆盖 |
| `frontend/src/views/products/ProductDetail.vue` | 同上 |
| `frontend/src/views/merchants/MerchantDetail.vue` | 同上 |
| `frontend/src/router/index.ts` | 新增 `/profile/proposals` 和 `/admin/email-config` 路由 |
| `frontend/src/views/admin/AdminDashboard.vue` | 新增"邮件配置"导航入口 |

---

## 无影响的模块

- 权限模型（users 表）无变更
- 现有提议框架 core（service.py / base.py / registry.py）无结构性变更
- 现有审核台 ProposalsView 无功能性变更
- 数据导出/导入无影响

注：本设计涉及的功能与后台管理中的提议审核台是完全独立的——审核台是管理员审批提议的工具，本设计是围绕审核流转的体验完善。
