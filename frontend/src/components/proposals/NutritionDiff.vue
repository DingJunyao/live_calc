<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { previewUsdaNutrients } from '@/api/usda'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

interface NutrientEntry { value: number | null; unit: string }

function numOrNull(v: any): number | null {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

// Unify multiple source shapes into {display_name → {value, unit}}
// Supports:
//   - Three-layer struct {core_nutrients, all_nutrients} (nutrition/product_nutrition/usda_product_match/USDA preview)
//   - Array of NutritionData rows (usda_ingredient_match snapshot.old_nutrition_data)
function normalizeNutritionMap(source: any): Map<string, NutrientEntry> {
  const out = new Map<string, NutrientEntry>()
  if (!source) return out
  if (Array.isArray(source)) {
    for (const row of source) {
      const m = normalizeNutritionMap(row?.nutrients)
      for (const [k, v] of m) out.set(k, v)
    }
    return out
  }
  const core = source.core_nutrients
  if (core && typeof core === 'object') {
    for (const [name, entry] of Object.entries(core)) {
      const e = entry as any
      if (e && typeof e === 'object') {
        out.set(name, { value: numOrNull(e.value), unit: e.unit || '' })
      }
    }
  }
  const all = source.all_nutrients
  if (all && typeof all === 'object') {
    for (const [key, entry] of Object.entries(all)) {
      const e = entry as any
      if (e && typeof e === 'object') {
        const display = e.key || key
        if (!out.has(display)) {
          out.set(display, { value: numOrNull(e.value), unit: e.unit || '' })
        }
      }
    }
  }
  return out
}

const entityType = computed(() => props.proposal.entity_type)
const isUsda = computed(() =>
  entityType.value === 'usda_ingredient_match' || entityType.value === 'usda_product_match')

const beforeMap = computed(() => {
  const snap = props.proposal.snapshot || {}
  if (entityType.value === 'nutrition') return normalizeNutritionMap(snap.nutrients)
  if (entityType.value === 'product_nutrition') return normalizeNutritionMap(snap.old_custom_nutrition_data)
  if (entityType.value === 'usda_product_match') return normalizeNutritionMap(snap.old_custom_nutrition_data)
  if (entityType.value === 'usda_ingredient_match') return normalizeNutritionMap(snap.old_nutrition_data)
  return new Map<string, NutrientEntry>()
})

const afterMapFromPayload = computed(() => {
  const p = props.proposal.payload || {}
  if (entityType.value === 'nutrition') return normalizeNutritionMap(p.nutrients)
  if (entityType.value === 'product_nutrition') return normalizeNutritionMap(p.custom_nutrition_data)
  return new Map<string, NutrientEntry>()
})

const fdcId = computed(() => (props.proposal.payload || {}).fdc_id ?? null)
const usdaAfter = ref<Map<string, NutrientEntry>>(new Map())
const usdaLoading = ref(false)
const usdaError = ref(false)

async function loadUsdaAfter() {
  if (!isUsda.value || fdcId.value == null) return
  usdaLoading.value = true
  usdaError.value = false
  try {
    const struct = await previewUsdaNutrients(fdcId.value as number)
    usdaAfter.value = normalizeNutritionMap(struct)
  } catch {
    usdaError.value = true
    usdaAfter.value = new Map()
  } finally {
    usdaLoading.value = false
  }
}

watch(() => [props.proposal.id, fdcId.value], loadUsdaAfter, { immediate: true })

const afterMap = computed(() => (isUsda.value ? usdaAfter.value : afterMapFromPayload.value))

function sameNum(a: number | null, b: number | null): boolean {
  if (a === null && b === null) return true
  if (a === null || b === null) return false
  return Math.abs(a - b) < 1e-9
}

interface DiffRow { name: string; before: number | null; after: number | null; unit: string; changed: boolean }

const rows = computed<DiffRow[]>(() => {
  const names = new Set<string>([...beforeMap.value.keys(), ...afterMap.value.keys()])
  const list: DiffRow[] = []
  for (const name of names) {
    const b = beforeMap.value.get(name)
    const a = afterMap.value.get(name)
    const before = b?.value ?? null
    const after = a?.value ?? null
    list.push({
      name, before, after,
      unit: a?.unit || b?.unit || '',
      changed: !sameNum(before, after),
    })
  }
  return list.sort((x, y) => Number(y.changed) - Number(x.changed) || x.name.localeCompare(y.name))
})

const changedRows = computed(() => rows.value.filter(r => r.changed))
const unchangedRows = computed(() => rows.value.filter(r => !r.changed))
const showUnchanged = ref(false)

function formatVal(v: number | null): string {
  return v === null ? '—' : String(v)
}
</script>

<template>
  <div>
    <v-alert v-if="usdaError && isUsda" type="warning" variant="tonal" density="compact" class="mb-2">
      USDA 营养素预览不可用（fdc_id 可能已失效），仅显示当前值。
    </v-alert>
    <v-table v-if="rows.length" density="compact" class="nutrition-diff-table">
      <thead>
        <tr>
          <th class="text-caption text-medium-emphasis" style="width: 44%">营养素</th>
          <th class="text-caption text-medium-emphasis">当前</th>
          <th class="text-caption text-medium-emphasis">新值</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in (showUnchanged ? rows : changedRows)" :key="row.name" :class="{ 'nut-changed': row.changed }">
          <td>{{ row.name }}</td>
          <td>
            {{ formatVal(row.before) }}<span class="text-medium-emphasis ms-1">{{ row.unit }}</span>
          </td>
          <td>
            <span v-if="usdaLoading && isUsda" class="text-medium-emphasis">加载中…</span>
            <span v-else>
              {{ formatVal(row.after) }}<span class="text-medium-emphasis ms-1">{{ row.unit }}</span>
            </span>
          </td>
        </tr>
        <tr v-if="!showUnchanged && unchangedRows.length">
          <td colspan="3">
            <v-btn variant="text" size="small" @click="showUnchanged = true">
              ＋ 展开未变化的 {{ unchangedRows.length }} 项
            </v-btn>
          </td>
        </tr>
        <tr v-else-if="showUnchanged && unchangedRows.length">
          <td colspan="3">
            <v-btn variant="text" size="small" @click="showUnchanged = false">收起未变化项</v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
    <div v-else-if="usdaLoading && isUsda" class="text-caption text-medium-emphasis">USDA 营养素加载中…</div>
    <div v-else class="text-caption text-medium-emphasis">暂无营养素数据</div>
  </div>
</template>

<style scoped>
.nutrition-diff-table .nut-changed { background: rgba(255, 193, 7, 0.12); }
</style>
