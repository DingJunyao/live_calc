// api/agent.ts
// Agent 任务台 REST 客户端，复用现有 axios 封装（@/api/client）。
// 拦截器自动注入 Authorization: Bearer <jwt>（从 localStorage.access_token）。
import api from './client'
import type { AgentSession, SessionDetail, TaskType } from '@/types/agent'

/**
 * Agent Provider 标识。后端 Task 5 的 runner_factory 按此分流：
 * - claude_code → ClaudeCodeRunner（默认，保现有行为）
 * - openai → LangChainRunner（OpenAI 兼容端点）
 * - anthropic → LangChainRunner（Anthropic 兼容端点）
 */
export type AgentProvider = 'claude_code' | 'openai' | 'anthropic'

/** 建会话（管理员）。返回 { session_id }。
 * provider: claude_code（默认）/ openai / anthropic，
 * 后端 runner_factory 按此分流（Task 5）。
 */
export function createSession(
  taskType: string,
  force = false,
  provider: AgentProvider = 'claude_code',
): Promise<{ session_id: number }> {
  return api.post('/agent/sessions', {
    task_type: taskType,
    force,
    provider,
  })
}

/** 列出会话（登录）。 */
export function listSessions(limit = 50): Promise<AgentSession[]> {
  return api.get('/agent/sessions', { params: { limit } })
}

/** 获取会话详情（含历史消息与待审批）。普通用户隔离由后端处理。 */
export function getSession(sid: number): Promise<SessionDetail> {
  return api.get(`/agent/sessions/${sid}`)
}

/** 插话（管理员）：在已终态会话上 resume 新轮。 */
export function postMessage(sid: number, text: string): Promise<void> {
  return api.post(`/agent/sessions/${sid}/messages`, { text })
}

/** 审批决策（管理员）。 */
export function decideApproval(
  aid: number,
  approved: boolean,
): Promise<{ ok: boolean }> {
  return api.post(`/agent/approvals/${aid}`, { approved })
}

/** 任务类型清单（登录）。 */
export function getTaskTypes(): Promise<TaskType[]> {
  return api.get('/agent/task-types')
}

/** 取消正在运行的 Agent 会话（管理员）。 */
export function cancelSession(sid: number): Promise<{ status: string }> {
  return api.post(`/agent/sessions/${sid}/cancel`)
}
