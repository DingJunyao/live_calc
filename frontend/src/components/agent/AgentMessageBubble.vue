<!--
  Agent 消息气泡 / 工具卡片
  - assistant：markdown 简易渲染（保留换行 + ```代码块```）
  - tool：折叠卡片，显示 tool_name + tool_input（代码块），tool_result 表格/JSON
-->
<template>
  <div v-if="msg.role === 'assistant'" class="agent-msg assistant">
    <div class="agent-avatar">
      <v-icon color="primary" size="20">mdi-robot</v-icon>
    </div>
    <div class="agent-bubble">
      <div v-if="!msg.content && !msg.toolDone" class="text-caption text-medium-emphasis">
        <v-progress-circular indeterminate size="14" width="2" class="mr-2" />
        思考中…
      </div>
      <div v-else class="md-body" v-html="rendered"></div>
    </div>
  </div>

  <div v-else class="agent-msg tool">
    <v-expansion-panels variant="accordion" :model-value="expanded ? [0] : []">
      <v-expansion-panel elevation="0" rounded="lg" class="tool-panel">
        <v-expansion-panel-title class="py-2">
          <div class="d-flex align-center w-100">
            <v-icon size="18" class="mr-2" :color="statusColor">
              {{ msg.toolDone ? 'mdi-check-circle' : 'mdi-tools' }}
            </v-icon>
            <span class="text-body-2 font-weight-medium text-truncate">{{ toolLabel }}</span>
            <v-spacer />
            <v-chip v-if="!msg.toolDone" size="x-small" color="info" variant="tonal">运行中</v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text class="pt-2">
          <div v-if="toolInputText" class="mb-3">
            <div class="text-caption text-medium-emphasis mb-1">输入</div>
            <pre class="code-block"><code>{{ toolInputText }}</code></pre>
          </div>
          <div v-if="msg.toolDone">
            <div class="text-caption text-medium-emphasis mb-1">结果</div>
            <div v-if="resultIsError" class="text-error text-body-2">
              <v-icon size="16" class="mr-1">mdi-alert-circle</v-icon>{{ resultErrorText }}
            </div>
            <template v-else>
              <component
                :is="'table'"
                v-if="resultRows.length"
                class="result-table"
              >
                <thead>
                  <tr>
                    <th v-for="(col, i) in resultCols" :key="i">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in resultRows" :key="ri">
                    <td v-for="(col, ci) in resultCols" :key="ci">{{ formatCell(row[col]) }}</td>
                  </tr>
                </tbody>
              </component>
              <pre v-else-if="resultText" class="code-block"><code>{{ resultText }}</code></pre>
            </template>
          </div>
          <div v-else class="text-caption text-medium-emphasis d-flex align-center">
            <v-progress-circular indeterminate size="12" width="2" class="mr-2" />
            等待工具返回…
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import type { RenderMessage } from '@/composables/useAgentSession'

const props = defineProps<{ msg: RenderMessage }>()

const expanded = ref(false)
// 工具卡片：结果到达后自动展开一次（便于查看），其余保持折叠
watch(
  () => props.msg.toolDone,
  (done) => {
    if (done) expanded.value = true
  },
)

const statusColor = computed(() => {
  if (!props.msg.toolDone) return 'info'
  return resultIsError.value ? 'error' : 'success'
})

const toolLabel = computed(() => {
  const name = props.msg.toolName || 'tool'
  // mcp__controlled_db__db_read → db_read
  const parts = name.split('__')
  return parts.length > 1 ? parts[parts.length - 1] : name
})

const toolInputText = computed(() => {
  const input = props.msg.toolInput
  if (input == null) return ''
  if (typeof input === 'string') return input
  // 常见字段优先
  const sqlLike = (input as any).sql ?? (input as any).query
  if (typeof sqlLike === 'string') return sqlLike
  try {
    return JSON.stringify(input, null, 2)
  } catch {
    return String(input)
  }
})

const resultIsError = computed(() => {
  const r = props.msg.toolResult
  return r != null && typeof r === 'object' && (r as any).is_error === true
})

