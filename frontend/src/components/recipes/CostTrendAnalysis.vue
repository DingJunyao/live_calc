<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="tertiary">mdi-chart-timeline-variant</v-icon>
      成本趋势
      <v-spacer />
      <v-btn-toggle v-model="selectedFilter" mandatory density="compact" variant="outlined" divided>
        <v-btn v-for="f in filters" :key="f.value" :value="f.value" size="small">
          {{ f.label }}
        </v-btn>
      </v-btn-toggle>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate size="32" />
      </div>
      <div v-else-if="!chartData.length" class="text-center py-8 text-medium-emphasis">
        <v-icon size="48" color="medium-emphasis">mdi-chart-line</v-icon>
        <div class="text-body-2 mt-2">暂无成本趋势数据</div>
      </div>
      <template v-else>
        <div class="trend-layout">
          <div ref="chartRef" class="trend-chart" style="flex:1;min-height:260px" />
          <div class="ingredient-tags">
            <div class="text-caption text-medium-emphasis mb-2">点击查看单食材趋势</div>
            <v-btn
              v-for="(item, i) in ingredientItems"
              :key="i"
              size="small"
              variant="tonal"
              class="mb-1"
              :color="item.color"
              :class="{ 'font-weight-bold': selectedIngredientIndex === i }"
              @click="selectIngredient(i)"
              block
            >
              <template #prepend>
                <v-icon size="small" :color="item.color">mdi-circle</v-icon>
              </template>
              {{ item.name }}
              <template #append>
                <span class="text-caption text-medium-emphasis">{{ item.percent }}</span>
              </template>
            </v-btn>
          </div>
        </div>
        <div v-if="selectedIngredientName" class="mt-2 pa-3 bg-surface-variant rounded">
          <div class="text-body-2 font-weight-medium mb-1">
            {{ selectedIngredientName }} — 价格趋势
          </div>
          <div v-if="loadingIngredientTrend" class="text-center py-4">
            <v-progress-circular indeterminate size="20" />
          </div>
          <div v-else ref="ingredientChartRef" class="ingredient-trend-chart" style="height:100px" />
        </div>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { api } from '@/api/client'

const props = defineProps<{
  recipeId: number
  costHistory: any[]
  ingredients?: any[]
  costBreakdown?: any[] | null
  loading?: boolean
  servingRatio?: number
}>()

const emit = defineEmits<{
  'filter-change': [filter: string]
}>()

const COLOR_PALETTE = [
  '#ff9800', '#4caf50', '#2196f3', '#9c27b0',
  '#f44336', '#00bcd4', '#ff5722', '#607d8b',
]

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null
const ingredientChartRef = ref<HTMLElement | null>(null)
let ingredientChartInstance: echarts.ECharts | null = null

const filters = [
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '季', value: 'quarter' },
  { label: '年', value: 'year' },
  { label: '全部', value: 'all' },
]
const selectedFilter = ref('quarter')

const selectedIngredientIndex = ref<number | null>(null)
const selectedIngredientName = ref('')
const ingredientTrendData = ref<any[]>([])
const loadingIngredientTrend = ref(false)

const ingredientItems = computed(() => {
  if (!props.costBreakdown?.length) return []
  const total = props.costBreakdown.reduce((s: number, b: any) => s + (parseFloat(b.cost) || 0), 0)
  return props.costBreakdown.slice(0, 8).map((b: any, i: number) => ({
    name: b.ingredient_name || `食材${i + 1}`,
    percent: total > 0 ? `${Math.round((parseFloat(b.cost) || 0) / total * 100)}%` : '',
    color: COLOR_PALETTE[i % COLOR_PALETTE.length],
    ingredientId: b.ingredient_id,
  }))
})

const chartData = computed(() => props.costHistory || [])

