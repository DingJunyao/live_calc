# 生计 - 生活成本计算器 设计文档

**创建日期:** 2026-02-25
**版本:** 1.0
**项目名称:** 生计 (Life Calculator)

---

## 目录

1. [项目概述](#项目概述)
2. [整体架构](#整体架构)
3. [数据模型](#数据模型)
4. [核心功能模块](#核心功能模块)
5. [前端设计](#前端设计)
6. [后端 API 设计](#后端-api-设计)
7. [部署与配置](#部署与配置)
8. [技术栈](#技术栈)

---

## 项目概述

### 项目简介

"生计"是一个基于 Web 的生活成本计算器，支持移动端 PWA。核心功能包括：

- 记录不同时间、不同地点的商品价格、重量、单价等信息
- 计算烹饪一道菜所需食材的成本，估计其营养成分
- 推荐经济实惠、营养均衡的购买和烹饪方案
- 生成每日、每周、每月的生活成本报告

### 核心需求

1. **用户系统** - 支持公开注册和邀请码注册，混合模式，后台可切换
2. **商品价格记录** - 支持实际购买和单价记录，多币种，多单位系统
3. **菜谱管理** - 支持 GitHub HowToCook 数据导入，用户自定义菜谱
4. **营养分析** - 集成 USDA 营养数据库，中英文智能匹配
5. **地图集成** - 支持多地图服务，路线规划和成本计算
6. **报告统计** - 深度分析报告，支持数据导出
7. **混合部署** - 支持 Docker 镜像和代码直接部署

### MVP 范围

**核心功能优先**，包含基础支撑模块：
- 商品价格记录
- 菜谱成本计算
- 基础报告功能
- 注册登录
- 地点管理
- 营养数据

---

## 整体架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         前端层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Vue.js SPA  │  │   PWA 应用   │  │  移动端支持   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                         后端层                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              FastAPI 应用（单体）                       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │   │
│  │  │  用户模块   │ │  数据模块   │ │  报告模块   │      │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │   │
│  │  │  菜谱模块   │ │  地图模块   │ │  配置模块   │      │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       任务管理层                               │
│  ┌──────────────────┐        ┌──────────────────┐            │
│  │  内置任务调度器   │  ←→   │  Celery（可选）  │            │
│  │  (APScheduler)   │        │   (后台切换)     │            │
│  └──────────────────┘        └──────────────────┘            │
│  任务：汇率更新、数据导入、报告生成等                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       数据层                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │   SQLite     │ │  MySQL/PG    │ │  Redis缓存   │         │
│  │  (开发默认)   │ │  (生产环境)   │ │  (可选)      │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       外部服务                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│  │   地图API   │ │  营养数据库 │ │   汇率API   │             │
│  └─────────────┘ └─────────────┘ └─────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                       Docker 环境                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Nginx     │  │  FastAPI    │  │  PostgreSQL │     │
│  │  (反向代理)  │  │  (应用容器)  │  │  (数据库)   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│  ┌─────────────┐  ┌─────────────┐                      │
│  │   Redis     │  │  Celery     │                      │
│  │  (缓存/队列) │  │  (任务容器)  │                      │
│  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

---

## 数据模型

### 核心实体关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   用户       │1   N  │   商品记录   │N   1  │   购买地点   │
└─────────────┘───────└─────────────┘───────└─────────────┘
│ id          │       │ id          │       │ id          │
│ username    │       │ user_id     │       │ name        │
│ password    │       │ product_name│       │ address     │
│ email       │       │ location_id │       │ longitude   │
│ phone       │       │ price       │       │ latitude    │
│ is_admin    │       │ original_qty│       │ user_id     │
│ invite_code │       │ standard_qty│       └─────────────┘
└─────────────┘       │ unit        │
                      │ currency    │
                      │ exchange_rate│
                      │ record_type │
                      │ recorded_at │
                      └─────────────┘

┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   菜谱       │1   N  │   菜谱食材   │N   1  │   食材       │
└─────────────┘───────└─────────────┘───────└─────────────┘
│ id          │       │ id          │       │ id          │
│ name        │       │ recipe_id   │       │ name        │
│ source      │       │ ingredient_id│     │ nutrition_id │
│ user_id     │       │ quantity    │       │ aliases     │
│ cooking_steps│      │ unit        │       └─────────────┘
│ ...         │       └─────────────┘
└─────────────┘

┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  营养数据     │1   N  │  食材营养映射  │       │  汇率记录    │
└─────────────┘───────└─────────────┘       └─────────────┘
│ id          │       │ id          │       │ date        │
│ usda_id     │       │ ingredient_id│     │ from_currency│
│ name_en     │       │ nutrition_id│     │ to_currency │
│ calories    │       └─────────────┘       │ rate        │
│ protein     │                              └─────────────┘
│ fat         │
│ carbs       │
│ ...         │
└─────────────┘

┌─────────────┐       ┌─────────────┐
│  常用位置     │1   N  │  费用记录    │
└─────────────┘───────└─────────────┘
│ id          │       │ id          │
│ name        │       │ user_id     │
│ user_id     │       │ type        │  (水/气/电/交通)
│ latitude    │       │ amount      │
│ longitude   │       │ unit        │
└─────────────┘       │ date        │
                      └─────────────┘
```

### 关键数据表说明

#### 商品记录表 (product_records)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户 ID |
| product_name | String | 商品名称 |
| location_id | Integer | 购买地点 ID |
| price | Decimal | 价格 |
| currency | String | 币种 |
| original_quantity | Decimal | 用户输入的数量 |
| original_unit | String | 用户输入的单位 |
| standard_quantity | Decimal | 标准单位数量（克/毫升/千克） |
| standard_unit | String | 标准单位 |
| record_type | Enum | 记录类型（purchase/price） |
| exchange_rate | Decimal | 当天汇率 |
| recorded_at | DateTime | 记录时间 |
| notes | Text | 备注 |

#### 菜谱表 (recipes)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String | 菜谱名称 |
| source | String | 来源（HowToCook/自定义） |
| user_id | Integer | 创建用户 ID |
| tags | JSON | 标签列表 |
| cooking_steps | JSON | 做法步骤 |
| total_time_minutes | Integer | 总耗时（分钟） |
| difficulty | String | 难度（简单/中等/复杂） |
| servings | Integer | 份量 |
| tips | JSON | 小贴士 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 菜谱食材表 (recipe_ingredients)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| recipe_id | Integer | 菜谱 ID |
| ingredient_id | Integer | 食材 ID |
| quantity | Decimal | 数量 |
| unit | String | 单位 |

#### 食材表 (ingredients)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String | 食材名称 |
| nutrition_id | Integer | 营养数据 ID |
| aliases | JSON | 同义词/别名 |

#### 营养数据表 (nutrition_data)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| usda_id | String | USDA ID |
| name_en | String | 英文名称 |
| calories | Decimal | 卡路里 |
| protein | Decimal | 蛋白质 (g) |
| fat | Decimal | 脂肪 (g) |
| carbs | Decimal | 碳水化合物 (g) |
| fiber | Decimal | 纤维 (g) |
| sugar | Decimal | 糖分 (g) |
| sodium | Decimal | 钠 (mg) |

#### 食材营养映射表 (ingredient_nutrition_mapping)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| ingredient_id | Integer | 食材 ID |
| nutrition_id | Integer | 营养数据 ID |
| priority | Integer | 优先级 |
| confidence | Decimal | 置信度 |

#### 汇率记录表 (exchange_rates)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| date | Date | 日期 |
| from_currency | String | 源币种 |
| to_currency | String | 目标币种 |
| rate | Decimal | 汇率 |

#### 常用位置表 (favorite_locations)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String | 位置名称 |
| user_id | Integer | 用户 ID |
| latitude | Decimal | 纬度 |
| longitude | Decimal | 经度 |
| type | String | 类型（家/工作地/其他） |

#### 费用记录表 (expenses)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 用户 ID |
| type | Enum | 类型（水/气/电/交通） |
| amount | Decimal | 数量 |
| unit | String | 单位 |
| date | Date | 日期 |

---

## 核心功能模块

### 1. 用户模块

#### 功能清单
- 用户注册（公开/邀请码模式，后台可切换）
- 用户登录（密码 SHA256 前端加密）
- 权限管理（首用户为管理员）
- 用户资料编辑
- 数据导出
- 账户注销与数据删除

#### 注册流程
```
用户填写信息 → 前端 SHA256 加密密码 → 检查邀请码（如需要）→
创建用户 → 发送验证邮件 → 验证成功 → 自动登录
```

### 2. 商品价格记录模块

#### 功能清单
- 添加商品记录（实际购买/单价记录）
- 编辑/删除商品记录
- 商品历史价格查询
- 价格趋势图表
- 单位自动转换

#### 价格记录流程
```
选择购买地点 → 输入商品信息（名称/价格/数量/单位）→
系统自动获取当天汇率 → 双重存储（原始值+标准值）→ 保存
```

### 3. 菜谱模块

#### 功能清单
- 菜谱创建/编辑/删除
- 菜谱导入（GitHub HowToCook，系统启动/后台手动）
- 菜谱分享（导出/导入）
- 菜谱标签/分类
- 菜谱成本计算
- 菜谱营养分析

#### 成本计算流程
```
遍历菜谱食材 → 获取关联标准食材 →
查找用户历史价格记录 → 按时间倒序获取最新价格 →
根据数量和单位计算总价 → 汇总所有食材成本
```

#### 首次启动导入流程
```
系统启动 → 检查是否首次运行 →
从 GitHub 克隆 HowToCook 数据 → 解析菜谱 →
关联标准食材 → 批量导入数据库
```

### 4. 营养数据库模块

#### 功能清单
- USDA 营养数据库导入
- 中文食材名称映射管理
- 混合匹配算法（映射表+关键词模糊搜索）
- 用户更正学习
- 营养成分查询

#### 匹配算法
```
用户输入食材名称 →
1. 优先查找映射表精确匹配
2. 未匹配则关键词模糊搜索（中→英翻译关键词）
3. 返回匹配候选项（按置信度排序）
4. 用户选择/更正 → 更新映射表（学习）
```

### 5. 地图与位置模块

#### 功能清单
- 地图展示（多地图底图支持）
- 购买地点添加/编辑/删除
- 常用位置管理（家/工作地/其他）
- 路线规划（集成地图 API）
- 交通成本计算

#### 地图服务切换
```
无 API Key：
中国大陆 → 高德地图（免费瓦片）
海外 → OpenStreetMap

有 API Key：
使用对应地图的原生引擎（高德/百度/腾讯）
```

### 6. 报告模块

#### 功能清单
- 每日/每周/每月支出报告
- 分类统计（食材/交通/水电气）
- 营养摄入趋势
- 单价价格变化趋势
- 购买地点性价比分析
- 报告导出（PDF/Excel）

#### 深度分析报告内容
1. 基础统计 - 总支出、分类支出、趋势图表
2. 营养摄入趋势 - 按时间段聚合菜谱营养数据
3. 单价变化趋势 - 同一商品历史价格波动
4. 购买地点性价比 - 同一商品不同地点价格对比

### 7. 后台任务管理模块

#### 功能清单
- 任务调度器切换（内置 APScheduler / Celery）
- 任务管理（启动/停止/监控）
- 任务日志查看
- 配置管理

#### 任务类型
1. 汇率更新 - 每日自动更新汇率数据
2. 菜谱数据导入 - 从 GitHub 更新菜谱数据
3. 报告生成 - 定期生成统计报告

---

## 前端设计

### 技术栈
- Vue 3 + Vite
- Pinia（状态管理）
- Vue Router（路由）
- Leaflet（地图）
- PWA 支持

### 核心页面结构

```
/src/views
├── auth/
│   ├── Login.vue          # 登录页
│   ├── Register.vue       # 注册页
│   └── ForgotPassword.vue # 忘记密码
├── dashboard/
│   ├── Dashboard.vue      # 仪表盘首页
│   └── QuickAdd.vue       # 快速添加记录
├── products/
│   ├── ProductList.vue    # 商品列表
│   ├── ProductForm.vue    # 商品添加/编辑
│   └── ProductHistory.vue # 商品历史价格
├── recipes/
│   ├── RecipeList.vue     # 菜谱列表
│   ├── RecipeDetail.vue   # 菜谱详情（含成本/营养）
│   └── RecipeForm.vue    # 菜谱添加/编辑
├── locations/
│   ├── LocationMap.vue    # 地图视图
│   ├── LocationList.vue   # 地点列表
│   └── FavoriteLocations.vue # 常用位置
├── reports/
│   ├── ReportOverview.vue # 报告总览
│   ├── ExpenseReport.vue  # 支出报告
│   ├── NutritionReport.vue # 营养报告
│   └── PriceTrend.vue     # 价格趋势
├── admin/
│   ├── AdminDashboard.vue # 管理后台
│   ├── UserManagement.vue # 用户管理
│   └── TaskManagement.vue # 任务管理
└── settings/
    ├── Profile.vue        # 个人资料
    ├── Settings.vue       # 系统设置
    └── DataExport.vue     # 数据导出
```

### 移动端适配策略
1. 响应式布局
2. 触摸优化（最小点击区域 44x44px）
3. 离线支持（PWA）
4. 底部导航（移动端）
5. 表单优化

---

## 后端 API 设计

### API 基础规范
- **Base URL**: `/api/v1`
- **认证方式**: Bearer Token (JWT)
- **请求格式**: JSON
- **响应格式**: 统一 JSON 响应

### 统一响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 核心端点

#### 认证模块
```
POST   /api/v1/auth/register          # 用户注册
POST   /api/v1/auth/login             # 用户登录
POST   /api/v1/auth/logout            # 用户登出
POST   /api/v1/auth/refresh           # 刷新 Token
POST   /api/v1/auth/forgot-password   # 忘记密码
POST   /api/v1/auth/reset-password    # 重置密码
GET    /api/v1/auth/verify-email      # 邮箱验证
```

#### 商品记录模块
```
GET    /api/v1/products              # 获取商品列表
POST   /api/v1/products              # 添加商品记录
GET    /api/v1/products/:id          # 获取商品详情
PUT    /api/v1/products/:id          # 更新商品记录
DELETE /api/v1/products/:id          # 删除商品记录
GET    /api/v1/products/:id/history  # 获取商品历史价格
```

#### 菜谱模块
```
GET    /api/v1/recipes               # 获取菜谱列表
POST   /api/v1/recipes               # 创建菜谱
GET    /api/v1/recipes/:id           # 获取菜谱详情（含做法）
PUT    /api/v1/recipes/:id           # 更新菜谱
DELETE /api/v1/recipes/:id           # 删除菜谱
GET    /api/v1/recipes/:id/cost      # 计算菜谱成本
GET    /api/v1/recipes/:id/nutrition # 计算菜谱营养
POST   /api/v1/recipes/:id/share     # 分享菜谱（导出）
POST   /api/v1/recipes/import        # 导入菜谱
GET    /api/v1/recipes/tags          # 获取标签列表
```

#### 营养数据库模块
```
GET    /api/v1/nutrition/search      # 搜索营养数据
GET    /api/v1/nutrition/:id         # 获取营养详情
POST   /api/v1/nutrition/match       # 匹配食材
POST   /api/v1/nutrition/correct     # 更正匹配
GET    /api/v1/nutrition/mappings    # 获取映射表
```

#### 地图与位置模块
```
GET    /api/v1/locations             # 获取地点列表
POST   /api/v1/locations             # 添加地点
GET    /api/v1/locations/:id         # 获取地点详情
PUT    /api/v1/locations/:id         # 更新地点
DELETE /api/v1/locations/:id         # 删除地点
GET    /api/v1/locations/favorites   # 获取常用位置
POST   /api/v1/locations/favorites   # 添加常用位置
DELETE /api/v1/locations/favorites/:id # 删除常用位置
POST   /api/v1/locations/route       # 计算路线
GET    /api/v1/locations/nearby      # 附近地点查询
```

#### 报告模块
```
GET    /api/v1/reports/overview      # 报告总览
GET    /api/v1/reports/expense       # 支出报告
GET    /api/v1/reports/nutrition     # 营养报告
GET    /api/v1/reports/price-trend   # 价格趋势
GET    /api/v1/reports/location-analysis # 地点分析
POST   /api/v1/reports/export        # 导出报告
```

#### 费用记录模块
```
GET    /api/v1/expenses              # 获取费用记录
POST   /api/v1/expenses              # 添加费用记录
GET    /api/v1/expenses/:id          # 获取费用详情
PUT    /api/v1/expenses/:id          # 更新费用记录
DELETE /api/v1/expenses/:id          # 删除费用记录
```

#### 用户与数据管理
```
GET    /api/v1/users/profile         # 获取用户资料
PUT    /api/v1/users/profile         # 更新用户资料
POST   /api/v1/users/change-password # 修改密码
POST   /api/v1/users/export-data     # 导出用户数据
POST   /api/v1/users/delete-account  # 删除账户
GET    /api/v1/users/settings        # 获取用户设置
PUT    /api/v1/users/settings        # 更新用户设置
```

#### 管理后台
```
GET    /api/v1/admin/users           # 用户列表（管理员）
PUT    /api/v1/admin/users/:id       # 管理用户（管理员）
POST   /api/v1/admin/invite-codes    # 生成邀请码（管理员）
GET    /api/v1/admin/tasks           # 任务管理（管理员）
POST   /api/v1/admin/tasks/:id/control # 控制任务（管理员）
GET    /api/v1/admin/recipes/import  # 导入菜谱数据（管理员）
```

---

## 部署与配置

### 部署模式

1. **Docker 镜像部署** - 一键启动，包含数据库和应用
2. **代码直接部署** - 使用 Poetry/pip 安装依赖，手动配置
3. **混合支持** - 开发时代码部署，生产时 Docker 部署

### 环境变量配置

```bash
# 数据库配置
DATABASE_URL=sqlite:///./data/livecalc.db

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0

# 应用配置
APP_NAME=生计
APP_URL=http://localhost:8000
SECRET_KEY=your-secret-key-here

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 注册配置
REGISTRATION_REQUIRE_INVITE_CODE=false

# 地图服务配置
DEFAULT_MAP_PROVIDER=amap
AMAP_API_KEY=your-amap-api-key
BAIDU_API_KEY=your-baidu-api-key
TENCENT_API_KEY=your-tencent-api-key

# 任务调度配置
TASK_SCHEDULER_TYPE=apscheduler
```

### 混合部署模式支持

1. **自托管模式** - 用户自行部署，数据本地存储
2. **云服务模式** - 运营方控制，多租户数据隔离
3. **配置切换** - 通过 `DEPLOYMENT_MODE` 环境变量控制

---

## 技术栈

### 前端
| 技术 | 说明 |
|------|------|
| Vue 3 | 渐进式 JavaScript 框架 |
| Vite | 快速构建工具 |
| Pinia | 状态管理 |
| Vue Router | 路由管理 |
| Leaflet | 地图组件 |
| Tailwind CSS | 样式框架（可选） |

### 后端
| 技术 | 说明 |
|------|------|
| FastAPI | 现代异步 Web 框架 |
| SQLAlchemy | ORM |
| Alembic | 数据库迁移 |
| Pydantic | 数据验证 |
| APScheduler | 内置任务调度 |
| Celery | 可选分布式任务队列 |

### 数据库
| 技术 | 说明 |
|------|------|
| SQLite | 开发默认 |
| PostgreSQL | 生产环境推荐 |
| MySQL | 可选支持 |

### 容器化
| 技术 | 说明 |
|------|------|
| Docker | 容器化部署 |
| Docker Compose | 多容器编排 |

---

## 附录

### 支持的币种

- 人民币 (CNY)
- 美元 (USD)
- 欧元 (EUR)
- 日元 (JPY)
- 港币 (HKD)
- 澳门币 (MOP)
- 新台币 (TWD)

### 支持的单位

| 类型 | 单位 |
|------|------|
| 重量 | 克(g)、千克(kg)、斤、两、磅(lb)、盎司(oz) |
| 容量 | 毫升(ml)、升(l)、杯、汤匙、茶匙 |
| 数量 | 个、片、块、包、盒 |

### 地图服务商

- 高德地图 (Amap)
- 百度地图 (Baidu)
- 腾讯地图 (Tencent)
- 天地图 (Tianditu)
- OpenStreetMap (OSM)

---

**文档版本:** 1.0
**最后更新:** 2026-02-25
