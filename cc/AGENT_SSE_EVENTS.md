# Agent SSE 事件契约（前端对接参考）

本文档定义 `GET /api/v1/agent/sessions/{sid}/stream` 的所有 SSE 事件。
每条事件格式：`event: message\ndata: <json>\n\n`。所有事件 payload 至少含 `kind` 字段。

## 鉴权（C2）

浏览器原生 `EventSource` 无法设置自定义 `Authorization` header，故本端点使用
**query token** 鉴权：

```
new EventSource(`/api/v1/agent/sessions/${sid}/stream?token=${encodeURIComponent(jwt)}`)
```

- `?token=<valid jwt>` → 200，开始流式回放/实时推送。
- `?token=<invalid>` → 401。
- 无 `token` 参数 → 401。

其它写端点（建会话/插话/审批）仍使用 `Authorization: Bearer <jwt>` header
（axios/fetch 能带 header）。

> 生产注意：query token 会进入 nginx access log，建议使用短时效 token，或改用
> `fetch` + `ReadableStream` 自行解析 SSE 帧。

## 连接生命周期

1. **先 subscribe 实时 queue**（C1：防止回放期间产生的实时事件被丢）。
2. **回放历史**：按 `seq` 升序发所有 `AgentMessage` → `history` 事件。
3. 发 `history_end` marker（历史结束、转入实时）。
4. **实时消费 queue**：对带 `seq` 的 `tool_use`/`tool_result` 按
   `seq <= max_seq_seen` 去重（重连时已回放过的不再重复）。
5. 终态兜底（B-5）：周期查 `session.status`，终态时发 synthesized `done` 关流。
6. 心跳（I1）：queue 空超过 ~15s 时发 `: ping` 注释行（浏览器忽略，仅保活 TCP）。

## 事件清单

### 历史回放（连接建立后立即发）

#### `history`
回放一条已落库的 `AgentMessage`。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"history"` | 固定 |
| `role` | `"assistant"` \| `"tool"` | 消息角色 |
| `seq` | int | 会话内单调递增序号（去重用） |
| `content` | string \| null | assistant 聚合文本 |
| `tool_name` | string \| null | tool 调用名 |
| `tool_use_id` | string \| null | tool 调用 id |
| `tool_input` | object \| null | tool 调用入参 |
| `tool_result` | any \| null | tool 返回结果 |

前端渲染建议：
- `role === "assistant"` → 渲染 markdown 文本气泡。
- `role === "tool"` → 折叠的工具调用/结果卡片。

#### `history_end`
历史回放结束、转入实时。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"history_end"` | 固定 |
| `status` | string | 当前 session.status（`running` / `awaiting_approval`） |

### 实时流（history_end 之后）

#### `text_delta`
assistant 文本增量（**不带 seq**，不去重——历史回放用聚合的 assistant 消息展示，
实时增量直接追加到当前 assistant 气泡）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"text_delta"` | 固定 |
| `text` | string | 增量文本片段 |

前端渲染建议：追加到当前 assistant 文本气泡（流式打字机效果）。

#### `tool_use`
工具调用开始（**带 seq**，重连去重）。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"tool_use"` | 固定 |
| `tool_name` | string | 工具名 |
| `tool_input` | object | 调用入参 |
| `tool_use_id` | string | 调用 id（与对应 `tool_result` 配对） |
| `seq` | int | AgentMessage seq（去重用） |

#### `tool_result`
工具调用结果（**带 seq**，重连去重）。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"tool_result"` | 固定 |
| `tool_use_id` | string | 对应 tool_use 的 id |
| `tool_result` | any | 工具返回结果 |
| `seq` | int | AgentMessage seq（去重用） |

#### `done`
会话正常终态。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"done"` | 固定 |
| `is_error` | bool \| null | 是否错误终态 |
| `cost_usd` | float \| null | 本轮成本（累计需前端自加） |
| `permission_denials` | list \| null | 权限拒绝列表 |
| `error` | string \| null | `is_error=true` 时的错误文本 |
| `synthesized` | bool \| undefined | true 表示终态兜底合成（非真实 Runner 事件） |
| `status` | string \| undefined | synthesized 时附带的 session.status |

前端渲染建议：`synthesized === true` 或实时到达都表示会话终态，应停止 loading、
关闭 EventSource。

#### `error`
Runner 异常终态。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"error"` | 固定 |
| `error` | string | 错误文本 |
| `is_error` | bool | 通常 true |

前端渲染建议：展示错误提示，关闭 EventSource。

#### `approval_needed`
dangerous SQL 需要人工审批。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"approval_needed"` | 固定 |
| `approval_id` | int | AgentApproval.id |
| `sql` | string | 待审批 SQL |
| `danger_reason` | string | 危险原因说明 |

前端渲染建议：弹出确认对话框，显示 SQL 和危险原因；用户选择后调
`POST /api/v1/agent/approvals/{approval_id}` `{approved: true|false}`。

#### `sql_executed`
SQL 已执行（safe 自动执行 或 approved 后执行）。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"sql_executed"` | 固定 |
| `approval_id` | int | 关联的 AgentApproval.id |
| `sql` | string | 已执行的 SQL |
| `affected` | int \| null | 影响行数 |
| `status` | string | `auto_executed` / `approved` |
| `auto` | bool | true=safe 自动执行，false=审批后执行 |
| `error` | string \| null | 执行失败时的错误 |

#### `sql_rejected`
dangerous SQL 被拒绝。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"sql_rejected"` | 固定 |
| `approval_id` | int | AgentApproval.id |
| `sql` | string | 被拒绝的 SQL |
| `status` | `"rejected"` | 固定 |

#### `sql_timeout`
审批等待超时（未响应）。字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | `"sql_timeout"` | 固定 |
| `approval_id` | int | AgentApproval.id |
| `sql` | string | 超时的 SQL |

前端渲染建议：`sql_timeout` 后会话进入 failed，应展示超时提示。

## 心跳（I1）

当 queue 长时间无事件时，约每 15s 发一行 SSE 注释：

```
: ping
```

浏览器原生 EventSource 会忽略注释行（不触发 `onmessage`），仅用于保活 TCP
连接、防止 nginx/CDN 超时断开。前端无需处理。

## 去重逻辑（C1，前端实现建议）

`tool_use` / `tool_result` 事件带 `seq`。重连场景：

1. 记录已展示的最大 seq：`maxSeqSeen`。
2. 收到 `history` 事件时更新 `maxSeqSeen = max(maxSeqSeen, seq)`。
3. 收到实时 `tool_use` / `tool_result` 事件：
   - `seq <= maxSeqSeen` → 跳过（历史已展示）。
   - `seq > maxSeqSeen` → 展示并更新 `maxSeqSeen`。

`text_delta` 不带 seq（增量），不参与去重；`done`/`error`/`sql_*`/`approval_*`
不进历史回放，无需去重。