function renderTrendChart() {
  if (!chartRef.value || !chartData.value.length) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const dates = chartData.value.map((d: any) => d.date || '')
  const avgValues = chartData.value.map((d: any) => d.avg_cost || 0)
  const minValues = chartData.value.map((d: any) => d.min_cost || 0)
  const maxValues = chartData.value.map((d: any) => d.max_cost || 0)

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        const date = params[0]?.axisValue || ''
        const avg = params.find((p: any) => p.seriesName === '平均成本')
        const minP = params.find((p: any) => p.seriesName === '最低')
        const maxP = params.find((p: any) => p.seriesName === '最高')
        return `${date}<br/>平均: ¥${avg?.value?.toFixed(2) || '-'}<br/>区间: ¥${minP?.value?.toFixed(2) || '-'} ~ ¥${maxP?.value?.toFixed(2) || '-'}`
      },
    },
    grid: { left: 50, right: 16, top: 8, bottom: 24 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 10, rotate: 30 },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '¥{value}', fontSize: 10 },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series: [
      {
        name: '最低',
        type: 'line',
        data: minValues,
        lineStyle: { width: 0 },
        symbol: 'none',
        areaStyle: { opacity: 0 },
        stack: 'total',
      },
      {
        name: '平均成本',
        type: 'line',
        data: avgValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: '#ff9800' },
        itemStyle: { color: '#ff9800' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255,152,0,0.25)' },
            { offset: 1, color: 'rgba(255,152,0,0.02)' },
          ]),
        },
      },
      {
        name: '最高',
        type: 'line',
        data: maxValues,
        lineStyle: { width: 0 },
        symbol: 'none',
        areaStyle: { opacity: 0 },
        stack: 'total',
      },
    ],
  }, true)
}

async function selectIngredient(index: number) {
  if (selectedIngredientIndex.value === index) {
    selectedIngredientIndex.value = null
    selectedIngredientName.value = ''
    ingredientTrendData.value = []
    ingredientChartInstance?.clear()
    return
  }

  selectedIngredientIndex.value = index
  const item = ingredientItems.value[index]
  if (!item) return
  selectedIngredientName.value = item.name
  loadingIngredientTrend.value = true

  try {
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - 90 * 86400000).toISOString().split('T')[0]
    const res = await api.get('/products', {
      params: {
        ingredient_id: item.ingredientId,
        start_date: startDate,
        end_date: endDate,
        limit: 500,
      },
    })

    const records = Array.isArray(res) ? res : res?.items || []
    const dateMap: Record<string, number[]> = {}
    for (const r of records) {
      const d = r.recorded_at?.split('T')[0] || r.recorded_at?.slice(0, 10)
      if (!d) continue
      if (!dateMap[d]) dateMap[d] = []
      const price = r.price ? parseFloat(r.price) : 0
      const qty = r.original_quantity ? parseFloat(r.original_quantity) : 1
      dateMap[d].push(qty > 0 ? price / qty : 0)
    }
    ingredientTrendData.value = Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, prices]) => ({
        date,
        avgPrice: prices.reduce((s, p) => s + p, 0) / prices.length,
      }))

    renderIngredientTrend()
  } catch {
    /* ignore */
  }
  loadingIngredientTrend.value = false
}

function renderIngredientTrend() {
  if (!ingredientChartRef.value || !ingredientTrendData.value.length) return

  if (!ingredientChartInstance) {
    ingredientChartInstance = echarts.init(ingredientChartRef.value)
  }

  ingredientChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 8, top: 8, bottom: 16 },
    xAxis: {
      type: 'category',
      data: ingredientTrendData.value.map(d => d.date),
      axisLabel: { fontSize: 9, rotate: 30, interval: 'auto' },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '¥{value}', fontSize: 9 },
    },
    series: [{
      type: 'line',
      data: ingredientTrendData.value.map(d => d.avgPrice),
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#ff9800' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(255,152,0,0.2)' },
          { offset: 1, color: 'rgba(255,152,0,0.02)' },
        ]),
      },
    }],
  }, true)
}

watch(selectedFilter, (val) => {
  emit('filter-change', val)
})

watch(() => [props.costHistory, props.loading], () => {
  nextTick(() => {
    if (!props.loading && chartData.value.length) renderTrendChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    if (!props.loading && chartData.value.length) renderTrendChart()
  })
})

onMounted(() => window.addEventListener('resize', () => {
  chartInstance?.resize()
  ingredientChartInstance?.resize()
}))
onUnmounted(() => {
  window.removeEventListener('resize', () => {
    chartInstance?.resize()
    ingredientChartInstance?.resize()
  })
  chartInstance?.dispose()
  ingredientChartInstance?.dispose()
})
</script>

<style scoped>
.trend-layout {
  display: flex;
  gap: 12px;
}
.ingredient-tags {
  width: 120px;
  flex-shrink: 0;
}
@media (max-width: 959px) {
  .trend-layout {
    flex-direction: column;
  }
  .ingredient-tags {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .ingredient-tags .v-btn {
    flex: 0 0 auto;
    min-width: 0;
  }
}
</style>
