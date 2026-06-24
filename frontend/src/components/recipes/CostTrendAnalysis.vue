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
      <!-- 加载中覆盖层 -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate size="32" />
      </div>
      <div v-else-if="!chartData.length" class="text-center py-8 text-medium-emphasis">
        <v-icon size="48" color="medium-emphasis">mdi-chart-line</v-icon>
        <div class="text-body-2 mt-2">暂无成本趋势数据</div>
      </div>
      <div v-show="!loading && chartData.length">
        <div class="trend-layout">
          <div ref="chartRef" class="trend-chart" style="flex:1;min-height:300px" />
          <div class="ingredient-tags">
            <div class="text-caption text-medium-emphasis mb-2">图例（点击高亮）</div>
            <v-btn
              v-for="(item, i) in breakdownIngredients"
              :key="i"
              size="small"
              variant="tonal"
              class="mb-1"
              :color="item.color"
              :class="{ 'font-weight-bold': selectedIngredientIndex === i }"
              @click="toggleIngredientHighlight(i)"
              block
            >
              <template #prepend>
                <v-icon size="small" :color="item.color">mdi-circle</v-icon>
              </template>
              {{ item.name }}
            </v-btn>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getIngredientColor } from '@/utils/ingredientColors'

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

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const filters = [
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '季', value: 'quarter' },
  { label: '年', value: 'year' },
  { label: '全部', value: 'all' },
]
const selectedFilter = ref('quarter')

const selectedIngredientIndex = ref<number | null>(null)

const chartData = computed(() => props.costHistory || [])

// 从 breakdown 数据中提取所有食材及其颜色映射
const breakdownIngredients = computed(() => {
  // 从所有日期的 breakdown 中收集唯一食材
  const seen = new Map<number, { name: string; maxCost: number }>()
  for (const day of chartData.value) {
    for (const bi of (day.breakdown || [])) {
      const existing = seen.get(bi.ingredient_id)
      if (!existing || bi.cost > existing.maxCost) {
        seen.set(bi.ingredient_id, { name: bi.ingredient_name, maxCost: bi.cost })
      }
    }
  }

  if (seen.size > 0) {
    return Array.from(seen.entries()).map(([id]) => ({
      name: seen.get(id)!.name,
      color: getIngredientColor(id),
      ingredientId: id,
      percent: '',
    }))
  }

  // 如果没有 breakdown 数据，回退到 costBreakdown（按成本降序排列后取前 12）
  if (!props.costBreakdown?.length) return []
  const total = props.costBreakdown.reduce((s: number, b: any) => s + (parseFloat(b.cost) || 0), 0)
  const sorted = [...props.costBreakdown].sort((a, b) => (parseFloat(b.cost) || 0) - (parseFloat(a.cost) || 0))
  return sorted.slice(0, 12).map((b: any) => ({
    name: b.ingredient_name || '未知食材',
    color: getIngredientColor(b.ingredient_id),
    ingredientId: b.ingredient_id,
    percent: total > 0 ? `${Math.round((parseFloat(b.cost) || 0) / total * 100)}%` : '',
  }))
})

// 检查是否有 breakdown 数据
const hasBreakdown = computed(() => {
  return chartData.value.some((d: any) => d.breakdown?.length)
})

function renderTrendChart() {
  if (!chartRef.value || !chartData.value.length) return

  // 如果实例已被销毁（如 DOM 被重建），重新初始化
  if (!chartInstance || chartInstance.isDisposed()) {
    chartInstance = echarts.init(chartRef.value)
  }

  const dates = chartData.value.map((d: any) => d.date || '')

  if (hasBreakdown.value) {
    // ========== 堆叠面积图 ==========
    const ingMap = new Map<number, { name: string; color: string; data: number[] }>()
    for (const bi of breakdownIngredients.value) {
      ingMap.set(bi.ingredientId, {
        name: bi.name,
        color: bi.color,
        data: new Array(dates.length).fill(0),
      })
    }

    // 填数据
    for (let di = 0; di < chartData.value.length; di++) {
      const day = chartData.value[di]
      for (const bi of (day.breakdown || [])) {
        const entry = ingMap.get(bi.ingredient_id)
        if (entry) {
          entry.data[di] = bi.cost || 0
        }
      }
    }

    const isHighlighted = selectedIngredientIndex.value !== null
    const series: any[] = []
    for (const [, entry] of ingMap) {
      const opacity = isHighlighted
        ? 0.15  // 非高亮食材变淡
        : 0.85
      series.push({
        name: entry.name,
        type: 'line',
        stack: 'total',
        data: entry.data,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: entry.color },
        itemStyle: { color: entry.color },
        areaStyle: {
          color: entry.color,
          opacity,
        },
        emphasis: {
          focus: 'series',
          areaStyle: { opacity: 1 },
        },
      })
    }

    // 高亮选中的食材
    if (isHighlighted && selectedIngredientIndex.value! < series.length) {
      const hi = selectedIngredientIndex.value!
      series[hi].areaStyle.opacity = 0.95
      series[hi].lineStyle.width = 2
      series[hi].z = 10
    }

    chartInstance.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          const date = params[0]?.axisValue || ''
          let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
          let total = 0
          for (const p of params) {
            if (p.value > 0) {
              html += `<div style="display:flex;align-items:center;gap:4px">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
                ${p.seriesName}: ¥${p.value.toFixed(2)}
              </div>`
              total += p.value
            }
          }
          html += `<div style="border-top:1px solid #ddd;margin-top:4px;padding-top:2px;font-weight:600">
            合计: ¥${total.toFixed(2)}
          </div>`
          return html
        },
      },
      legend: { show: false },
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
      series,
    }, true)
  } else {
    // ========== 回退：原有折线+区间图（无 breakdown 数据时） ==========
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
}

function toggleIngredientHighlight(index: number) {
  if (selectedIngredientIndex.value === index) {
    selectedIngredientIndex.value = null
  } else {
    selectedIngredientIndex.value = index
  }
  // 重新渲染堆叠图（高亮或取消高亮选中食材）
  renderTrendChart()
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
}))
onUnmounted(() => {
  window.removeEventListener('resize', () => {
    chartInstance?.resize()
  })
  chartInstance?.dispose()
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
