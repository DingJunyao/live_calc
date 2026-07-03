<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { previewUsdaNutrients } from '@/api/usda'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

interface NutrientEntry { value: number | null; unit: string }

const NUTRIENT_LABELS: Record<string, string> = {
  // 宏观
  energy_kcal: '能量', energy: '能量', protein: '蛋白质', total_fat: '脂肪', fat: '脂肪',
  carbohydrate: '碳水化合物', fiber: '膳食纤维', sugar: '糖', total_sugars: '总糖',
  starch: '淀粉', water: '水分', alcohol: '酒精', alcohol_ethyl: '酒精', ash: '灰分',
  // 脂肪细分
  saturated: '饱和脂肪酸', saturated_fat: '饱和脂肪酸',
  monounsaturated: '单不饱和脂肪酸', monounsaturated_fat: '单不饱和脂肪酸',
  polyunsaturated: '多不饱和脂肪酸', polyunsaturated_fat: '多不饱和脂肪酸',
  trans: '反式脂肪酸', trans_fat: '反式脂肪酸', cholesterol: '胆固醇',
  // 脂肪酸谱
  'sfa_4:0': 'SFA 4:0 (丁酸)', 'sfa_6:0': 'SFA 6:0 (己酸)', 'sfa_8:0': 'SFA 8:0 (辛酸)',
  'sfa_10:0': 'SFA 10:0 (癸酸)', 'sfa_12:0': 'SFA 12:0 (月桂酸)',
  'sfa_14:0': 'SFA 14:0 (豆蔻酸)', 'sfa_16:0': 'SFA 16:0 (棕榈酸)',
  'sfa_18:0': 'SFA 18:0 (硬脂酸)',
  'mufa_16:1': 'MUFA 16:1 (棕榈油酸)', 'mufa_18:1': 'MUFA 18:1 (油酸)',
  'mufa_20:1': 'MUFA 20:1 (花生一烯酸)', 'mufa_22:1': 'MUFA 22:1 (芥酸)',
  'pufa_18:2': 'PUFA 18:2 (亚油酸)', 'pufa_18:3': 'PUFA 18:3 (α-亚麻酸)',
  'pufa_18:4': 'PUFA 18:4 (十八碳四烯酸)', 'pufa_20:4': 'PUFA 20:4 (花生四烯酸)',
  'pufa_20:5_n_3_epa': 'PUFA 20:5 n-3 (EPA)',
  'pufa_22:5_n_3_dpa': 'PUFA 22:5 n-3 (DPA)',
  'pufa_22:6_n_3_dha': 'PUFA 22:6 n-3 (DHA)',
  // 维生素
  vitamin_a: '维生素A', vitamin_a_rae: '维生素A (RAE)',
  vitamin_c: '维生素C', vitamin_d: '维生素D', vitamin_e: '维生素E',
  vitamin_k: '维生素K',
  thiamin: '维生素B1', vitamin_b1: '维生素B1',
  riboflavin: '维生素B2', vitamin_b2: '维生素B2',
  niacin: '烟酸',
  b6: '维生素B6', vitamin_b6: '维生素B6',
  b12: '维生素B12', vitamin_b12: '维生素B12',
  folate: '叶酸', folate_food: '叶酸（食物）', folate_dfe: '叶酸（DFE）',
  folic_acid: '叶酸（合成）',
  pantothenic_acid: '泛酸', choline: '胆碱', choline_total: '总胆碱',
  betaine: '甜菜碱',
  vitamin_e_added: '维生素E（添加）', vitamin_b_12_added: '维生素B12（添加）',
  retinol: '视黄醇',
  carotene_beta: 'β-胡萝卜素', carotene_alpha: 'α-胡萝卜素',
  cryptoxanthin_beta: 'β-隐黄素',
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
  caffeine: '咖啡因', theobromine: '可可碱',
  lutein_plus_zeaxanthin: '叶黄素+玉米黄质',
  lycopene: '番茄红素',
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
  // 先处理 all_nutrients（用英文 key 做唯一标识），跳过 nutrient_details（内容同 all）
  const all = source.all_nutrients
  if (all && typeof all === 'object') {
    for (const [key, entry] of Object.entries(all)) {
      const e = entry as any
      if (e && typeof e === 'object') {
        const k = e.key || key
        if (!out.has(k)) {
          out.set(k, { value: numOrNull(e.value), unit: e.unit || '' })
        }
      }
    }
  }
  // core_nutrients 用 e.key 做键（不另加中文名行），与 all_nutrients 去重
  const core = source.core_nutrients
  if (core && typeof core === 'object') {
    for (const [name, entry] of Object.entries(core)) {
      const e = entry as any
      if (e && typeof e === 'object') {
        const k = e.key || name
        if (!out.has(k)) {
          out.set(k, { value: numOrNull(e.value), unit: e.unit || '' })
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
  if (a === b) return true
  // 容忍表单精度丢失：四舍五入到 2 位小数后比较（输入框一般为 2 位小数）
  // USDA 原始值 0.037/0.028 经表单回来变 0.04/0.03，应视为未变更
  return Math.round(a * 100) === Math.round(b * 100)
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
    const inBefore = beforeMap.value.has(name)
    const inAfter = afterMap.value.has(name)
    // 只有以下情况才算「已变更」：
    //   - 用户提交了新值（afterMap 有）且值不同
    //   - 纯新增（beforeMap 无）
    // 仅 beforeMap 有的条目（用户未提交）不算变更
    const changed = hasBeforeData.value && inAfter && (!inBefore || !sameNum(before, after))
    list.push({
      name, displayName, before, after,
      unit: a?.unit || b?.unit || '',
      changed,
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
