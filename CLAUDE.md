# 生计 - 生活成本计算器

## 项目概述

这是一个全栈的生活成本计算器应用，旨在帮助用户记录商品价格、计算烹饪成本、优化生活开支。

### 核心功能
- 📝 商品价格记录 - 记录不同时间、不同地点的商品价格
- 🍳 菜谱成本计算 - 根据价格记录计算菜谱成本
- 🥗 营养成分分析 - 基于 USDA 数据库的营养分析
- 📍 地图与路线规划 - 集成地图服务，计算出行成本
- 📊 生活成本报告 - 生成每日、每周、每月报告
- 💰 多币种支持 - 支持多种货币
- 🌏 多单位转换 - 支持公制/市制/英制转换
- 🔐 用户认证 - 支持 JWT 认证和邀请码注册

## 系统架构

```
live_calc/
├── backend/              # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/        # API 路由定义
│   │   ├── core/       # 核心配置与安全
│   │   ├── models/     # 数据库模型
│   │   ├── schemas/    # Pydantic 模式
│   │   ├── services/   # 业务逻辑层
│   │   └── utils/      # 工具函数
│   ├── alembic/        # 数据库迁移
│   └── tests/          # 测试用例
├── frontend/            # 前端应用 (Vue 3)
│   ├── src/
│   │   ├── api/       # API 客户端
│   │   ├── components/ # 可复用组件
│   │   ├── stores/    # Pinia 状态管理
│   │   ├── views/     # 页面视图
│   │   └── router/    # 路由配置
│   └── public/         # 静态资源
├── docker-compose.yml   # Docker 编排
└── README.md           # 项目文档
```

## 技术栈

### 后端 (FastAPI)
- **框架**: FastAPI - 现代化的 Python Web 框架
- **ORM**: SQLAlchemy - Python SQL 工具包和对象关系映射
- **迁移**: Alembic - 数据库迁移工具
- **认证**: Python-JOSE + Passlib - JWT 认证和密码哈希
- **任务调度**: APScheduler - 任务调度器
- **异步任务**: Celery（可选）- 分布式任务队列

### 前端 (Vue 3)
- **框架**: Vue 3 - 渐进式 JavaScript 框架
- **构建工具**: Vite - 新一代前端构建工具
- **状态管理**: Pinia - Vue 的官方状态管理库
- **路由**: Vue Router - 官方路由管理器
- **HTTP 客户端**: Axios - Promise 基础的 HTTP 客户端
- **地图**: Leaflet - 开源地图库
- **图表**: Chart.js - 简单灵活的图表库

### 数据库
- **开发**: SQLite - 轻量级嵌入式数据库
- **生产**: PostgreSQL / MySQL - 企业级数据库

### 容器化
- **容器**: Docker - 容器化平台
- **编排**: Docker Compose - 多容器应用编排
- **Web 服务器**: Nginx - 高性能 Web 服务器

## 模块说明

### 后端模块
- **auth** - 用户认证与授权
- **products** - 商品价格记录与历史追踪
- **locations** - 地点管理与地图服务
- **nutrition** - 营养数据库与匹配算法
- **recipes** - 菜谱管理与成本计算
- **reports** - 报告生成与统计分析

### 前端模块
- **auth** - 登录/注册页面
- **dashboard** - 仪表盘与概览
- **products** - 商品管理界面
- **recipes** - 菜谱管理界面
- **locations** - 地点与地图界面
- **reports** - 报告与统计界面

## API 端点

### 认证 API
- `GET /api/v1/auth/config` - 获取注册配置
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新令牌
- `GET /api/v1/auth/me` - 获取当前用户信息

### 核心 API
- `GET/POST /api/v1/products/` - 商品价格记录
- `GET/POST /api/v1/locations/` - 地点管理
- `GET/POST /api/v1/nutrition/` - 营养数据
- `GET/POST /api/v1/recipes/` - 菜谱管理
- `GET/POST /api/v1/reports/` - 报告统计

