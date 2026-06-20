// composables/useAgentSession.ts
// Agent 会话 SSE 订阅 + 事件分发。对照 cc/AGENT_SSE_EVENTS.md。
//
// 关键点：
// - EventSource 无法带 header，用 query token 鉴权（从 localStorage.access_token 取）。
// - baseURL 对齐 vite dev proxy（/api → http://localhost:8000），EventSource URL 用相对路径。
// - seq 去重：history 回放时更新 maxSeqSeen；实时 tool_use/tool_result 中
//   seq <= maxSeqSeen 视为重连回放重复，跳过。
// - text_delta 无 seq，直接追加到最后一条 assistant 气泡（流式）。
// - tool_use / tool_result 按 tool_use_id 配对。
import { ref, onUnmounted } from 'vue'
import type { Ref } from 'vue'
import type {
  AgentApproval,
  AgentEvent,
  AgentMessage,
} from '@/types/agent'
import {
  createSession as apiCreateSession,
  decideApproval as apiDecideApproval,
  postMessage as apiPostMessage,
} from '@/api/agent'
import type { AgentProvider } from '@/api/agent'

/**
 * 渲染用的消息项（assistant 文本气泡 / tool 卡片）。
 * 一条 assistant 消息可能由 history 给出，也可能由实时 text_delta 流式拼接。
 */
export interface RenderMessage {
  /** 前端生成的稳定 key */
  key: string
  role: 'assistant' | 'tool'
  /** assistant: 聚合文本；tool: null */
  content: string | null
  /** tool 字段 */
  toolName: string | null
  toolUseId: string | null
  toolInput: any | null
  toolResult: any | null
  /** tool_result 是否已到达 */
  toolDone: boolean
}

/** 拼接 EventSource 的 stream URL（query token 鉴权）。 */
function buildStreamUrl(sid: number): string {
  const token = localStorage.getItem('access_token') || ''
  const base = import.meta.env.VITE_API_URL || '/api/v1'
  // base 可能是相对路径（/api/v1）或绝对 URL；dev proxy 统一走 /api。
  const url = `${base.replace(/\/$/, '')}/agent/sessions/${sid}/stream`
  return `${url}?token=${encodeURIComponent(token)}`
}

let renderKeySeq = 0
function nextKey(): string {
  renderKeySeq += 1
  return `msg-${Date.now()}-${renderKeySeq}`
}

