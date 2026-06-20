# 给 OpenAI / Anthropic 集成 langchain Agent · 设计稿

> 日期：2026-06-20
> 状态：设计已对齐（brainstorm 四问四答），待转实现计划
> 关联：[FEATURE_Agent维护任务台.md](../../../cc/FEATURE_Agent维护任务台.md)、[FEATURE_USDA营养素匹配.md](../../../cc/FEATURE_USDA营养素匹配.md)

## 1. 背景与目标

**现状**：菜谱导入与 USDA 维护链路里有四项 AI 后处理任务——

| 任务 | 现有执行路径 | 浪费点 |
|---|---|---|
| ① USDA 食材翻译 | [TranslateTask](../../../backend/app/services/translate/task.py)：50 条/批，逐批串行 `await` | 串行死等，无并发 |
| ② 未映射营养素翻译 | [TranslateNutrientsTask](../../../backend/app/services/translate/nutrient_task.py)：同上 | 同上 |
| ③ 模糊量推测 | [AIInferrer.infer_fuzzy_quantities](../../../backend/app/services/importer/ai_inference/inferrer.py)：按 `(ingredient_id, unit_id)` **逐组**调一次 | 每组带完整 prompt 往返 |
| ④ 密度推测 | [AIInferrer.infer_densities](../../../backend/app/services/importer/ai_inference/inferrer.py)：**逐个原料**调一次 | 最浪费，逐条往返 |

