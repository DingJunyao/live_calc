# Agent 维护任务台 · 设计稿（待实现）

> 状态：**阶段 1（补单位质量）已实现并通过端到端验收（2026-06-19）**。实测 252 条脏数据（全 100 占位）修正 247 条（98%），剩 5 条（方便面/泡面/手抓饼/手指饼干 1 包份，~100g 合理）Agent 判断保留。阶段 2（补密度/USDA 食材翻译/未映射营养素翻译）计划中，见[阶段 2 实施计划](./PLAN_Agent维护任务台_阶段2.md)。
> 日期：2026-06-19

## 1. 背景与目标

**现状痛点**：菜谱导入的 AI 推测（模糊量 `infer_fuzzy_quantities`、密度 `infer_densities`）在 [inferrer.py](../backend/app/services/importer/ai_inference/inferrer.py) 里**逐条/逐组串行**调 AI；AI 客户端 [claude_code.py](../backend/app/services/translate/claude_code.py) 是 `subprocess.run([cli, "-p", "--allowedTools", "Read,Write"])` 的**一次性无状态**调用，**没有数据库访问权限、不并发**，故极慢。

**历史验证过的更优模式**（来自 Claude Code 会话转录）：用户曾下指令「先看看有多少，再维护」，Claude 自主走「`COUNT`/`GROUP BY` 摸底 → 诊断异常值 → 提方案 → 带守卫批量 `UPDATE`」——从不逐条改，一次看全局、批量执行。

**目标**：把这套「下指令 → Agent 自主统计/诊断/批量改」搬进系统，做成**前端任务台**：按按钮触发预设维护任务，Agent 跑起来后流式展示对话，必要时可插话，会话持久化、刷新可回看。

**非目标（YAGNI）**：不做自由输入对话框；不替代导入主流程的数据导入段（只替换 AI 推测段）；任务台仅管理员可用；第一版不支持中途打断正在跑的 Agent。

## 2. 设计决策（已对齐）

| 维度 | 决策 |
|---|---|
| 形态 | 任务台 = 预设任务按钮 + 对话流展示（流式）+ 轮次间插话 + 会话持久化 |
| Agent 大脑 | **claude code CLI**（subprocess，`-p` + `--output-format stream-json` + `--resume` + 第三方代理 env）为主；`NativeLoopRunner`（tool-use 自实现循环）为备用。**必须 CLI**：用户走第三方 Coding Plan，靠「claude code 调用者身份」放行，SDK 直连官方 API 不通。 |
| 数据库访问 | 后端实现的「**受控 DB MCP**」（`db_read`/`db_write`/`describe`），通过 `--mcp-config` 挂给 CLI |
| 守卫 | `db_write` 危险判定：DELETE/TRUNCATE/DROP/无 WHERE/预估影响行数超阈值 → 挂起审批；所有改动标 `source=agent` |
| 安全策略 | 默认自动，仅危险操作挂起等管理员确认 |
| 插话 | `--resume <session-id>` 起新进程带新消息（轮次之间），不打断当前轮 |
| MVP 起点 | 维护类，阶段 1 先做「补单位质量」跑通全链路 |
| 部署平台 | **兼容 Windows 与 Linux**；子进程驱动统一用「线程 `Popen` 逐行读 + `asyncio.Queue` 桥接」，规避 Windows `SelectorEventLoop` 不支持子进程传输的限制，两平台行为一致 |

## 3. 架构总览

```
前端 AgentTaskConsole.vue                后端 FastAPI
┌──────────────────────┐   SSE 流式        ┌──────────────────────────────┐
│ 左:任务按钮列表       │ ◄──────────────── │ /agent/sessions/{id}/stream  │
│   (补质量/补密度/    │                    │ AgentSession / AgentMessage  │
│    USDA 翻译/…)      │  POST 启动/插话    │ AgentApproval (待确认写)     │
│ 右:对话流(流式渲染)  │ ─────────────────► │          ▲                   │
│   +危险确认弹窗       │  POST 审批         │   AgentRunner (接口)         │
│ 底:插话输入框         │ ─────────────────► │   ├ ClaudeCodeRunner (主,CLI)│
└──────────────────────┘                    │   └ NativeLoopRunner  (备)   │
   ▲ 刷新=按 session 重放                   │          ▲ 后台线程 + 独立Session│
   └ 持久化在 AgentMessage                  │          │ subprocess -p      │
                                            │          │ --resume <sid>     │
                                            │     ┌────┴───────────┐ (第三方代理env)│
                                            │     │ claude code CLI │              │
                                            │     └────┬───────────┘              │
                                            │       MCP │ 工具调用                 │
                                            │          ▼                          │
                                            │ 后端「受控 DB MCP」                │
                                            │  db_read / db_write / describe     │
                                            │  ├ 安全 → 执行 + source=agent       │
                                            │  └ 危险 → 挂起 → SSE 确认 → 放行    │
                                            │          ▼ live_calc SQLite         │
                                            └──────────────────────────────────────┘
```

