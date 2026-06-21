# 数据维护中心「从本地路径导入」改用 .env 配置

## 背景与问题

数据维护中心（`DataMaintenanceView.vue`）有一张「从本地路径导入」卡片，当前实现是：

- 前端用一个 `v-text-field` 让管理员**手动输入**服务器上的目录绝对路径；
- 点击「开始导入」后，把该路径作为 `local_path` 查询参数传给 `POST /import/data/import-from-local`；
- 后端 `trigger_local_import` 校验目录存在后，调用 service 层 `import_from_local_dir` 执行导入。

问题在于：后端其实**早就有**一套统一的本地数据路径配置——

- `backend/.env` 中的 `DATA_LOCAL_PATH`（当前值为 `D:/code/HowToCook_json`）；
- `backend/app/config.py` 的 `settings.data_local_path` 字段；
- `backend/app/main.py` 启动时的首次初始化导入，已经在读 `settings.data_local_path`。

也就是说，「页面上手填路径」与「启动时从配置读路径」是同一件事的两个入口，路径来源不统一，管理员还可能手滑填错。属于重复造轮子，违反 DRY。

## 目标

- 「从本地路径导入」不再在页面上填写目录路径，改为直接复用 `.env` 中的 `DATA_LOCAL_PATH`。
- 与启动时的导入逻辑共享同一个路径来源，消除不一致。
- 管理员仍能在页面上看到当前会导入哪个目录（只读），但无法在页面上修改。

## 现状（改动前）

| 层 | 文件 | 现状 |
|---|---|---|
| 前端 UI | `frontend/src/views/admin/DataMaintenanceView.vue` | `v-text-field` 绑定 `localPath` ref（约 L58-103、L495、L638-647） |
| 前端任务 composable | `frontend/src/composables/useImportTask.ts` | `startTask('/import/data/import-from-local', { params: { local_path } })`（L50-76） |
| 后端路由 | `backend/app/api/import_api.py` | `trigger_local_import(local_path: str, ...)`，校验 `os.path.isdir`（L100-122） |
| 后端 service | `backend/app/services/importer/api_service.py` | `import_from_local_dir(db, local_path, user_id, ...)`（L137-163） |
| 配置 | `backend/app/config.py` / `backend/.env` | `data_local_path: Optional[str]`；`DATA_LOCAL_PATH=D:/code/HowToCook_json` |
| 启动导入 | `backend/app/main.py` | 首次初始化时读 `settings.data_local_path` 导入（L210-239） |

## 设计

### 后端

**1. 改造 `POST /import/data/import-from-local`（`import_api.py`）**

- 移除 `local_path: str` 查询参数。
- 函数体内改为从 `settings.data_local_path` 读取路径。
- 校验逻辑细化为两种 400：
  - `settings.data_local_path` 为空 → `400「未在 .env 配置 DATA_LOCAL_PATH，请在 backend/.env 设置」`；
  - 路径不是有效目录 → `400「目录不存在: {path}」`（保留原有提示）。
- 通过校验后，把 `settings.data_local_path` 作为 `local_path` 传给 `import_from_local_dir`，其余流程不变。

**2. 新增 `GET /import/data/local-path-config`（`import_api.py`）**

- 仅管理员（与导入端点同样的 `is_admin` 校验）。
- 返回结构：

```json
{ "configured": true, "path": "D:/code/HowToCook_json" }
```

未配置时：

```json
{ "configured": false, "path": null }
```

- 该端点只读，仅用于前端展示。**不**在此端点判断目录是否存在——目录校验交给导入端点负责，避免展示接口承担过多职责。

### 前端

**`DataMaintenanceView.vue`**

- 删除 `v-text-field`（含 `localPath` ref、相关提示）。
- 新增一个只读展示区：
  - `onMounted`（或现有初始化时机）调用 `GET /import/data/local-path-config`；
  - `configured === true` → 显示「将导入：`{path}`」，「开始导入」按钮可用；
  - `configured === false` → 显示「未配置 `DATA_LOCAL_PATH`，请在 `backend/.env` 设置」，「开始导入」按钮 `disabled`；
  - 展示区用只读文本（非可编辑输入框），视觉上弱化为信息提示。
- `importFromLocalPath()` 调整为不传 `params`：`startTask('/import/data/import-from-local')`，POST 空体。
- 配置拉取失败时降级：按钮禁用 + 展示「配置加载失败」，避免在未知状态下放行导入。

**`useImportTask.ts`**

- `inferTaskType` 中 `import-from-local` → `local_import` 的推断逻辑保持不变（端点路径没变）。
- `startTask` 不再为该端点传 `params`，无需改动通用签名。

### 不变的部分

- service 层 `import_from_local_dir(db, local_path, user_id, ...)` 签名不变——它只负责「给路径就导入」，路径来源由 API 层注入，职责清晰（单一职责）。
- `backend/.env` 的 `DATA_LOCAL_PATH` 变量、`config.py` 的 `data_local_path` 字段、`main.py` 启动导入逻辑：全部原样复用，零改动。
- 子目录自动检测（`out/`、`data/`、`recipes/`）、格式自动检测、导入器选择等 service 内部逻辑不变。

## 错误处理

| 场景 | 行为 |
|---|---|
| `.env` 未配 `DATA_LOCAL_PATH` | 导入端点 400；展示端点返回 `configured: false`，前端禁用按钮 |
| 配置了但目录不存在 | 导入端点 400「目录不存在」；展示端点仍返回 `configured: true`（不校验存在性），前端允许点击，点击后由导入端点报错并在任务里反馈 |
| 展示端点拉取失败 | 前端降级禁用按钮 + 「配置加载失败」 |
| 非管理员调用 | 两个端点均 403 |

## 测试策略

- **后端**：
  - 无语法错误（遵循 CLAUDE.md「所有后端修改必须确保无语法错误」）；
  - 人工核对：未配置时 400、目录不存在时 400、正常时返回 task_id；展示端点 configured 两种取值。
- **前端**：
  - 构建通过（遵循 CLAUDE.md「所有前端修改必须确保构建通过」）；
  - 人工核对：已配置/未配置两种展示、按钮禁用态、点击后任务进入列表并轮询。
- 不涉及数据库表结构变更，无需 alembic / SQL 脚本。

## 范围与非目标

- **不做**：不在页面上提供修改 `DATA_LOCAL_PATH` 的能力（改配置仍走 `.env` 文件 + 重启）。
- **不做**：不构建统一的「系统配置查询」接口。当前只有一个配置项需要展示，单独一个 GET 端点足矣；将来配置项变多再合并（YAGNI）。
- **不做**：不改动启动时的导入逻辑、不改动 service 层签名、不改动任务轮询机制。
