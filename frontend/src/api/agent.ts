// api/agent.ts
// Agent 任务台 REST 客户端，复用现有 axios 封装（@/api/client）。
// 拦截器自动注入 Authorization: Bearer <jwt>（从 localStorage.access_token）。
import api from './client'
import type { AgentSession, SessionDetail, TaskType } from '@/types/agent'

/** 建会话（管理员）。返回 { session_id }。 */
export function createSession(taskType: string): Promise<{ session_id: number }> {
  return api.post('/agent/sessions', { task_type: taskType })
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
