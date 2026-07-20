# 存储配置后台化与个人信息编辑重组

## 概述

两个子任务：
- **个人信息编辑重组 + 地区**：ProfileView 头像/地区收进「用户信息编辑」对话框，地区 seed 从首次菜谱初始化解耦。
- **图片存储配置后台化**：存储配置（local/S3）从 .env 迁移至数据库后台管理，支持向导式切换与双向迁移。

## 子任务一：个人信息编辑重组 + 地区

### Task 1: 行政区划 seed 解耦

**问题**：`ensure_administrative_regions` 在 `main.py` lifespan 中被嵌套在 `FIRST_RUN_INIT_RECIPES` 的 `else` 块内（非首次运行），导致非首次初始化库 `administrative_regions` 表为空，前端级联选择 No data。

**根因**：行政区划是纯地理基础数据，不应依赖菜谱初始化。

**修复**：将 `ensure_administrative_regions` 从 `first_run_init_recipes` 条件块外提（[main.py:257-263](backend/app/main.py)），与 `ensure_allergen_groups` 对齐，独立执行。

### Task 2: 地区 seed 手动更新 API

**实现**：新增两 API（[regions.py](backend/app/api/regions.py)）：
- `GET /admin/regions/seed-status` - 返回统计（total_count/china_count/needed）
- `POST /admin/regions/seed` - 调用 `upsert_administrative_regions` 手动更新

**对齐范式**：与过敏原 seed 双轨一致（lifespan ensure + 手动按钮）。

### Task 3: ProfileView 头像/地区收进「用户信息编辑」

**前端改动**（[ProfileView.vue](frontend/src/views/profile/ProfileView.vue)）：
- **删顶部独立头像卡**：头像/地区收进「用户信息编辑」对话框内
- **地区整合**：删独立 `regionDialog`，地区选择直接在编辑表单内（v-select 级联）
- **保存整合**：地区保存整合进 `PUT /auth/me/account`（`UserAccountUpdate` 已支持 `region_id`）
- **昵称去图标**：昵称输入框删 `prepend-icon`（与其他输入框一致）
- **第一级文案**：地区级联第一级标签改「国家/地区」（原「国家」）

### Task 4: 数据维护中心「行政区划」卡片

**前端改动**（[DataMaintenanceView.vue](frontend/src/views/admin/DataMaintenanceView.vue)）：
- 新增「行政区划」v-card（统计 + needed 提示 + 更新按钮）
- onMounted 并行 `loadStatus` + `loadTasks`
- needed 时显示 v-alert 提示 + 更新按钮

## 子任务二：图片存储配置后台化

### Task 5: StorageConfiguration 表

**设计**：单行配置表（对齐 `MapConfiguration`），字段：
- `storage_backend`（local/s3）
- `base_url`（local 静态路径 / S3 公共 URL）
- S3 配置（endpoint/access_key/secret_key/bucket/region/url_style）
- `updated_at`

**迁移**：
- [alembic 20260720_0001](backend/alembic/versions/20260720_0001_storage_configuration.py)
- 三引擎 SQL 脚本（[backend/scripts/sql/](backend/scripts/sql/)）
- 开发库直补（SQLite +4 列）

### Task 6: .env 存储变量加 BOOTSTRAP_ 前缀

**目的**：明确「初始化引导」语义，与后台 DB 配置区分。

**改动**：
- .env 变量加前缀（`BOOTSTRAP_STORAGE_BACKEND` / `BOOTSTRAP_STORAGE_BASE_URL` / `BOOTSTRAP_S3_*`）
- [config.py Settings](backend/app/config.py) 同步加前缀
- [storage/factory.py](backend/app/services/storage/factory.py) 引用同步
- [migrate.py CLI](backend/app/services/storage/migrate.py) 引用同步

### Task 7: load_effective_storage_config() 三层优先级

