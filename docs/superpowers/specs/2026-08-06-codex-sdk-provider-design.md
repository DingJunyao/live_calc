# Codex SDK Provider 接入 · 设计稿

> 日期：2026-08-06
> 状态：设计已对齐，待转实现计划
> 关联：[FEATURE_Agent维护任务台.md](../../../cc/FEATURE_Agent维护任务台.md)、[FEATURE_USDA营养素匹配.md](../../../cc/FEATURE_USDA营养素匹配.md)

## 1. 背景与目标

仓库已实现两处 Claude Code CLI 接入：

- Agent 任务台通过 [claude_code_runner.py](../../../backend/app/services/agent/claude_code_runner.py) 驱动本机 `claude`，完成只读 MCP 查询、SQL 文本输出、多轮续跑和取消。
- USDA 翻译通过 [claude_code.py](../../../backend/app/services/translate/claude_code.py) 调用本机 `claude`，完成食材名和营养素名翻译。
- 原料黑名单分组的 AI 匹配同样硬编码使用 Claude Code runner。

**目标**：新增 `codex` provider，与 Claude Code 平级接入以上三个入口。Codex 配置与 Claude Code 一致，只保留启用开关；模型、Base URL、API Key 由服务器 `~/.codex/config.toml` 和 cc-switch 管理。

**采用路线**：使用 `openai-codex` Python SDK，而不是直接调用 `codex exec`，也不是手写 app-server JSON-RPC 客户端。

## 2. 非目标（YAGNI）

- 不在应用配置里新增 Codex 的 `base_url`、`model`、`api_key` 字段。
- 不替换 Claude Code 路径；`ClaudeCodeRunner` 和 `ClaudeCodeTranslator` 保留。
- 不重写 `run_agent_loop`、SQL 提取、审批、SSE 等 provider 无关逻辑。
- 不把 Codex 的 token usage 强行换算成 USD 成本；`cost_usd` 对 Codex 会话保持空值。
- 不为 Codex 单独实现常驻共享 app-server；沿用当前“每个 runner 独立生命周期”的简单模型。

## 3. 已对齐的关键决策

1. **范围**：同时覆盖 Agent 任务台、USDA 翻译、黑名单分组 AI 匹配。
2. **实现形态**：使用 `openai-codex` Python SDK 的固定 runtime。
3. **配置形态**：Codex 只保留 `enabled` 开关，模型/provider 配置由服务器 Codex 配置负责。
4. **下拉规则**：执行/翻译下拉只展示已启用 provider；翻译下拉包含 AI provider 和机器翻译 provider。
5. **顺序**：所有相关下拉统一为 `Claude Code`、`Codex`、`OpenAI 兼容`、`Anthropic 兼容`，机器翻译按配置顺序追加。
6. **会话锚点**：数据库和 API 用 `external_session_id` 彻底替换 `claude_session_id`，不做兼容字段。
7. **黑名单入口**：新增 provider 下拉，默认 Claude Code，可切换其他已启用 AI provider。

## 4. 整体架构

新增 `CodexRunner`，与 `ClaudeCodeRunner` 平级实现 [AgentRunner 协议](../../../backend/app/services/agent/runner.py)。`run_agent_loop` 只依赖该协议，因此现有多轮 SQL 提取、审批、SSE、插话逻辑不变。

```
任务台 / 黑名单 / USDA 维护入口
        │
        ▼
runner_factory.build_runner(provider=...)
  ├ claude_code → ClaudeCodeRunner（保留）
  ├ codex       → CodexRunner ◀ 新增
  ├ openai/anthropic → LangChainRunner（保留）
        │
        ▼
run_agent_loop（provider 无关，不动）
        │
        ▼
CodexRunner.run()
  ├ CodexClient（openai-codex SDK，app-server stdio）
  ├ thread_start / thread_resume
  ├ turn_handle.stream() 事件适配
  └ external_session_id = thread.id
```

USDA 翻译走独立 `CodexTranslator`，与 Claude Code 翻译后端平级注册到翻译 registry。

## 5. CodexRunner

### 5.1 依赖

后端新增：

```text
openai-codex==0.144.4
```

该包会自动引入固定的 `openai-codex-cli-bin==0.144.4` runtime 和 `pydantic>=2.12`。实现时同步更新 `backend/pyproject.toml`、`backend/requirements.txt` 和 `backend/uv.lock`。

### 5.2 生命周期

`CodexRunner.run()` 为同步生成器，每次运行独立创建并关闭一个 `CodexClient`：

1. 新建会话：`thread_start(...)`。
2. 续跑：`thread_resume(thread_id, ...)`。
3. 启动一轮：`turn_start(thread_id, prompt, ...)`。
4. 消费 `turn_handle.stream()` 事件。
5. 结束后关闭 app-server 进程。

`last_session_id` 返回 Codex `thread.id`，`uses_db_pk_resume = False`，与 Claude Code 的 resume 语义对齐。

