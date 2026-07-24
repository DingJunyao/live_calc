# 生记 · Flutter 移动端应用设计方案

> 生记（LiveCalc）移动端 App，基于 Flutter 跨平台框架，支持 Android/iOS/HarmonyOS。

## 1. 项目背景

生记是一套生活成本计算系统（FastAPI + Vue 3），已有完整的 Web 端功能。本次目标是为已有系统补充移动端原生 App，最大化复用现有后端 API，不做后端架构改动。

## 2. 技术选型

| 层面 | 选择 | 理由 |
|------|------|------|
| 框架 | Flutter 3.x | 一套代码编译 Android/iOS/HarmonyOS，性能接近原生 |
| 语言 | Dart | Flutter 官方语言 |
| 状态管理 | Riverpod | 类型安全、编译期可验证、无 BuildContext 依赖，易于测试 |
| HTTP 客户端 | dio | 拦截器机制成熟（token 刷新、超时重试），生态丰富 |
| 路由 | go_router | Flutter 官方推荐声明式路由，支持 ShellRoute 嵌套（Tab + Drawer） |
| 本地存储 | shared_preferences（偏好设置）+ drift（SQLite，离线缓存） | drift 类型安全，适合复杂查询 |
| 地图 | 平台 SDK（iOS MapKit / HarmonyOS PetalMaps） + flutter_map（Android） | 优先系统 SDK 避免授权问题；Android 碎片化用 flutter_map 换瓦片 |
| 图表 | fl_chart | 轻量无额外许可成本，覆盖折线图/饼图/柱状图需求 |
| 图片 | image_picker | 系统相册/相机选择 |
| 设计语言 | Material 3 | 与 Web 端 Vuetify（Material）风格一致 |

## 3. 项目结构

```
live_calc/
├── backend/              # 现有后端（不变）
├── frontend/             # 现有 Web 前端（不变）
└── mobile/               # ✨ 新 Flutter 项目
    ├── lib/
    │   ├── main.dart             # 入口
    │   ├── app.dart              # MaterialApp + 路由
    │   ├── core/                 # 基础设施
    │   │   ├── api/              # Dio 实例、拦截器、API 端点
    │   │   ├── database/         # drift SQLite 定义
    │   │   ├── router/           # go_router 配置（Tab + Drawer）
    │   │   ├── theme/            # Material 3 主题
    │   │   └── utils/            # 通用工具
    │   ├── features/             # 功能模块
    │   │   ├── auth/             # 登录/注册 + 服务器配置
    │   │   ├── home/             # 首页（今日推荐 + 快捷入口）
    │   │   ├── prices/           # 价格记录、快速填写、粘贴导入
    │   │   ├── recipes/          # 菜谱列表、详情、分析
    │   │   ├── ingredients/      # 原料管理
    │   │   ├── products/         # 商品管理
    │   │   ├── merchants/        # 商家管理 + 地图
    │   │   ├── profile/          # 个人中心、提议、地点
    │   │   └── report/           # 报表
    │   └── shared/               # 跨功能复用组件
    │       ├── widgets/          # 通用组件
    │       └── models/           # 共享数据模型
    ├── android/
    ├── ios/
    ├── harmony/                  # HarmonyOS 平台代码
    ├── test/
    └── pubspec.yaml
```

### 模块分组说明

采用按 feature 组织而非按类型组织（feature-first），每个 feature 内部可包含：

```
feature/
├── screens/        # 页面
├── widgets/        # 子组件
├── providers/      # Riverpod providers
├── models/         # 数据模型
└── services/       # 业务逻辑
```

页面少的功能可直接平铺不建子目录。

### 离线数据表（drift SQLite）

| 表 | 用途 | 同步策略 |
|----|------|----------|
| `products` | 商品缓存 | 写时同步 + 拉取更新 |
| `price_records` | 价格记录离线写入 | 联网后自动同步 |
| `recipes` | 菜谱缓存 | 首次打开拉取 |
| `merchants` | 商家缓存 | 首次打开拉取 |

## 4. 导航结构

### 4.1 登录导航（未认证）

```
/                   → 服务器地址配置页（首次或无配置时）
/login              → 登录页
/register           → 注册页
```

### 4.2 主导航（已认证）— ShellRoute + BottomTab + Drawer

四个底部 Tab，通过 go_router 的 `ShellRoute` 嵌套：

| Tab | 路由前缀 | 默认页 | 说明 |
|-----|----------|--------|------|
| 首页 | `/home` | HomeScreen | 今日推荐 + 快捷入口 |
| 记价 | `/prices` | PriceListScreen | 价格列表，FAB 快速记价 |
| 菜谱 | `/recipes` | RecipeListScreen | 菜谱网格 |
| 我的 | `/profile` | ProfileScreen | 个人中心 |

