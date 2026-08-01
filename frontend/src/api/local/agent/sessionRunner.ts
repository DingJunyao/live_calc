// 本地 Agent 会话运行器（共享：composable 与 agents handler 复用）
import { runAgent } from './runner'
import type { AgentProgress } from './runner'
import { api } from '@/api'

export interface RenderMessage {
  key: string
  role: 'assistant' | 'tool'
  content: string | null
  toolName: string | null
  toolUseId: string | null
  toolInput: any
  toolResult: any
  toolDone: boolean
}

export const TASK_PROMPTS: Record<string, string> = {
  data_analysis: '请分析本地数据：用工具查询商品、食材、菜谱的价格与营养信息，给出整体情况与值得关注的发现。',
  nutrition_audit: '请审核食材营养数据：逐个检查食材的营养信息是否完整，找出缺失关键营养素的数据；如需补充可调用 update_nutrition 工具。',
  price_analysis: '请分析商品价格：用工具查询商品与价格记录，找出价格异常或更优购买方案。',
  inventory_check: '请检查数据完整性：用 read_statistics 等工具统计各表数据量，发现缺失或不一致的数据并报告。',
  fill_piece_weight: '请为商品补充规格/件重信息：用 read_products 查询商品，结合原料、价格等数据推测并补全 piece_weight（每件重量）；可调用 batch_update 更新。',
  infer_densities: '请推测食材密度：用 read_ingredients、read_nutrition 查询食材，结合常识推测密度（g/ml），并写入；可调用 batch_update 更新。',
  usda_translate: '请翻译食材名为英文：用 read_ingredients 查询食材，把食材的中文名翻译成对应的英文 USDA 食物名；可调用 batch_update 更新 name_en 字段。',
  unmapped_nutrient_translate: '请翻译营养素名：查询现有营养数据中的 nutrient_name，把中文营养素名翻译成 USDA 标准英文名；可调用 batch_update 更新。',
}

export function buildPrompt(taskType: string): string {
  return TASK_PROMPTS[taskType] || `请执行任务：${taskType}。可调用工具查询本地数据后用中文总结。`
}

export type AgentProviderLike = 'claude_code' | 'openai' | 'anthropic'

export interface AgentRunConfig {
  provider: 'anthropic' | 'openai'
  apiKey: string
  model: string
  baseUrl?: string
}

export async function resolveAgentConfig(provider: AgentProviderLike): Promise<AgentRunConfig> {
  if (provider === 'claude_code') {
    throw new Error('本地模式不支持 claude_code，请在 AI 配置中选择 OpenAI 或 Anthropic 兼容。')
  }
  const cfg: any = await api.get('/admin/translation-config')
  const p = cfg?.ai?.providers?.[provider]
  if (!p || !p.api_key) {
    throw new Error(`未配置 ${provider} 的 API Key，请先在「AI 与机翻配置」中填写并保存。`)
  }
  return {
    provider,
    apiKey: p.api_key,
    model: p.model || (provider === 'anthropic' ? 'claude-sonnet-4-6' : 'gpt-4o-mini'),
    baseUrl: p.base_url,
  }
}

let renderKeySeq = 0
export function nextKey(): string {
  renderKeySeq += 1
  return `msg-${Date.now()}-${renderKeySeq}`
}

export function mkAssistant(content: string): RenderMessage {
  return { key: nextKey(), role: 'assistant', content, toolName: null, toolUseId: null, toolInput: null, toolResult: null, toolDone: false }
}

/** 把 runner 的 AgentProgress 映射到渲染消息（原地修改 renders 数组） */
export function applyProgress(p: AgentProgress, renders: RenderMessage[]): void {
  if (p.type === 'text') {
    const last = renders[renders.length - 1]
    if (last && last.role === 'assistant') {
      last.content = (last.content ?? '') + p.content
    } else {
      renders.push(mkAssistant(p.content))
    }
  } else if (p.type === 'tool_use') {
    renders.push({ key: nextKey(), role: 'tool', content: null, toolName: p.name, toolUseId: null, toolInput: p.input, toolResult: null, toolDone: false })
  } else if (p.type === 'tool_result') {
    const target = [...renders].reverse().find((m) => m.role === 'tool' && !m.toolDone)
    if (target) {
      target.toolResult = p.result
      target.toolDone = true
    } else {
      renders.push({ key: nextKey(), role: 'tool', content: null, toolName: p.name, toolUseId: null, toolInput: null, toolResult: p.result, toolDone: true })
    }
  } else if (p.type === 'error') {
    throw new Error(p.message)
  }
}

/** 运行 Agent 并累积渲染消息；返回最终状态。 */
export async function executeAgentRun(
  config: AgentRunConfig,
  taskType: string,
  renders: RenderMessage[],
  aiMessages: any[],
  signal?: AbortSignal,
): Promise<{ status: 'success' | 'failed'; error?: string }> {
  const prompt = buildPrompt(taskType)
  try {
    const gen = runAgent(config as any, prompt, signal, aiMessages)
    for await (const p of gen) {
      applyProgress(p, renders)
    }
    return { status: 'success' }
  } catch (e: any) {
    return { status: 'failed', error: e?.message || '运行失败' }
  }
}
