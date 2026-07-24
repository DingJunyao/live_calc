// Browser Agent 运行器 — 直接调用 Anthropic/OpenAI API，驱动 Agent 与 IndexedDB 交互。
// 基于 AsyncGenerator 逐步产生事件，支持 AbortSignal 取消。

import { TOOLS, getToolByName, type ToolDefinition } from './tools'

// ============================================================
// 事件类型
// ============================================================

export interface AgentProgressText {
  type: 'text'
  content: string
}

export interface AgentProgressToolUse {
  type: 'tool_use'
  name: string
  input: Record<string, any>
}

export interface AgentProgressToolResult {
  type: 'tool_result'
  name: string
  result: any
}

export interface AgentProgressError {
  type: 'error'
  message: string
}

export interface AgentProgressDone {
  type: 'done'
  content: string
}

export type AgentProgress =
  | AgentProgressText
  | AgentProgressToolUse
  | AgentProgressToolResult
  | AgentProgressError
  | AgentProgressDone

// ============================================================
// 配置
// ============================================================

export interface AgentConfig {
  provider: 'anthropic' | 'openai'
  apiKey: string
  model: string
}

// ============================================================
// 系统提示词
// ============================================================

const SYSTEM_PROMPT = `你是一个生活成本计算器（「生计」App）的本地数据助手。你的任务是帮助用户查询和分析存储在 IndexedDB 本地的数据。

你有以下工具可用：
- read_products: 查询商品
- read_ingredients: 查询食材
- read_recipes: 查询菜谱
- read_nutrition: 查询营养数据
- update_nutrition: 更新营养数据（批量）
- read_statistics: 统计数据量
- batch_update: 批量更新字段

请用中文与用户交流。在回答用户问题前，先思考需要调用哪些工具来获取数据。可以同时调用多个工具。

工具使用规则：
1. 优先使用查询工具获取数据，再基于数据进行分析
2. 修改数据的操作（update_nutrition、batch_update）经过用户确认后再执行
3. 如果一次调用无法获取足够信息，继续调用更多工具
4. 用自然语言总结分析结果，不要只是罗列原始数据`

// ============================================================
// 运行器
// ============================================================

const MAX_ITERATIONS = 10

export async function* runAgent(
  config: AgentConfig,
  task: string,
  signal?: AbortSignal,
): AsyncGenerator<AgentProgress> {
  const toolsPayload = TOOLS.map((t: ToolDefinition) => ({
    name: t.name,
    description: t.description,
    input_schema: t.parameters,
  }))

  const messages: any[] = [{ role: 'user', content: task }]

  for (let iteration = 0; iteration < MAX_ITERATIONS; iteration++) {
    if (signal?.aborted) {
      yield { type: 'error', message: '任务已被用户取消' }
      return
    }

    // ---- 调用 AI API ----
    let response: any
    try {
      response = await callAI(config, SYSTEM_PROMPT, toolsPayload, messages, signal)
    } catch (err: any) {
      yield { type: 'error', message: err.message || 'API 调用失败' }
      return
    }

    // ---- 解析响应 ----
    let content: string = ''
    let toolCalls: any[] = []

    if (config.provider === 'anthropic') {
      content = ''
      for (const block of response.content || []) {
        if (block.type === 'text') {
          content += block.text
          yield { type: 'text', content: block.text }
        } else if (block.type === 'tool_use') {
          toolCalls.push({
            id: block.id,
            name: block.name,
            input: block.input,
          })
        }
      }
    } else {
      // OpenAI
      const choice = response.choices?.[0]
      if (choice?.message?.content) {
        content = choice.message.content
        yield { type: 'text', content: choice.message.content }
      }
      if (choice?.message?.tool_calls) {
        toolCalls = choice.message.tool_calls.map((tc: any) => ({
          id: tc.id,
          name: tc.function.name,
          input: JSON.parse(tc.function.arguments),
        }))
      }
    }

    // ---- 没有工具调用 → 完成 ----
    if (toolCalls.length === 0) {
      yield { type: 'done', content }
      return
    }

    // ---- 构建消息（含 AI 回复） ----
    const assistantMsg: any = { role: 'assistant', content: [] as any[] }
    if (content) {
      assistantMsg.content.push({ type: 'text', text: content })
    }

    if (config.provider === 'anthropic') {
      for (const tc of toolCalls) {
        assistantMsg.content.push({
          type: 'tool_use',
          id: tc.id,
          name: tc.name,
          input: tc.input,
        })
      }
    } else {
      assistantMsg.content = content || null
      assistantMsg.tool_calls = toolCalls.map((tc: any) => ({
        id: tc.id,
        type: 'function',
        function: { name: tc.name, arguments: JSON.stringify(tc.input) },
      }))
    }
    messages.push(assistantMsg)

    // ---- 逐个执行工具 ----
    for (const tc of toolCalls) {
      if (signal?.aborted) {
        yield { type: 'error', message: '任务已被用户取消' }
        return
      }

      yield { type: 'tool_use', name: tc.name, input: tc.input }

      const tool = getToolByName(tc.name)
      let result: any
      if (!tool) {
        result = { error: `未知工具: ${tc.name}` }
      } else {
        try {
          result = await tool.execute(tc.input)
        } catch (err: any) {
          result = { error: `工具执行错误: ${err.message}` }
        }
      }

      yield { type: 'tool_result', name: tc.name, result }

      // ---- 把结果加入消息 ----
      if (config.provider === 'anthropic') {
        messages.push({
          role: 'user',
          content: [
            {
              type: 'tool_result',
              tool_use_id: tc.id,
              content: typeof result === 'string' ? result : JSON.stringify(result),
            },
          ],
        })
      } else {
        messages.push({
          role: 'tool',
          tool_call_id: tc.id,
          content: typeof result === 'string' ? result : JSON.stringify(result),
        })
      }
    }
  }

  // 达到最大迭代次数
  yield { type: 'error', message: `已达到最大迭代次数 (${MAX_ITERATIONS})` }
}

// ============================================================
// AI API 调用
// ============================================================

async function callAI(
  config: AgentConfig,
  systemPrompt: string,
  tools: any[],
  messages: any[],
  signal?: AbortSignal,
): Promise<any> {
  if (config.provider === 'anthropic') {
    return callAnthropic(config, systemPrompt, tools, messages, signal)
  } else {
    return callOpenAI(config, systemPrompt, tools, messages, signal)
  }
}

async function callAnthropic(
  config: AgentConfig,
  systemPrompt: string,
  tools: any[],
  messages: any[],
  signal?: AbortSignal,
): Promise<any> {
  const body: any = {
    model: config.model,
    max_tokens: 4096,
    system: systemPrompt,
    messages,
    tools,
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': config.apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => '')
    throw new Error(`Anthropic API ${response.status}: ${errText || response.statusText}`)
  }

  return response.json()
}

async function callOpenAI(
  config: AgentConfig,
  systemPrompt: string,
  tools: any[],
  messages: any[],
  signal?: AbortSignal,
): Promise<any> {
  // Convert tools to OpenAI format
  const openaiTools = tools.map((t: any) => ({
    type: 'function',
    function: {
      name: t.name,
      description: t.description,
      parameters: t.input_schema,
    },
  }))

  const body: any = {
    model: config.model,
    max_tokens: 4096,
    messages: [
      { role: 'system', content: systemPrompt },
      ...messages,
    ],
    tools: openaiTools.length > 0 ? openaiTools : undefined,
  }

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => '')
    throw new Error(`OpenAI API ${response.status}: ${errText || response.statusText}`)
  }

  return response.json()
}