### 5.3 受控只读 MCP

`CodexConfig` 通过 `config_overrides` 注入临时 MCP 配置，不修改用户全局 `~/.codex/config.toml`：

```text
mcp_servers.controlled_db.enabled=true
mcp_servers.controlled_db.required=true
mcp_servers.controlled_db.command=<python>
mcp_servers.controlled_db.args=["-m", "app.services.agent.controlled_db_mcp"]
mcp_servers.controlled_db.cwd=<backend>
mcp_servers.controlled_db.env={"LIVECALC_DB_URL"="<db_url>"}
mcp_servers.controlled_db.enabled_tools=["db_read", "describe", "list_tables"]
```

`db_url` 继续复用 [runner_factory.py](../../../backend/app/services/agent/runner_factory.py) 的 `resolve_db_url`，确保 SQLite 相对路径在子进程 cwd 下仍正确。

### 5.4 事件适配

`CodexRunner` 把 SDK 通知映射为 `AgentEvent`：

| SDK 通知 | AgentEvent |
|---|---|
| `item/agentMessage/delta` | `text_delta` |
| `item/started` 中 `mcpToolCall` | `tool_use`，名称 `mcp__<server>__<tool>` |
| `item/completed` 中 `mcpToolCall` | `tool_result` |
| `turn/completed` 且成功 | `done` |
| `turn/completed` 且失败 | `error` / `done.is_error` |
| 其他进度通知 | 忽略 |

`tool_use_id` 使用 SDK item id，`tool_input` 使用 `arguments`，`tool_result` 规整为文本，和现有前端展示兼容。

### 5.5 超时与取消

SDK 的 turn stream 是阻塞队列，因此 runner 内部加一层带超时的通知泵：

- `idle_timeout`：超过该时间没有事件，调用 `turn_handle.interrupt()` 并产出 `error`。
- `total_timeout`：整个 turn 超过上限，同样中断并产出 `error`。
- `cancel()`：保存当前 thread/turn，调用 `turn_handle.interrupt()`，再关闭 app-server。

SDK 进程自身异常转 `AgentEvent(kind="error", crash=True)`，让现有崩溃重试逻辑继续生效。

## 6. CodexTranslator

新增 [codex.py](../../../backend/app/services/translate/codex.py)，实现现有 `Translator` 接口：

- `name = "codex"`。
- `translate_batch(texts, system_prompt)` 按批次调用 Codex。
- 使用 `AsyncCodex` 和 `asyncio.wait_for` 保留现有 timeout 语义。
- 使用 `ephemeral=True` 线程，不污染 Codex 会话历史。
- 使用 `Sandbox.read_only` 和 `ApprovalMode.deny_all`。
- `health_check()` 用 `["Water"]` 做一次最小翻译验证。

翻译 registry 增加 `codex` 分支，`list_provider_names()` 顺序为：

```text
claude_code, codex, openai, anthropic, baidu, aliyun, deepl
```

## 7. 配置与下拉

### 7.1 后端默认配置

`DEFAULT_TRANSLATION_CONFIG` 的 `ai.providers` 顺序改为：

```text
claude_code, codex, openai, anthropic
```

`codex` 配置结构：

```json
{ "enabled": false }
```

配置读取时需要用默认配置补齐缺失的 provider 条目，避免旧数据库配置里没有 `codex` 时，前端配置页或下拉读取到 `undefined`。补齐只补缺失 key，不覆盖已有字段。

### 7.2 前端配置页

`AiConfigView` 的 AI provider 卡片顺序为 `Claude Code`、`Codex`、`OpenAI 兼容`、`Anthropic 兼容`。配置页仍显示所有卡片，便于启用/禁用；只有执行/翻译下拉做“只显示已启用”过滤。

### 7.3 共享下拉定义

新增 `frontend/src/utils/agentProviders.ts`，统一维护：

- provider key 到显示名的映射。
- AI provider 顺序。
- 机器翻译 provider 顺序。
- 从 translation config 过滤已启用 provider。

`AgentTaskConsole`、`BlacklistGroupsView`、`DataMaintenanceView`、`RecipeImportView` 全部改用该共享定义。

### 7.4 下拉过滤规则

- AI 类下拉：只读 `ai.providers` 中 `enabled === true` 的项。
- 翻译类下拉：读取 `ai.providers` 和 `machine.providers` 中已启用项，AI 在前、机器翻译在后。
- 本地模式：隐藏 Claude Code 和 Codex；机器翻译沿用现有“本地模式不支持”的限制。
- 默认值：`claude_code` 已启用时仍优先选它；否则取第一个已启用 AI provider。

## 8. 黑名单 AI 匹配

后端 [blacklist_groups.py](../../../backend/app/api/blacklist_groups.py) 的 `ai-match` 接口新增请求体：

