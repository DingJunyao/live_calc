# 数据导入过程无进度反馈修复

## 症状

个人中心「数据导入」（`ImportUploadDialog`）上传合法 ZIP 后，前端一直转圈、无任何反馈。上传非法包（快速 failed）反而能弹错误提示。

## 根因（systematic-debugging 5 步定位）

不是「完成后没提示」，而是「过程里没有可感知的进度」，用户没等到结束就以为卡死。证据链：

1. **后端任务能正常 success**：DB 实测 id=1 `upload_import status=success`（29s 完成，stats 完整 764 原料/362 菜谱/2370 价格记录），`GET /import/task/1` 返回 200 + 正确 success。
2. **前端 watch 机制正常**：上传垃圾包触发 `failed`，前端**正常弹了「无法识别的数据格式」alert**、停转圈——证明 `ImportUploadDialog` 的 watch（监听 `currentTask.status` 终态）工作。
3. **真凶——导入过程 progress 恒为空**：三层断链
   - [`_run_import_task`](backend/app/services/importer/api_service.py#L78) 设 `status="running"` 时**不同时写 progress** → 初始即 `null`。
   - [`import_from_upload_path`](backend/app/services/importer/api_service.py#L220) 收到 `progress_callback` 参数却**不透传**给 `importer.import_all`（`import_from_git_repo`/`import_from_local_dir`/`import_from_upload` 四个函数同款毛病）。
   - 两个 importer 的 `import_all(self, collection)` 签名**不接受 `progress_callback`**：[`HowToCookImporter`](backend/app/services/importer/importers/howtocook.py#L54) 4 阶段、[`ExportImporter`](backend/app/services/importer/importers/export.py#L49) 16 阶段，全程零回调。

后果：导入全程（大包几分钟）`progress` 恒 `{}`，前端只显示 `{{ currentTask?.progress?.message || '正在导入，请稍候…' }}` fallback + 转圈，无阶段、无数字。

## 修复（KISS，只动后端，前端零改动自动受益）

`Importer.import_all` 加 `progress_callback` 参数，两个 importer 在**阶段边界** + **大循环周期**回调；`api_service` 透传 + 写初始 progress。4 文件：

- [`models.py`](backend/app/services/importer/models.py#L87)：基类 `import_all(self, collection, progress_callback=None)` 签名 + 文档。
- [`howtocook.py`](backend/app/services/importer/importers/howtocook.py)：`import_all` 加 `cb` 兜底（`lambda` 空操作）+ 4 阶段前置 cb；`_import_ingredients`/`_import_recipes` 加 `cb=None` 参数 + 循环 cb（复用既有 `idx % 100`/`idx % 50` logger 节流点，零额外开销）。
- [`export.py`](backend/app/services/importer/importers/export.py)：`import_all` 16 阶段前置 cb；`_import_ingredients`/`_import_recipes`/`_import_products`/`_import_price_records` 加 `cb` 参数 + 初始 `cb(stage,0,total,...)` + 循环周期 cb（原料/商品每 100、菜谱每 25、价格记录每 200）。
- [`api_service.py`](backend/app/services/importer/api_service.py)：`_run_import_task` 设 `running` 时同时写初始 progress `{"stage":"初始化","message":"正在准备导入…"}`（前端第一次轮询就有反馈）；四个 `import_from_*` 把 `progress_callback` 透传给 `importer.import_all`（`result = importer.import_all(collection)` 用 `replace_all` 一次覆盖 git/upload/upload_path 三处 + local_dir 的 return 形式单独处理）。

## 验证

- **py_compile** 四文件通过。
- **单元验证**（`uv run` 之外的坑见下）：造 manifest + 150 原料包，直接调 `ExportImporter.import_all(coll, progress_callback=cb)`，cb 被调 **13 次**：11 个非循环阶段各 1 次 + ingredients 循环 2 次（`导入原料 0/150` → `导入原料 100/150`，**数字滚动**），`STATS {ingredients:150}`、`ERRORS []`（success），清理 150 条测试数据。
- **DB 演变实证**（浏览器端到端 + 后台 0.3s 轮询 `import_tasks.progress`）：任务 `pending(progress=None) → running(progress={"stage":"初始化","message":"正在准备导入…"}) → 终态`——初始 progress 生效。
- **failed 路径前端 UI**：垃圾包上传，前端正常弹「无法识别的数据格式」alert + 停转圈（证明 watch 工作）。

无表结构变更，纯后端逻辑。

## 附带发现的潜在隐患（本次未修，超范围）

测试包触发、用户真实系统导出包不触发（导出器写字段完整），但值得后续修：

1. **`Product.tags` list 绑定 SQLite 崩**：[`_import_products`](backend/app/services/importer/importers/export.py) `Product(tags=item.get("tags", []))`，当包缺 `tags` 字段时默认 `[]`（Python list），SQLite pysqlite 驱动不支持直接绑 list（报 `type 'list' is not supported`）。而 `aliases` 不崩（`MutableDict.as_mutable(JSON)` 会序列化）。根因是 `Product.tags` 列没像 `aliases` 那样用 `MutableDict`。修法：`Product.tags` 改 `MutableDict.as_mutable(JSON)` 对齐 `aliases`（改模型，影响面待评估），或 importer 侧 `item.get("tags") or []` 后确保序列化。
2. **`ProductRecord.original_unit_id` NOT NULL**：[`_import_price_records`](backend/app/services/importer/importers/export.py) 缺 `original_unit_id` 时插 None 触发 NOT NULL 崩。系统导出包有该字段不触发。

## 教训

- **「一直转圈无反馈」要区分「过程无进度」vs「完成后无提示」**：本次是前者（progress 恒空），不是 watch 失效。failed 能弹 alert 是关键判据——证明 watch 链路正常，把怀疑缩到 progress 生成。
- **多组件系统先在各层加证据**：DB 查任务真实状态（后端未卡）+ 浏览器复现 failed（前端 watch 正常）+ DB 轮询 progress 演变（progress 恒空）三层证据一合，根因自现。
- **`py_compile` 过 ≠ 依赖装了**：`py_compile` 只编译字节码不执行 import，不触发 `from sqlalchemy import`。要确认 env 装了依赖，得真跑 import。
- **venv 路径坑**：CLAUDE.md 说「根目录下的 .venv」实为**项目根** `d:\code\live_calc\.venv`（`VIRTUAL_ENV` 指向它，后端服务用、装了 sqlalchemy）；`backend/.venv` 是 `uv` 默认想用的空壳（没装依赖）。后端脚本要用项目根 `.venv` 的 python，不是 `backend/.venv`。
- **测试包要字段完整**：造测试导入包要 mimic 系统导出格式（manifest + 各 json 字段齐全），否则连续踩 NOT NULL / list 绑定坑，干扰验证核心修复。
