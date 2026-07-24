# Flutter 移动端 App — P0+P1 基础设施与认证

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 Flutter 项目脚手架，集成核心基础设施（Dio、Riverpod、go_router、Material 3 主题、drift SQLite），完成登录/注册/服务器配置功能。产出可编译运行、可登录进入空白首页的 App。

**Architecture:** Feature-first 组织方式，core 层封装基础设施（API 客户端、数据库、路由、主题），features 层按功能模块组织。Riverpod 状态管理，Dio 封装 REST API 调用，go_router 管理路由栈和 Tab 导航。

**Tech Stack:** Flutter 3.x + Dart 3.x, flutter_riverpod, go_router, dio, drift, flutter_secure_storage, shared_preferences, flutter_native_splash

**Reference spec:** `docs/superpowers/specs/2026-07-24-livecalc-flutter-mobile-app-design.md`

---

## 文件结构规划

```
mobile/
├── pubspec.yaml
├── lib/
│   ├── main.dart                        # 入口：ProviderScope + 初始化
│   ├── app.dart                         # MaterialApp.router + 主题
│   ├── core/
│   │   ├── api/
│   │   │   ├── api_client.dart          # Dio 单例工厂（base URL 动态配置）
│   │   │   ├── auth_interceptor.dart    # 401 自动 refresh + 注入 X-Timezone
│   │   │   └── endpoints/
│   │   │       └── auth_endpoints.dart  # 可选的端点进一步封装
│   │   ├── database/
│   │   │   ├── app_database.dart        # drift Database 定义
│   │   │   └── tables.dart              # 表定义（offline_queue）
│   │   ├── router/
│   │   │   ├── app_router.dart          # go_router 主配置
│   │   │   └── route_names.dart         # 路由名称常量
│   │   ├── theme/
│   │   │   └── app_theme.dart           # Material 3 亮色/暗色主题
│   │   └── utils/
│   │       └── constants.dart           # 常量
│   ├── features/
│   │   ├── auth/
│   │   │   ├── models/                  # AuthConfig, LoginRequest, User
│   │   │   ├── providers/               # auth_provider, server_provider
│   │   │   ├── repositories/            # auth_repository
│   │   │   ├── screens/                 # server_config, login, register
│   │   │   └── widgets/                 # auth_text_field
│   │   ├── home/screens/home_screen.dart
│   │   ├── prices/screens/price_list_screen.dart
│   │   ├── recipes/screens/recipe_list_screen.dart
│   │   └── profile/screens/profile_screen.dart
│   └── shared/widgets/                  # loading, error, empty
├── android/
├── ios/
├── test/
│   ├── features/auth/
│   │   ├── providers/auth_provider_test.dart
│   │   └── repositories/auth_repository_test.dart
│   └── shared/widgets/
│       └── loading_indicator_test.dart
└── integration_test/
    └── auth_flow_test.dart
```

## 任务列表

### Task 1: Flutter 项目脚手架
- [ ] 创建 `mobile/` 目录，编写 `pubspec.yaml`（flutter_riverpod, go_router, dio, drift, flutter_secure_storage 等）
- [ ] 创建 `mobile/analysis_options.yaml`、`mobile/.gitignore`
- [ ] 创建 `mobile/lib/main.dart`（ProviderScope 入口）
- [ ] 创建 `mobile/lib/app.dart`（骨架 MaterialApp）
- [ ] 创建 `mobile/assets/images/` 目录
- [ ] 执行 `flutter pub get && flutter analyze` 验证无错误
- [ ] Commit: `feat(mobile): scaffold Flutter project`

### Task 2: Material 3 主题
- [ ] 创建 `mobile/lib/core/theme/app_theme.dart`
  - 亮色主题 + 暗色主题（`ColorScheme.fromSeed`，seed 色 #1976D2）
  - AppBarTheme、NavigationBarTheme、CardTheme、InputDecorationTheme
- [ ] 执行 `flutter analyze` 验证
- [ ] Commit: `feat(mobile): add Material 3 theme`

### Task 3: Dio API 客户端与拦截器
- [ ] 创建 `mobile/lib/core/api/api_client.dart`（Dio 单例工厂，`updateBaseUrl` 方法）
- [ ] 创建 `mobile/lib/core/api/auth_interceptor.dart`
  - 请求拦截器注入 `Authorization: Bearer <token>` 和 `X-Timezone`
  - 错误拦截器 401 时自动 refresh token
  - `saveTokens` / `clearTokens` 静态方法
- [ ] `flutter analyze` 验证
- [ ] Commit: `feat(mobile): add Dio API client with auth interceptor`

### Task 4: go_router 路由框架
- [ ] 创建 `route_names.dart`（路由常量）
- [ ] 创建 `app_router.dart`
  - 登录前：`/server-config` → `/login` → `/register`
  - 登录后：ShellRoute 包含 4 个 Tab `/home` `/prices` `/recipes` `/profile`
  - `ScaffoldWithNavBar` 组件：手机端 `NavigationBar` 底部 Tab，平板 `NavigationRail` 侧栏
  - `redirect` 逻辑：未认证跳 `/server-config`，已认证跳 `/home`