## 4. 数据模型（新增 3 表，复用 `ImportTask` 模式）

**`agent_sessions`**
- `id`, `task_type`（如 `fill_piece_weight`/`fill_density`/`usda_translate`/`infer_quantities`/`infer_densities`）
- `title`, `status`（`pending`/`running`/`awaiting_approval`/`success`/`failed`/`cancelled`）
- `runner_type`（`claude_code`/`native_loop`）
- `claude_session_id`（CLI `--resume` 用的会话 ID）
- `initial_prompt`（预设任务模板渲染后的首条指令）
- `user_id`, `created_at`, `updated_at`, `error`

**`agent_messages`**（对话流水，持久化以便刷新重放）
- `id`, `session_id`, `seq`（顺序号）
- `role`（`user`/`assistant`/`tool`）
- `content`（文本，token 增量聚合成完整段）
- `tool_name`, `tool_input`（JSON）, `tool_result`（JSON）
- `created_at`

**`agent_approvals`**（危险写审批）
- `id`, `session_id`, `message_id`（关联触发它的 tool_use 消息）
- `sql`, `danger_reason`, `affected_estimate`
- `status`（`pending`/`approved`/`rejected`/`auto_executed`）
- `decided_by`, `decided_at`, `created_at`

**现有表 source 扩展**：
- `entity_unit_overrides.source`：新增 `'agent'`（现仅 `import`/`manual`）
- `entity_densities.source`（`String(200)` 自由文本）：Agent 写入时标 `agent: <依据>`

## 5. 执行流

1. 管理员点任务按钮 → `POST /agent/sessions`（带 `task_type`）→ 建 `AgentSession(status=pending)`，渲染预设 prompt 为 `initial_prompt`
2. 后台线程（daemon + 独立 Session，参考 [api_service.py](../backend/app/services/importer/api_service.py) 的 `start_background_import`/`_run_import_task`）起 `AgentRunner`
3. `ClaudeCodeRunner`：`subprocess.Popen` 起 `claude -p <initial_prompt> --output-format stream-json --include-partial-messages --mcp-config <受控MCP> [--resume <sid>]`，env 注入第三方代理（`ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`）
4. 线程逐行读 stdout 的 stream-json 事件 → 解析 → 写 `AgentMessage` + 推 `asyncio.Queue`
5. SSE 协程 `GET /agent/sessions/{id}/stream` 从 queue 读 → 推给前端（token 增量 / tool_use / tool_result / approval_request）
6. Agent 调 `db_write` → 受控 MCP 判定 → 安全直接执行（`source=agent` + 回传影响行数）；危险 → 写 `AgentApproval(status=pending)` + 返回「等待确认」阻塞 → 前端弹确认 → `POST /agent/approvals/{id}` → 执行或拒绝 → 结果回 CLI
7. Agent 一轮结束 → `status=success`；用户插话 → `POST /agent/sessions/{id}/messages` → 用 `--resume <claude_session_id>` 起新进程带新消息（回到步骤 3）

## 6. 受控 DB MCP（只读）+ 写操作文本解析（spike 验证后的方案 B）

**spike 结论（Task 0）**：CLI 的 `--mcp-config` 默认**合并**用户全局 MCP（实测加载了开发者私人的 `live_calc_sqlite_mcp`），有越权风险；让 stdio MCP 子进程经 HTTP 回调主后端审批（方案 A）复杂且未验证。故采用**方案 B**：

