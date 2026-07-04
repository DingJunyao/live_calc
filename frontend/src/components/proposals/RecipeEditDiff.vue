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
  'steps', 'cooking_steps', 'tips', 'images',
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
  // 旧食材按名字建表，用于补全新食材缺失的 unit（payload 通常只传 unit_id）
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

// 数值化比较：2.0 与 2 视为相等
function qtyEqual(a: string, b: string): boolean {
  const na = Number(a), nb = Number(b)
  if (!isNaN(na) && !isNaN(nb)) return Math.abs(na - nb) < 1e-9
  return a === b
}

const ingRows = computed<IngRow[]>(() => {
  // 按位置索引对齐（体现顺序变动）：同位内容不同→changed；旧多余→removed；新多余→added
  const maxLen = Math.max(oldIngs.value.length, newIngs.value.length)
  const hasOld = oldIngs.value.length > 0
  const rows: IngRow[] = []
  for (let i = 0; i < maxLen; i++) {
    const o = i < oldIngs.value.length ? oldIngs.value[i] : null
    const n = i < newIngs.value.length ? newIngs.value[i] : null
    if (o && n) {
      const changed = o.name !== n.name || !qtyEqual(o.qty, n.qty) || o.note !== n.note
      rows.push({ oldItem: o, newItem: n, kind: changed ? 'changed' : 'unchanged' })
    } else if (o) {
      rows.push({ oldItem: o, kind: 'removed' })
    } else if (n) {
      rows.push({ newItem: n, kind: hasOld ? 'added' : 'unchanged' })
    }
  }
  return rows
})

const hasOldIngredients = computed(() => Array.isArray((snap.value as any).old_ingredients))
const hasIngredientsChange = computed(() => 'ingredients' in updateData.value && updateData.value.ingredients !== null)

// ---- 图片列表 diff（缩略图对比）----
function getImageUrl(p: string): string {
  if (!p) return ''
  if (p.startsWith('http')) return p
  if (p.startsWith('/static/images/')) return `/api/v1${p}`
  const base = import.meta.env.VITE_DATA_REPO_IMAGE_BASE || 'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out'
  return `${base}/${p}`
}
const hasImagesChange = computed(() =>
  'images' in updateData.value && updateData.value.images !== null)
