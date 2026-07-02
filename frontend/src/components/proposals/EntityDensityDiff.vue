<script setup lang="ts">
import { computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()
const snap = computed(() => props.proposal.snapshot || {})
const p = computed(() => props.proposal.payload || {})
const action = computed(() => props.proposal.action)

function fmtDensity(d: any, u: any): string {
  if (d == null) return '—'
  return u ? `${d} ${u}` : String(d)
}
</script>

<template>
  <v-table density="compact" class="diff-table">
    <tbody>
      <tr>
        <td class="text-caption text-medium-emphasis" style="width:28%">密度</td>
        <td class="diff-cell before unchanged">
          {{ action === 'create' ? '—' : fmtDensity(snap.density, snap.unit) }}
        </td>
        <td class="text-center text-medium-emphasis" style="width:32px">→</td>
        <td class="diff-cell after added">
          {{ action === 'delete' ? '（删除）' : fmtDensity(p.density, p.unit) }}
        </td>
      </tr>
      <tr v-if="p.confidence !== undefined || snap.confidence !== undefined">
        <td class="text-caption text-medium-emphasis">置信度</td>
        <td class="diff-cell before unchanged">{{ snap.confidence ?? '—' }}</td>
        <td class="text-center text-medium-emphasis">→</td>
        <td class="diff-cell after added">{{ p.confidence ?? '—' }}</td>
      </tr>
      <tr v-if="p.condition !== undefined || snap.condition !== undefined">
        <td class="text-caption text-medium-emphasis">条件</td>
        <td class="diff-cell before unchanged">{{ snap.condition ?? '—' }}</td>
        <td class="text-center text-medium-emphasis">→</td>
        <td class="diff-cell after added">{{ p.condition ?? '—' }}</td>
      </tr>
    </tbody>
  </v-table>
</template>

<style scoped>
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }
</style>