- [ ] 更新 `app.dart` 使用 `MaterialApp.router`
- [ ] `flutter analyze` 验证
- [ ] Commit: `feat(mobile): add go_router with tab navigation`

### Task 5: 4 个 Tab 占位页 + Drawer
- [ ] 创建 `home_screen.dart`（AppBar + 菜单按钮 + Drawer 入口）
- [ ] 创建 `price_list_screen.dart`（AppBar + FAB）
- [ ] 创建 `recipe_list_screen.dart`
- [ ] 创建 `profile_screen.dart`
- [ ] 更新 `ScaffoldWithNavBar` 添加 `NavigationDrawer`（搜索、原料管理、商品管理、商家管理、商家地图、报表、设置）
- [ ] `flutter analyze` 验证
- [ ] Commit: `feat(mobile): add placeholder tab screens with drawer`

### Task 6: 通用 UI 组件
- [ ] 创建 `shared/widgets/loading_indicator.dart`（CircularProgressIndicator + 可选文字）
- [ ] 创建 `shared/widgets/error_display.dart`（错误消息 + 重试按钮）
- [ ] 创建 `shared/widgets/empty_state.dart`（图标 + 标题 + 副标题 + 可选操作）
- [ ] `flutter analyze` + Commit

### Task 7: Auth 数据模型
- [ ] 创建 `models/auth_config.dart`（requireInviteCode, allowRegistration, fromJson）
- [ ] 创建 `models/login_request.dart`（LoginRequest, LoginResponse）
- [ ] 创建 `models/user.dart`（id, username, email, isAdmin, fromJson）
- [ ] `flutter analyze` + Commit

### Task 8: Auth Repository
- [ ] 创建 `repositories/auth_repository.dart`
  - `getConfig()` → `AuthConfig`
  - `login(LoginRequest)` → `LoginResponse`
  - `register(...)` → `LoginResponse`
  - `getCurrentUser()` → `User`
- [ ] `flutter analyze` + Commit

### Task 9: Auth & Server Provider（Riverpod）
- [ ] 创建 `providers/server_provider.dart`
  - `ServerConfigNotifier`：load/setUrl/clear（SharedPreferences 持久化）
- [ ] 创建 `providers/auth_provider.dart`
  - `AuthNotifier`：checkAuth/login/register/logout
  - `authProvider`（StateNotifierProvider）+ `isLoggedInProvider`
- [ ] `flutter analyze` + Commit

### Task 10: 服务器配置页
- [ ] 创建 `widgets/auth_text_field.dart`（通用认证输入框）
- [ ] 创建 `screens/server_config_screen.dart`
  - 输入框：服务器地址（https://...）
  - 按钮"连接服务器"：调用 AuthRepository.getConfig() 验证
  - 成功 → 保存地址 → 跳 `/login`
  - 失败 → 显示错误
- [ ] `flutter analyze` + Commit

### Task 11: 登录页 + 注册页
- [ ] 创建 `screens/login_screen.dart`
  - 用户名 + 密码 → AuthNotifier.login → 成功跳 `/home`
  - 失败显示错误、"去注册""更换服务器"链接
- [ ] 创建 `screens/register_screen.dart`
  - 用户名、邮箱、密码、手机号（可选）、邀请码（可选）
  - 注册成功跳 `/home`
- [ ] `flutter analyze` + Commit

### Task 12: AuthGuard 与路由联动
- [ ] 更新 `app_router.dart` redirect 逻辑：从 `authProvider` 读取状态
- [ ] `flutter analyze` + Commit

### Task 13: drift SQLite 数据库
- [ ] 创建 `tables.dart`：OfflineQueue（id, endpoint, method, payload, createdAt, synced, retryCount）
- [ ] 创建 `app_database.dart`：AppDatabase（enqueue, getPendingItems, markSynced, deleteSynced）
- [ ] `dart run build_runner build` 生成 `.g.dart`
- [ ] `flutter analyze` + Commit

### Task 14: 集成测试脚手架
- [ ] 创建 `integration_test/auth_flow_test.dart`（服务器配置页显示验证）
- [ ] Commit

### Task 15: 单元测试
- [ ] `test/features/auth/repositories/auth_repository_test.dart`
- [ ] `test/features/auth/providers/auth_provider_test.dart`
- [ ] `flutter test` 运行验证
- [ ] Commit

## 自审检查

- [x] **Spec 覆盖**：P0+P1 覆盖了 spec 的第 2、3、4、6、7、9、10 节
- [x] **无占位符**：所有步骤包含完整实现方向
- [x] **边界清晰**：每个 task 产出独立可验证的单元

## 下一阶段

P0+P1 完成后，进入 P2 核心业务页面：首页今日推荐、价格记录（含快速填写和数字键盘）、菜谱列表和详情。
