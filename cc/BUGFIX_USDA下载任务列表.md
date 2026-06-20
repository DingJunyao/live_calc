# USDA 下载/上传任务纳入数据维护页任务列表

## 背景

数据维护中心（`DataMaintenanceView.vue`）的「任务列表」原本只合并两种来源：

1. `import_tasks`（仓库/本地/上传/AI 推测，走 `useImportTask` composable）
2. `agent_sessions`（Agent 任务台会话，走 `listSessions` + 轮询）

而「下载 USDA」「上传 ZIP」走的是第三条路——`usda_tasks` 表（`usda_admin.py` 的 `_do_download`/`_run` 在后台任务里创建），既没接进 `mergedTasks`，`POST /usda/download`、`/usda/upload` 也只返回 `{"message": ...}`、不回 `task_id`，前端无从入列/轮询。故点下载后任务列表无任何记录——即用户反馈的「下载 USDA，未写到任务列表里面」。

## 方案

`usda_tasks` 作为第三种来源（`_kind: 'usda'`）合并进 `mergedTasks`，复刻 agent 那套「拿 id → 入列 → 轮询」的机制。执行路径不变，仍走现有后台 httpx 下载/导入。

## 改动

### 后端 `backend/app/api/usda_admin.py`

- `POST /usda/download`、`/usda/upload`：改为在端点内（同步）先建 `UsdaTask(status="running")` 并 commit 拿到 id，返回 `{task_id, ...}`；后台 `_do_download(db_factory, task_id, datasets)` 与上传闭包改为按 `task_id` 取回记录更新（极端情况下记录丢失则现场兜底新建）。
- 新增 `GET /usda/tasks`（列表，按 id 倒序，limit 夹在 1–100）与 `GET /usda/tasks/{task_id}`（单条，轮询用），共用 `_usda_task_dict` 序列化（含 `created_at`/`updated_at`）。
- 旧 `GET /usda/task`（最新一条）保留兼容，未改。

### 前端

- `api/usda.ts`：新增 `getUsdaTasks(limit)`、`getUsdaTaskById(id)`。
- `views/admin/DataMaintenanceView.vue`：
  - 新增 `UsdaTaskItem` 类型 + `usdaTasks` ref + `usdaPollingMap`。
  - `mergedTasks` 合并第三类 `UsdaTaskLike`（`_kind: 'usda'`）。
  - `downloadUsdaData`/`triggerUsdaUpload` 拿 `task_id` 后 `addUsdaTask` 入列 + 启动轮询。
  - `addUsdaTask`/`startUsdaPolling`/`stopUsdaPolling`：轮询 `/usda/tasks/{id}`，到终态停轮询并刷新统计（`loadUsdaStats`）。
  - `onMounted` 恢复近期 usda 任务历史 + 运行中任务的轮询；`onUnmounted` 清理 usda 轮询。
  - 模板三分支：`import`（进度条/统计）/ `usda`（食材数 + 错误 + 运行中提示）/ `agent`（点击跳详情）；usda 任务不显示取消按钮（后台 httpx 下载无法中途取消），但保留运行中 spinner。
  - `taskTypeLabels` 补 `download: 'USDA 数据下载'`、`upload: 'USDA 数据上传'`（usda_tasks.task_type 沿用后端原值 download/upload）。

## 说明

- 进度粒度：USDA 下载/上传的 `progress` 仅在完成时写 `{foods, ...result}`，运行中无实时进度（httpx 下载不回传进度给 UsdaTask）。故 running 时只显示 spinner + 「后台处理中…」，完成显示食材数。符合「走现有后台下载」要求，未改 `downloader.py`。
- 翻译任务不走 `usda_tasks`（走 `TranslateTask`），不纳入本列表。
- 顺带把「上传 ZIP」一并纳入：与下载同表同机制，零成本，且二者都在「USDA 数据管理」卡片下，统一展示才一致。

## 验证

- 后端 `python -m py_compile backend/app/api/usda_admin.py` 通过。
- 前端 `npm run build` 通过（`DataMaintenanceView-BmdXOlcA.js` 23.07 kB）。
