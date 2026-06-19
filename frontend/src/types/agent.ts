// types/agent.ts
// Agent 任务台相关类型，对齐后端 schemas/agent.py 与 cc/AGENT_SSE_EVENTS.md。

// --------------------------------------------------------------------------- //
// 出参（对齐 AgentSessionOut / AgentMessageOut / AgentApprovalOut）
// --------------------------------------------------------------------------- //
export interface AgentSession {
  id: number
  task_type: string | null
  title: string | null
  status: string
  runner_type: string
  user_id: number | null
  claude_session_id: string | null
  cost_usd: number | null
  error: string | null
  created_at: string | null
  updated_at: string | null
}

export interface AgentMessage {
  id: number
  session_id: number | null
  seq: number | null
  role: string | null // 'assistant' | 'tool' | 'user' | ...
  content: string | null
  tool_name: string | null
  tool_use_id: string | null
  tool_input: any | null
  tool_result: any | null
  created_at: string | null
}

export interface AgentApproval {
  id: number
  session_id: number | null
  sql: string
  danger_reason: string | null
  affected_estimate: number | null
  status: string // pending / approved / rejected / auto_executed / timeout / ...
  decided_by: number | null
  decided_at: string | null
  created_at: string | null
}

export interface SessionDetail {
  session: AgentSession
  messages: AgentMessage[]
  pending_approvals: AgentApproval[]
}

export interface TaskType {
  task_type: string
  title: string
}

// --------------------------------------------------------------------------- //
// SSE 事件（对齐 cc/AGENT_SSE_EVENTS.md，11 种 kind）
// --------------------------------------------------------------------------- //
export interface AgentEventHistory {
  kind: 'history'
  role: 'assistant' | 'tool'
  seq: number
  content: string | null
  tool_name: string | null
  tool_use_id: string | null
  tool_input: object | null
  tool_result: any | null
}

export interface AgentEventHistoryEnd {
  kind: 'history_end'
  status: string
}

export interface AgentEventTextDelta {
  kind: 'text_delta'
  text: string
}

export interface AgentEventToolUse {
  kind: 'tool_use'
  tool_name: string
  tool_input: object
  tool_use_id: string
  seq: number
}

export interface AgentEventToolResult {
  kind: 'tool_result'
  tool_use_id: string
  tool_result: any
  seq: number
}

export interface AgentEventDone {
  kind: 'done'
  is_error: boolean | null
  cost_usd: number | null
  permission_denials: string[] | null
  error: string | null
  synthesized?: boolean
  status?: string
}

export interface AgentEventError {
  kind: 'error'
  error: string
  is_error: boolean
}

export interface AgentEventApprovalNeeded {
  kind: 'approval_needed'
  approval_id: number
  sql: string
  danger_reason: string
}

export interface AgentEventSqlExecuted {
  kind: 'sql_executed'
  approval_id: number
  sql: string
  affected: number | null
  status: string // auto_executed / approved
  auto: boolean
  error: string | null
}

export interface AgentEventSqlRejected {
  kind: 'sql_rejected'
  approval_id: number
  sql: string
  status: 'rejected'
}

export interface AgentEventSqlTimeout {
  kind: 'sql_timeout'
  approval_id: number
  sql: string
}

export type AgentEvent =
  | AgentEventHistory
  | AgentEventHistoryEnd
  | AgentEventTextDelta
  | AgentEventToolUse
  | AgentEventToolResult
  | AgentEventDone
  | AgentEventError
  | AgentEventApprovalNeeded
  | AgentEventSqlExecuted
  | AgentEventSqlRejected
  | AgentEventSqlTimeout
