// Agent 会话处理 — 管理浏览器端 Agent 会话的生命周期。
// 会话存储在 IndexedDB 的 agent_sessions 表中。
// 本地模式：会话 id 为自增数字（与云端/控制台 currentSid:number 一致）；
// listSessions 返回数组；额外提供 PUT 更新用于持久化对话渲染与 AI 消息历史。

import { getAll, addOne, putOne } from '../database'
import {
  executeAgentRun,
  resolveAgentConfig,
  type AgentProviderLike,
  type RenderMessage,
} from '../agent/sessionRunner'

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

/** 生成自增数字 id：基于已有最大 id（兼容历史字符串 id） */
async function nextId(): Promise<number> {
  const all: any[] = await getAll('agent_sessions')
  let max = 0
  for (const s of all) {
    const n = Number(s.id)
    if (Number.isFinite(n) && n > max) max = n
  }
  return Math.max(Date.now(), max + 1)
}

function nowISO(): string {
  return new Date().toISOString()
}

/** 按 id 查找（兼容历史字符串 id） */
function findById(all: any[], id: string | number): any | undefined {
  const n = Number(id)
  return all.find((s: any) => Number(s.id) === n)
}

// ============================================================
// 公开 Handler
// ============================================================

/** GET /agent/task-types — 返回可用任务类型列表 */
export async function getTaskTypes(): Promise<any> {
  // 控制台按 task_type / title 字段渲染与启动，映射成兼容结构
  return TASK_TYPES.map((t) => ({
    task_type: t.id,
    title: t.name,
    description: t.description,
  }))
}

/** POST /agent/sessions — 创建新会话，返回 { session_id } */
export async function createSession(_params: Record<string, string>, data?: any): Promise<any> {
  const taskType = data?.task_type || 'data_analysis'
  const meta = TASK_TYPES.find((t) => t.id === taskType)
  const now = nowISO()
  const session = {
    id: await nextId(),
    task_type: taskType,
    title: data?.title || meta?.name || '新对话',
   status: 'running' as const,
   provider: data?.provider || 'anthropic',
   error: null as string | null,
   created_at: now,
    updated_at: now,
    /** 供历史回放的渲染消息（RenderMessage[]） */
    renders: [] as any[],
    /** AI API 原始消息历史（用于插话续跑） */
    ai_messages: [] as any[],
  }

  await addOne('agent_sessions', session)
  // 本地模式：创建后即触发后台运行（composable 路径也复用本 handler 创建会话）
  void runSessionInBackground(session.id, session.task_type, session.provider)
  return { session_id: session.id }
}

/** 后台运行 Agent 会话：解析配置 → 驱动 runner → 持久化状态。失败时写入 error/status。 */
async function runSessionInBackground(
  sid: number,
  taskType: string,
  providerKey: string,
) {
  const renders: RenderMessage[] = []
  const aiMessages: any[] = []
  try {
    const config = await resolveAgentConfig(providerKey as AgentProviderLike)
    const { status: finalStatus, error: errMsg } = await executeAgentRun(
      config,
      taskType,
      renders,
      aiMessages,
    )
    await updateSession({ id: String(sid) }, {
      renders,
      ai_messages: aiMessages,
      status: finalStatus,
      error: errMsg || null,
    })
  } catch (e: any) {
    await updateSession({ id: String(sid) }, {
      renders,
      ai_messages: aiMessages,
      status: 'failed',
      error: e?.message || '运行失败',
    })
  }
}

/** GET /agent/sessions — 列出会话（数组，按创建时间降序；支持 ?limit） */
export async function listSessions(_params: Record<string, string>, query?: any): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  all.sort(
    (a, b) =>
      new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime(),
  )
  const limit = Math.max(1, Number(query?.limit) || 50)
  return all.slice(0, limit)
}

/** GET /agent/sessions/:id — 获取会话详情 */
export async function getSession(params: Record<string, string>): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  const session = findById(all, params.id)
  if (!session) throw { status: 404, message: `Session ${params.id} not found` }
  return session
}

/** PUT /agent/sessions/:id — 更新会话（持久化 renders / ai_messages / status） */
export async function updateSession(
  params: Record<string, string>,
  data?: any,
): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  const session = findById(all, params.id)
  if (!session) throw { status: 404, message: `Session ${params.id} not found` }
  const updated = {
    ...session,
    ...(data || {}),
    id: session.id,
    updated_at: nowISO(),
  }
  await putOne('agent_sessions', updated)
  return updated
}

/** POST /agent/sessions/:id/cancel — 取消会话 */
export async function cancelSession(params: Record<string, string>): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  const session = findById(all, params.id)
  if (!session) throw { status: 404, message: `Session ${params.id} not found` }

  const updated = { ...session, status: 'cancelled', updated_at: nowISO() }
  await putOne('agent_sessions', updated)
  return updated
}

/** POST /agent/sessions/:id/messages — 添加用户消息（本地由 composable 处理续跑，此 handler 保留兼容） */
export async function postMessage(params: Record<string, string>, data?: any): Promise<any> {
  const all: any[] = await getAll('agent_sessions')
  const session = findById(all, params.id)
  if (!session) throw { status: 404, message: `Session ${params.id} not found` }

  const msg = {
    role: 'user',
    content: data?.content || data?.text || '',
    created_at: nowISO(),
  }

  const messages = session.messages || []
  messages.push(msg)
  const updated = { ...session, messages, updated_at: nowISO() }
  await putOne('agent_sessions', updated)
  return msg
}
