// Agent 会话处理 — 管理浏览器端 Agent 会话的生命周期。
// 会话存储在 IndexedDB 的 agent_sessions 表中。

import { getAll, getById, addOne, putOne } from '../database'

// ============================================================
// 任务类型
// ============================================================

const TASK_TYPES = [
  {
    id: 'data_analysis',
    name: '数据分析',
    description: '分析本地数据，查看商品、食材、菜谱的价格和营养信息',
  },
  {
    id: 'nutrition_audit',
    name: '营养审核',
    description: '检查食材营养数据是否完整，补充缺失的营养信息',
  },
  {
    id: 'price_analysis',
    name: '价格分析',
    description: '分析商品价格趋势，查找价格异常或最优购买方案',
  },
  {
    id: 'inventory_check',
    name: '库存检查',
    description: '检查各类数据的完整性，发现缺失或不一致的数据',
  },
]

// ============================================================
// 辅助函数
// ============================================================

function generateId(): string {
  const ts = Date.now().toString(36)
  const rand = Math.random().toString(36).substring(2, 8)
  return `agent_${ts}_${rand}`
}

function nowISO(): string {
  return new Date().toISOString()
}

// ============================================================
// 公开 Handler
// ============================================================

/** GET /agent/task-types — 返回可用任务类型列表 */
export async function getTaskTypes(): Promise<any> {
  return TASK_TYPES
}

/** POST /agent/sessions — 创建新会话 */
export async function createSession(_params: Record<string, string>, data?: any): Promise<any> {
  const session = {
    id: generateId(),
    task_type: data?.task_type || 'data_analysis',
    title: data?.title || '新对话',
    status: 'running' as const,
    created_at: nowISO(),
    updated_at: nowISO(),
    messages: [] as any[],
  }

  await addOne('agent_sessions', session)
  return session
}

/** GET /agent/sessions — 列出所有会话 */
export async function listSessions(): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  // 返回按创建时间降序排列
  const sorted = all.sort((a, b) => {
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
  })
  return { items: sorted, total: sorted.length }
}

/** GET /agent/sessions/:id — 获取会话详情 */
export async function getSession(params: Record<string, string>): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  const session = all.find((s: any) => s.id === params.id)
  if (!session) throw { status: 404, message: `Session ${params.id} not found` }
  return session
}

/** POST /agent/sessions/:id/cancel — 取消会话 */
export async function cancelSession(params: Record<string, string>): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  const session = all.find((s: any) => s.id === params.id)
  if (!session) throw { status: 404, message: `Session ${params.id} not found` }

  session.status = 'cancelled'
  session.updated_at = nowISO()
  await putOne('agent_sessions', session)
  return session
}

/** POST /agent/sessions/:id/messages — 添加用户消息（stub） */
export async function postMessage(params: Record<string, string>, data?: any): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  const session = all.find((s: any) => s.id === params.id)
  if (!session) throw { status: 404, message: `Session ${params.id} not found` }

  const msg = {
    role: 'user',
    content: data?.content || '',
    created_at: nowISO(),
  }

  session.messages = session.messages || []
  session.messages.push(msg)
  session.updated_at = nowISO()
  await putOne('agent_sessions', session)
  return msg
}
