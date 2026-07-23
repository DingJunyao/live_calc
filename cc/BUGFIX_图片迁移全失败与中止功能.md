# 图片迁移修复与中止功能

## 问题

后台「图片存储配置」向导的「S3→本地」迁移存在三个问题：

1. **迁移全部失败**：to_local 方向每个文件 404，日志 `to_local 失败 livecalc/recipes/麻婆豆腐_0.jpeg: livecalc/recipes/麻婆豆腐_0.jpeg`（错误信息就是 key 本身）。
2. **路径未限定**：list 了整个 bucket 的文件，而非只迁应用命名空间。
3. **进度不实时 + 无中止**：已上传/跳过/失败计数要等跑完才出现；无法中途停止。

## 根因

**问题 1（全部失败，base_path 翻倍）** 是最隐蔽的 bug。

链路：[migrate.py:50](backend/app/services/storage/migrate.py#L50) `_migrate_from_s3_core` 用裸 client `list_objects_v2` 列 bucket，拿到的 `obj["Key"]` 是 bucket 里的**真实完整 key**（含 base_path 前缀 `livecalc/`）。然后直接把真实 key 传给 [s3.py:104](backend/app/services/storage/s3.py#L104) `s3_backend.get(key)`，内部 `_full_key(key)` = `f"{base_path}/{key}"` → `livecalc/livecalc/recipes/麻婆豆腐_0.jpeg`（**前缀翻倍**）。get_object 请求翻倍路径 → 404 → 转 `FileNotFoundError(key)`（[s3.py:107](backend/app/services/storage/s3.py#L107)），`str(e)` = key → 日志就成了「失败 key: key」，两者看起来一样，极其迷惑。

to_s3 方向走本地 walk（逻辑 key），put 加一次前缀正确——仅 from_s3 坏。

**问题 2**：`list_objects_v2` 不带 `Prefix`，全 bucket 扫。

**问题 3（计数不实时）**：前端 `migrationStats` 读 `task.stats`，只在 [api_service.py:107](backend/app/services/importer/api_service.py#L107) 结束时写入。运行中 `progress` 只含 `{stage, current, total, message}`。无分类计数。中止功能完全不存在。

## 修复方案

核心思路：顺着项目已有的 `status="cancelled"` + 后台循环检查范式（USDA 翻译 [import_api.py:434](backend/app/api/import_api.py#L434) 同款），最小波及。

**改动 1：from_s3 路径限定 + base_path 剥前缀**（[migrate.py:55-114](backend/app/services/storage/migrate.py#L55)）
- 新增 `_strip_base_path(full_key, base_path)` 辅助函数
- list 带 `Prefix = base_path + "/"`（base_path 非空时）
- 真实 key 剥前缀还原逻辑 key（`livecalc/recipes/a.jpg` → `recipes/a.jpg`）
- 逻辑 key 喂给 `get()`（内部 _full_key 加一次前缀→正确路径）
- 落地 `images_dir / 逻辑key`，与 to_s3 对称、幂等闭环
- 过滤目录占位符（key 以 `/` 结尾）
- 查阅 spec：[[FEATURE_存储配置后台化与个人信息编辑重组]]

**改动 2：实时分类计数**（[api_service.py:49-78](backend/app/services/importer/api_service.py#L49)）
- `make_progress_callback` 加可选 `counts` 参数（向后兼容）合并进 progress
- 两个 core 循环传 `counts={uploaded, skipped, failed}`
- 前端 `migrationStats` 优先读 progress 实时计数

**改动 3：中止功能**（复用现有取消端点）
- `make_progress_callback` 返回 `t.status == "cancelled"` 作为取消信号
- 两个 core 循环检查返回值，True 则 break
- `_run_import_task` 末尾：若 status 已是 cancelled 则保留，不被 success/failed 覆盖
- 前端进度区加「中止迁移」按钮 → `POST /import/task/{id}/cancel`

**KISS 决策：零表结构变更**（用 status 字符串，不加 cancelling 中间态）

## 验证

- `py_compile` 无语法报错
- 13 个单测全过（涵盖剥前缀/路径限定/目录占位符/counts/cancel/保留 cancelled/成功/失败）0.30s
- 前端 `npm run build` 通过（40.50s, precache 131 entries）
- 无表结构变更，无需 alembic/SQL

## 文件变更

| 文件 | 变更 |
|------|------|
| `backend/app/services/storage/migrate.py` | 新增 `_strip_base_path`；`_migrate_from_s3_core` 全改；`_migrate_to_s3_core` 加 counts+cancel |
| `backend/app/services/importer/api_service.py` | `make_progress_callback` 加 counts+返回cancel；`_run_import_task` 保留 cancelled |
| `frontend/src/views/admin/StorageConfigView.vue` | 实时计数、中止按钮、cancelled 轮询处理 |
| `backend/tests/services/test_storage_migrate.py` | 新建，13 个 TDD 用例 |

## 教训

「to_local 失败 key: key」这种两值相同的日志是 base_path 翻倍 404 的典型信号——`str(FileNotFoundError(key))` = key，所以前后一致。看到日志值两次一样但路径有 base_path 前缀，第一反应就该查 `get` 是不是加了两次前缀。**list_objects 返回的是 bucket 里的真实 key（含 base_path），不能直接喂给同个 backend 的 get/put/exists**，否则前缀必然翻倍。

另一教训：迁移幂等性（已存在跳过）让「暂停」很自然地等价于「中止后再跑一次」——支持取消就足够，YAGNI 不做暂停状态机。设计文档存于 [spec](docs/superpowers/specs/2026-07-22-图片迁移修复与中止-design.md)，实现计划存于 [plan](docs/superpowers/plans/2026-07-22-图片迁移修复与中止.md)。
