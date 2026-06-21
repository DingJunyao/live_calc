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

## 项目索引

本项目文档已模块化拆分，按需加载以提高性能。详细信息请查看 `./cc` 目录下的对应文件。

所有与 Claude Code 相关的文档，都放在 `./cc` 目录下。并且，在这里描述文档内容，以便索引。

如：部署说明：详见 [DEPLOYMENT.md](cc/DEPLOYMENT.md) 和 [QUICKSTART.md](cc/QUICKSTART.md)

### 最新修复记录
- 移动端优化和功能修复：详见 [BUGFIX_移动端优化和功能修复.md](cc/BUGFIX_移动端优化和功能修复.md) - 记录了移动端输入框放大、菜谱搜索功能、菜谱成本更新和商品自动完成功能的修复
- None值处理修复：详见 [NONE_VALUE_FIXES.md](cc/NONE_VALUE_FIXES.md) - 修复了在计算菜谱成本和营养素时未将None值视为0的问题
- 地图配置持久化：实现了地图配置的数据库存储功能，解决了地图API密钥等配置重启后丢失的问题。详细信息请见 [MAP_CONFIG_PERSISTENCE.md](cc/MAP_CONFIG_PERSISTENCE.md)
- 鸡蛋价格显示异常修复：修复了在原料管理中价格显示异常的问题，确保价格历史列表与价格趋势图表的显示逻辑一致。详细信息请见 [EGG_PRICE_DISPLAY_FIX.md](cc/EGG_PRICE_DISPLAY_FIX.md)
- 默认单位改为斤：商品和原料的默认单位统一改为「斤」，涉及后端 API 创建接口、导入服务和前端表单默认值。详见 [DEFAULT_UNIT_JIN.md](cc/DEFAULT_UNIT_JIN.md)
- quantity_range 成本计算修复：修复了使用 quantity_range（用量区间）的食材成本显示为 0 的问题。在成本计算函数中新增 `_get_effective_quantity()` 辅助函数，当 quantity 为 None 时从 quantity_range 取平均值计算成本。详见 [QUANTITY_RANGE_COST_FIX.md](cc/QUANTITY_RANGE_COST_FIX.md)
- 成本计算单位转换 & substitutable 回退：修复成本计算中价格记录单位（如"个"）与菜谱用量单位（如"克"）不同时直接相乘导致成本异常偏高的问题；同时让 substitutable（可替代）关系也能作为价格/营养回退源。详见 [BUGFIX_UNIT_CONVERSION_IN_COST.md](cc/BUGFIX_UNIT_CONVERSION_IN_COST.md)

