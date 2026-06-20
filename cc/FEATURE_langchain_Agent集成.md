# langchain Agent 集成（OpenAI / Anthropic）

## 功能

给 OpenAI 兼容 / Anthropic 兼容两个 AI provider 集成 langchain Agent，让四项 AI 后处理任务（USDA 食材翻译 / 未映射营养素翻译 / 模糊量推测 / 密度推测）从「分批串行 / 逐条调用」改为「Agent 自主批量循环」，节约时间与 token。与现有 Claude Code Agent（[FEATURE_Agent维护任务台.md](./FEATURE_Agent维护任务台.md)）对齐体验。

## 架构

核心：新增 `LangChainRunner`（实现 `AgentRunner` 协议），与 `ClaudeCodeRunner` 平级——「只读工具查库 + 文本吐 ```sql``` + sql_guard 审批」行为对称，仅大脑不同（langchain `create_agent` 驱动的 OpenAI/Anthropic vs CLI subprocess）。

```
任务台（选 provider）─▶ runner_factory.build_runner(provider=...)
                         ├ claude_code → ClaudeCodeRunner（原有，不动）
                         └ openai/anthropic → LangChainRunner（新增）
                                    ▼
              run_agent_loop（provider 无关，复用：事件聚合 + SQL 提取/执行 + SSE + 审批）
                                    ▼
老路径（无人值守）─▶ TranslateTask / TranslateNutrientsTask / AIInferrer
                    引擎替换为 LangChainRunner + run_agent_loop(unattended=True)
```

**最大红利**：5 个 `task_template`（含四项 + fill_piece_weight）、`run_agent_loop`、SSE、审批、`AgentSession` 全部复用，不新设计写库机制。

## 关键决策

| 维度 | 决策 |
|---|---|
| langchain 版本 | **1.x**（实测 1.3.10）。`create_tool_calling_agent` + `AgentExecutor` 在 1.x 已移除，改用 `create_agent(model, tools, system_prompt=..., middleware=...)`（基于 langgraph，agent 本身即执行器，支持 `.stream()`） |
| 只读工具 | 3 个 `@tool`（`db_read`/`describe`/`list_tables`），**进程内独立 Session 查库**（SQLAlchemy `inspect`，跨库 SQLite/MySQL/PostgreSQL），不起 MCP 子进程（比 Claude Code 轻）。复用 `db_query.check_read_only` 共享纯函数（拒非 SELECT） |
| 写库机制 | SQL 文本 + `sql_guard`（与 Claude Code 对齐，复用 5 个 prompt 模板 + 审批）。不引入结构化写 `@tool`（YAGNI，避免两套写库路径） |
| 事件映射 | `create_agent.stream(stream_mode=["messages","updates"])` → `AgentEvent`：messages 的 `AIMessageChunk.text` → `text_delta`（**过滤 HumanMessage/ToolMessage，只 AI 消息产 text_delta**）；updates 的 model 节点 `tool_calls` → `tool_use`；tools 节点 `ToolMessage` → `tool_result`；`done`/`error` 兜底 |
| resume（插话） | langchain 无原生 session，靠 `_load_history` 从 `AgentMessage` 表回放 chat_history（dict 形式 `[{"role":"user",...}]`，替代 CLI `--resume`） |
| 封顶 | `max_iterations` → `recursion_limit = max_iterations*2+4`（每轮 model+tools 两步 + 余量） |
| provider 分流 | `runner_factory.build_runner(provider=...)`：openai/anthropic → `_build_langchain_runner`（从 `TranslationConfig` 取配置 + `build_chat_model` + `LangChainRunner(READ_ONLY_TOOLS)`）；claude_code → 原逻辑不变 |
| 老路径无人值守 | `run_agent_loop(unattended=True)`：dangerous SQL 自动跳过（记日志 + `sql_skipped` SSE），不挂审批、不阻塞（宁漏勿错）；safe SQL 照常执行 |
| 老路径载体 | 建 `[后台]` AgentSession（复用 run_agent_loop 全套，对话可在任务台回看）+ 保留 UsdaTask（USDA 维护页进度）/ AIInferrer（import_api 端点）。AIInferrer 保留 `ai_caller` 老路径回退（provider 非 openai/anthropic 走逐条逻辑） |
| async/同步桥接 | TranslateTask/TranslateNutrientsTask 是 async（调用方 await）→ `asyncio.to_thread(run_agent_loop)`；AIInferrer 是同步（调用方已在 daemon 线程）→ 直接调，`main_loop = asyncio.new_event_loop()` 占位（try/finally close，publish_sync 吞 RuntimeError） |