export function useAgentSession() {
  const messages: Ref<RenderMessage[]> = ref([])
  const status: Ref<string> = ref('pending')
  const pendingApprovals: Ref<AgentApproval[]> = ref([])
  /** 累计成本（done 事件每次到达都累加；前端展示本会话总成本） */
  const costUsd: Ref<number | null> = ref(null)
  const error: Ref<string> = ref('')
  const connected: Ref<boolean> = ref(false)

  let es: EventSource | null = null
  /** 已展示过的最大 seq（用于重连去重） */
  let maxSeqSeen = 0

  /** 由 history 事件构造一条 RenderMessage */
  function fromHistory(evt: Extract<AgentEvent, { kind: 'history' }>): RenderMessage {
    if (evt.role === 'assistant') {
      return {
        key: nextKey(),
        role: 'assistant',
        content: evt.content ?? '',
        toolName: null,
        toolUseId: null,
        toolInput: null,
        toolResult: null,
        toolDone: false,
      }
    }
    // role === 'tool'：一条消息同时承载 tool_use 与 tool_result（历史回放已落库）
    return {
      key: nextKey(),
      role: 'tool',
      content: null,
      toolName: evt.tool_name ?? null,
      toolUseId: evt.tool_use_id ?? null,
      toolInput: evt.tool_input ?? null,
      toolResult: evt.tool_result ?? null,
      toolDone: evt.tool_result != null,
    }
  }

  /** 更新或插入一条 approval（按 id 去重）。 */
  function upsertApproval(ap: AgentApproval) {
    const idx = pendingApprovals.value.findIndex((a) => a.id === ap.id)
    if (idx >= 0) pendingApprovals.value[idx] = ap
    else pendingApprovals.value.push(ap)
  }

  function applyEvent(evt: AgentEvent) {
    switch (evt.kind) {
      case 'history': {
        if (typeof evt.seq === 'number') {
          maxSeqSeen = Math.max(maxSeqSeen, evt.seq)
        }
        messages.value.push(fromHistory(evt))
        break
      }
      case 'history_end': {
        // 历史回放结束，转入实时。status 可能是 running / awaiting_approval。
        status.value = evt.status
        break
      }
      case 'text_delta': {
        // 追加到最后一条 assistant 消息；没有则新建。
        const last = messages.value[messages.value.length - 1]
        if (last && last.role === 'assistant') {
          last.content = (last.content ?? '') + evt.text
        } else {
          messages.value.push({
            key: nextKey(),
            role: 'assistant',
            content: evt.text,
            toolName: null,
            toolUseId: null,
            toolInput: null,
            toolResult: null,
            toolDone: false,
          })
        }
        break
      }
      case 'tool_use': {
        // seq 去重（重连后历史已回放过的不再加）
        if (evt.seq <= maxSeqSeen) break
        maxSeqSeen = evt.seq
        messages.value.push({
          key: nextKey(),
          role: 'tool',
          content: null,
          toolName: evt.tool_name,
          toolUseId: evt.tool_use_id,
          toolInput: evt.tool_input,
          toolResult: null,
          toolDone: false,
        })
        break
      }
      case 'tool_result': {
        if (evt.seq <= maxSeqSeen) break
        maxSeqSeen = evt.seq
        // 按 tool_use_id 配对更新对应 tool 消息（从后往前找最近未完成的）
        const target = [...messages.value]
          .reverse()
          .find(
            (m) =>
              m.role === 'tool' &&
              !m.toolDone &&
              ((evt.tool_use_id && m.toolUseId === evt.tool_use_id) ||
                m.toolUseId == null),
          )
        if (target) {
          target.toolResult = evt.tool_result
          target.toolDone = true
          if (!target.toolUseId && evt.tool_use_id) {
            target.toolUseId = evt.tool_use_id
          }
        } else {
          // 没找到配对（极端情况），兜底单独追加一条
          messages.value.push({
            key: nextKey(),
            role: 'tool',
            content: null,
            toolName: null,
            toolUseId: evt.tool_use_id,
            toolInput: null,
            toolResult: evt.tool_result,
            toolDone: true,
          })
        }
        break
      }
      case 'approval_needed': {
        upsertApproval({
          id: evt.approval_id,
          session_id: null,
          sql: evt.sql,
          danger_reason: evt.danger_reason,
          affected_estimate: null,
          status: 'pending',
          decided_by: null,
          decided_at: null,
          created_at: null,
        })
        status.value = 'awaiting_approval'
        break
      }
      case 'sql_executed': {
        const idx = pendingApprovals.value.findIndex(
          (a) => a.id === evt.approval_id,
        )
        if (idx >= 0) {
          pendingApprovals.value[idx] = {
            ...pendingApprovals.value[idx],
            status: evt.error ? 'failed' : evt.status,
          }
        }
        break
      }
      case 'sql_rejected': {
        const idx = pendingApprovals.value.findIndex(
          (a) => a.id === evt.approval_id,
        )
        if (idx >= 0) {
          pendingApprovals.value[idx] = {
            ...pendingApprovals.value[idx],
            status: 'rejected',
          }
        }
        break
      }
      case 'sql_timeout': {
        const idx = pendingApprovals.value.findIndex(
          (a) => a.id === evt.approval_id,
        )
        if (idx >= 0) {
          pendingApprovals.value[idx] = {
            ...pendingApprovals.value[idx],
            status: 'timeout',
          }
        }
        error.value = 'SQL 审批等待超时'
        status.value = 'failed'
        break
      }
      case 'done': {
        if (typeof evt.cost_usd === 'number') {
          costUsd.value = (costUsd.value ?? 0) + evt.cost_usd
        }
        if (evt.is_error && evt.error) {
          error.value = evt.error
          status.value = 'failed'
        } else {
          status.value = evt.status ?? 'completed'
        }
        // 终态：关闭连接
        disconnect()
        break
      }
      case 'error': {
        error.value = evt.error
        status.value = 'failed'
        disconnect()
        break
      }
      default: {
        // 兜底：未知 kind 忽略
        break
      }
    }
  }

  function reset() {
    messages.value = []
    status.value = 'pending'
    pendingApprovals.value = []
    costUsd.value = null
    error.value = ''
    maxSeqSeen = 0
  }

  /** 建立 SSE 连接（不重置已渲染状态，便于断线重连）。 */
  function connect(sid: number): Promise<void> {
    disconnect()
    return new Promise<void>((resolve, reject) => {
      try {
        const url = buildStreamUrl(sid)
        es = new EventSource(url)
        es.onopen = () => {
          connected.value = true
          resolve()
        }
        es.onmessage = (e: MessageEvent) => {
          if (!e.data) return
          try {
            const evt = JSON.parse(e.data) as AgentEvent
            if (evt && typeof (evt as any).kind === 'string') {
              applyEvent(evt)
            }
          } catch (err) {
            console.warn('[useAgentSession] parse SSE failed', err, e.data)
          }
        }
        es.onerror = (e: Event) => {
          // EventSource 浏览器会自动重连；这里只标记连接状态。
          // 终态由后端 done/error/close 流处理；若 readyState 为 CLOSED 表示彻底断开。
          connected.value = false
          if (es && es.readyState === EventSource.CLOSED) {
            // 已彻底关闭，若仍在 running 态，标记连接断开（UI 可提示重连）
            if (status.value === 'running' || status.value === 'awaiting_approval') {
              // 不改 status（终态以 done 为准），仅记日志
              console.warn('[useAgentSession] EventSource closed unexpectedly', e)
            }
          }
          // 首次 open 前出错 → reject（通常 401）
          if (messages.value.length === 0 && status.value === 'pending') {
            reject(new Error('SSE 连接失败（可能鉴权失败或会话不存在）'))
          }
        }
      } catch (err) {
        reject(err)
      }
    })
  }

  function disconnect() {
    if (es) {
      es.close()
      es = null
    }
    connected.value = false
  }

  /** 一站式：建会话 + 连接 SSE，返回 session_id。
   * provider 默认 claude_code（保现有行为）；Vue 层传入用户选择。
   */
  async function startTask(
    taskType: string,
    provider: AgentProvider = 'claude_code',
  ): Promise<number> {
    reset()
    const { session_id } = await apiCreateSession(taskType, false, provider)
    status.value = 'running'
    await connect(session_id)
    return session_id
  }

  /** 插话（resume 新轮）。 */
  async function interject(sid: number, text: string): Promise<void> {
    await apiPostMessage(sid, text)
  }

  /** 审批决策；本地同步更新 approval 状态（最终态以 sql_* 事件为准）。 */
  async function approve(aid: number, ok: boolean): Promise<void> {
    await apiDecideApproval(aid, ok)
    const idx = pendingApprovals.value.findIndex((a) => a.id === aid)
    if (idx >= 0) {
      pendingApprovals.value[idx] = {
        ...pendingApprovals.value[idx],
        status: ok ? 'approved' : 'rejected',
      }
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    // state
    messages,
    status,
    pendingApprovals,
    costUsd,
    error,
    connected,
    // actions
    connect,
    disconnect,
    startTask,
    interject,
    approve,
    reset,
  }
}

export type { AgentMessage }
