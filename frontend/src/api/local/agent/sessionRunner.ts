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
  nutrition_audit: '请审核食材营养数据：逐个检查食材的营养信息是否完整，找出缺失关键营养素的数据；任务明确要求补充时，直接用 update_nutrition 写入，不要等待用户确认。',
  price_analysis: '请分析商品价格：用工具查询商品与价格记录，找出价格异常或更优购买方案。',
  inventory_check: '请检查数据完整性：用 read_statistics 等工具统计各表数据量，发现缺失或不一致的数据并报告。',
  fill_piece_weight: '请完成「自定义单位校准」：先用 read_entity_units 查询 entity_unit_overrides，找出 weight_per_unit 为空或等于 100 的占位项；再用 read_units 确认克、个等单位的 ID，用 read_ingredients、read_products 关联实体名称，找出使用计数单位但尚未建档的食材/商品。已存在的记录用 batch_update 修正 weight_per_unit，缺失记录用 batch_insert 补建。所有估值直接执行，不要等待用户确认；每处理完一批就继续查询剩余项，直到没有待处理记录，最后用中文总结本轮修正了多少条。',
  infer_densities: '请完成「密度推测」：先用 read_densities 查询 entity_densities，找出缺失密度记录的食材；再用 read_units 确认密度单位 ID，用 read_ingredients、read_nutrition 获取食材上下文，结合常识估算密度（kg/m³）。已有记录用 batch_update 修正，缺失记录用 batch_insert 补建。直接写入、不要等待用户确认；分批处理直到没有缺失记录，最后总结修正数量。',
  usda_translate: '请完成「食材名翻译」：用 read_ingredients 分批查询食材，把中文名翻译成对应的英文 USDA 食物名，通过 batch_update 写入 name_en。直接写入、不要等待用户确认；分批处理全部食材，最后总结翻译数量。',
  unmapped_nutrient_translate: '请完成「营养素翻译」：查询 nutrition_data 中的中文营养素名，翻译成 USDA 标准英文名。由于 nutrition_data 需要用 update_nutrition 整组替换，请分批对每个食材调用 update_nutrition 写入翻译后的营养素列表；直接执行、不要等待用户确认，处理完所有未映射营养素后总结。',
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
  onProgress?: (renders: RenderMessage[], aiMessages: any[]) => void | Promise<void>,
): Promise<{ status: 'success' | 'failed'; error?: string }> {
  const prompt = buildPrompt(taskType)
  if (!aiMessages.length) {
    aiMessages.push({ role: 'user', content: prompt })
  }
  try {
    const gen = runAgent(config as any, prompt, signal, aiMessages)
    for await (const p of gen) {
      applyProgress(p, renders)
      if (onProgress) {
        try {
          await onProgress(renders, aiMessages)
        } catch {
          // 中间快照落盘失败不阻断 Agent 继续执行。
        }
      }
    }
    return { status: 'success' }
  } catch (e: any) {
    return { status: 'failed', error: e?.message || '运行失败' }
  }
}