### 4.3 子路由

```
/home
  /home/meal/{date}           → 某日三餐详情

/prices
  /prices/records             → 价格列表（默认）
  /prices/quick-fill          → 快速填写页
  /prices/paste-import        → 粘贴导入

/recipes
  /recipes/{id}               → 菜谱详情
  /recipes/{id}/analysis      → 菜谱分析

/ingredients                  → 原料列表（Drawer）
  /ingredients/{id}           → 原料详情

/products
  /products/{id}              → 商品详情

/merchants                   → 商家列表（Drawer）
  /merchants/{id}            → 商家详情
  /merchants/map             → 商家地图

/profile
  /profile/places            → 我的地点
  /profile/proposals         → 我的提议
  /profile/settings          → 设置

/report                      → 报表
```

### 4.4 侧边抽屉（Drawer）

Drawer 从全局唤出（首页左上角菜单按钮，或左滑手势），包含：

- 搜索（全局）
- 原料管理 → `/ingredients`
- 商品管理 → `/products`
- 商家管理 → `/merchants`
- 商家地图 → `/merchants/map`
- 报表 → `/report`
- 设置 → `/profile/settings`

## 5. 核心页面设计

### 5.1 登录与服务器配置

**服务器配置页（首次启动）：**
- 文本框：服务器地址（https://...）
- "连接服务器"按钮 → 请求 `GET /api/v1/auth/config`
- 成功 → 跳转登录页；失败 → 显示错误提示
- 优先级：编译注入 `--dart-define=API_BASE_URL=` > 本地持久化 > 手动输入

**登录页：**
- 用户名 + 密码输入
- "登录"按钮
- "去注册"链接
- JWT token 存入安全存储（flutter_secure_storage）

**注册页：**
- 用户名、邮箱、密码、手机号（可选）、邀请码（可选）

### 5.2 首页

**布局：**
- AppBar：标题"生记" + 左侧 Drawer 展开按钮 + 右侧通知/设置
- 今日推荐卡片（三餐：早餐/午餐/晚餐），每餐显示推荐菜谱名和预计成本
- "换一换"按钮
- 快捷入口网格：记价、菜谱、原料、商品、商家
- 悬浮按钮（FAB）：快速记价

**数据流：** `GET /api/v1/meals/today` → 解析推荐结果 → 渲染卡片

### 5.3 价格记录

**列表页：**
- AppBar：标题"价格记录" + 搜索/筛选
- 价格记录列表（商家 + 商品名 + 价格 + 日期）
- 支持按商家、日期筛选
- FAB → 快速记价弹窗

**快速填写页（QuickFill）：**
- 第一步：选择商家（搜索 + 列表）
- 第二步：逐行填写价格
  - 每行：商品名 | 单价输入框 | 数量/单位
  - **数量输入：自定义大按钮数字键盘**
  - 支持添加新商品（搜索+选择原料）
- 保存：发送 `POST /products`（仅保存填了价格的）

**粘贴导入：**
- 对话框粘贴文本 → 解析（`名称 价格[/数量单位]` 四种格式）→ 预览 → 确认导入

**数据流：** `GET /api/v1/products?merchant_id=X` → 列表渲染
`POST /products` → 创建价格记录

### 5.4 菜谱

**列表页：**
- 卡片网格（封面图 + 菜名 + 预估成本）
- 搜索 + 分类筛选

**详情页：**
- 封面大图 + 菜名 + 简介
- 食材清单（食材名 + 用量 + 预估价格）
- 步骤列表（编号 + 描述 + 步骤图）
- 成本统计：总成本 + 各项占比（小型饼图）
- "分析"按钮 → 跳转分析页

**分析页：**
- 成本比例分布图（饼图）
- 营养素分布（NRV%）
- 历史成本趋势（折线图，周/月/季/全部）

**数据流：** `GET /api/v1/recipes/{id}` → 详情
`GET /api/v1/recipes/{id}/cost-history` → 成本趋势

### 5.5 原料管理

**列表页：**
- 原料列表（名称 + 分类层级）
- 搜索 + 分类筛选

**详情页：**
- 基本信息：名称、分类、别名
- 营养素数据（USDA 匹配结果）
- 挂靠商品列表（商品名 + 最新价格 + 权重）
- 价格趋势图（折线图）

### 5.6 商品管理

**列表页：**
- 商品列表（名称 + 挂靠原料 + 最新价格）
- 搜索筛选

**详情页：**
- 基本信息：名称、原料、条形码
- 价格记录列表（时间 + 金额 + 数量 + 商家）
- 支持编辑/删除价格记录

### 5.7 商家与地图

