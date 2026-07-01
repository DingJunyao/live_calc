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

如：部署说明：详见 [DEPLOYMENT.md](cc/DEPLOYMENT.md) 和 [QUICKSTART.md](cc/QUICKSTART.md)；开发时的规则，详见 [DEV_RULE.md](cc/DEV_RULE.md)

### 最新修复记录
- 菜谱推荐长事务导致 database is locked：POST /products 创建价格记录报 `database is locked`（35 秒超时）。根因 [generate_recommendations](backend/app/services/meal_recommender.py) 后台生成循环内 `db.add+db.flush`（持 SQLite 写锁）后继续 `_pick_best_recipe`（扫候选菜谱池 + 算营养/成本，慢计算）、最后才 `db.commit`，写锁持有整个 3 餐循环；并发写（POST /products）等 busy_timeout 30s 超时（[database.py](backend/app/core/database.py) `timeout=30`）。修复改「先算后写」——循环内只 `_pick_best_recipe` 收集 picks（读不持锁）、循环后批量 `db.add+commit`（写锁毫秒级），主分支 + 黑名单重生成分支两处；`refresh_meal_recommendation` 已正确（先 pick 后写）无需改。写锁持有从「整个循环」缩到「批量写」。既有 bug（菜谱推荐后台生长事务），非审核框架改动引入（POST /products 不走审核）。详见 [BUGFIX_菜谱推荐长事务锁.md](cc/BUGFIX_菜谱推荐长事务锁.md)
- 共享转型 schema 漂移修复：后端启动报 `no such column: units.is_standard`。根因是开发库 [livecalc.db](backend/data/livecalc.db) 由 `Base.metadata.create_all()` 建库、**从未走 alembic**（无 `alembic_version` 表），create_all 只建新表、不碰「加列/改约束」的 ALTER，致迁移 [20260627_0002_shared_data_transform.py](backend/alembic/versions/20260627_0002_shared_data_transform.py) 三处变更漂移——`units.is_standard`、`recipes.is_public` 缺列（SELECT 必崩）、`merchants.user_id` 仍 NOT NULL（语义已改可空）。同批两新表（user_merchant_favorites/product_merchant_price_summary）因 create_all 建表机制已落地，反证只漏 ALTER 老表。`alembic upgrade head` 走不通（无版本表 + create_table 撞已存在表）。修复：直接补开发库（备份 `livecalc.db.bak_20260629_103713` 后），两列 ADD COLUMN，`merchants.user_id` 改 nullable 用 alembic `batch_alter_table` 离线执行（SQLite 需表重建，交 alembic 免手写易错 SQL，不依赖 alembic_version）。验证三处生效 + merchants 空表数据完整 + 索引保留 + 模拟 ORM SELECT 跑通。纯开发库欠账（alembic 迁移/模型本就正确未改）。配套：因项目不用 alembic，完善 [20260627_shared_transform_sqlite.sql](backend/scripts/sql/20260627_shared_transform_sqlite.sql) 为可直接手动执行（放开 is_public/is_standard 加列 + 补 merchants.user_id 官方表重建流程，不依赖 alembic；MySQL/PG 本就可直接执行），模拟旧结构测试库 executescript 实跑验证表重建零损（数据/9 列/索引全保留）+ 加列/建表/回填全对。附带记录前序报错：`Settings`（pydantic）`extra=forbid` 拒绝 `backend/.env` 混入的 `VITE_DATA_REPO_IMAGE_BASE`/`VITE_REQUEST_TIMEOUT`/`VITE_LONG_REQUEST_TIMEOUT`（前端变量），用户已删 `.env` 中这三项解决，`extra→ignore` 的根因修法未动。详见 [BUGFIX_共享转型表结构漂移.md](cc/BUGFIX_共享转型表结构漂移.md)
- 共享写端点分流改造（Task 2.5b）：P0 阶段共享数据写端点统一限管理员（`get_current_admin_user`），P1 框架 + P2 业务执行器就绪后升级为分流——管理员 `apply_as_admin`（经框架执行器 apply 立即生效 + change_proposals 留痕 status=applied）/ 普通用户 `submit`（按治理总表策略：auto_approve 立即 / manual 待审）。改造 5 文件：[ingredient_hierarchy.py](backend/app/api/ingredient_hierarchy.py) 食材合并 + 层级 create/update/delete（注意 delete 改软删 is_active=False 支持回滚，原硬删）；[units.py](backend/app/api/units.py) 单位 create/update/delete（执行器 validate 拒改标准单位，delete 软删）；[nutrition.py](backend/app/api/nutrition.py) 食材营养写入（抽 `_build_structured_nutrients` 共用构造，补空→auto 覆盖→manual）；[merchants.py](backend/app/api/merchants.py) 商家 update/delete（delete 不再拒绝有价格商家，改软停用+ProductRecord.merchant_id 置 NULL）；[ingredient_extended.py](backend/app/api/ingredient_extended.py) 硬删除保留管理员直写（高危不可逆，执行器软删语义不符）。未进分流（同模式待续）：units 换算/覆盖/密度（执行器未覆盖多表）、nutrition 商品营养/correct（写 Product.custom_nutrition_data / IngredientNutritionMapping，与 NutritionData 执行器语义不符）、products_entity 条码/别名。测试：P0 改造 + 新增 8 条分流测试（[test_shared_data.py](backend/tests/test_shared_data.py) 管理员直写 + 普通提议各一类，覆盖 ingredient.merge/unit.create/hierarchy.create/merchant.update）；P0 加 autouse fixture 显式 `register_all()`（TestClient 不触发 main.py lifespan）。`pytest tests/test_permissions_p0.py tests/test_proposals_framework.py tests/test_shared_data.py` 46 passed；全量回归 16 failed/368 passed（失败数与基线一致——全是预存 auth/import/locations/recipes/reports 等无关失败，通过数从 360 升到 368）。py_compile 全通过，无表结构变更。详见 [BUGFIX_共享写端点分流改造.md](cc/BUGFIX_共享写端点分流改造.md)
- 食材合并路由重复修复：启动报 `Duplicate Operation ID merge_ingredients_api_v1_ingredients_merge_post`。根因是已删的 `ingredient_merge.py` 与 [ingredient_hierarchy.py:329](backend/app/api/ingredient_hierarchy.py#L329) 都注册了 `POST /api/v1/ingredients/merge` 且函数同名 `merge_ingredients` → operation ID 撞车；更隐蔽的是 [main.py](backend/app/main.py) 里 ingredient_merge.router 先注册，Starlette 按序匹配先注册胜出，实际生效的是宽松版（仅 401），hierarchy 后来加的 `is_admin`（403）管理员校验形同虚设。修复：删除孤立的早期遗留文件 ingredient_merge.py（整个文件仅此一个重复路由），保留 hierarchy 完整实现（含 merge-history/merge-status 配套），同步清理 main.py 的 import 与 include_router；schema 文件 app/schemas/ingredient_merge.py 被 nutrition.py 引用故保留。权限规则经需求澄清细化（非「仅管理员」）：管理员可合并任意食材；普通用户只能把自己创建的源食材合并进自己创建的目标食材（源与目标 created_by 均须为本人，系统/历史数据 created_by 为 NULL 一并挡住），实现于 merge_ingredients（查涉及食材 created_by 逐个比对，非本人则 403 并列出食材名），created_by 由 AuditMixin 提供无需改表；合并仍会迁移食材的所有引用（含他人菜谱），本次只卡所有权不限制跨用户引用迁移。py_compile 通过、grep 确认无遗留引用，无表结构变更。详见 [BUGFIX_食材合并路由重复.md](cc/BUGFIX_食材合并路由重复.md)
- 快速填写排序写入失败修复：「按填写顺序排序」从未生效、历史商品始终按拼音序。根因是 [merchants.py](backend/app/api/merchants.py) `save_product_orders`（`POST /merchants/{id}/product-orders`）upsert 循环只在请求开始查一次当天已有记录塞进 `existing` 字典，本轮 `db.add` 的新对象没登记回去；粘贴导入时 `product_ids` 含重复 pid（error.log 实测 622 出现两次）→ 第二次遇同 pid 仍走 add → 同 `(user,merchant,product,date)` UNIQUE 冲突 → IntegrityError 500。前端 `saveAll`/`onPasteImported` 用 try/catch+console.warn 静默吞错，故 `user_merchant_product_orders` count 恒 0、`get_merchant_product_prices` 算不出 `custom_sort_score`（全 undefined）、前端全回退「分类+拼音」分支。取证：error.log 实锤 `[parameters:(1,1,622,'2026-06-27',26)]` + TestClient 复现 `[325,78,325,1,30]`→500；而小量不重复 pid 与 DB 直写均 200（排除表/鉴权/路由/序列化）。修复：加 `seen` 字典跟踪本轮记录、`existing` 改以 pid 为键（本请求内 user/merchant/date 固定），重复 pid 时更新 sort_order 不再重复 add。TestClient 验证 200 + 去重（325 仅一条、sort_order=最后位置）+ 同日 upsert 不新增。无表结构变更，无需 SQL/alembic。前端配套：手动 `saveAll` 原按 `visibleHistoryRows`（显示顺序=拼音序）收集 savedProductIds，经确认改为按填写顺序——[QuickFillView.vue](frontend/src/views/prices/QuickFillView.vue) `FillRow` 加 `filledAt`（首次填上有效价的时间戳），价格框 `@update:model-value`→新增 `onPriceChange` 记时，`saveAll` 按 `filledAt` 升序排序收集 savedProductIds；粘贴导入本就是文本顺序=填写顺序无需改。前端 `npm run build` 通过。详见 [BUGFIX_快速填写排序写入失败.md](cc/BUGFIX_快速填写排序写入失败.md)
- 连接池耗尽修复：后端报 `QueuePool limit of size 10 overflow 20 reached`（栈顶 `resolve_user_from_token` 是受害者非凶手——它是每请求第一个借连接的点，池一空先炸）。根因是「长持有并发叠加」打爆 30 连接池：`run_agent_loop` 主 db 每会话占 1 连接达数分钟、SSE `stream_session` 的 `Depends(get_db)` 整个流期间白占连接（鉴权后进 event_gen 再没用过）、`resolve_user_from_token` 的 `next(get_db())` 反模式异常路径归还依赖 GC 且正常路径因 generator 立即被 GC 而借两次连接。三处 `SessionLocal()` 使用点排查均无永久泄漏（都有 try/finally+close）。修复三板斧：(1) [security.py](backend/app/core/security.py) `resolve_user_from_token` 改 `SessionLocal()`+try/finally 消除反模式；(2) [agent_api.py](backend/app/api/agent_api.py) `stream_session` 去掉 `Depends(get_db)` 改短命鉴权 session（捕获 `initial_status` 标量避免碰 detached `sess`）；(3) [database.py](backend/app/core/database.py) SQLite 池扩容 size 15/overflow 30。静态验证 py_compile+import+grep 通过，单测因 .venv 未装 pytest 未跑，运行时待观察。详见 [BUGFIX_连接池耗尽.md](cc/BUGFIX_连接池耗尽.md)
- 邀请码过期时间无法指定修复：后台「创建/编辑邀请码」的「过期时间」栏空白点不动。根因三叠：(1) 该栏用 `<v-date-input>`，Vuetify 3.12.4 里属 labs 组件，项目 [vuetify.ts](frontend/src/plugins/vuetify.ts) 只注册 `vuetify/components` 稳定版、未注册 labs（`vite-plugin-vuetify` 的 autoImport 只管样式不碰组件注册），运行时 `Failed to resolve component` 渲染空壳，且该组件只到「天」承载不了时间点；(2) 后端 `is_expired` 用 `naive < aware(now utc)`，SQLite 读回的 `DateTime(timezone=True)` 实为 naive（参 [products.py:459](backend/app/api/products.py#L459) 也要手动转 naive）→ 修好前端即触发 TypeError（此前因 expires_at 全 NULL 短路没崩）；(3) `_serialize_invite_code` 用 `strftime` 抹了时区，前端 [formatToLocalDateTimeShort](frontend/src/utils/timezone.ts)（要求输入带时区）显示偏。修复按「后端统一 UTC、前端按本地时区」：前端 `v-date-input`→`v-text-field type=datetime-local`（复用 PricesView 既有模式 + 新增局部 `toDatetimeLocalValue` 回填 + `getLocalDateTimeString` 做 min）、提交 `new Date(local).toISOString()`；模型加 `ensure_utc`（naive 视作 UTC）改 `is_expired` 防 TypeError；序列化 `expires_at`/`created_at` 改 `ensure_utc(dt).isoformat()` 带 `+00:00`。新增 [test_invite_code.py](backend/tests/models/test_invite_code.py) 10 例（含 naive/aware 防 TypeError）。build 通过 + 单测 10 passed；UI 实测待管理员账号。详见 [BUGFIX_邀请码过期时间.md](cc/BUGFIX_邀请码过期时间.md)
- 邀请码 schema 漂移修复：创建邀请码报 `no such column: invite_codes.used_count`（[invite_codes.py:47](backend/app/api/invite_codes.py#L47) 查询触发）。根因是开发库 schema 与 `alembic_version` 漂移——0002 迁移（[20260622_0002](backend/alembic/versions/20260622_0002_add_system_config_and_enhance_invite_codes.py)）里 system_config 建表落地了，但 invite_codes 的 batch_alter_table（used→used_count + max_uses）没落地，而版本号已盖到 0003，故 `alembic upgrade head` 无效。模型/迁移/SQL 脚本本身正确，纯环境漂移。不改代码，直接补两列（RENAME used→used_count + ADD max_uses，与已提交的 [sqlite 脚本](backend/scripts/sql/20260622_user_and_invite_code_enhancement_sqlite.sql) 一致），操作前备份；ORM 层验证查询/插入/属性全通。详见 [BUGFIX_邀请码schema漂移.md](cc/BUGFIX_邀请码schema漂移.md)
- 注册校验对齐与错误透传：注册 `username="a"` 前端放过、后端 422 拒，且报错只显示「请求参数验证失败」不指明字段。根因全在前端 Register.vue：username/email 只校验非空（缺后端要求的 3-50 字符 / 邮箱格式）+ catch 读笼统 `detail` 没用拦截器拼好的 `userMessage`（后端其实已在 `errors` 数组返回字段详情、`extractErrorDetail` 也已正确解析）。纯前端修复：补 username 3-50 + email 格式正则、catch 改读 `error.userMessage`，后端零改动。build 通过 + MCP 实测 `username="a"` 被前端拦（中文提示「用户名需 3-50 个字符」+ 无 `POST /auth/register`）。详见 [BUGFIX_注册校验对齐与错误透传.md](cc/BUGFIX_注册校验对齐与错误透传.md)
- 地图 SDK 点击标记偏移修复：商家管理添加/修改商家用各地图 SDK（高德/百度/腾讯）选点时点击地图，标记偏离点击处（火星偏移）、保存坐标也错。根因是三个 SDK 引擎（`AMapSDKEngine`/`BaiduSDKEngine`/`TencentSDKEngine`）违背「与调用方传地图坐标系原始坐标」契约（Leaflet 引擎都遵守），内部 click/markerDragend（百度/腾讯连 init center）多做一次 →WGS84 转换，致 `MapPicker` 双重转换且把 WGS84 当地图坐标画到偏移底图。修复：三个 SDK 引擎统一为「传啥用啥」契约，去掉引擎内所有 `convertCoordinate`，转换职责回归调用方，清未用 import。仅影响 MapPicker，MerchantMapView 不受影响。详见 [BUGFIX_地图SDK点击标记偏移.md](cc/BUGFIX_地图SDK点击标记偏移.md)
- 本地路径导入改用 .env 配置：数据维护中心「从本地路径导入」不再在页面手填目录路径，改为直接复用 `.env` 的 `DATA_LOCAL_PATH`（与启动导入共用同一来源，消除配置漂移）。后端 `trigger_local_import` 去掉 `local_path` 参数改读 `settings.data_local_path`（未配置/目录不存在各一 400）、新增只读 `GET /data/local-path-config`；前端删输入框换三态只读展示、未配置禁用按钮、点击不再传参。详见 [BUGFIX_本地路径导入改用env配置.md](cc/BUGFIX_本地路径导入改用env配置.md)
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
- 成本趋势并行加载优化：菜谱详情成本趋势切大跨度区间（季/年/全部）时，分批加载由串行 `while await`（每批 90 天一批接一批）改为并行。拆出无副作用 `fetchCostHistoryBatch` + 并行合并核心 `loadCostHistoryParallel`（各段 offset 不重叠 → `Promise.all` 并发，后端纯读无竞态）；固定区间一次性并行到底，「全部」分波次并行（每波 4 批 ≈360 天，末批空即终止）；任务间仍走 `costHistoryQueue` 串行队列避免区间切换竞态。「年」约 4×、「全部」约 4× 提速。详见 [PERF_成本趋势并行加载.md](cc/PERF_成本趋势并行加载.md)

### 功能实现记录
- USDA 匹配接入审核框架：放开 USDA 原料/商品匹配两端点（[usda.py](backend/app/api/usda.py) match_ingredient/match_product，原锁管理员 403），接入 change_proposals 框架（治理总表「有数据→人工」：有数据 manual / 没数据补空 auto_approve + 管理员 apply_as_admin 直写即时）。5 task：matcher 去 commit（match_ingredient/match_product commit→flush，调用方 commit）；service.submit 加可选 `policy_override` 参数（补空 auto 的正确实现——不用 nutrition 那套 apply 内 set_policy 权宜，那个其实没生效因 submit 在 validate 前读 policy）；两执行器 UsdaIngredientMatchExecutor（替换语义：snapshot 旧 NutritionData 全行→调 matcher 清空+写新→revert 删新+插旧）+ UsdaProductMatchExecutor（覆盖 custom_nutrition_data）+ bootstrap 注册全 manual；usda.py 两端点分流（判断有无数据→manual/auto policy_override）；前端 UsdaMatchDialog 按角色/status 提示（管理员成功/普通用户 pending 蓝色不误报/补空 success，pending 不刷新）+ entityTypeLabel 补 USDA 原料/商品匹配 + 清 dead import。关键技术：替换语义 snapshot/revert（区别 CRUD update）+ `_restore_row`（全行重插时 DateTime isoformat 转回 datetime——任何全列 snapshot 重插的执行器都踩 SQLite DateTime 拒收 string 的坑）。80 passed、build 通过。遗留：nutrition 端点补空 auto 仍未真正生效（apply 内 set_policy 权宜），可后续迁移 policy_override。续：商品营养端点 edit_product_nutrition 放开走审核（原锁管理员 403）——新建 ProductNutritionExecutor（写 custom_nutrition_data + source，同构 UsdaProductMatchExecutor）+ bootstrap 注册 + 端点分流（保留 structured_nutrients 构建，走提议 + policy_override 有数据 manual/补空 auto）+ ProductDetail saveNutritionEdit 按审核状态提示，与原料营养对齐，19 passed + build。续修 PUT 清空路径（update_product_nutrition 全删除时同款分流 + 前端按审核状态），21 passed。详见 [FEATURE_USDA匹配审核框架.md](cc/FEATURE_USDA匹配审核框架.md) 与 [FEATURE_原料商品改删审核框架.md](cc/FEATURE_原料商品改删审核框架.md) 增强 7
- 原料/商品改删+层级提示接入审核框架：放开普通用户对原料、商品的 update+delete（原 created_by 限制 403），接入 change_proposals 框架（全 manual + 管理员 apply_as_admin 直写即时 + delete 完整反级联）。5 task：新建 [ProductExecutor](backend/app/services/proposals/executors/product.py)（继承 CrudExecutorBase，delete 覆写：唯一商品检查 + 软删 Product + 级联软删 ProductRecord + snapshot + revert 反级联）+ [IngredientExecutor](backend/app/services/proposals/executors/ingredient.py) delete 覆写加级联（菜谱引用检查 + 软删 ingredient + 级联 Product + IngredientHierarchy parent/child + snapshot + revert 反级联）；bootstrap 注册 ProductExecutor（全 manual）；4 端点分流去 created_by（商品 [update/delete](backend/app/api/products_entity.py) + 原料 [update ingredient_extended](backend/app/api/ingredient_extended.py) / [delete nutrition.py](backend/app/api/nutrition.py) 前端实际调用）；前端 7 处按角色提示（[IngredientDetail](frontend/src/views/ingredients/IngredientDetail.vue) 基本信息/删除/层级 + [ProductDetail](frontend/src/views/products/ProductDetail.vue) 基本信息/删除，含层级关系前端提示 bug 修复）。update 只基本信息走提议（nutrition 走独立 NutritionExecutor，update_ingredient nutrition 段保留）；delete 双层业务检查（唯一商品/菜谱引用：端点提交时拒 + 执行器 apply 时再查）；snapshot 用 _json_safe + 在置 is_active=False 之前（对齐基类 _crud_base.py:81）；两个 soft_delete_ingredient（nutrition + ingredient_extended）都接入分流对齐消除漂移。90 passed（含 11 e2e 端到端 改/删→待审→审核生效→回滚反级联）、前端 build 通过。遗留：nutrition.py:482 旧 update_ingredient 影子路由（前端不用）。**后续修复（2026-06-30 用户反馈）**：① IngredientDetail 商品编辑/删除按角色提示遗漏（Task 5 只改 ProductDetail，漏了原料详情页的关联商品编辑入口 saveProduct/deleteProduct，普通用户误报「已更新/已删除」+ deleteProduct 提前移除列表；按 userStore.is_admin 分支修复）；② 审核台变更内容改 diff——CrudExecutorBase 加 build_snapshot + service.submit 预填 proposal.snapshot（getattr 兜底特殊执行器）+ ProposalResponse 返回 snapshot + 前端 ProposalsView before→after 字段对比（delete 显示原内容/update 旧→新高亮/create 标新增），解决审核 delete 提议看不到原内容（payload 空 + snapshot 仅 apply 时填）；③ 审核 diff 时 entity_type/entity_id 看不出具体实体（如 entity_unit_override 的 entity_id 是哪个原料），加执行器 entity_label（目标实体可读名称——CrudExecutorBase 默认查 name/title、entity_unit_override/density/hierarchy/nutrition/merge 等特殊执行器覆写）+ ProposalResponse.entity_label + proposals 序列化填充 + 审核台列表 payloadSummary 前置 + 详情顶部醒目显示；④ 商品/原料详情页密度数值不显示——根因 EntityDensityResponse.density 是 Decimal、Pydantic v2 序列化为 string（`{"density":"2254.273"}`）、前端 displayDensityValue 严格 `typeof !== 'number'` 永远返空，修复前端 loadDensity/displayDensityValue/openDensityDialog 用 Number() 兜底（两文件各 3 处）；⑤ 营养/商家编辑前端提示遗漏——普通用户编辑原料营养（manual 审核）/商家时前端固定「已保存」误报成功，修 IngredientDetail saveNutritionEdit（读后端 message：pending→info 待审不刷新）、MerchantsView saveItem（按 userStore.is_admin 区分）；排查确认层级/商品实体/合并/拆分/商家删除已正确、单位/USDA admin 页 admin-only；遗留商品营养端点 edit_product_nutrition 锁管理员（普通用户 403，需单独改造放开）。详见 [FEATURE_原料商品改删审核框架.md](cc/FEATURE_原料商品改删审核框架.md)
- 实体单位覆盖/密度接入审核框架：放开原料、商品的自定义单位（实体单位覆盖 `entity_unit_overrides`）与密度（`entity_densities`）的 5 个写端点给普通用户，接入 change_proposals 提议-审核框架（全 manual 审核 + 管理员 apply_as_admin 直写即时生效 + is_active 软删回滚）。6 task：两表加 is_active（含 server_default=sa.text("1") 防 task_templates/migrate_from_bak 原始 INSERT 路径在 create_all 库崩）+ 拆唯一约束（SQLite 匿名 UNIQUE 只能表重建，drop_constraint/drop_index 均失效）+ alembic/三引擎 SQL + 补开发库（258 覆盖/1 密度保留）；两执行器 EntityUnitOverrideExecutor/EntityDensityExecutor 继承 CrudExecutorBase 复用软删/复活、覆写 validate（两种 entity_type 区分：框架注册名 vs 业务 ingredient/product）；bootstrap 全 manual 注册；32 个下游读取点加 is_active 过滤（漏一处成本算错，plan 原清单漏 units.py 7 处管理读取点靠 grep 全量比对抓出补全，packaging 共用 _query 条件分支精准过滤不影响其他 13 模型）；units.py 5 端点分流（管理员 apply_as_admin/普通用户 submit）；两详情页前端按角色提示。Decimal 三处 JSON 序列化（payload model_dump(mode=json) / 占位补 confidence / snapshot）。⚠️ 顺带修 P0：CrudExecutorBase 的 update/delete snapshot 把 ORM Decimal 塞进 change_proposals.snapshot JSON 列致管理员直写 update/delete 带 Numeric 字段必 500（潜伏 P1 框架代码、既有执行器测试没碰 Numeric 字段 update/delete 故未暴露、Task 5 让管理员直写走执行器才激活），加 _json_safe（Decimal→str、datetime/date→isoformat）应用到两处 snapshot，revert 时 str 经 Numeric 列 setter 自动转回无损，修一处惠及所有 CRUD 执行器（ingredient/unit/hierarchy/merchant/override/density）。subagent-driven 6 task 两阶段 review，全程不 commit。77 passed（含 4 e2e 端到端 submit→pending→review→applied→revert，下游 pending 隔离/applied 生效）、前端 build 通过。详见 [FEATURE_实体单位密度审核框架.md](cc/FEATURE_实体单位密度审核框架.md)
- 多用户权限系统：完整的多用户权限体系（六桶数据分类 + 通用提议-审核框架 + 审核策略三档 + 管理员超级权限）。P0 堵漏（收紧共享写/越权读/统一鉴权，含路由遮蔽与 HTTPException 被吞两个 bug 修复）+ P1 框架（change_proposals 表 + 类型执行器 + submit/review/revert/apply_as_admin API + ProposalAutoReviewer 预留接口）+ P2 共享转型（商家共享池+收藏、价格去标识 latest-price 跨用户公开、菜谱 is_public+发布、5 业务执行器含合并 snapshot/revert+分流改造、前端适配）+ P3 增强（商家合并执行器、反垃圾批量回退）。管理员超级权限：所有写操作直写 apply_as_admin、菜谱创建即发布（单用户零负担）。29 commit 在 `feat/multi-user-permissions` 分支（未合并，待 review）。新增 51 个权限/框架/共享测试。详见 [MULTI_USER_PERMISSIONS.md](cc/MULTI_USER_PERMISSIONS.md)
- 用户重置密码与 token 失效：后台「用户管理」编辑表单去掉密码字段，改为「重置密码」按钮 + 独立对话框输两次新密码（仅编辑态，新增态密码框保留）；后端给 users 加 `token_version` 列，JWT 签发带 `ver`、`resolve_user_from_token` 与 `/auth/refresh` 校验比对版本，`update_user` 改密码时 `token_version += 1` 作废该用户所有 access/refresh token（存量用户默认 0 不受影响、老 token 无 ver 取 0 兼容、前端 401 自动 refresh 闭环零改动）；bump 仅限改密码，改其他字段不踢人。详见 [FEATURE_重置密码与token失效.md](cc/FEATURE_重置密码与token失效.md)
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
- 后台管理 UI 调整：合并 AI 配置与机翻配置为单页「AI 与机翻配置」（`/admin/ai-config`，`v-expansion-panels` 双面板默认全展 + 统一保存；抽 `components/admin/ProviderCard.vue` 子组件按 `fields` 配置数组渲染 6 个 provider，消除原两页重复的 `setField`/`testProvider`/`save` 逻辑；`/admin/mt-config` 重定向到 `/admin/ai-config`）；移除 USDA 数据页（功能已由数据维护中心 100% 覆盖，删 `UsdaDataView.vue` + 路由 + 导航项）；删 `MtConfigView.vue`（并入合并页）；后台导航重排为 邀请码→单位→地图→AI 与机翻配置→数据维护中心→Agent 任务台。后端无改动。详见 [FEATURE_后台管理UI调整.md](cc/FEATURE_后台管理UI调整.md)
- 价格趋势「全部」区间：三详情页（菜谱/商品/原料）价格趋势在「周/月/季/年」后加「全部」标签看完整历史；商品/原料图表由「分页 10 条」改按时间区间累积取数（复用 `/products` 已有 `start_date/end_date`）；菜谱「全部」循环分批（每批 90 天 + `loadCostHistory` 放宽 timeout 30s，纳入 `costHistoryQueue` 串行）、商品/原料「全部」单请求 `timeout` 放宽 30s 规避前端 10s 超时；纯前端、后端零改动。详见 [FEATURE_价格趋势全部区间.md](cc/FEATURE_价格趋势全部区间.md)
- 价格记录编辑与删除：商品详情页新增编辑功能（添加/编辑共用对话框，列表每行加编辑按钮）；原料详情页新增编辑和删除功能（新对话框含价格/数量/单位/商家，列表每行加编辑+删除按钮）。两页统一调用后端已有 `PUT/DELETE /products/{record_id}`。详见 [FEATURE_价格记录编辑删除.md](cc/FEATURE_价格记录编辑删除.md)
- 商家管理定位按钮：商家管理列表每项新增「定位」按钮（`mdi-crosshairs-gps`），点击使右侧地图居中显示该商家并加红色特殊标记（复用 `MerchantMapView` 已有 `selectedMerchant` 机制：watch → setCenter + setZoom(15) + selected 红标，与商家详情页一致，地图组件零改动）。`@click.stop` 阻止冒泡不触发跳详情；无坐标时按钮禁用并提示「未设置位置」；移动端点完 `nextTick` + `scrollIntoView(block:center)` 滚到地图。仅改 `MerchantsView.vue`。详见 [FEATURE_商家管理定位按钮.md](cc/FEATURE_商家管理定位按钮.md)
- 商家地图默认范围（常用地点聚焦）：商家管理地图默认范围由「框住当前页商家」（SDK 引擎甚至只跳第一个）改为「聚焦用户常用地点周边约 5km」。新增 `user_places` 表（家/公司/自定义 kind，带 is_default）+ `/places` CRUD（含设默认联动）+ `/merchants/coordinates` 全集坐标接口；`MerchantMapView` 加 `initialCenter`/`allCoordinates` props 与地点切换器（控件区下拉），翻页/搜索保持地点视角不飞回全国，补 SDK 真 fitBounds（高德 `setBounds`/百度 `setViewport`/腾讯 `fitBounds`），定位圆 1km→5km；`UserPlacesView` 子页（个人中心入口 + `/profile/places` 路由）管理地点，复用 `MapPicker`；没设地点时显示全部商家分布（allCoordinates 算 bounds、标记仍画当前页）；切换记 localStorage。清理遗留死代码 `FavoriteMerchant` 表 + `POST /merchants/route` 端点 + `map_service.calculate_route` 孤儿（前端从未接入），导出/导入链路 `favorite_merchants`→`user_places` 全迁移。详见 [FEATURE_商家地图默认范围.md](cc/FEATURE_商家地图默认范围.md)
