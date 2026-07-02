<script setup lang="ts">
import { computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()
const snap = computed(() => props.proposal.snapshot || {})
const p = computed(() => props.proposal.payload || {})
const action = computed(() => props.proposal.action)

function fmtUnit(name: any, factor: any): string {
  if (name == null) return '—'
  return factor != null ? `${name}（× ${factor}）` : String(name)
}
</script>

<template>
  <v-table density="compact" class="diff-table">
    <tbody>
      <tr>
        <td class="text-caption text-medium-emphasis" style="width:28%">单位</td>
        <td class="diff-cell before unchanged">
          {{ action === 'create' ? '—' : fmtUnit(snap.unit_name, snap.factor) }}
        </td>
        <td class="text-center text-medium-emphasis" style="width:32px">→</td>
        <td class="diff-cell after added">
          {{ action === 'delete' ? '（删除）' : fmtUnit(p.unit_name, p.factor) }}
        </td>
      </tr>
      <tr v-if="p.is_standard !== undefined || snap.is_standard !== undefined">
        <td class="text-caption text-medium-emphasis">标准单位</td>
        <td class="diff-cell before unchanged">{{ snap.is_standard ? '是' : (snap.is_standard === false ? '否' : '—') }}</td>
        <td class="text-center text-medium-emphasis">→</td>
        <td class="diff-cell after added">{{ p.is_standard ? '是' : (p.is_standard === false ? '否' : '—') }}</td>
      </tr>
    </tbody>
  </v-table>
</template>

<style scoped>
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }
</style>