**商家列表：**
- 商家卡片（名称 + 地址 + 距离）
- 搜索 + 定位按钮

**商家详情：**
- 基本信息 + 位置
- 在该商家的价格记录列表
- "在地图上查看"按钮

**地图页：**
- iOS：`MapKit` 原生地图（`UIKitView` 嵌入）
- HarmonyOS：花瓣地图
- Android：`flutter_map` + 可配置瓦片（高德/百度/腾讯/OSM，读取服务端配置）
- 商家标记 + 点击弹出信息卡
- 定位到用户位置
- 常用地点快速切换

### 5.8 个人中心

**页面：**
- 用户头像 + 昵称 + 邮箱
- 设置项列表：
  - 单位偏好（质量/体积/能量）
  - 营养目标
  - 预算设置
  - 服务器地址
  - 关于
- "我的提议"入口
- "我的地点"入口
- "退出登录"按钮

## 6. 数据流与离线策略

### 6.1 API 层

Dio 实例配置：
- Base URL：从服务器配置获取
- 请求拦截器：自动注入 `Authorization: Bearer <token>` 和 `X-Timezone` 头
- 响应拦截器：401 时自动尝试 refresh token；refresh 失败则登出
- 超时：连接 10s，读写 30s

### 6.2 离线写入

价格记录在无网络时：
1. 写入本地 drift SQLite（`offline_queue` 表）
2. 标记 `synced: false`
3. 网络恢复后，`Connectivity` 监听触发同步
4. 同步成功 → 标记 `synced: true` + 删除本地队列项
5. 同步冲突 → 以服务端时间为准覆盖

### 6.3 读取优先顺序

```
内存缓存 (Riverpod State) → drift 本地库 → 网络请求 → 写入缓存
```

## 7. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 网络不可用 | 显示离线 banner，读本地缓存 |
| 请求超时 | 弹 SnackBar "网络超时，请重试" |
| 401 | 自动 refresh；失败 → 清除 token → 跳转登录 |
| 422/400 验证错误 | 显示服务端返回的具体错误信息 |
| 500 | 弹 SnackBar "服务异常，请稍后重试" |
| 无数据 | 显示空状态提示 + 操作引导 |

## 8. 测试策略

| 层级 | 范围 | 工具 |
|------|------|------|
| Unit | Provider、Service、数据模型 | `flutter_test` + `mocktail` |
| Widget | 核心页面组件 | `flutter_test` |
| Integration | 登录→记价→查菜谱主流程 | `integration_test` |
| E2E | 完整业务流程 | Patrol 或集成测试 |

## 9. 分支策略与开发阶段

### 分支
```
feat/mobile-app  ← 独立分支开发，不与主分支混合
```

### 开发阶段

| 阶段 | 内容 | 产出 |
|------|------|------|
| P0 基础设施 | Flutter 项目脚手架、Dio + Riverpod + go_router 集成、主题、本地数据库 | 可运行空白 App |
| P1 认证 | 服务器配置、登录、注册、token 管理 | 可登录 |
| P2 核心 | 首页、记价、快速填写、价格列表 | 可记价 |
| P3 菜谱 | 菜谱列表、详情、分析、成本 | 可看菜谱 |
| P4 资料 | 原料、商品、商家、地图 | 完整数据浏览 |
| P5 个人 | 个人中心、提议、地点、设置 | 完整功能 |
| P6 离线 | drift 离线表、同步队列、Connectivity 监听 | 离线可用 |
| P7 地图 | iOS MapKit / HarmonyOS PetalMaps / Android flutter_map | 地图可用 |
| P8 打磨 | 自定义数字键盘、动画、空状态、加载骨架、错误恢复 | 体验完善 |

## 10. 关键 Flutter Package 清单

```yaml
dependencies:
  flutter_riverpod: ^2.5
  riverpod_annotation: ^2.3
  go_router: ^14.0
  dio: ^5.4
  drift: ^2.16
  sqlite3_flutter_libs: ^0.5
  shared_preferences: ^2.2
  flutter_secure_storage: ^9.0
  fl_chart: ^0.68
  flutter_map: ^6.1
  image_picker: ^1.0
  connectivity_plus: ^6.0
  path_provider: ^2.1
  intl: ^0.19
  cupertino_icons: ^1.0
  latlong2: ^0.9

dev_dependencies:
  flutter_test:
    sdk: flutter
  riverpod_generator: ^2.4
  build_runner: ^2.4
  drift_dev: ^2.16
  mocktail: ^1.0
```

## 11. 未纳入 v1（后续迭代）

- 管理员功能（用户管理、单位管理、地图配置、AI 配置、数据维护、Agent 台等）
- 数据导入/导出
- USDA 营养素匹配主动操作
- 提议审核
- 通知推送
- 多语言