- 快速填写移动端三处修复：新增商品搜索下拉与 iOS 地址栏重叠（菜单改 `location: 'top'`）、单位选择器闪退且只有斤/个（`v-select`+`@blur` 改 `v-menu`+`v-list`，`loadUnits` 加 `is_common` 过滤和 `Array.isArray` 兼容）、批量保存缓慢（串行改并发 `Promise.allSettled`，并发数 5，加进度显示）。详见 [BUGFIX_快速填写移动端修复.md](cc/BUGFIX_快速填写移动端修复.md)
- 旧版数据库迁移：从 livecalc_bak.db 迁移用户、商家、商品和价格记录（475 条）到新数据库，含兼容 SQLite/MySQL/PostgreSQL 的 SQL 脚本。详见 [DATA_MIGRATION_BAK_DB.md](cc/DATA_MIGRATION_BAK_DB.md)
- 成本数据延迟加载优化：菜谱管理列表和详情页的成本/营养/趋势数据改为异步延迟加载，先渲染基础数据再后台补计算数据。列表取消 `include_cost` 参数，详情页拆分加载流程，趋势图覆盖层不销毁图表 DOM。详见 [LAZY_LOADING_COST_DATA.md](cc/LAZY_LOADING_COST_DATA.md)
- 原料删除后无法同名重建修复：去掉 ingredients.name 的数据库唯一约束（改普通索引），创建/更新接口重名检查增加 is_active 过滤，与 Product 模型对齐；附带将 alembic.ini 注释 ASCII 化以修复 Python 3.14 下的 GBK 编码加载问题。详见 [BUGFIX_原料同名重建.md](cc/BUGFIX_原料同名重建.md)
- 启动导入仅在数据库初始化时进行：菜谱/原料/营养等初始数据的导入改为仅首次初始化时执行，lifespan 外层统一判断「已有 `source=json_repo` 菜谱则跳过」，修复本地路径 `import_from_local_dir` 每次重启重复遍历数据文件、重复执行营养增量导入的问题（判据与远程路径短路逻辑一致）。详见 [BUGFIX_启动导入仅初始化时进行.md](cc/BUGFIX_启动导入仅初始化时进行.md)
- USDA 下载 SSL 握手失败修复：四组对照定位根因——USDA 的 WAF 按 TLS 指纹 + UA 概率性切断非浏览器客户端，原 downloader 的 `USDA_UA` 是半截（缺 `Chrome/... Safari/... Edg/...`）被当 bot 切断率飙升（同库同窗口：完整 UA 4/6、半截 1/6），叠加网络窗口剧烈波动（好窗口单次近 100%、差窗口近 0%）。核心修复：UA 改完整 Edge 浏览器串（对齐参考项目 HowToCook_json_organizer）；纯 Python 兜底：httpx 并发重试（每轮 5 握手任一成功即返、全失败指数退避等窗口恢复）+ 可选 `usda_http_proxy`。不依赖 curl/curl_cffi（跨系统不可靠/Py3.14 库错误）。实测 fetch 3/3、foundation 363 条、sr_legacy 7793 条均成功。详见 [BUGFIX_USDA_DOWNLOAD_SSL_RETRY.md](cc/BUGFIX_USDA_DOWNLOAD_SSL_RETRY.md)
- USDA 匹配后营养不显示修复：原料匹配 USDA 后详情页营养仍为空，根因是 matcher 写入的 NutritionData 为 source=usda_manual_match 但未置 is_verified，而 NutritionCalculator 仅取 source='custom' 或 is_verified=True 的记录故查不到（商品走 custom_nutrition_data 不受影响）。修复：match_ingredient 写入时置 is_verified=True（source 保留追溯）；附带将 UsdaMatchDialog 的浏览器原生 confirm() 改为 Vuetify 二级模态确认对话框。续修：NRV 未计算——matcher 写入缺 nrp_pct/standard，提取模块级 calc_nrv_pct 共享函数补算中国 GB 标准 NRV%（商品复用、DRY）；USDA 搜索改 AND（空格分词每词都须命中，每词中/英任一子串即可）。详见 [BUGFIX_USDA匹配后营养不显示.md](cc/BUGFIX_USDA匹配后营养不显示.md)
- USDA 下载/上传任务纳入任务列表：数据维护页「任务列表」原本只合并 import_tasks + agent_sessions，而下载/上传走 usda_tasks 表未接入，点击后列表无记录。将 usda_tasks 作为第三来源（`_kind: 'usda'`）合并进 mergedTasks，复刻 agent「拿 id→入列→轮询」机制；后端 `/usda/download`、`/usda/upload` 端点预建 UsdaTask 返回 task_id、新增 `/usda/tasks` 列表与 `/usda/tasks/{id}` 单条端点；前端下载/上传后入列轮询、onMounted 恢复历史、模板三分支展示，usda 任务不显示取消按钮（后台无法取消）。详见 [BUGFIX_USDA下载任务列表.md](cc/BUGFIX_USDA下载任务列表.md)
- 营养素翻译被 100 行护栏误伤修复：USDA 维护页「未映射营养素名翻译」（openai）卡 running、name_zh 未写入，根因是 `run_agent_loop` 默认 `safe_row_threshold=100` 把单名批量 UPDATE（实测 SFA 16:0 未译 6398 行、全表单名最大 15600）误判 dangerous → unattended 跳过，Agent 被迫 LIMIT 分批甚至卡死。修复：`nutrient_task.py` 新增 `_SAFE_ROW_THRESHOLD=50000` 传给 `run_agent_loop`，放行单名批量同时兜底全表误更新（65 万行仍触发）；另三条老路径（`translate/task.py` 食材翻译、`inferrer` 模糊量/密度）一并覆盖 `_SAFE_ROW_THRESHOLD=5000`（按各表行数取值，同根因预防性修复）；续修：该任务 prompt 模板漏写「安全 SQL 自动执行」说明致 Agent 误报「请审批后执行」（实测 48 条 UPDATE 已全 auto_executed），已补全模板并约束 Agent 措辞。详见 [BUGFIX_营养素翻译行数护栏.md](cc/BUGFIX_营养素翻译行数护栏.md)

