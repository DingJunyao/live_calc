<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="success">mdi-food-apple-outline</v-icon>
      营养贡献溯源
      <v-spacer />
      <v-btn-toggle v-model="showAll" mandatory density="compact">
        <v-btn :value="false" size="small">NRV 指标</v-btn>
        <v-btn :value="true" size="small">全部</v-btn>
      </v-btn-toggle>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate size="32" />
      </div>
      <div v-else-if="!displayNutrients.length" class="text-center py-8 text-medium-emphasis">
        <v-icon size="48" color="medium-emphasis">mdi-food-apple-outline</v-icon>
        <div class="text-body-2 mt-2">暂无营养数据</div>
      </div>
      <div v-else class="nutrition-grid">
        <div
          v-for="nutrient in displayNutrients"
          :key="nutrient.key"
          class="nutrition-donut-card"
        >
          <div class="text-body-2 font-weight-medium text-center mb-1">{{ nutrient.label }}</div>
          <div :ref="el => setChartRef(nutrient.key, el as HTMLElement)" class="mini-donut" />
          <div class="text-caption text-center text-medium-emphasis mt-1">{{ nutrient.totalText }}</div>
          <div class="text-caption text-center text-disabled">{{ nutrient.topContributors }}</div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  nutritionData?: any | null
  loading?: boolean
}>()

const COLOR_PALETTE = [
  '#ff9800', '#4caf50', '#2196f3', '#9c27b0',
  '#f44336', '#00bcd4', '#ff5722', '#607d8b',
]

const showAll = ref(false)
const chartRefs = new Map<string, HTMLElement>()
const chartInstances = new Map<string, echarts.ECharts>()

function setChartRef(key: string, el: HTMLElement | null) {
  if (el) chartRefs.set(key, el)
}

const NRV_KEYS = new Set([
  'energy', 'protein', 'fat', 'carbohydrate', 'fiber',
  'calcium', 'iron', 'sodium', 'potassium',
  'vitamin_a_rae', 'vitamin_c', 'vitamin_b1', 'vitamin_b2',
  'vitamin_b12', 'vitamin_d', 'vitamin_e', 'vitamin_k',
])

const NRV_LABELS: Record<string, string> = {
  energy: '能量', protein: '蛋白质', fat: '脂肪', carbohydrate: '碳水化合物',
  fiber: '膳食纤维', calcium: '钙', iron: '铁', sodium: '钠', potassium: '钾',
  vitamin_a_rae: '维生素A', vitamin_c: '维生素C', vitamin_b1: '维生素B1',
  vitamin_b2: '维生素B2', vitamin_b12: '维生素B12', vitamin_d: '维生素D',
  vitamin_e: '维生素E', vitamin_k: '维生素K',
}

interface NutrientDisplay {
  key: string
  label: string
  totalValue: number
  unit: string
  nrpPct: number | null
  totalText: string
  topContributors: string
  items: { name: string; value: number; color: string }[]
}

const displayNutrients = computed<NutrientDisplay[]>(() => {
  const nutrition = props.nutritionData
  if (!nutrition?.ingredient_details?.length) return []

  const perServing = nutrition.per_serving_nutrition
  if (!perServing) return []

  const allNutrients = perServing.all_nutrients || perServing.core_nutrients || {}
  const result: NutrientDisplay[] = []

  for (const [key, data] of Object.entries(allNutrients)) {
    const nData = data as any
    if (!nData || nData.value === undefined || nData.value === null) continue

    const isNrv = NRV_KEYS.has(key)
    if (!showAll.value && !isNrv) continue

    const label = NRV_LABELS[key] || nData.name_zh || key
    const totalValue = typeof nData.value === 'number' ? nData.value : parseFloat(nData.value) || 0
    const unit = nData.unit || ''
    const nrpPct = nData.nrp_pct != null ? Math.round(nData.nrp_pct) : null
    const totalText = nrpPct !== null ? `${totalValue}${unit} · NRV ${nrpPct}%` : `${totalValue}${unit}`

    const ingredientItems: { name: string; value: number; color: string }[] = []
    let colorIndex = 0
    for (const detail of nutrition.ingredient_details) {
      const contrib = detail.nutrition_contribution?.[label] || detail.nutrition_contribution?.[key]
      if (contrib && contrib.value != null && Number(contrib.value) > 0) {
        ingredientItems.push({
          name: detail.ingredient_name || `食材${colorIndex + 1}`,
          value: Number(contrib.value) || 0,
          color: COLOR_PALETTE[colorIndex % COLOR_PALETTE.length],
        })
        colorIndex++
      }
    }

    if (!ingredientItems.length) continue

    ingredientItems.sort((a, b) => b.value - a.value)
    const totalIngredientValue = ingredientItems.reduce((s, i) => s + i.value, 0)
    const top2 = ingredientItems.slice(0, 2)
    const topContributors = top2
      .map(i => `${i.name} ${Math.round((i.value / totalIngredientValue) * 100)}%`)
      .join(' · ')

    result.push({
      key,
      label,
      totalValue,
      unit,
      nrpPct,
      totalText,
      topContributors,
      items: ingredientItems,
    })
  }

  return result
})

function renderDonuts() {
  for (const nutrient of displayNutrients.value) {
    const el = chartRefs.get(nutrient.key)
    if (!el) continue

    let instance = chartInstances.get(nutrient.key)
    if (!instance) {
      instance = echarts.init(el)
      chartInstances.set(nutrient.key, instance)
    }

    const total = nutrient.items.reduce((s, i) => s + i.value, 0)

    instance.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${p.name}: ${p.value.toFixed(2)}${nutrient.unit} (${p.percent}%)`,
      },
      series: [{
        type: 'pie',
        radius: ['50%', '75%'],
        center: ['50%', '50%'],
        silent: true,
        label: { show: false },
        emphasis: { scale: false },
        itemStyle: {
          borderRadius: 2,
          borderColor: '#fff',
          borderWidth: 1,
        },
        data: nutrient.items.map(i => ({
          name: i.name,
          value: i.value,
          itemStyle: { color: i.color },
        })),
      }],
      graphic: [{
        type: 'text',
        left: 'center',
        top: '48%',
        style: {
          text: `${total.toFixed(1)}${unit === 'kcal' ? '' : unit}`,
          textAlign: 'center' as const,
          fill: '#666',
          fontSize: 11,
          fontWeight: 'bold' as const,
        },
        z: 100,
      }],
    }, true)
  }
}

watch(showAll, () => nextTick(renderDonuts))
watch(() => [props.nutritionData, props.loading], () => {
  nextTick(() => {
    if (!props.loading && displayNutrients.value.length) renderDonuts()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    if (!props.loading && displayNutrients.value.length) renderDonuts()
  })
})

onMounted(() => window.addEventListener('resize', () => {
  chartInstances.forEach(c => c.resize())
}))
onUnmounted(() => {
  window.removeEventListener('resize', () => {
    chartInstances.forEach(c => c.resize())
  })
  chartInstances.forEach(c => c.dispose())
  chartInstances.clear()
})
</script>

<style scoped>
.nutrition-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}
.nutrition-donut-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.mini-donut {
  width: 120px;
  height: 120px;
}
@media (max-width: 599px) {
  .nutrition-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .mini-donut {
    width: 100px;
    height: 100px;
  }
}
</style>
