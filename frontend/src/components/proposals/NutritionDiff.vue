<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { previewUsdaNutrients } from '@/api/usda'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

interface NutrientEntry { value: number | null; unit: string }

const NUTRIENT_LABELS: Record<string, string> = {
  // 宏观
  energy_kcal: '能量', protein: '蛋白质', total_fat: '脂肪', carbohydrate: '碳水化合物',
  fiber: '膳食纤维', sugar: '糖', starch: '淀粉',
  // 脂肪细分
  saturated: '饱和脂肪酸', monounsaturated: '单不饱和脂肪酸', polyunsaturated: '多不饱和脂肪酸',
  trans: '反式脂肪酸', cholesterol: '胆固醇',
  // 维生素
  vitamin_a: '维生素A', vitamin_c: '维生素C', vitamin_d: '维生素D', vitamin_e: '维生素E',
  vitamin_k: '维生素K', thiamin: '维生素B1', riboflavin: '维生素B2', niacin: '烟酸',
  b6: '维生素B6', b12: '维生素B12', folate: '叶酸',
  pantothenic_acid: '泛酸', choline: '胆碱', betaine: '甜菜碱',
  // 矿物质
  calcium: '钙', iron: '铁', magnesium: '镁', phosphorus: '磷', potassium: '钾',
  sodium: '钠', zinc: '锌', copper: '铜', manganese: '锰', selenium: '硒',
  iodine: '碘', chromium: '铬', molybdenum: '钼', fluoride: '氟',
  // 氨基酸
  tryptophan: '色氨酸', threonine: '苏氨酸', isoleucine: '异亮氨酸',
  leucine: '亮氨酸', lysine: '赖氨酸', methionine: '蛋氨酸',
  phenylalanine: '苯丙氨酸', tyrosine: '酪氨酸', valine: '缬氨酸',
  arginine: '精氨酸', histidine: '组氨酸', alanine: '丙氨酸',
  aspartic_acid: '天冬氨酸', glutamic_acid: '谷氨酸', glycine: '甘氨酸',
  proline: '脯氨酸', serine: '丝氨酸',
  // 其他
  caffeine: '咖啡因', lutein_plus_zeaxanthin: '叶黄素+玉米黄质',
  lycopene: '番茄红素', water: '水分', alcohol: '酒精', ash: '灰分',
  // 常见中文名（直接映射回自身）
  '能量': '能量', '蛋白质': '蛋白质', '脂肪': '脂肪', '碳水化合物': '碳水化合物',
  '膳食纤维': '膳食纤维', '糖': '糖',
  '饱和脂肪酸': '饱和脂肪酸', '单不饱和脂肪酸': '单不饱和脂肪酸',
  '多不饱和脂肪酸': '多不饱和脂肪酸', '反式脂肪酸': '反式脂肪酸',
  '维生素A': '维生素A', '维生素C': '维生素C', '维生素D': '维生素D',
  '钙': '钙', '铁': '铁', '镁': '镁', '磷': '磷', '钾': '钾', '钠': '钠',
  '锌': '锌', '铜': '铜', '叶酸': '叶酸', '烟酸': '烟酸',
}

function nutrientLabel(name: string): string {
  return NUTRIENT_LABELS[name] || name
}

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
const isClearOp = computed(() => {
  const p = props.proposal.payload || {}
  if (entityType.value === 'product_nutrition' || entityType.value === 'usda_product_match') {
    return 'custom_nutrition_data' in p && p.custom_nutrition_data === null
  }
  return false
})

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

const hasBeforeData = computed(() => beforeMap.value.size > 0)

function sameNum(a: number | null, b: number | null): boolean {
  if (a === null && b === null) return true
  if (a === null || b === null) return false
  return Math.abs(a - b) < 1e-9
}

interface DiffRow { name: string; displayName: string; before: number | null; after: number | null; unit: string; changed: boolean }

const rows = computed<DiffRow[]>(() => {
  const names = new Set<string>([...beforeMap.value.keys(), ...afterMap.value.keys()])
  const list: DiffRow[] = []
  for (const name of names) {
    const b = beforeMap.value.get(name)
    const a = afterMap.value.get(name)
    const before = b?.value ?? null
    const after = a?.value ?? null
    const displayName = nutrientLabel(name)
    list.push({
      name, displayName, before, after,
      unit: a?.unit || b?.unit || '',
      changed: hasBeforeData.value && !sameNum(before, after),
    })
  }
  return list.sort((x, y) => Number(y.changed) - Number(x.changed) || x.displayName.localeCompare(y.displayName))
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
          <td>{{ row.displayName }}</td>
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
    <div v-else-if="isClearOp" class="text-caption text-medium-emphasis">
      <v-icon size="small" color="warning">mdi-alert</v-icon>
      将清空所有营养数据
    </div>
    <div v-else class="text-caption text-medium-emphasis">暂无营养素数据</div>
  </div>
</template>

<style scoped>
.nutrition-diff-table .nut-changed { background: rgba(255, 193, 7, 0.12); }
</style>
