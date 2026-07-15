# Agent 任务台

![Agent 任务台](../img/admin_agent.png)

## 工作原理

Agent 拿到任务模板后，自主读数据库、分析、写 SQL 修正。关键是**受控读写**：

- **只读工具**：Agent 有 `db_read` / `describe` / `list_tables` 三个只读 MCP 工具，能查不能写
- **写操作走 SQL 文本**：Agent 在回答里输出 ` ```sql ` 代码块，由**SQL 守卫**（`sql_guard`）判定：
  - **safe**（受控的 UPDATE/INSERT，如单字段批量修正）→ 自动执行
  - **dangerous**（DROP / 无 WHERE 的批量 / 跨表大改等）→ 弹**审批卡**，管理员批准才执行

这样 Agent 既能批量干活，又不会误删数据。

## 支持的 Agent 引擎

- **Claude Code**（subprocess，stream-json 协议；需自行安装、配置，本系统仅调用其 CLI）
- **LangChain Agent**（OpenAI 兼容 / Anthropic 兼容，`create_agent`）

两者共用 `run_agent_loop` + `sql_guard` + 任务模板，在任务台选 provider 分流。

## 多轮循环

一个任务可能要写很多条 SQL。Agent 循环：提取 SQL → 守卫判定 → 自动执行或等审批 → 把执行结果回流给 Agent（`--resume`）→ Agent 继续，直到任务完成或超时。

## 任务台界面

- **触发任务**：从任务模板列表选一个（如"补单位质量""密度推测""营养素翻译"）
- **对话流**：实时看 Agent 的思考和工具调用
- **插话**：中途给 Agent 追加指令（"顺便把 X 也处理了"）
- **审批卡**：dangerous SQL 弹卡，批准/拒绝
- **刷新重放**：重新加载会话历史

> 后台任务用 `agent_sessions` / `agent_messages` / `agent_approvals` 三张表记录，SSE 流式推送进度。

## 超时配置

在 `backend/.env` 配（见 [配置](config-init.md#后端-backendenv)）：

- `AGENT_IDLE_TIMEOUT`：空闲超时
- `AGENT_TOTAL_TIMEOUT`：总时长上限
- `AGENT_APPROVAL_TIMEOUT`：等审批的最长时间

## 行数安全护栏

单条 SQL 影响行数有护栏阈值（默认单名批量 UPDATE 允许到几万行，全表更新仍触发审批）。护栏阈值可在任务模板里调。

## 已内置的任务模板

- 补单位质量（修正脏数据）
- 密度推测（按食材名推测密度）
- USDA 食材名翻译
- 营养素名翻译

管理员也可以在 [数据维护中心](data-maintenance.md) 触发相关的批量任务。