const oldImgs = computed<string[]>(() => {
  const v = (snap.value as any).images
  return Array.isArray(v) ? v : (v ? [String(v)] : [])
})
const newImgs = computed<string[]>(() => {
  const v = (updateData.value as any).images
  return Array.isArray(v) ? v : (v ? [String(v)] : [])
})

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
function stepSubFields(item: any): Array<{ icon: string; text: string }> {
  if (!item || typeof item !== 'object') return []
  const lines: Array<{ icon: string; text: string }> = []
  if (item.duration_minutes != null) lines.push({ icon: 'mdi-timer-outline', text: `${item.duration_minutes}min` })
  if (item.tips) lines.push({ icon: 'mdi-lightbulb-on-outline', text: item.tips })
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

const FIELD_LABELS: Record<string, string> = {
  name: '名称', category: '分类', difficulty: '难度', description: '描述',
  servings: '份数', total_time_minutes: '总时长(分)', tags: '标签',
  result_ingredient_id: '成品原料', image_url: '图片',
}
function fieldLabel(f: string): string { return FIELD_LABELS[f] || f }

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
      <v-table density="compact" class="diff-table scalar-diff-table">
        <colgroup>
          <col style="width: 22%" />
          <col style="width: calc(39% - 16px)" />
          <col style="width: 32px" />
          <col style="width: calc(39% - 16px)" />
        </colgroup>
        <tbody>
          <tr v-for="row in scalarRows" :key="row.field">
            <td class="text-caption text-medium-emphasis diff-field-label">{{ fieldLabel(row.field) }}</td>
            <td :class="['diff-cell', 'before', row.kind]">
              <span v-if="row.before === null" class="text-medium-emphasis">—</span>
              <img v-else-if="row.field === 'image_url' && typeof row.before === 'string' && row.before" :src="row.before" style="max-height:60px;max-width:120px;object-fit:cover;border-radius:4px" />
              <span v-else class="cell-text">{{ formatValue(row.before) }}</span>
            </td>
            <td class="text-center text-medium-emphasis">→</td>
            <td :class="['diff-cell', 'after', row.kind]">
              <span v-if="row.after === null" class="text-medium-emphasis">—</span>
              <img v-else-if="row.field === 'image_url' && typeof row.after === 'string' && row.after" :src="row.after" style="max-height:60px;max-width:120px;object-fit:cover;border-radius:4px" />
              <span v-else class="cell-text">{{ formatValue(row.after) }}</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <!-- images 缩略图对比 -->
    <template v-if="hasImagesChange">
    <div class="text-subtitle-2 mb-2">图片</div>
    <div class="diff-head">
      <div>当前（{{ oldImgs.length }} 张）</div><div>新（{{ newImgs.length }} 张）</div>
    </div>
    <div class="diff-row">
      <div class="diff-cell old">
        <div v-if="oldImgs.length" class="d-flex flex-wrap ga-2">
          <div v-for="(img, i) in oldImgs" :key="'oi'+i" class="image-diff-thumb">
            <img :src="getImageUrl(img)" />
          </div>
        </div>
        <span v-else class="text-medium-emphasis">无</span>
      </div>
      <div class="diff-cell new">
        <div v-if="newImgs.length" class="d-flex flex-wrap ga-2">
          <div v-for="(img, i) in newImgs" :key="'ni'+i" class="image-diff-thumb"
               :class="{ 'is-new': !oldImgs.includes(img) }">
            <img :src="getImageUrl(img)" />
            <v-chip v-if="i === 0" size="x-small" color="primary" variant="flat" class="cover-badge">封面</v-chip>
            <v-chip v-if="!oldImgs.includes(img)" size="x-small" color="success" variant="flat" class="new-badge">新增</v-chip>
          </div>
        </div>
        <span v-else class="text-medium-emphasis">无</span>
      </div>
    </div>
    </template>

    <!-- ingredients two-column -->
    <template v-if="hasIngredientsChange">
    <div class="text-subtitle-2 mb-2">食材列表</div>
    <div v-if="!hasOldIngredients" class="text-caption text-medium-emphasis mb-2">
      历史提议，旧食材数据缺失（仅展示新食材）
    </div>
    <div class="diff-head">
      <div>当前</div><div>新</div>
    </div>
    <div class="diff-rows">
      <div v-for="(row, i) in ingRows" :key="i" class="diff-row">
        <div :class="['diff-cell', 'old', row.kind === 'removed' ? 'del' : (row.kind === 'changed' ? 'mod-old' : '')]">
          <template v-if="row.oldItem">
            <div class="text-body-2">{{ row.oldItem.name }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ row.oldItem.qty }}{{ row.oldItem.unit ? ' ' + row.oldItem.unit : '' }}
              <span v-if="row.oldItem.note">· {{ row.oldItem.note }}</span>
            </div>
          </template>
          <span v-else class="text-medium-emphasis">—</span>
        </div>
        <div :class="['diff-cell', 'new', row.kind === 'added' ? 'add' : (row.kind === 'changed' ? 'mod-new' : '')]">
          <template v-if="row.newItem">
            <div class="text-body-2">{{ row.newItem.name }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ row.newItem.qty }}{{ row.newItem.unit ? ' ' + row.newItem.unit : '' }}
              <span v-if="row.newItem.note">· {{ row.newItem.note }}</span>
            </div>
          </template>
          <span v-else class="text-medium-emphasis">—</span>
        </div>
      </div>
    </div>
    </template>
    <div v-else class="text-caption text-medium-emphasis mb-3">食材未修改</div>

    <!-- text-list fields（cooking_steps / tips / steps）：逐行左右对齐 -->
    <div v-if="textListFields.length" class="mt-4">
      <div v-for="field in textListFields" :key="field" class="mb-3">
        <div class="text-subtitle-2 mb-2">{{ stepLabel(field) }}</div>
        <div class="diff-head">
          <div>当前</div><div>新</div>
        </div>
        <div class="diff-rows">
          <div v-for="(r, i) in (stepRowsMap.get(field) ?? [])" :key="i" class="diff-row">
            <div :class="['diff-cell', 'old', r.kind === 'removed' ? 'del' : (r.kind === 'changed' ? 'mod-old' : '')]">
              <template v-if="r.oldItem">
                <div>{{ renderStepItem(r.oldItem) }}</div>
                <div v-for="(sf, si) in stepSubFields(r.oldItem)" :key="si"
                     class="text-caption text-medium-emphasis d-flex align-center ga-1">
                  <v-icon size="x-small">{{ sf.icon }}</v-icon>{{ sf.text }}
                </div>
              </template>
              <span v-else class="text-medium-emphasis">—</span>
            </div>
            <div :class="['diff-cell', 'new', r.kind === 'added' ? 'add' : (r.kind === 'changed' ? 'mod-new' : '')]">
              <template v-if="r.newItem">
                <div>{{ renderStepItem(r.newItem) }}</div>
                <div v-for="(sf, si) in stepSubFields(r.newItem)" :key="si"
                     class="text-caption text-medium-emphasis d-flex align-center ga-1">
                  <v-icon size="x-small">{{ sf.icon }}</v-icon>{{ sf.text }}
                </div>
              </template>
              <span v-else class="text-medium-emphasis">—</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scalar-diff-table :deep(table) { table-layout: fixed; width: 100%; }