## 开发规范

### Python 代码规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 Flake8 进行代码检查
- 使用 MyPy 进行类型检查

### JavaScript/TypeScript 代码规范
- 使用 Prettier 进行代码格式化
- 使用 ESLint 进行代码检查
- 遵循 Vue 3 最佳实践

### Git 工作流
- 使用 Conventional Commits 提交规范
- 保持主分支稳定
- 功能开发在特性分支进行
- 通过 Pull Request 进行代码审查

## 环境变量

### 后端
- `DATABASE_URL` - 数据库连接字符串
- `SECRET_KEY` - 应用密钥
- `JWT_SECRET_KEY` - JWT 签名密钥
- `REGISTRATION_REQUIRE_INVITE_CODE` - 是否需要邀请码注册

### 前端
- `VITE_API_URL` - 后端 API 地址（默认为 `/api/v1`）

## 开发情况

本项目为 monorepo 项目，包含前端和后端。

### 前端

技术栈：TypeScrPt + Vue + Vite

目录：`frontend`，所有前端相关操作均在此目录下进行。

开发 URL：`http://localhost:5173`

通常会打开浏览器调试。如有需要，可以使用 Chrome 开发者工具 MCP 查看页面情况，操作页面。由于一般情况下已经打开了页面，所以不要使用 Playwright。开发者在 Windows 下使用 Edge 浏览器，在 Linux 下使用 Chromium 浏览器。

响应式设计。开发时要兼顾不同地图引擎和桌面、移动端的体验。

目前需要考虑的地图引擎如下：

- 高德地图
- 百度地图（分为 GL 版本和 Legacy 版本，前者常用，后者只在一些特殊场景下使用）
- 腾讯地图
- Leaflet：目前支持高德地图、百度地图、腾讯地图、天地图、OpenStreetMap。

所有前端的修改都必须确保构建通过。

### 后端

技术栈：Python + FastAPI

目录：`backend`，所有后端相关操作均在此目录下进行，并且使用虚拟环境。

开发时使用 `uv` 管理。

虚拟环境：根目录下的 `.venv` 下的环境。

所有后端的修改都必须确保无语法错误。

### 数据库

数据库：`backend/.env` 文件中指定。一般情况下为 `backend/data/livecalc.db`。

数据库操作优先使用相应的 MCP。

开发过程中不要自行修改数据库，除非开发者明确允许此操作。

表结构需要变动时，除了维护 alembic 外，还需要提供对应的 SQL 脚本，包括一下数据库引擎的版本：

- SQLite
- MySQL
- PostgreSQL（未启用 PostGIS 支持）
- PostgreSQL（启用 PostGIS 支持）（如与 PostGIS 无关，则不需要此项）

### 测试

所有操作均需确保无语法层面上的报错，构建、编译通过。

不要在对话中启动服务，因为我已经启动了自动重载的前端、后端服务。

### 记录要点

当某项开发工作完成、告一段落或有关键性进展时，需要自动记录要点。用户要求记录要点时，也要记录。

要点按照以下的索引记录。

注意：为了节约 token，即便用户要求记录到 CLAUDE.md，也要按照下面的索引记录。

定期清理最新修复记录，以减少 token 消耗。保留 10 条最近的修复记录。

### 不同分支的修改限制

目前有三个需要留意的分支：

- `master`: 主分支，包括 web 前端、后端
- `feat/local`：开发本地模式的分支
- `feat/mobile-app`：开发移动 App 的分支

注意：feat 分支只更改各自新增功能的问题和功能。比如：feat/local 只更改本地模式的功能和问题，feat/mobile-app 只更改移动端的功能和问题。如确有涉及到主分支上 web 前端、后端的问题，请更改到 master 分支修改，然后将修改合并到各 feat 分支。

### 各端体验一致性

移动端 app 在体验上要与 web 前端保持一致。