### 功能实现记录
- 商品拆分为原料：在商品详情页添加「拆分为原料」按钮，将商品从当前原料中拆分为独立同名原料，迁移营养数据 mixin，同名冲突时支持重命名。详见 [FEATURE_PRODUCT_SPLIT_TO_INGREDIENT.md](cc/FEATURE_PRODUCT_SPLIT_TO_INGREDIENT.md)
- 详情页宽屏响应式布局：菜谱、原料、商品三个详情页实现宽屏（≥960px）双栏布局，行对齐区域用 CSS Grid，不对齐区域用 Flexbox。详见 [FEATURE_WIDESCREEN_DETAIL_LAYOUT.md](cc/FEATURE_WIDESCREEN_DETAIL_LAYOUT.md)
- 原料分类显示与编辑：原料详情页基本信息区显示分类，编辑表单支持选择分类（复用 GET /ingredients/categories）；后端 get_ingredient 详情接口补充返回 category_id/category。详见 [FEATURE_原料分类显示与编辑.md](cc/FEATURE_原料分类显示与编辑.md)
- 快速填写：价格记录页 app-bar 新增闪电入口，进入独立批量填写页面。选商家后自动列出历史商品（按拼音/字母顺序排序），逐行填价格（数量/单位默认 1/斤，点击可改），可新增行搜索商品。只保存填了价格的商品，近 1h 内填过的按商家独立隐藏（sessionStorage）。纯前端，后端复用现有 API。详见 [FEATURE_QUICK_FILL.md](cc/FEATURE_QUICK_FILL.md)
- 半成品菜谱成本传递：原料可指向其制作菜谱（激活 recipes.result_ingredient_id + 新增 ingredients.serving_weight），成本计算时商品无价则由制作菜谱推导每克单价（份×每份重桥接），支持递归套娃与循环检测。菜谱页「成品产出」与原料页「自制来源」双入口，成本明细 tooltip 显示 recipe_chain。附带修复 alembic 坏链与 as_of 的 Decimal×float 隐患。详见 [FEATURE_半成品菜谱成本传递.md](cc/FEATURE_半成品菜谱成本传递.md)
- 数据导出：个人中心「数据导出」，两档（全量 `full` / 仅我的 `mine`，mine 含外键可达性遍历保证引用完整）；菜谱/食材/营养/单位 HowToCook 兼容 + id 扩展，扩展知识库与账户交易数据独立规格，图片打包 zip 同步流式下载（`GET /api/v1/export/data?scope=`）；`services/export/` 分层（serializers/reachability/packaging）。详见 [FEATURE_数据导出.md](cc/FEATURE_数据导出.md)
- 快速填写粘贴导入：快速填写导航栏「粘贴导入」按钮，对话框粘贴文本（`名称 价格[/[数量]单位]` 四种格式）→ 解析预览 → 未匹配商品支持「关联已有 / 创建同名原料+商品 / 挂靠已有原料」三种手动处理 → 并发导入（`record_type=price` 不计入支出，并发数 5，进度+失败明细）；后端 `POST /products` 加可选 `ingredient_id` 支持「挂靠已有原料」创建商品。详见 [FEATURE_快速填写粘贴导入.md](cc/FEATURE_快速填写粘贴导入.md)
- USDA 营养素匹配：给原料/商品手动匹配 USDA 营养素。下载 USDA 原始数据（Foundation+SR Legacy）入库去重；6 后端翻译食材名（AI: Claude Code/OpenAI/Anthropic 兼容，机翻: 百度/阿里云/DeepL），营养素名走 172 条预设映射表（不耗 AI）；内存 OR 搜索（空格分词任意命中）；原料清空写 USDA、商品复制原料骨架设 0 再 USDA 覆盖；后台 AI/机翻/USDA 三管理页；前端匹配对话框接入原料/商品详情页营养编辑区。详见 [FEATURE_USDA营养素匹配.md](cc/FEATURE_USDA营养素匹配.md)
- Agent 维护任务台：管理员按按钮触发 claude code CLI 驱动 Agent 自主读写 SQLite 批量维护数据（方案 B：受控只读 MCP `db_read`/`describe`/`list_tables`，Agent 无写工具；写操作在 ` ```sql ` 代码块输出，经 `sql_guard` 判定 safe 自动执行 / dangerous 审批）。后端 `agent_sessions`/`agent_messages`/`agent_approvals` 三表 + `ClaudeCodeRunner`（subprocess stream-json + 线程桥接规避 Windows 事件循环 + `--strict-mcp-config`/`--resume`/`CLAUDECODE` pop）+ SSE 流式（query token 鉴权、subscribe 前置 seq 去重、终态兜底）+ 写操作多轮 loop（提取 SQL → 守卫 → 执行或审批 → `--resume` 回流）；前端任务台 UI（按钮 / 对话流 / 插话 / 审批卡 / 刷新重放，响应式）。阶段 1 实现「补单位质量」，实测 252 条脏数据修正 247 条（98%）。详见 [FEATURE_Agent维护任务台.md](cc/FEATURE_Agent维护任务台.md)
- langchain Agent 集成（OpenAI/Anthropic）：给 OpenAI 兼容/Anthropic 兼容两 provider 集成 langchain Agent，四项 AI 后处理（食材翻译/营养素翻译/模糊量推测/密度推测）从分批串行/逐条改成 Agent 自主批量（省时省 token）。新增 `LangChainRunner`（langchain 1.x `create_agent`，与 `ClaudeCodeRunner` 平级，复用 AgentRunner 协议 + run_agent_loop + sql_guard + 5 个 task_template）；只读 `@tool`（db_read/describe/list_tables，进程内 SQLAlchemy inspect 跨库，复用 db_query.check_read_only）；写库走 SQL 文本 + 守卫（不引入结构化写工具）；事件映射过滤消息类型（只 AI 消息产 text_delta）；resume 靠 AgentMessage 回放 chat_history；`run_agent_loop(unattended=True)` 老路径无人值守（dangerous 自动跳过）；任务台选 provider（runner_factory 分流）+ 老路径（TranslateTask/TranslateNutrientsTask/AIInferrer）引擎替换（建 `[后台]` AgentSession + 保留 UsdaTask/AIInferrer 载体 + ai_caller 回退 + async/同步桥接）。详见 [FEATURE_langchain_Agent集成.md](cc/FEATURE_langchain_Agent集成.md)