其中 ③④ 经 [import_api.py:197-199](../../../backend/app/api/import_api.py#L197-L199) 把 `translate_batch([单条 prompt])` 当 `ai_caller` 注入——本质是逐条 HTTP，token 全烧在重复的 system prompt 封装开销上。

而 Claude Code 那边早已是完整 Agent：[claude_code_runner.py](../../../backend/app/services/agent/claude_code_runner.py) 走 CLI + 受控 DB MCP + 工具调用循环，模型能「查一批 → 处理 → 写回 → 再查」，一次看全局。

**目标**：让 OpenAI 兼容 / Anthropic 兼容这两个 provider 也以「自主 Agent 循环」方式跑这四项任务，用 **langchain** 抹平两 provider 的 tool-use 差异，节约时间与 token。

## 2. 非目标（YAGNI）

- 不为这四项任务引入结构化写工具（`@tool` 写库）。写库仍走 SQL 文本 + `sql_guard`，与 Claude Code 对齐。
- 不替换 Claude Code 路径——`ClaudeCodeRunner` 保留，`LangChainRunner` 与之平级共存。
- 第一版不做多会话并发队列（单会话单 runner，沿用现有模型）。
- 不引入 langgraph（用经典 `create_tool_calling_agent` + `AgentExecutor` 即可）。

## 3. 已对齐的关键决策（brainstorm 四问）

1. **形态**：自主 tool-use 循环 + langchain（抹平 OpenAI/Anthropic 差异）。
2. **入口**：两者都接——任务台做成第二个 runner，老路径执行引擎整体换成 `LangChainRunner`。
3. **写库机制**：只读工具 + SQL 文本（复用 `sql_guard` 审批），5 个 `task_template` 全复用。
4. **依赖**：接受引入 langchain 重依赖（`langchain` + `langchain-openai` + `langchain-anthropic`）。

## 4. 整体架构

核心：**新增 `LangChainRunner`（`backend/app/services/agent/langchain_runner.py`），与 `ClaudeCodeRunner` 平级，都实现 `AgentRunner` 协议**。两 runner 行为对称——「只读工具查库 + 文本吐 SQL + sql_guard 审批」，仅大脑不同（CLI subprocess vs langchain 驱动的 OpenAI/Anthropic）。

[run_agent_loop](../../../backend/app/services/agent/session_runner.py) 本就 provider 无关，只认 [AgentRunner 协议](../../../backend/app/services/agent/runner.py)（`run(prompt) → Iterator[AgentEvent]`），故挂上即用。

```
                 ┌─────────────────────────────────────────────┐
   任务台入口 ──▶│  runner_factory.build_runner(provider=...)   │
  (选 provider)  │   ├ claude_code → ClaudeCodeRunner           │
                 │   └ openai/anthropic → LangChainRunner ◀ 新增│
                 └───────────────────┬─────────────────────────┘
                                     ▼
                ┌────────────────────────────────────────────┐
                │  run_agent_loop（provider 无关，不动）       │
                │  事件聚合落 AgentMessage + SSE + 多轮 + 审批 │
                └───────────────────┬────────────────────────┘
                                    ▼
            ┌───────────────────────────────────────────────────┐
            │  AgentRunner.run() → Iterator[AgentEvent]          │
            │  ├ ClaudeCodeRunner: CLI + 受控 MCP 只读工具        │
            │  └ LangChainRunner:  langchain AgentExecutor +     │
            │                       进程内 @tool 只读工具 ◀ 新增  │
            └───────────────────────────────────────────────────┘
                                    ▼
   老路径入口 ──▶ TranslateTask / TranslateNutrientsTask / AIInferrer
  (无人值守)     内部构造 LangChainRunner + 渲染 task_template prompt
                 + run_agent_loop(unattended=True)  ◀ 引擎替换
```

**最大红利**：5 个 `task_template`（[task_templates.py](../../../backend/app/services/agent/task_templates.py)，含这四项 + `fill_piece_weight`）、`run_agent_loop`、SSE、审批、`AgentSession` **全部复用**，不新设计写库机制。langchain 只负责「用 `ChatOpenAI`/`ChatAnthropic` 抹平两 provider、驱动只读 tool-use 循环」一件事。

## 5. LangChainRunner 内部

**大脑**：`create_tool_calling_agent(ChatModel, tools, prompt)` + `AgentExecutor`。OpenAI、Anthropic 均原生支持 tool calling，`ChatOpenAI`/`ChatAnthropic`（`base_url` 指兼容端点）的 `.bind_tools()` 接口统一，一套代码两 provider 通吃。

**只读工具**：3 个 `@tool` 函数——`db_read(sql)` / `describe(table)` / `list_tables()`，在后端进程内直接查库（独立 `SessionLocal`），复用现成 [db_query.py](../../../backend/app/services/agent/db_query.py) 逻辑。比 Claude Code 轻一大截：不起 stdio MCP 子进程、不生成 `mcp_config.json`、不需 `--strict-mcp-config`。工具名与 `task_templates` 里 prompt 提到的只读工具对齐（必要时把 prompt 里 `mcp__controlled_db__db_read` 这类带前缀的表述改为中性 `db_read`，使两 runner 都能喂）。

**事件适配层**：`AgentExecutor.stream()` 产出的 `(action, observation)` → 映射成 `AgentEvent`：

| langchain 产出 | AgentEvent |
|---|---|
| 模型中间/最终文本 | `text_delta`（聚合） |
| `AgentAction`（决定调 tool） | `tool_use` |
| observation（tool 返回） | `tool_result` |
| `AgentFinish` | `done`（带 final 文本） |

最终 assistant 文本照旧含 ```sql``` 块，外层 `run_agent_loop` 的 `extract_sqls` 原样吃。

**两个与 Claude Code 不同的处理**：

- **只读工具进程内查库**（不起 MCP 子进程）——`@tool` 是 Python 函数，天然在后端进程跑，省掉一整套子进程协议。
- **resume（插话）靠 chat_history 回放**——langchain 无原生 session 概念，`resume_session_id` 映射成「从 `AgentMessage` 表加载该 session 历史对话塞进 agent 的 `chat_history`」，等价实现多轮续跑（替代 CLI 的 `--resume`）。

**线程模型**：`LangChainRunner.run()` 为同步生成器（`AgentExecutor.stream()` 同步迭代），跑在现有后台线程模型里，与 `session_runner` 的线程桥接一致。

## 6. 两个入口怎么接

### 6.1 任务台

改动很小：

- [runner_factory](../../../backend/app/services/agent/runner_factory.py) 的 `build_runner` 加 `provider` 分流：`claude_code` → `ClaudeCodeRunner`，`openai`/`anthropic` → `LangChainRunner`（从 `TranslationConfig` 取 base_url/key/model 构造对应 `ChatModel`）。
- 前端任务台（`AgentTaskConsole.vue`）加 provider 选择控件。
- `AgentSession`、`run_agent_loop`、SSE、审批——一行不动，Claude Code 那套体验原样搬到 OpenAI/Anthropic。

### 6.2 老路径（引擎替换，载体不动）

- [TranslateTask](../../../backend/app/services/translate/task.py) / [TranslateNutrientsTask](../../../backend/app/services/translate/nutrient_task.py) 仍用 `UsdaTask` 记进度；[AIInferrer](../../../backend/app/services/importer/ai_inference/inferrer.py) 仍走 `import_api` 端点 + `progress_callback`。
- 内部把「分批调 `translate_batch`」「逐条调 `ai_caller`」整个换成「构造 `LangChainRunner` + 渲染对应 `task_template` prompt + 跑 `run_agent_loop`」。前端 USDA 维护页、导入页 UI 与进度展示基本不动，只是底下从串行/逐条变成 Agent 自主批量。

### 6.3 无人值守审批（关键）

老路径是导入后处理，用户不在线，dangerous SQL 不能挂起等人确认。方案：给 `run_agent_loop` 加 `unattended: bool = False` 参数——

- `unattended=True` 时，dangerous SQL **自动跳过 + 记日志**（宁漏勿错）。这些任务的 SQL 本就是带 WHERE 的批量 UPDATE/INSERT，`sql_guard` 基本判 safe，极少触发 dangerous。
- safe SQL 照常执行。
- 老路径不建 `AgentSession`（不污染任务台列表），关键步骤落 `operation_log` 供排查。

## 7. 配置 / 错误兜底 / 成本超时

**provider 抹平**：从现有 `TranslationConfig` 取 `openai`/`anthropic` 的 `base_url`/`api_key`/`model`，构造 `ChatOpenAI`/`ChatAnthropic`（`base_url` 指兼容端点，`streaming=True`）。timeout 复用 `translate_http_timeout` 思路。配置零新增。

**错误兜底**（尽量复用现有）：

- langchain agent 的 API 错误 / tool 异常 / `max_iterations` 超限 → 适配层转 `AgentEvent(kind="error")`，`run_agent_loop` 已有 failed 收尾。
- SQL 执行失败走 `_handle_safe_sql` 的 err 分支。
- 新增防护：agent 偶尔「没吐 SQL 却自称完成」——靠 `max_turns` 上限 + 「跑前后 pending 条数对比」兜住，没处理完再喂一轮。

**成本/超时**：langchain 无 CLI 的 `--max-budget-usd`，改用 `AgentExecutor(max_iterations=…)` 限轮数 + 单次 LLM 超时 + `run_agent_loop` 的 `max_turns` 三重封顶。token 红利来自「推测逐条 → Agent 批量」「翻译串行分批 → Agent 自主多批」，每轮 system prompt 复用、上下文累积。

## 8. 测试策略

- **LangChainRunner 单测**：用 langchain `FakeListChatModel`（或自定义假模型）mock，验证 `(action, observation) → AgentEvent` 映射正确（`text_delta`/`tool_use`/`tool_result`/`done`）。
- **只读 @tool 单测**：验证查库正确 + `db_read` 拒绝非 SELECT（注入防护）。
- **resume 回放单测**：给定历史 `AgentMessage`，验证 chat_history 正确注入、多轮续跑。
- **`run_agent_loop(unattended=True)` 单测**：dangerous SQL 自动跳过 + 记日志、safe SQL 执行。
- **老路径集成测试**：`TranslateTask` / `TranslateNutrientsTask` / `AIInferrer` 换引擎后，验证翻译/推测产出与原实现等价（写库字段、条数正确）。
- 复用现有 `ClaudeCodeRunner` 的测试模式与 `agent_sessions`/`agent_messages` 断言套路。

## 9. 文件清单

**新增**

- `backend/app/services/agent/langchain_runner.py`——`LangChainRunner`（实现 `AgentRunner` 协议：ChatModel + 只读 @tool + 事件适配）。
- `backend/app/services/agent/langchain_tools.py`——3 个只读 `@tool`（`db_read`/`describe`/`list_tables`），复用 `db_query.py`。
- `backend/app/services/agent/langchain_chat.py`——按 provider + 配置构造 `ChatOpenAI`/`ChatAnthropic`（抹平 base_url/兼容端点）。
- 测试：`backend/tests/.../test_langchain_runner.py`、`test_langchain_tools.py`、`test_run_agent_loop_unattended.py`。

**修改**

- `backend/app/services/agent/runner_factory.py`——`build_runner` 加 `provider` 分流。
- `backend/app/services/agent/session_runner.py`——`run_agent_loop` 加 `unattended` 参数（dangerous 自动跳过）。
- `backend/app/services/agent/task_templates.py`——prompt 里 `mcp__controlled_db__*` 表述中性化（两 runner 通用）。
- `backend/app/services/translate/task.py`、`nutrient_task.py`——引擎替换为 `LangChainRunner`。
- `backend/app/services/importer/ai_inference/inferrer.py`——引擎替换为 `LangChainRunner`。
- `frontend/src/views/admin/AgentTaskConsole.vue` + `frontend/src/api/agent.ts`——任务台加 provider 选择。
- `backend/pyproject.toml`——纳入 `langchain` / `langchain-openai` / `langchain-anthropic` 依赖。

## 10. 风险与待验证（plan 阶段实测）

1. **langchain 依赖纳入**：项目为 poetry 结构，按 `mcp` 先例 `uv add` 可能要手动处理；三个包版本耦合需锁定。
2. **两 provider tool calling 遵循度**：OpenAI/Anthropic 对「文本里输出 ```sql``` 块」的格式遵循度可能不如 Claude Code，需 prompt 约束 + `sql_extractor` 容错 + 实测。
3. **`max_iterations` / `max_turns` 调参**：批量大时 agent 可能多轮，需平衡 token 与完成度。
4. **老路径 unattended 漏改**：dangerous 自动跳过可能漏少量数据，需跑前后条数对比 + 日志可追溯。
5. **resume chat_history 注入**：长会话历史可能撑大上下文，需考虑截断策略。
6. **流式事件完整性**：`AgentExecutor.stream()` 在兼容端点下的事件序列需实测（对齐 `ClaudeCodeRunner` 的 stream-json 处理经验）。

## 11. 与现有系统的关系

- `translate/` 6 后端保留（机翻三后端仍走老 `translate_batch`；AI 三后端中 `claude_code` 走任务台、`openai`/`anthropic` 经本次改造走 `LangChainRunner`）。
- `AgentRunner` 协议、`run_agent_loop`、`AgentSession`/`AgentMessage`/`AgentApproval`、`sql_extractor`/`sql_guard`、SSE、审批——全部复用，不改。
- 本设计即 FEATURE_Agent维护任务台「阶段 3 `NativeLoopRunner`」的 langchain 落地版本，但写库机制对齐 Claude Code（SQL 文本 + 守卫）而非独立工具循环。