尽管移动端 app 在 UI 上偏向于原生，但功能上要保持一致，比如：价格列表，每项能够看到的内容要一样。

## Tips

> 来自 Claude Code 的 Inspect 工具。

### Overall

Before writing any fix, trace the full data flow for this bug: from database query → serialization → API response → frontend rendering. Show me what each layer returns at each step, and identify exactly which layer the bug is in. Do NOT propose a fix until you've completed this trace.

Before writing any SQL, run \d tablename or SELECT column_name, data_type FROM information_schema.columns WHERE table_name='tablename' to verify the exact column names and types. Then write your SQL using only confirmed column names.

Use a subagent to explore and map out the full codebase structure for feature, including all files, functions, and data flows involved. Return a detailed map. Then I'll review it before we start implementing step by step.

### Code Quality

Always verify column names, field names, and API paths against the actual codebase before writing SQL or making edits. Never guess — use Grep or Read to confirm the correct name.

### Debugging

When fixing bugs, always trace the full data pipeline end-to-end before proposing a fix. For backend→API→frontend flows, check: (1) DB query/storage, (2) serialization (_to_response or schema), (3) API response shape, (4) frontend consumption.

Before creating new data mappings or lookups, always check if the data already exists in related tables (e.g., entity_unit_overrides, existing product/ingredient records). Use Grep to search for existing implementations.

### Database

When working with PostgreSQL, never use JSON LIKE queries or naive/aware datetime comparisons without explicitly checking compatibility. Prefer ilike for text, and always ensure datetime objects are timezone-aware before comparison.

For boolean columns in SQL INSERT/UPDATE statements, always use true/false (SQL literals), not 0/1 (integers). Python False does not automatically map correctly in all ORMs.

### Architecture

When the user reports a permission/error issue, do not just add a permission check or toggle on the endpoint. First understand the intended UX flow — some operations should not exist as separate endpoints at all (e.g., image deletion should be part of recipe update, not a standalone DELETE).

## Testing

After editing Python files that may be cached (__pycache__, .pyc), remind the user to restart the server or clear cache before testing, to avoid false negatives where the fix appears not to work.

## 项目索引

本项目文档已模块化拆分，按需加载以提高性能。详细信息请查看 `./cc` 目录下的对应文件。

所有与 Claude Code 相关的文档，都放在 `./cc` 目录下。并且，在这里描述文档内容，以便索引。

如：部署说明：详见 [DEPLOYMENT.md](cc/DEPLOYMENT.md) 和 [QUICKSTART.md](cc/QUICKSTART.md)；开发时的规则，详见 [DEV_RULE.md](cc/DEV_RULE.md)

