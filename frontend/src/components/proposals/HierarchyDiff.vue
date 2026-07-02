<script setup lang="ts">
import { computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()
const snap = computed(() => props.proposal.snapshot || {})
const p = computed(() => props.proposal.payload || {})

const RELATION_LABELS: Record<string, string> = {
  contains: '包含',
  is_parent: '上级',
  is_child: '下级',
  equivalent: '等同',
  alternative: '替代',
}

const rows = computed(() => {
  const before = snap.value
  const after = p.value
  const fields = ['relation_type', 'strength']
  return fields.filter(f => f in before || f in after).map(f => {
    const b = before[f] ?? null
    const a = after[f] ?? null
    let kind: string = 'unchanged'
    if (b === null && a !== null) kind = 'added'
    else if (b !== null && a === null) kind = 'removed'
    else if (JSON.stringify(b) !== JSON.stringify(a)) kind = 'changed'
    return { field: f, before: b, after: a, kind }
  })
})

function fmtRelation(v: any): string {
  if (v === null || v === undefined) return '—'
  return RELATION_LABELS[String(v)] || String(v)
}
</script>

<template>
  <v-table v-if="rows.length" density="compact" class="diff-table">
    <tbody>
      <tr v-for="r in rows" :key="r.field">
        <td class="text-caption text-medium-emphasis" style="width:28%">
          {{ r.field === 'relation_type' ? '关系类型' : '关联强度' }}
        </td>
        <td :class="['diff-cell', 'before', r.kind]">
          {{ r.field === 'relation_type' ? fmtRelation(r.before) : (r.before ?? '—') }}
        </td>
        <td class="text-center text-medium-emphasis" style="width:32px">→</td>
        <td :class="['diff-cell', 'after', r.kind]">
          {{ r.field === 'relation_type' ? fmtRelation(r.after) : (r.after ?? '—') }}
        </td>
      </tr>
    </tbody>
  </v-table>
  <div v-else class="text-caption text-medium-emphasis">父子食材信息见上方「目标实体」</div>
</template>

<style scoped>
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }
</style>