## 文件清单

**新增（后端）**
- `backend/app/services/agent/langchain_runner.py` — LangChainRunner（create_agent + 事件适配 + _load_history）
- `backend/app/services/agent/langchain_tools.py` — 只读 @tool（db_read/describe/list_tables + READ_ONLY_TOOLS）
- `backend/app/services/agent/langchain_chat.py` — provider 抹平（build_chat_model 构造 ChatOpenAI/ChatAnthropic）
- 测试：`tests/agent/test_langchain_runner.py`（14）、`test_langchain_tools.py`（4）、`test_langchain_chat.py`（4）、`test_runner_factory.py`（5）、`tests/translate/test_translate_task_agent.py`、`test_nutrient_task_agent.py`、`tests/importer/test_inferrer_agent.py`（4：fuzzy Agent+回退、densities Agent+回退）

**修改（后端）**
- `backend/app/services/agent/runner_factory.py` — build_runner 加 provider 分流 + _build_langchain_runner
- `backend/app/services/agent/session_runner.py` — run_agent_loop 加 unattended 参数（dangerous/safe-escalate 跳过）
- `backend/app/services/agent/task_templates.py` — 5 个 prompt 只读工具表述中性化（db_read 为主名，保留 Claude Code MCP/bash 说明）
- `backend/app/services/agent/db_query.py` — 抽 `check_read_only` 共享纯函数（CLI 行为不变）
- `backend/app/services/translate/task.py` / `nutrient_task.py` — 引擎替换为 LangChainRunner + run_agent_loop(unattended)
- `backend/app/services/importer/ai_inference/inferrer.py` — infer_fuzzy_quantities/infer_densities 加 provider 分流（Agent 路径 + legacy 回退）
- `backend/app/api/agent_api.py` — create_session/post_message 接 provider
- `backend/app/schemas/agent.py` — CreateSessionIn 加 provider
- `backend/app/api/import_api.py` — AIInferrer(db, provider=provider)
- `backend/pyproject.toml` — langchain/langchain-openai/langchain-anthropic（1.x）

**修改（前端）**
- `frontend/src/views/admin/AgentTaskConsole.vue` — provider 选择 v-select（桌面侧栏 + 移动端抽屉，默认 claude_code）
- `frontend/src/api/agent.ts` — AgentProvider 类型 + createSession 参数
- `frontend/src/composables/useAgentSession.ts` — startTask 透传 provider

## 测试

本功能相关（agent + translate + importer + import_api + usda_admin_api）：**220 passed**。TDD 全程（每 task 先写失败测试 → 实现 → 通过），含 spec review + code quality review 两阶段把关（Task 1/3/7/9 独立 spec reviewer，Task 3 抓到真实 bug：消息类型过滤缺失，已修）。

## 端到端手测（需真实 provider 配置）