### 最新修复记录
- 移动端分析页筛选按钮与营养溯源优化（用户 5 项反馈全闭环）：①详情页成本估算调整范围按钮 RIGHT OVERFLOWED 22px → [cost_trend_chart.dart](mobile/lib/features/recipes/widgets/cost_trend_chart.dart) SegmentedButton → DropdownButton（key range_dropdown、isDense、onChanged null 守卫）+ 图表 onTapDown 修 tap 无提示；②③分析页/详情页调整范围按钮小屏拥挤同改下拉（stacked 图 key filter_dropdown 5 选项）；④成本趋势图表 tap 无提示真根因 = **fl_chart 1.2.0 竞技场缺陷**（RenderBaseChart 先注册 longPress 再 tap，longPress sweep 盲取 members.first → 移动端 tap 被 reject → FlTapCancel(null) 清空 tooltip；onTapDown 同走竞技场必被吞）→ 绕开 `handleBuiltInTouches: false` + Listener + `RenderLineChart.getResponseAtLocation` + showingTooltipIndicators；⑤营养贡献溯源进度条对齐食材成本占比（高 10 圆角 5、段间 1px surface 细缝、stretch、flex 仅保下界 max(1,…)）+ 单列卡片（每营养素一张，点击展开折叠明细 `_expanded` Set<String>）+ 顶部 NRV/全部 SegmentedButton → PopupMenuButton 折叠按钮（key show_all_menu）+ 明细行含贡献值（NutrientContributor 加 unit）。**审查抓 4 真问题全修**：①fl_chart tooltip 契约 `tooltipItems.length == showingSpots.length` 否则 throw（回退图 3 条 vs 1 spot → 1 spot 1 item + touchSpotThreshold: infinity）②混日 bug（每条线独立取最近 spot 致远线跳 i±1 天、逆推负成本 Σ明细≠合计 → 统一 `spot.bar.spots[dayIndex]`，红→绿精确复现）③锚点（`touchedSpots` 距离升序 first = 触点天，`sorted.first` 是 barIndex=0 底部线 ≠ 锚点 → dayIndex 移到排序前 + 锚点反例测试 [tomatoSpot(x=0), eggSpot(x=1)] 守住）④测试数段把 1px 细缝 Container 内部 ColoredBox 算进（规格自身矛盾 → 按 `w.color != surface` 排除，色板 16 色均非 surface）。TDD 77/77 全绿（26 新增）+ analyze 3 改动文件 0 新增 + build windows 通过（36.5s，先杀 livecalc_mobile PID 8764 占用）。经验：tap 后须 pump(200ms) 走完 150ms 动画才读到 tooltip；细缝也是 widget，find.byType 计数会算进去。详见 [FEATURE_移动端分析页筛选按钮与营养溯源优化.md](cc/FEATURE_移动端分析页筛选按钮与营养溯源优化.md)
- 移动端分析页饼图改进度条（用户反馈手机上饼图割裂、占空间，①成本占比+③营养溯源两模块）：①[cost_proportion_chart.dart](mobile/lib/features/recipes/widgets/cost_proportion_chart.dart) 环形饼图 → 彩色进度条（高10px 圆角5 占满宽、每段 `Expanded(flex: max(1,(value*1000).round()))` 宽=占比、段色 getIngredientColor 同食材全图表同色、段间 1px surface 细缝、总价移标题行右侧、下方清单 色块+名称+金额+百分比、点段/行高亮 alpha0.2）；③[nutrition_source_grid.dart](mobile/lib/features/recipes/widgets/nutrition_source_grid.dart) 迷你环形图 → 迷你进度条（填充=nrpPct/100、填充色=Top1 贡献食材色 空回退 primary、NRV% 上移标题行、Grid aspectRatio 0.95→1.2）。Subagent-Driven 两任务，**spec 审查抓 3 真问题全修**：①进度条 0 高不可见（Row 默认 center 对齐→flex 子项 ColoredBox 无子取最小 0 高、paint 还跳过 zero size→只剩 1px 细缝；修复 `crossAxisAlignment: CrossAxisAlignment.stretch`）②flex 上界 clamp(1,100000) 压平单段 ≥¥100 宽度失真（flex:0 不崩是误判，SDK 走非弹性路径；修复仅保下界 max(1,…)）③tap 测试假绿（只断言不崩，检测不出死点击；改真断言高亮色）。TDD 63/63 全绿 + analyze 0 新增 + build windows 通过。经验：Row+Expanded+ColoredBox 撑高必须 stretch，测试必须真断言渲染结果（0 高时 find.byKey 照样命中）。详见 [FEATURE_移动端饼图改进度条.md](cc/FEATURE_移动端饼图改进度条.md)
- 移动端菜谱分析页对齐 web（12 任务全完成）：分析页从单模块「成本分析」重写为 5 模块（①成本占比环形图→②成本趋势堆叠图→③营养贡献溯源→④按商家预估成本卡片→⑤商家比价推荐矩阵），引入 fl_chart ^1.2.0；AppBar 菜谱名+「分析」chip（primaryContainer）；详情页 tooltip「成本分析」→「菜谱分析」；趋势默认「季」90 天由 [recipe_analysis_screen.dart](mobile/lib/features/recipes/screens/recipe_analysis_screen.dart) initState 显式 `reloadHistory(90)` 实现（**不改** `_loadHistory` 默认 30 天，保详情页初始「月」一致）。Subagent-Driven 全流程，双审查抓到 7 个真问题（计划堆叠算法跨天累加 bug、fl_chart touchedSpots 按触点距离排序须先按 barIndex 排序、null/duplicate ingredientId 破坏堆叠用 fold+where、touchSpotThreshold 默认 10px 过滤远线须 double.infinity、暗色模式 1.5:1 对比度回退 surface、IconButton M3 最小尺寸撑爆 168px 用 SizedBox(20x20) 包裹、¥ 须单 Text 前缀嵌入）。TDD 59/59 全绿 + analyze 0 新增 + build windows 通过（25.2s）。**隐藏 bug（Task 10 测试逼出，计划外修复）**：[recipe_provider.dart](mobile/lib/features/recipes/providers/recipe_provider.dart) RecipeDetailPageState.copyWith 末行 `error: error` 缺 `?? this.error`，initState 并发 load()+reloadHistory(90) 把 load 失败写入的 error 清成 null → 错误页永不显示卡无限加载，改 `error: error ?? this.error` 对齐 RecipeListState。**最终审查又抓 1 Important 竞态**：initState 并发 `load()`+`reloadHistory(90)` 与 load 内部 `_loadHistory(30)` 竞争 `state.costHistory`，load 整态重建清空后 30 天兜底写入 → 筛选「季」却显 30 天数据（非确定性）；修复 `load({int initialDays = 30})` 参数化 + 分析页改单请求 `load(initialDays: 90)`；`_loadHistory({int days = 30})` 保详情页默认。**经验**：`| tail` 管道吞 flutter 退出码（返回 tail 的 0）致构建失败误判通过；build windows 失败 MSB3073 cmake_install 先查调试进程占用输出文件。详见 [FEATURE_移动端菜谱分析页对齐web.md](cc/FEATURE_移动端菜谱分析页对齐web.md)
- 移动端 Flutter 调试失败（drift 生成代码缺失）：Windows 桌面 `flutter run` 编译报 [app_database.dart](mobile/lib/core/database/app_database.dart) 的 `select`/`update`/`delete` 未定义、`offlineQueue` getter 未定义、27 行 `Not a constant expression`。根因：`mobile/.gitignore` 忽略 `*.g.dart`（drift 标准做法不入库）+ 本环境从未跑过生成器 → `app_database.g.dart` 缺失，drift 的 `select`/`update`/`delete`/表 getter/`OfflineQueueCompanion` 全由生成代码定义；`Not a constant expression` 是生成缺失时的级联误报。修复：`cd mobile && dart run build_runner build --delete-conflicting-outputs`（76s，138 outputs）。验证：`flutter analyze` 通过，仅剩 3 个预先存在无关问题（avoid_print info + recipe_repository 两个 unused 警告）。教训：drift/riverpod/freezed 项目（`*.g.dart` 入 gitignore）**新环境 clone 后必须先跑 build_runner**，特征识别：「生成 API 全未定义 + 级联 Not a constant expression」→ 先查 `.g.dart` 是否存在。同日续修：flutter_secure_storage_windows 插件硬依赖 ATL，VS Build Tools 缺组件报 `atlstr.h` 找不到 → 提权装 `Microsoft.VisualStudio.Component.VC.ATL`（非提权会话直接调 setup.exe 会静默失败不写日志，须 `Start-Process -Verb RunAs -Wait`），`flutter build windows --debug` 122s 通过。详见 [BUGFIX_移动端drift生成代码缺失.md](cc/BUGFIX_移动端drift生成代码缺失.md)
- 部署 nginx 图片 404 + 图标 403 修复（NAS all-in-one 部署两个独立根因）：①图片 `/api/v1/images/*.jpg` 全 404（连 307 都没有）根因是 [default.conf.template](deploy/nginx/default.conf.template) 的静态资源长缓存正则 `~* \.(...|jpg|png|svg|ico|...)$` **优先级高于**普通前缀 `location /api/`（nginx 优先级：正则 > 普通前缀），把 `/api/v1/images/*.jpg`、`/api/v1/static/*.jpg` 全截走去 `/usr/share/nginx/html` 下找文件 → 404，请求**根本没到后端** serve_image（[main.py:579](backend/app/main.py#L579) 必返 307）；对比铁证 `/api/v1/auth/config`（非图片后缀）200 JSON 而 `/api/v1/images/*.jpg` 404。修复 `location /api/` → `location ^~ /api/`（前缀命中后不再查正则），一行加 `^~`。②`/logo.svg`、`/favicon.ico`、`/pwa-*.png`、`/apple-touch-*`、`/maskable-*`（全是 `frontend/public/` 源文件）全 403 而同目录 vite 生成的 `/assets/*` 200，根因是 public 源文件从 **Windows 构建上下文** COPY 进 Linux 容器后权限不可读，nginx try_files stat 命中（存在）→ static 模块 open 读失败 → 403（非 404，因 try_files 的 =404 只在 stat 失败触发）；vite 容器内新生成的 assets 是 node umask 022→644 正常。修复 [Dockerfile](Dockerfile) frontend-builder `RUN npm run build && chmod -R a+rX dist`（a+r 文件可读、a+X 大写只给目录加遍历位，放 builder 两 target 都受益）。两处都藏在容器化部署配置里，dev 走 vite proxy 按前缀转发不看后缀、不经过这套 nginx 故从未暴露，必须 prod nginx 端到端验证媒体链路。宿主头像文件存在、DB `storage_configurations` backend=local 配置无误，纯被 nginx 挡在前面。详见 [BUGFIX_部署nginx图片图标404_403.md](cc/BUGFIX_部署nginx图片图标404_403.md)
- 粘贴导入 autocomplete 并发风暴修复：粘贴一两百行价格「解析并匹配」后半部分大量 unmatched。systematic-debugging 定位双层瓶颈——主因 [PasteImportDialog.doParse:256](frontend/src/components/prices/PasteImportDialog.vue#L256) `Promise.all(okRows.map(r => tryAutoMatch(r)))` 零并发限制齐发 autocomplete，200 行瞬间 200 请求；放大器 [product_autocomplete](backend/app/api/products_entity.py#L815) 全表扫描 851 活跃商品 + joinedload 原料 + Python 逐行子串遍历（O(N×M) 不走索引），SQLite（`.env` 确认）并发读弱；vite proxy HTTP/1.1 浏览器并发~6 排队 + 前端 axios 10s 超时（[client.ts:5](frontend/src/api/client.ts#L5)）→ 后排请求干等超时 → [tryAutoMatch catch:310](frontend/src/components/prices/PasteImportDialog.vue#L310) 静默吞保持 unmatched。讽刺的是同文件 [doImport:450](frontend/src/components/prices/PasteImportDialog.vue#L450) 导入阶段有 `CONCURRENCY=5` 分批、解析阶段却裸奔。修复对齐 doImport 范式：doParse 改 `for slice + Promise.all` 每批 5 并发（MATCH_CONCURRENCY=5），tryAutoMatch 内部 try/catch 必 resolve 故 Promise.all 不会被单行失败带崩；200 行约 2-3s 完成。后端 autocomplete 被 4 处共用（QuickFillView/PricesView/PasteImportDialog×2）未动。纯前端单文件改动，build 通过（26.03s，precache 131 entries），手动验证待做（DevTools Network 看每批 5 并发不再超时）。教训：`Promise.all(map)` 是并发风暴经典坑，限流要覆盖所有批量调用点；后端全表扫+Python 遍历是潜伏放大器（量小无感量大崩）。详见 [BUGFIX_粘贴导入autocomplete超时.md](cc/BUGFIX_粘贴导入autocomplete超时.md)
- S3 全量导出补图片打包（从 feat/local 搬运）：feat/local 分支（94c3fd6）发现主分支「全量导出 zip 无图片」并修复，因两分支差距大（feat/local 领先 46 提交、94c3fd6 还混入纯前端 local 模式代码 `frontend/src/api/local/*` 与 CLAUDE.md 改动）无法直接 cherry-pick，改用 `git checkout 94c3fd6 -- <指定文件>` 单文件挑取 6 个（packaging.py + 测试 + 4 文档），坚决不带 frontend/local 与 CLAUDE.md。铁证：master packaging.py blob 与 94c3fd6 改动前完全相同（`f67ef97a3f6…`，feat/local 在该文件仅此一提交动过）→ 整文件覆盖即纯应用 fix，零冲突零杂质。核心改动 [packaging.py](backend/app/services/export/packaging.py)：外链图 `ThreadPoolExecutor` 并发下载（admin 去 query 下原图、普通用户原样瘦身图）、storage key 图 `storage.get()` 直读 S3 bytes 打包（图物理在 S3、DB 存 storage key 是「全量无图」根因，原 `_collect_image_files` 只找本地图故漏）、`build_export_zip` tmpdir `try/finally shutil.rmtree` 清理；依赖 `get_storage()`/`StorageBackend.get(key)->bytes` master 已确认存在（[base.py:16](backend/app/services/storage/base.py#L16)）。py_compile 过；未跑测试（feat/local 纯前端分支从未运行此 backend fix），建议 `pytest backend/tests/services/test_export_packaging.py` + 实测一次 S3 全量导出确认图片进 zip。⚠️ 附带文档 `cc/BUGFIX_local模式数据流修复.md` 主体 #1~#7 为 local 模式（纯前端 IndexedDB）笔记（master 无此模式、引用的 frontend/src/api/local/* master 全无），仅文末附录「云模式全量导出诊断」与本次 fix 相关，事后可裁剪。commit 84fd09f，未 push。详见 [FEATURE_外链图打包导出.md](cc/FEATURE_外链图打包导出.md)
- 粘贴导入展开错位修复：移动端快速填写「粘贴导入」展开待处理项时视口剧烈下跳、当前行被挤出可视区。七轮拉锯定位真凶——前几轮 `.paste-preview-table { table-layout: fixed }` 加在 Vuetify v-table **外层 div** 上根本没生效（`table-layout` 必须作用在 `<table>` 元素，要用 `:deep(table)` 穿透），fixed 失效→列宽 auto→autocomplete 面板撑宽名称列→挤窄其他列致内容换行→**reflow 把当前行挤出可视区**（reflow 不触发 scroll 事件，故 overflow-anchor/rAF 对冲 scrollTop 全打空；诊断一度被「用户手动滚动惯性」日志误导）。关键转折是全量枚举诊断「展开后无任何 scroll 事件」+ 用户两次坚持列宽变化。最终修复 4 点：①`.paste-preview-table :deep(table) { table-layout: fixed }` 让 fixed 真生效（列宽钉死不 reflow）②列宽重分配（图标28+价格56+数量48+单位44=176，移动端名称列~150px）③展开态 `colspan="5"` 整行撑满表格宽度（给面板充足空间避免截断）+ 按钮 flex-wrap ④展开态顶部加商品名+价格摘要行。撤掉所有 scroll 对抗 hack，overflow-anchor:none 留作双保险。详见 [BUGFIX_粘贴导入展开错位.md](cc/BUGFIX_粘贴导入展开错位.md)
- local 模式数据流修复（菜谱/原料/商品详情 7 项）：纯前端本地模式（`VITE_STORAGE_MODE=local`）详情页数据对不上/缺失批量修复——根因同构，local handler 移植时与「云模式返回格式 + 前端消费字段名 + DB 存储字段名」三方契约没对齐。① 菜谱 NRV 与数量口径拧着（[recipes.ts:351](frontend/src/api/local/handlers/recipes.ts#L351) 用了 aggregator 基于「每100g菜谱」的 nrv_pct，改 `calcNRV(name, n.amount)` 基于每份，对齐云模式 [nutrition.py:1506](backend/app/api/nutrition.py#L1506)）；② 原料价格记录越界（[products.ts listRecords:118](frontend/src/api/local/handlers/products.ts#L118) 不认 `ingredient_id` → 全表返回，加按原料商品集过滤）；③ 相关菜谱空（[nutrition.ts:321](frontend/src/api/local/handlers/nutrition.ts#L321) 返回裸 recipe_ingredients，改为 `{items:[菜谱详情]}` 含 is_public）；④ 食材单位全变「斤」（云 seed 克=3 vs 本地 斤=3，[exportImport.ts:375](frontend/src/api/local/handlers/exportImport.ts#L375) 单菜谱分支漏传 resolveLocalUnitId 致 cloudId 直接保留，补传后按名重映射；存量错数据需清空 livecalc IndexedDB 重导）；⑤ 食材成本空（[costCalculator](frontend/src/api/local/business/costCalculator.ts) 五处 push + [recipes.ts:203](frontend/src/api/local/handlers/recipes.ts#L203) cost_breakdown 都没透传 recipe_ingredient_id，前端按它匹配失败）；⑥ 相关菜谱全标「未发布」（#3 漏返 is_public，`!undefined` 触发 chip）；⑦ 层级关系空（[hierarchy.ts:5](frontend/src/api/local/handlers/hierarchy.ts#L5) 返回 `{parents,children,relations}`，前端要 `{parent_relations,child_relations}` 含 parent_name/child_name/relation_type，对齐云模式 [ingredient_hierarchy.py:181](backend/app/api/ingredient_hierarchy.py#L181)）。附云导出诊断：全量导出「数据少」非 bug（git 实锤本次未动后端；当前代码+SQLite 库复现 `build_export_zip('full')` 完整 merchants 8/price_records 2375/hierarchy 124；22:00 ZIP 少是当时后端连了另一较空的库；图片外链跳过是设计行为，另起特性「外链图打包」）。build 通过、dev HMR 实测全验证。local 库实为 `livecalc`（[database.ts:154](frontend/src/api/local/database.ts#L154)）非设计文档的 `livecalc_local`（空壳遗物）。详见 [BUGFIX_local模式数据流修复.md](cc/BUGFIX_local模式数据流修复.md)
- 天地图「地图类型」死选项清理：后台「地图配置」天地图折叠面板的「地图类型」下拉（矢量/影像/地形）切换后地图毫无变化，是误导用户的死选项。trace 全链路确认 `config.map_api_keys.tianditu.type` 无人消费——[TiandituEngine.ts:34](frontend/src/utils/map/engines/TiandituEngine.ts#L34) 硬编码 `TianDiTu.Normal.Map` 矢量底图只读 token 不读 type、[mapAdapters.ts:101](frontend/src/utils/mapAdapters.ts#L101) 另一套也写死，无论 UI 选 vec/img/ter 永远矢量层。KISS 删 [MapSettingsView.vue:159](frontend/src/views/admin/MapSettingsView.vue#L159) 的 v-select + 加注释；**保留 type 默认值 'vec' 不动**（config 默认值/MapApiKeys 接口/mapTypes.ts 全留），让 config 结构不变（TS 类型/保存 payload/后端透传/向后兼容全不受影响），不扩大到接口与后端 schema。单文件 template 改动，build 通过（precache 128 entries 不变），无表结构变更。详见 [BUGFIX_天地图地图类型死选项.md](cc/BUGFIX_天地图地图类型死选项.md)