**实现**（[storage/factory.py](backend/app/services/storage/factory.py)）：
- **优先级**：DB（最高）→ .env BOOTSTRAP_* → 代码默认（最低）
- **逐字段 source 标注**：`StorageConfigResponse.sources` 返回每字段来源（db/env/default）
- **lru_cache 单例**：factory 函数用 `@lru_cache` 缓存，PUT 配置后 `reset_cache` 热生效
- **_query_db_row 独立 SessionLocal**：防长事务跨请求持连接
- **_is_truthy 统一空值判断**：对齐地图配置范式

### Task 8: storage 四管理 API

**实现**（[storage.py](backend/app/api/storage.py)）：
- **GET /admin/storage/config**：脱敏返回（`secret` 字段 masked 为 `********`）+ `sources`
- **PUT /admin/storage/config**：仅 s3 写前强制测试连接（`test_connection` 探针），secret 哨兵（null=不变，防误清凭证）
- **POST /admin/storage/test**：测试连接（local 返回 fixed string/s3 调 boto3）
- **POST /admin/storage/migrate**：建 `ImportTask(task_type='storage_migrate')` 返回 task_id

**Schema 对齐**：`StorageConfigResponse` 对齐 `MapConfigResponse` 范式（脱敏 + sources）。

### Task 9: 双向异步迁移

**迁移复用 ImportTask**：蹭成熟任务机制（task_type='storage_migrate'）。

**核心迁移逻辑**（[storage/migrate.py](backend/app/services/storage/migrate.py)）：
- **_migrate_to_s3_core**：
  - `walk(top=images_dir)` 遍历本地文件
  - 幂等上传（exists 跳过）
  - 进度回调（uploaded/skipped/failed）
- **_migrate_from_s3_core**：
  - `list_objects_v2` 分页（1000/批）
  - get 落本地（幂等不覆盖）
  - 进度回调

**CLI 复用 core**：`python -m app.services.storage.migrate` DRY 复用两核心函数。

### Task 10: StorageConfigView 向导五步

**前端实现**（[StorageConfigView.vue](frontend/src/views/admin/StorageConfigView.vue)）：
1. **选**：选择 local 或 s3
2. **填**：动态表单（local 填 base_url / s3 填 7 字段）
3. **强制测试**：点下一步强制「测试连接」通过
4. **迁移轮询**：若切换 storage 则触发迁移（direction 自动判定 local↔s3），轮询任务状态（uploaded/skipped/failed 三色统计）
5. **确认**：迁移完成/无需迁移后保存配置

**修复**：向导关闭时 `watch wizardDialog` 清理 `poller`（泄漏修复）。

**去 any 类型**：替换 `storageForm: any` 为显式接口（LocalStorageConfig/S3StorageConfig）。

### Task 11: 任务列表 storage_migrate 分支

**前端改动**（[DataMaintenanceView.vue](frontend/src/views/admin/DataMaintenanceView.vue)）：
- 任务列表 `task_kind === 'import' && task.type === 'storage_migrate'` 分支
- **命名**：`direction` 命名（'上传至 S3' / '从 S3 下载'）
- **三色 stats**：uploaded 绿 / skipped 灰 / failed 红

## 关键设计与教训

### DB 覆盖 .env 三层优先级

**问题**：配置 DB 化后与 .env 冲突（环境变量读不过来 DB）。

**解决**：三层优先级（DB→.env→默认），逐字段 `source` 透明标注，用户知道每字段从哪来。

**BOOTSTRAP_ 前缀明确语义**：初始化引导用（BOOTSTRAP_*）与后台 DB 配置彻底区分，避免歧义。

### 行政区划 seed 错位

**教训**：基础数据 seed（行政区划）不该依赖业务初始化（菜谱），应独立执行。非首次库表空→前端 No data。

### 双向迁移复用 ImportTask

**DRY**：蹭成熟任务机制（ImportTask）+ CLI 复用 core 函数，不重复造轮子。

### PUT secret 哨兵

**防误清凭证**：`PUT /admin/storage/config` secret 字段 null=不变（哨兵），非误清空。

**仅 s3 写前探针**：PUT 时仅 s3 强制测试连接，local 跳过（防配错锁死）。

