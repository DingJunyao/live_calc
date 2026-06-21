# 本地路径导入改用 .env 配置

## 背景

数据维护中心「从本地路径导入」此前在页面上用 `v-text-field` 让管理员**手填**服务器目录绝对路径，作为 `local_path` 查询参数传给 `POST /import/data/import-from-local`。

而后端其实早有 `.env` 变量 `DATA_LOCAL_PATH`（读到 `settings.data_local_path`），且启动时的首次初始化导入（`main.py` 的 `lifespan`）一直在用它（见 [BUGFIX_启动导入仅初始化时进行.md](BUGFIX_启动导入仅初始化时进行.md)）。三处来源不统一：页面上手填的路径可能与 `.env` 配置漂移，管理员还可能手滑填错。

## 方案

把「从本地路径导入」收口到 `.env` 的 `DATA_LOCAL_PATH`，与启动导入共用同一来源（单一数据源，消除漂移）：

- 后端 `trigger_local_import` 移除 `local_path` 查询参数，改读 `settings.data_local_path`；未配置 → 400「未在 .env 配置 DATA_LOCAL_PATH，请在 backend/.env 设置」，目录不存在 → 400「目录不存在」（保留原校验）。
- 新增只读 `GET /data/local-path-config`（仅管理员），返回 `{"configured": bool, "path": str|null}`，供前端展示。刻意**不**在该端点校验目录存在性（交给导入端点，避免展示与执行两套校验打架）。
- 前端删掉输入框，换成三态只读展示（读取中 / 已配置显示路径 / 未配置警告）；`onMounted` 非阻塞拉取 GET 填充（失败降级为「未配置」）；未配置时禁用「开始导入」按钮；`importFromLocalPath()` 不再传路径参数。

**不改**：service 层 `import_from_local_dir(db, local_path, ...)` 签名（路径来源由 API 层注入，职责单一）、启动导入逻辑、`.env` 变量与 `config.py` 的 `data_local_path` 字段、`useImportTask.ts`（`startTask` 第二参有默认值 `{}`，裸调合法）。

## 改动文件

- `backend/app/api/import_api.py`：加 `from app.config import settings`；改造 `trigger_local_import`（去参、读 settings、两种 400、更新 docstring）；新增 `GET /data/local-path-config`。
- `frontend/src/views/admin/DataMaintenanceView.vue`：删 `v-text-field` 与 `localPath` ref，换成 `localPathConfig` reactive（`loaded`/`configured`/`path`）+ 三态只读展示；`onMounted` 加配置拉取（非阻塞、失败降级）；按钮 `:disabled` 联动；`importFromLocalPath` 去参。
- `backend/tests/test_import_api.py`：`test_local_import_admin_only` 去掉过时的 `?local_path=/tmp` query（反映新契约）。

## 验证

- 后端 `py_compile` 通过；前端 `npm run build` 通过（退出码 0）。
- subagent-driven-development 三道审查（spec 符合性 + 代码质量 + 端到端 final）均通过：前后端字段名/类型、路由前缀、参数有无、配置来源逐项对齐，端到端流程无断点。
- 运行时浏览器手动核对（已配置显示路径 / 未配置禁用按钮 / 点击导入正常入列轮询）待用户确认。

## 已知 follow-up（未做，YAGNI）

- **未补**「管理员未配置 `DATA_LOCAL_PATH` 得 400」单测——该测试文件是极简 TestClient + 状态码断言风格（无 fixture/mock），补该用例需临时篡改全局 `settings` 单例，破坏既有风格且有竞态。该 400 分支靠手动核对验证。
- `backend/app/api/admin.py` 有一条历史遗留死端点 `POST /import-from-local-path`（接收 body `local_path`，前端无调用方），与本次改造端点语义重叠，**非本次引入**，可后续单独清理。

## 相关

- 设计文档：`docs/superpowers/specs/2026-06-21-本地路径导入改用env配置-design.md`
- 实施计划：`docs/superpowers/plans/2026-06-21-本地路径导入改用env配置.md`
- 关联启动导入逻辑：[BUGFIX_启动导入仅初始化时进行.md](BUGFIX_启动导入仅初始化时进行.md)