```python
class AiMatchRequest(BaseModel):
    provider: str = "claude_code"
```

[blacklist_group_task.py](../../../backend/app/services/agent/blacklist_group_task.py) 的 `trigger_blacklist_group_match` 增加 `provider` 参数：

- 写入 `AgentSession.runner_type`。
- 传给 `runner_factory.build_runner(..., provider=provider)`。
- 默认仍为 `claude_code`。

前端黑名单分组页新增 provider 下拉，默认 Claude Code，可选其他已启用 AI provider。

## 9. 数据库与 API 迁移

### 9.1 Alembic

新增迁移，操作 `agent_sessions`：

1. 增加 `external_session_id String(128)`。
2. 将 `claude_session_id` 数据复制到 `external_session_id`。
3. 删除 `claude_session_id`。

迁移需兼容 SQLite 和 PostgreSQL；实现时按现有 Alembic 模式处理 SQLite 列删除。

### 9.2 后端

以下位置全部从 `claude_session_id` 改为 `external_session_id`：

- [agent_session.py](../../../backend/app/models/agent_session.py)
- [agent.py](../../../backend/app/schemas/agent.py)
- [agent_api.py](../../../backend/app/api/agent_api.py)
- [session_runner.py](../../../backend/app/services/agent/session_runner.py)

API 不再返回 `claude_session_id`；插话校验改为“缺少外部会话 ID”。

### 9.3 前端类型

[agent.ts](../../../frontend/src/types/agent.ts) 的 `AgentSession` 字段改为 `external_session_id`。

## 10. 任务模板

[task_templates.py](../../../backend/app/services/agent/task_templates.py) 中“Claude Code 环境下使用 MCP”的表述改为“Claude Code / Codex 环境下使用 MCP 只读工具”。SQL 输出、只读工具、审批流程不变。

## 11. 测试策略

- `CodexRunner`：协议满足、事件映射、resume、取消、idle/total timeout、SDK 启动失败。
- `runner_factory`：`provider="codex"` 返回 `CodexRunner`，MCP overrides 注入正确。
- 翻译 registry：`codex` 在 Claude Code 之后，`get_translator` 返回 `CodexTranslator`。
- `CodexTranslator`：mock SDK 调用，验证批处理与 timeout。
- 黑名单：`ai-match` 接收 provider，创建会话和 runner 使用该 provider。
- API：`external_session_id` 替换后列表、详情、插话、取消仍正确。
- Alembic：旧 `claude_session_id` 数据迁移到 `external_session_id`。
- 前端：`npm run build` 通过，下拉只显示已启用 provider，顺序正确。
- 手工冒烟：服务器配好 cc-switch/Codex 后，跑一次 Agent 任务和一次 USDA 翻译。

## 12. 文件清单

**新增**

- `backend/app/services/agent/codex_runner.py`
- `backend/app/services/translate/codex.py`
- `backend/alembic/versions/20260806_0001_add_external_session_id.py`
- `frontend/src/utils/agentProviders.ts`
- `backend/tests/agent/test_codex_runner.py`
- `backend/tests/services/test_translate_codex.py`

**修改**

- `backend/pyproject.toml`、`backend/requirements.txt`、`backend/uv.lock`
- `backend/app/services/agent/runner_factory.py`
- `backend/app/services/agent/task_templates.py`
- `backend/app/services/agent/session_runner.py`
- `backend/app/models/agent_session.py`
- `backend/app/schemas/agent.py`
- `backend/app/api/agent_api.py`
- `backend/app/api/usda_admin.py`
- `backend/app/api/blacklist_groups.py`
- `backend/app/services/agent/blacklist_group_task.py`
- `backend/app/services/translate/registry.py`
- `backend/tests/agent/test_runner_factory.py`
- `backend/tests/agent/test_agent_api.py`
- `backend/tests/services/test_translate_claude.py`（如需要同步 registry 断言）
- `frontend/src/api/agent.ts`
- `frontend/src/types/agent.ts`
- `frontend/src/views/admin/AiConfigView.vue`
- `frontend/src/views/admin/AgentTaskConsole.vue`
- `frontend/src/views/admin/BlacklistGroupsView.vue`
- `frontend/src/views/admin/DataMaintenanceView.vue`
- `frontend/src/views/admin/RecipeImportView.vue`
- `frontend/src/api/local/agent/sessionRunner.ts`
- `frontend/src/api/local/handlers/agents.ts`
- `frontend/src/composables/useAgentSession.ts`

## 13. 风险与后续注意

- Codex 自定义 provider 必须兼容 OpenAI Responses API；仅兼容 Chat Completions 的代理不可用。
- SDK 固定 runtime 与系统已有 `codex` CLI 可能版本不同；按 SDK 包自己的 runtime 运行，避免版本漂移。
- Codex 会话 thread 会持久化在 `~/.codex`，后续若担心堆积，可增加归档策略，但不在本次范围内。