## 文件清单

### 后端
- [backend/app/main.py](backend/app/main.py) - lifespan 地区 seed 解耦
- [backend/app/api/regions.py](backend/app/api/regions.py) - 地区 seed API
- [backend/app/models/storage_config.py](backend/app/models/storage_config.py) - StorageConfiguration 模型
- [backend/app/schemas/storage_config.py](backend/app/schemas/storage_config.py) - StorageConfigResponse/Update
- [backend/app/services/storage/factory.py](backend/app/services/storage/factory.py) - load_effective_storage_config
- [backend/app/services/storage/migrate.py](backend/app/services/storage/migrate.py) - 双向迁移 core + CLI
- [backend/app/api/storage.py](backend/app/api/storage.py) - 四管理 API
- [backend/app/config.py](backend/app/config.py) - BOOTSTRAP_ 前缀变量
- [backend/alembic/versions/20260720_0001_storage_configuration.py](backend/alembic/versions/20260720_0001_storage_configuration.py) - alembic 迁移
- [backend/scripts/sql/20260720_storage_configuration_*.sql](backend/scripts/sql/) - 三引擎 SQL 脚本
- [backend/tests/services/storage/](backend/tests/services/storage/) - 7 单测文件（base/effective/factory/local/migrate/api + s3 跳过）
- [backend/tests/services/test_region_admin.py](backend/tests/services/test_region_admin.py) - 地区 admin API 3 测试
- [backend/tests/services/test_region_seed_lifespan.py](backend/tests/services/test_region_seed_lifespan.py) - 地区 lifespan 解耦验证

### 前端
- [frontend/src/views/profile/ProfileView.vue](frontend/src/views/profile/ProfileView.vue) - 头像/地区收进编辑对话框
- [frontend/src/views/admin/DataMaintenanceView.vue](frontend/src/views/admin/DataMaintenanceView.vue) - 地区卡片 + 任务列表 storage_migrate 分支
- [frontend/src/views/admin/StorageConfigView.vue](frontend/src/views/admin/StorageConfigView.vue) - 存储配置向导
- [frontend/src/api/storage.ts](frontend/src/api/storage.ts) - storage API 客户端
- [frontend/src/router/index.ts](frontend/src/router/index.ts) - /admin/storage 路由
- [frontend/src/components/layout/AdminNav.vue](frontend/src/components/layout/AdminNav.vue) - 导航加「图片存储」入口

## 测试结果

### 后端
- **compileall**：✅ 无语法错误
- **存储/地区单测**：✅ 31 passed, 2 skipped（s3 boto3 未安装）
- **全量 pytest**：✅ 593 passed, 23 failed, 8 skipped（失败全预存无关项：auth/import/locations/nutrition/permissions/proposals/recipes/reports/usda/agent/downloader/export-importer/format_detector，无本次引入的新失败）

### 前端
- **build**：✅ 38.03s，130 entries

## 手动核验清单（开发者）

- 个人中心头像/地区在「用户信息编辑」对话框内，昵称无图标，第一级「国家/地区」，各级有数据
- 后台「数据维护中心」：「行政区划」卡片（统计 + 更新按钮）+ 任务列表显示 storage_migrate
- 后台「图片存储」：向导切换 local↔S3 全流程（填配置 → 测试连接 → 迁移 → 确认）
- 地区级联、头像上传、菜谱图片（local 模式）正常

## 同步改动

- [backend/tests/services/storage/test_base.py](backend/tests/services/storage/test_base.py) - `test_settings_has_storage_config` 改 BOOTSTRAP_ 前缀（对齐 .env 变量名）

## 备注

- 本 feature 涉及数据库表变更（`storage_configurations`），开发库已直接补列，生产环境需跑 alembic 或 SQL 脚本。
- S3 相关测试因 boto3 未安装跳过（预存），不影响 local 模式功能。
- 存储配置切换后需重启后端服务才能完全生效（factory lru_cache 单例），PUT 后有提示。