.scalar-diff-table :deep(td) { height: auto !important; min-height: unset !important; padding-top: 6px !important; padding-bottom: 6px !important; }
.scalar-diff-table :deep(td.diff-field-label) { vertical-align: top; word-break: break-word; }
.scalar-diff-table :deep(td.diff-cell) { vertical-align: top; word-break: break-word; white-space: normal; overflow-wrap: anywhere; }
.scalar-diff-table :deep(.cell-text) { display: inline-block; max-width: 100%; }
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }

/* 逐行左右对齐：标题行 + 行容器 */
.diff-head { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 4px; }
.diff-head > div { font-size: 12px; color: rgba(var(--v-theme-on-surface), 0.6); padding: 0 6px; }
.diff-rows { display: flex; flex-direction: column; gap: 6px; }
.diff-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; align-items: stretch; }
.diff-cell { padding: 6px 8px; border-radius: 4px; border: 1px solid rgba(var(--v-theme-on-surface), 0.10); min-height: 36px; display: flex; flex-direction: column; justify-content: center; }
.diff-cell.old.del { background: rgba(244, 67, 54, 0.10); text-decoration: line-through; }
.diff-cell.new.add { background: rgba(76, 175, 80, 0.12); }
.diff-cell.old.mod-old { background: rgba(244, 67, 54, 0.08); }
.diff-cell.new.mod-new { background: rgba(76, 175, 80, 0.08); }

.image-diff-thumb { position: relative; }
.image-diff-thumb img { width: 80px; height: 80px; object-fit: cover; border-radius: 4px; border: 1px solid rgba(var(--v-theme-on-surface), 0.15); }
.image-diff-thumb.is-new img { border-color: rgb(var(--v-theme-success)); box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.3); }
.image-diff-thumb .cover-badge { position: absolute; top: 2px; left: 2px; }
.image-diff-thumb .new-badge { position: absolute; bottom: 2px; left: 2px; }

.diff-pane { border: 1px solid rgba(var(--v-theme-on-surface), 0.12); border-radius: 6px; padding: 6px; min-height: 48px; }
.diff-line { padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; }
.diff-line.del { background: rgba(244, 67, 54, 0.10); text-decoration: line-through; }
.diff-line.add { background: rgba(76, 175, 80, 0.12); }
.diff-line.mod-old { background: rgba(244, 67, 54, 0.08); }
.diff-line.mod-new { background: rgba(76, 175, 80, 0.08); }
</style>