1. **任务台**：后台 AI 配置页配好 OpenAI 兼容 / Anthropic 兼容 provider（base_url/api_key/model）。任务台选 provider=openai，点任一任务（如「补密度」），观察对话流（db_read 工具调用、```sql``` 输出、sql_guard 执行）、刷新重放、`entity_densities` 写入。同样测 anthropic。对比 Claude Code 路径行为对称。
2. **老路径**：USDA 维护页点「翻译」（走 TranslateTask → LangChainRunner），观察 UsdaTask 进度、`usda_foods.description_zh` 写入。菜谱导入触发模糊量/密度推测，观察 `entity_densities` / `recipe_ingredients` 写入。
3. **回退**：provider=claude_code（默认）时，老路径走 ai_caller 逐条逻辑（向后兼容）。

## 已知问题 / 待办

1. **flaky 测试** `test_end_to_end_real_loop_with_fake_runner`：SSE + 后台线程 + asyncio + 全局 dict 时序竞态，全套跑间歇失败（单独跑过）。预存，建议治理测试隔离。
2. **进度降级**：老路径 Agent 一次性批量，`UsdaTask.progress` 只结束时写一次（老路径每批更新，USDA 维护页翻译时无实时进度条）。补回方案：轮询线程定期 `SELECT COUNT(*) WHERE done` 更新 progress（最轻）。
3. **progress 字段名不匹配（既有 bug）**：后端写 `{done, total}`，前端 `DataMaintenanceView.vue` 读 `progress.current`——老路径就这样，非本次引入。建议前端兼容 `done` 或后端改 `current`。
4. **`get_event_loop` → `get_running_loop`**：Task 7 的 TranslateTask 用 `asyncio.get_event_loop()`（Py 3.12+ DeprecationWarning），Task 8 已用规范的 `get_running_loop()`。建议 Task 7 统一。
5. **`.flake8` 配置缺失**：项目 Black line=88 与 flake8 默认 79 冲突（无配置文件），导致中文 docstring/comment 行报 E501。建议加 `.flake8`（`max-line-length=88` + `extend-ignore=E203,W503`）根治。
6. **`[后台]` session 前端过滤**：老路径建的 `[后台]` AgentSession 会出现在任务台列表（靠 title 前缀区分）。如需隐藏，前端按 title 前缀或新增字段过滤。
7. **真实 create_agent 循环未端到端测**：单测用 mock chunk（GenericFakeChatModel 不支持 bind_tools）。真实 ChatOpenAI/ChatAnthropic 下的 stream 行为依赖手测（见上）。
8. **Agent 路径取消弱化**：老路径 `cancel_event` 在 Agent 路径下被忽略（Agent 循环内部只查 `AgentSession.status`，不查 `ImportTask` 取消状态），用户点取消 Agent 不会立即停（unattended 后台跑完）。低优，建议文档化或后续支持。
9. **（已修复）C1 多轮上下文丢失 + 插话阻断**：final review 发现 `LangChainRunner.last_session_id` 是 echo 入参，导致 langchain 第 2 轮起 `_load_history` 不调用（上下文丢失）+ `claude_session_id` 永远 NULL → `post_message` 409 拒插话。已修：`AgentRunner` 协议加 `uses_db_pk_resume` 属性（`LangChainRunner=True` 每轮用 `str(session_id)` resume，`ClaudeCodeRunner=False` 用 CLI claude session id）+ `run_agent_loop` 按它分流 + 2 回归测试（`test_session_runner.py::test_c1_*`）。

## 与现有系统的关系

- `ClaudeCodeRunner` 保留不动，`LangChainRunner` 与之平级共存。
- `AgentRunner` 协议、`run_agent_loop`、`AgentSession`/`AgentMessage`/`AgentApproval`、`sql_extractor`/`sql_guard`、SSE、审批——全部复用。
- `translate/` 6 后端：机翻三后端（百度/阿里云/DeepL）仍走老 `translate_batch`；AI 三后端中 claude_code 走任务台、openai/anthropic 经本次改造走 `LangChainRunner`（老路径 unattended）。
- 本设计即 FEATURE_Agent维护任务台「阶段 3 NativeLoopRunner」的 langchain 落地版，但写库机制对齐 Claude Code（SQL 文本 + 守卫）。
