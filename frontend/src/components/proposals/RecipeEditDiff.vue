<script setup lang="ts">
import { computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

const snap = computed(() => props.proposal.snapshot || {})
const updateData = computed(() => (props.proposal.payload || {}).update_data || {})

// ---- scalar field diff (upper half) ----
const META_KEYS = new Set([
  'id', 'is_public', 'user_id', 'source', 'created_at', 'updated_at',
  'created_by', 'updated_by', 'is_active', 'old_ingredients', 'ingredients',
  'steps', 'cooking_steps', 'tips',
])
interface ScalarRow { field: string; before: any; after: any; kind: 'added' | 'removed' | 'changed' }
const scalarRows = computed<ScalarRow[]>(() => {
  const before = snap.value
  const after = updateData.value
  const keys = new Set<string>([...Object.keys(before), ...Object.keys(after)])
  const rows: ScalarRow[] = []
  for (const k of keys) {
    if (META_KEYS.has(k)) continue
    const hasB = k in before, hasA = k in after
    const b = before[k], a = after[k]
    let kind: ScalarRow['kind'] | null = null
    if (hasB && !hasA) continue
    if (!hasB && hasA) kind = 'added'
    else if (JSON.stringify(b) !== JSON.stringify(a)) kind = 'changed'
    if (!kind) continue
    rows.push({ field: k, before: hasB ? b : null, after: hasA ? a : null, kind })
  }
  return rows
})

// ---- ingredient two-column alignment (align key: ingredient_name) ----
interface IngItem { name: string; qty: string; unit: string; note: string }
interface IngRow { oldItem?: IngItem; newItem?: IngItem; kind: 'added' | 'removed' | 'changed' | 'unchanged' }

function fmtQty(q: any, qr: any): string {
  const base = (q != null && q !== '') ? String(q) : null
  let range: string | null = null
  if (qr && typeof qr === 'object') {
    const min = (qr as any).min, max = (qr as any).max
    if (min != null && max != null) range = `${min}~${max}`
  }
  if (base && range) return `${base}（${range}）`
  if (range) return range
  if (base) return base
  return '—'
}

const oldIngs = computed<IngItem[]>(() =>
  ((snap.value.old_ingredients || []) as any[]).map(r => ({
    name: r.ingredient_name || `#${r.ingredient_id}`,
    qty: fmtQty(r.quantity, r.quantity_range),
    unit: r.unit_name || '',
    note: r.note || '',
  })))

const newIngs = computed<IngItem[]>(() => {
  const oldMap = new Map(oldIngs.value.map(i => [i.name, i]))
  return ((updateData.value.ingredients || []) as any[]).map(r => {
    const name = r.ingredient_name || ''
    const old = oldMap.get(name)
    return {
      name,
      qty: fmtQty(r.quantity, r.quantity_range),
      unit: r.unit_name || old?.unit || '',
      note: r.note || '',
    }
  })
})

const ingRows = computed<IngRow[]>(() => {
  const newMap = new Map<string, IngItem>()
  newIngs.value.forEach(i => newMap.set(i.name, i))
  const ordered: IngRow[] = []
  const seen = new Set<string>()
  for (const o of oldIngs.value) {
    seen.add(o.name)
    const n = newMap.get(o.name)
    if (n) {
      const changed = o.qty !== n.qty || o.note !== n.note
      ordered.push({ oldItem: o, newItem: n, kind: changed ? 'changed' : 'unchanged' })
    } else {
      ordered.push({ oldItem: o, kind: 'removed' })
    }
  }
  for (const n of newIngs.value) {
    if (!seen.has(n.name)) ordered.push({ newItem: n, kind: 'added' })
  }
  return ordered
})

const hasOldIngredients = computed(() => Array.isArray((snap.value as any).old_ingredients))
const hasIngredientsChange = computed(() => 'ingredients' in updateData.value && updateData.value.ingredients !== null)

const textListFields = computed<string[]>(() => {
  const ud = updateData.value
  return ['cooking_steps', 'tips', 'steps'].filter(f => Array.isArray(ud[f]) && ud[f].length > 0)
})

interface StepRow { oldItem?: any; newItem?: any; kind: 'added' | 'removed' | 'changed' | 'unchanged' }

function alignStepsByIndex(field: string): StepRow[] {
  const oldArr = (snap.value[field] || []) as any[]
  const newArr = (updateData.value[field] || []) as any[]
  const keyFn = (s: any): string => typeof s === 'string' ? s : (s?.content ?? '')
  const maxLen = Math.max(oldArr.length, newArr.length)
  const hasOld = oldArr.length > 0
  const rows: StepRow[] = []
  for (let i = 0; i < maxLen; i++) {
    const os = i < oldArr.length ? oldArr[i] : null
    const ns = i < newArr.length ? newArr[i] : null
    if (os && ns) {
      rows.push({
        oldItem: os, newItem: ns,
        kind: keyFn(os) === keyFn(ns) && !stepSubChanged(os, ns) ? 'unchanged' : 'changed',
      })
    } else if (os) {
      rows.push({ oldItem: os, kind: 'removed' })
    } else if (ns) {
      rows.push({ newItem: ns, kind: hasOld ? 'added' : 'unchanged' })
    }
  }
  return rows
}

const stepRowsMap = computed(() => {
  const map = new Map<string, StepRow[]>()
  for (const f of textListFields.value) map.set(f, alignStepsByIndex(f))
  return map
})

function renderStepItem(item: any): string {
  if (typeof item === 'string') return item
  if (item && typeof item === 'object') return item.content ?? JSON.stringify(item)
  return String(item)
}
function stepSubFields(item: any): string[] {
  if (!item || typeof item !== 'object') return []
  const lines: string[] = []
  if (item.duration_minutes != null) lines.push(`🕐 ${item.duration_minutes}min`)
  if (item.tips) lines.push(`💡 ${item.tips}`)
  return lines
}
function stepSubChanged(os: any, ns: any): boolean {
  return String(os?.duration_minutes ?? '') !== String(ns?.duration_minutes ?? '') ||
         String(os?.tips ?? '') !== String(ns?.tips ?? '')
}

const STEP_LABELS: Record<string, string> = {
  cooking_steps: '操作步骤',
  tips: '小贴士',
  steps: '步骤',
}
function stepLabel(f: string): string { return STEP_LABELS[f] || f }

function formatValue(v: any): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
</script>

<template>
  <div>
    <!-- scalar fields -->
    <div v-if="scalarRows.length" class="mb-4">
      <div class="text-subtitle-2 mb-2">基本字段</div>
      <v-table density="compact" class="diff-table">
        <tbody>
          <tr v-for="row in scalarRows" :key="row.field">
            <td class="text-caption text-medium-emphasis" style="width: 28%">{{ row.field }}</td>
            <td :class="['diff-cell', 'before', row.kind]">
              <span v-if="row.before === null" class="text-medium-emphasis">—</span>
              <img v-else-if="row.field === 'image_url' && typeof row.before === 'string' && row.before" :src="row.before" style="max-height:60px;max-width:120px;object-fit:cover;border-radius:4px" />
              <span v-else>{{ formatValue(row.before) }}</span>
            </td>
            <td class="text-center text-medium-emphasis" style="width: 32px">→</td>
            <td :class="['diff-cell', 'after', row.kind]">
              <span v-if="row.after === null" class="text-medium-emphasis">—</span>
              <img v-else-if="row.field === 'image_url' && typeof row.after === 'string' && row.after" :src="row.after" style="max-height:60px;max-width:120px;object-fit:cover;border-radius:4px" />
              <span v-else>{{ formatValue(row.after) }}</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <!-- ingredients two-column -->
    <template v-if="hasIngredientsChange">
    <div class="text-subtitle-2 mb-2">食材列表</div>
    <div v-if="!hasOldIngredients" class="text-caption text-medium-emphasis mb-2">
      历史提议，旧食材数据缺失（仅展示新食材）
    </div>
    <v-row dense>
      <v-col cols="6">
        <div class="text-caption text-medium-emphasis mb-1">当前</div>
        <div class="diff-pane diff-old">
          <template v-for="(row, i) in ingRows" :key="'o' + i">
            <div v-if="row.oldItem"
                 :class="['diff-line', row.kind === 'removed' ? 'del' : (row.kind === 'changed' ? 'mod-old' : '')]">
              <div class="text-body-2">{{ row.oldItem.name }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ row.oldItem.qty }}{{ row.oldItem.unit ? ' ' + row.oldItem.unit : '' }}
                <span v-if="row.oldItem.note">· {{ row.oldItem.note }}</span>
              </div>
            </div>
          </template>
          <div v-if="!ingRows.some(r => r.oldItem)" class="text-caption text-medium-emphasis">（空）</div>
        </div>
      </v-col>
      <v-col cols="6">
        <div class="text-caption text-medium-emphasis mb-1">新</div>
        <div class="diff-pane diff-new">
          <template v-for="(row, i) in ingRows" :key="'n' + i">
            <div v-if="row.newItem"
                 :class="['diff-line', row.kind === 'added' ? 'add' : (row.kind === 'changed' ? 'mod-new' : '')]">
              <div class="text-body-2">{{ row.newItem.name }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ row.newItem.qty }} {{ row.newItem.unit }}
                <span v-if="row.newItem.note">· {{ row.newItem.note }}</span>
              </div>
            </div>
          </template>
          <div v-if="!ingRows.some(r => r.newItem)" class="text-caption text-medium-emphasis">（空）</div>
        </div>
      </v-col>
    </v-row>
    </template>
    <div v-else class="text-caption text-medium-emphasis mb-3">食材未修改</div>

    <!-- text-list fields（cooking_steps / tips / steps）：按内容对齐 diff -->
    <div v-if="textListFields.length" class="mt-4">
      <div v-for="field in textListFields" :key="field" class="mb-3">
        <div class="text-subtitle-2 mb-2">{{ stepLabel(field) }}</div>
        <v-row dense>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis mb-1">当前</div>
            <div class="diff-pane diff-old">
              <template v-if="(stepRowsMap.get(field) ?? []).length">
                <div v-for="(r, i) in stepRowsMap.get(field)!" :key="'o'+i"
                     class="diff-line" :class="r.kind === 'removed' ? 'del' : (r.kind === 'changed' ? 'mod-old' : '')">
                  <template v-if="r.oldItem">
                    <div>{{ renderStepItem(r.oldItem) }}</div>
                    <div v-for="(sf, si) in stepSubFields(r.oldItem)" :key="si"
                         class="text-caption text-medium-emphasis">{{ sf }}</div>
                  </template>
                  <span v-else class="text-medium-emphasis">—</span>
                </div>
              </template>
              <div v-else class="text-caption text-medium-emphasis">—</div>
            </div>
          </v-col>
          <v-col cols="6">
            <div class="text-caption text-medium-emphasis mb-1">新</div>
            <div class="diff-pane diff-new">
              <template v-if="(stepRowsMap.get(field) ?? []).length">
                <div v-for="(r, i) in stepRowsMap.get(field)!" :key="'n'+i"
                     class="diff-line" :class="r.kind === 'added' ? 'add' : (r.kind === 'changed' ? 'mod-new' : '')">
                  <template v-if="r.newItem">
                    <div>{{ renderStepItem(r.newItem) }}</div>
                    <div v-for="(sf, si) in stepSubFields(r.newItem)" :key="si"
                         class="text-caption text-medium-emphasis">{{ sf }}</div>
                  </template>
                  <span v-else class="text-medium-emphasis">—</span>
                </div>
              </template>
              <div v-else class="text-caption text-medium-emphasis">—</div>
            </div>
          </v-col>
        </v-row>
      </div>
    </div>
  </div>
</template>

<style scoped>
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }
.diff-pane { border: 1px solid rgba(var(--v-theme-on-surface), 0.12); border-radius: 6px; padding: 6px; min-height: 48px; }
.diff-line { padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; }
.diff-line.del { background: rgba(244, 67, 54, 0.10); text-decoration: line-through; }
.diff-line.add { background: rgba(76, 175, 80, 0.12); }
.diff-line.mod-old { background: rgba(244, 67, 54, 0.08); }
.diff-line.mod-new { background: rgba(76, 175, 80, 0.08); }
</style>