- **受控 MCP 只暴露只读工具**：`db_read(sql)`（SELECT 限行）、`describe(table)`、`list_tables()`。CLI 用 `--strict-mcp-config`（隔离到只此 server、不合并全局）+ `--allowedTools` 白名单锁死。**Agent 没有任何 write 工具**，写库无越权路径。
- **写操作走文本**：Agent 改库时，按 prompt 约定在 assistant 文本里输出 SQL（` ```sql ... ``` ` 块 + 动作意图）。主后端从 assistant 文本/`result` 解析出 SQL → 过 `sql_guard` 危险判定 → 安全则执行（打 `source=agent`）、危险则写 `AgentApproval` + SSE 弹确认 → 执行结果作为下一轮 user 消息经 `--resume` 喂回 Agent。
- `permission_denials`（CLI `result` 字段）监控 Agent 试图越权的尝试，前端可告警。

预设 prompt 约束 Agent「写操作必须带 WHERE 守卫、SQL 用代码块输出」，与历史 `AND weight_per_unit=<原值>` 一致。

## 7. 流式与持久化（含 Windows 约束）

- **传输**：SSE（单向推送够用，非 WebSocket）。新增 `GET /agent/sessions/{id}/stream`。
- **跨平台事件循环约束（Windows / Linux，关键）**：Linux 默认 `SelectorEventLoop` 支持子进程传输，`asyncio.create_subprocess_exec` 可用；而在 Windows 的 `SelectorEventLoop` 下会抛 `NotImplementedError`（[claude_code.py:20-23](../backend/app/services/translate/claude_code.py#L20-L23) 已踩坑）。**统一方案（两平台同一套代码）**：后台线程用 `subprocess.Popen` 逐行读 stdout → 行经 `loop.call_soon_threadsafe` 入 `asyncio.Queue` → SSE 协程从 queue 读，不按平台分支。刷新重连 = 先回放 `AgentMessage` 历史，若会话仍在跑则续接 queue。
- **跨平台其他注意**：路径用 `pathlib`（不拼分隔符）；CLI 与 `--mcp-config` 路径跨平台解析；stdin/stdout 强制 `encoding="utf-8"`；换行统一 `\n`；`shutil.which("claude")` 定位 CLI（找不到则友好报错）。
- **CLI 嵌套启动陷阱**（spike 发现）：后端若跑在 Claude Code 会话内（开发期），subprocess 起 claude 前必须 `env.pop("CLAUDECODE", None)`，否则 CLI 报「cannot be launched inside another Claude Code session」。Runner 固化此处理。
- `--strict-mcp-config` 必须开启（spike 发现）：否则 `--mcp-config` 会合并用户全局 MCP 配置，存在越权调用开发者私人 MCP 的风险。
- **流式事件落 utf-8 jsonl**（spike 发现）：Windows 控制台 GBK 乱码，事件持久化与传输用 utf-8。
- **成本兜底**：每次 CLI 调用 $0.04–0.13（智谱 GLM Coding Plan / `glm-5`），Runner 加 `--max-budget-usd` 封顶。
- `mcp` 依赖：spike 用 `uv pip install mcp` 装入 `.venv`（项目 pyproject 为 poetry 结构，`uv add` 失败），后续须手动把 `mcp` 正式纳入依赖清单。
- **持久化**：每条 stream-json 事件聚合成 `AgentMessage`（assistant 文本增量合并、tool_use/tool_result 各成行），刷新即完整重放。

## 8. 预设任务定义（按钮 → prompt + 工具 + 落点）

| 任务 | 落点表/字段 | prompt 要点 | 守卫 |
|---|---|---|---|
| 补单位质量 | `entity_unit_overrides.weight_per_unit`（注意 `ingredient.piece_weight` 历史上无数据） | 统计缺值/占位（如一堆 `100`）→ 按食材常识估算（花椒1颗、干辣椒1个、蒜1头…）→ 分类批量改 | `UPDATE ... WHERE id IN(...) AND weight_per_unit=<原占位值>` |
| 补密度 | `entity_densities.density`（**kg/m³**） | 找缺密度的液体/粉状原料 → 按常识补（水1000、油920、面粉550…） | 只 INSERT 缺失，不覆盖已有 |
| USDA 翻译 | `ingredients` 的 `usda_id`/翻译名 | 复用现有 6 翻译后端 + 172 预设映射；Agent 协调批量 + 不确定项确认 | 匹配结果可复核 |

**⚠️ 密度单位坑**：[inferrer.py](../backend/app/services/importer/ai_inference/inferrer.py) 的密度 prompt 用 `g/cm³`（水=1.0），而 `entity_densities.density` 字段是 `kg/m³`（水=1000）。现有推测可能存在 1000 倍换算隐患，plan 阶段必须先核对并统一。

## 9. MVP 分阶段

- **阶段 1（核心链路）**：3 张表 + 受控 DB MCP + `ClaudeCodeRunner`（CLI stream-json + 线程桥接 + SSE）+ 前端任务台（按钮 / 对话流 / 插话 / 确认弹窗 / 刷新重放）+ 先跑通「补单位质量」一个任务
- **阶段 2**：补密度（含单位对齐）+ USDA 翻译任务；导入推测端点 [import_api.py](../backend/app/api/import_api.py) 的 `/ai-infer/quantities`、`/ai-infer/densities` 改为调 `AgentRunner`（复用 `task_type` 与 `ImportTask` 思路或迁至 `AgentSession`）
- **阶段 3（可选）**：`NativeLoopRunner` 备用实现；并发队列；审计日志

## 10. 文件清单

**新增（后端）**
- `backend/app/models/agent_session.py` / `agent_message.py` / `agent_approval.py`
- `backend/app/services/agent/runner.py`（`AgentRunner` 接口）
- `backend/app/services/agent/claude_code_runner.py`（CLI stream-json + 线程桥接）
- `backend/app/services/agent/native_loop_runner.py`（备用，阶段 3）
- `backend/app/services/agent/controlled_db_mcp.py`（受控 DB MCP server）
- `backend/app/services/agent/task_templates.py`（预设任务 prompt 模板）
- `backend/app/services/agent/stream_bridge.py`（stdout → queue → SSE）
- `backend/app/api/agent_api.py`（`/agent/sessions`、`/stream`、`/messages`、`/approvals`）
- `backend/app/schemas/agent.py`
- alembic 迁移 + SQL（SQLite / MySQL / PostgreSQL / PostgreSQL-PostGIS）

**新增（前端）**
- `frontend/src/views/admin/AgentTaskConsole.vue`
- `frontend/src/composables/useAgentSession.ts`（SSE 订阅 + 重放）
- `frontend/src/api/agent.ts`
- 管理页入口 + 路由

**修改**
- `backend/app/services/translate/claude_code.py`（流式能力抽到 Runner，或 Runner 内独立实现）
- `backend/app/api/import_api.py`（阶段 2：`/ai-infer/*` 改调 Runner）
- `backend/app/services/importer/ai_inference/inferrer.py`（阶段 2：逐步替换逐条逻辑）

## 11. 风险与待验证（plan 阶段实测）

1. **跨平台子进程**：Windows/Linux 统一线程桥接规避事件循环差异（已有先例）；需验证 `--include-partial-messages` 在第三方代理下事件完整性、Linux 上 `Popen` 逐行读的缓冲行为
2. **`--resume` 跨进程上下文连续性**：实测多轮插话是否丢失上下文
3. **受控 MCP 进程模型**：后端进程内 vs 独立 stdio 子进程，能否访问会话审批状态/SSE 通道
4. **第三方代理下 MCP Tool Search 默认禁用**：需 `ENABLE_TOOL_SEARCH=true` 或显式 `--allowedTools mcp__*`
5. **API 超时 / 长任务**：调大 `API_TIMEOUT_MS`，单会话单 subprocess，并发靠多进程
6. **密度单位不一致**：见 §8，plan 先对齐
7. **成本**：走第三方 Coding Plan 计费（非官方 API），按代理规则，单任务可设预算上限

## 12. 与现有 AI 后端的关系

现有 [translate/](../backend/app/services/translate/) 的 6 种翻译后端（claude_code / openai / anthropic / 百度 / 阿里云 / DeepL）与 [TranslationConfig](../backend/app/models/usda.py) 配置保留。任务台的 `NativeLoopRunner`（阶段 3）可复用这些后端做 tool-use 循环；`ClaudeCodeRunner` 主路径走 claude code CLI（与现有 `ClaudeCodeTranslator` 同源，升级为流式）。USDA 翻译任务复用现有翻译 service。
