<script setup lang="ts">
import { computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

const snap = computed(() => props.proposal.snapshot || {})
const updateData = computed(() => (props.proposal.payload || {}).update_data || {})

// ---- scalar field diff (upper half) ----
const META_KEYS = new Set([
  'id', 'is_public', 'user_id', 'source', 'created_at', 'updated_at',
  'created_by', 'updated_by', 'is_active', 'old_ingredients', 'ingredients', 'steps',
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
  if (q != null && q !== '') return String(q)
  if (qr && typeof qr === 'object') {
    const min = (qr as any).min, max = (qr as any).max
    if (min != null && max != null) return `${min}~${max}`
  }
  return '—'
}

const oldIngs = computed<IngItem[]>(() =>
  ((snap.value.old_ingredients || []) as any[]).map(r => ({
    name: r.ingredient_name || `#${r.ingredient_id}`,
    qty: fmtQty(r.quantity, r.quantity_range),
    unit: r.unit_name || '',
    note: r.note || '',
  })))

const newIngs = computed<IngItem[]>(() =>
  ((updateData.value.ingredients || []) as any[]).map(r => ({
    name: r.ingredient_name || '',
    qty: fmtQty(r.quantity, r.quantity_range),
    unit: '',
    note: r.note || '',
  })))

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
              <span v-else>{{ formatValue(row.before) }}</span>
            </td>
            <td class="text-center text-medium-emphasis" style="width: 32px">→</td>
            <td :class="['diff-cell', 'after', row.kind]">
              <span v-if="row.after === null" class="text-medium-emphasis">—</span>
              <span v-else>{{ formatValue(row.after) }}</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <!-- ingredients two-column -->
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
                {{ row.oldItem.qty }} {{ row.oldItem.unit }}
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