const resultErrorText = computed(() => {
  const r = props.msg.toolResult as any
  return r?.error || r?.message || '工具执行失败'
})

const resultRows = computed<Record<string, any>[]>(() => {
  const r = props.msg.toolResult
  if (!Array.isArray(r)) return []
  // 仅当元素是对象（行集合）时渲染表格
  if (r.length > 0 && typeof r[0] === 'object' && r[0] !== null && !Array.isArray(r[0])) {
    return r as Record<string, any>[]
  }
  return []
})

const resultCols = computed<string[]>(() => {
  if (resultRows.value.length === 0) return []
  return Object.keys(resultRows.value[0])
})

const resultText = computed(() => {
  const r = props.msg.toolResult
  if (r == null) return ''
  if (typeof r === 'string') return r
  if (Array.isArray(r)) {
    if (resultRows.value.length === 0) {
      return r.map((x) => (typeof x === 'object' ? JSON.stringify(x) : String(x))).join('\n')
    }
    return ''
  }
  try {
    return JSON.stringify(r, null, 2)
  } catch {
    return String(r)
  }
})

function formatCell(v: any): string {
  if (v == null) return ''
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

/** 简易 markdown 渲染：转义 → ```代码块``` → `行内代码` → **粗体** → 换行 */
const rendered = computed(() => renderMarkdown(props.msg.content || ''))

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function renderMarkdown(src: string): string {
  const parts: string[] = []
  const fence = /```([\w-]*)\n?([\s\S]*?)```/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = fence.exec(src)) !== null) {
    if (m.index > last) parts.push(renderInline(src.slice(last, m.index)))
    const code = m[2].replace(/\n$/, '')
    parts.push(`<pre class="code-block"><code>${escapeHtml(code)}</code></pre>`)
    last = m.index + m[0].length
  }
  if (last < src.length) parts.push(renderInline(src.slice(last)))
  return parts.join('')
}

function renderInline(s: string): string {
  let out = escapeHtml(s)
  // 行内代码
  out = out.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  // 粗体
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // 列表项
  const lines = out.split('\n')
  const outLines: string[] = []
  let inUl = false
  for (const ln of lines) {
    const li = ln.match(/^\s*[-*]\s+(.*)$/)
    if (li) {
      if (!inUl) {
        outLines.push('<ul class="md-ul">')
        inUl = true
      }
      outLines.push(`<li>${li[1]}</li>`)
    } else {
      if (inUl) {
        outLines.push('</ul>')
        inUl = false
      }
      outLines.push(ln)
    }
  }
  if (inUl) outLines.push('</ul>')
  return outLines.join('\n').replace(/\n/g, '<br/>')
}
</script>

<style scoped>
.agent-msg {
  margin-bottom: 12px;
}
.agent-msg.assistant {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.agent-avatar {
  margin-top: 2px;
  flex-shrink: 0;
}
.agent-bubble {
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 12px;
  padding: 8px 12px;
  max-width: 100%;
  word-break: break-word;
  flex: 1;
}
.md-body {
  font-size: 14px;
  line-height: 1.6;
}
.md-body :deep(.md-ul) {
  margin: 4px 0;
  padding-left: 20px;
}
.code-block,
.md-body :deep(.code-block) {
  background: rgb(var(--v-theme-code, 30, 30, 30));
  color: rgb(var(--v-theme-on-code, 245, 245, 245));
  padding: 8px 10px;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12.5px;
  overflow-x: auto;
  white-space: pre;
  margin: 4px 0;
}
.inline-code {
  background: rgba(var(--v-theme-on-surface), 0.08);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: ui-monospace, monospace;
  font-size: 12.5px;
}
.tool-panel {
  background: rgba(var(--v-theme-on-surface), 0.04);
}
.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  margin-top: 4px;
}
.result-table th,
.result-table td {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  padding: 4px 8px;
  text-align: left;
  vertical-align: top;
}
.result-table thead th {
  background: rgba(var(--v-theme-on-surface), 0.06);
  font-weight: 600;
}
</style>
