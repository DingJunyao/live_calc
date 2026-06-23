<template>
  <v-card elevation="0" class="price-trend-chart">
    <v-card-title class="d-flex align-center flex-wrap pb-2">
      <v-icon start :color="iconColor">{{ icon }}</v-icon>
      {{ title }}
      <v-spacer />
      <v-btn-toggle
        v-model="selectedFilter"
        mandatory
        density="compact"
        variant="outlined"
        divided
        class="filter-buttons"
      >
        <v-btn
          v-for="filter in filters"
          :key="filter.value"
          :value="filter.value"
          size="small"
        >
          {{ filter.label }}
        </v-btn>
      </v-btn-toggle>
    </v-card-title>
    <v-divider />

    <div class="chart-area" style="position: relative; min-height: 300px">
      <!-- 加载中覆盖层（不销毁图表 DOM） -->
      <div
        v-if="loading"
        class="d-flex align-center justify-center"
        style="position: absolute; inset: 0; z-index: 1; background: rgba(var(--v-theme-surface), 0.8);"
      >
        <v-progress-circular indeterminate color="primary" size="48" />
      </div>

      <!-- 无数据（仅在非加载且无数据时显示） -->
      <div
        v-if="!loading && (!chartData || chartData.length === 0)"
        class="text-center py-12"
      >
        <v-icon size="64" color="medium-emphasis">mdi-chart-line</v-icon>
        <div class="text-body-1 text-medium-emphasis mt-4">{{ emptyText }}</div>
      </div>

      <!-- 图表（一旦有数据就始终渲染，DOM 不被销毁） -->
      <template v-if="hasEverHadData || (chartData && chartData.length > 0)">

        <div ref="chartRef" class="chart-container"></div>
      </template>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'
import { UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

// 注册 ECharts 组件
echarts.use([
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  UniversalTransition,
  CanvasRenderer
])

interface DataPoint {
  date: string
  min: number
  max: number
  avg: number
  count?: number
}

const props = withDefaults(defineProps<{
  title?: string
  icon?: string
  iconColor?: string
  unit?: string
  emptyText?: string
  data: DataPoint[]
  loading?: boolean
  color?: string
}>(), {
  title: '价格趋势',
  icon: 'mdi-chart-line',
  iconColor: 'primary',
  unit: '',
  emptyText: '暂无数据',
  loading: false,
  color: '#42b883'
})

const emit = defineEmits<{
  'filter-change': [filter: 'week' | 'month' | 'quarter' | 'year' | 'all']
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// 是否曾经有过数据（一旦为 true，图表 DOM 不再销毁）
const hasEverHadData = ref(false)

const selectedFilter = ref<'week' | 'month' | 'quarter' | 'year' | 'all'>('month')

const filters = [
  { label: '周', value: 'week' as const },
  { label: '月', value: 'month' as const },
  { label: '季', value: 'quarter' as const },
  { label: '年', value: 'year' as const },
  { label: '全部', value: 'all' as const }
]

// 单位后缀
const unitSuffix = computed(() => props.unit ? `/${props.unit}` : '')

// 过滤数据
const chartData = computed(() => {
  if (!props.data || props.data.length === 0) return []

  // 「全部」区间：不按时间窗口切片，返回全部数据（仅排序）
  if (selectedFilter.value === 'all') {
    return [...props.data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  }

  const now = new Date()
  const startDate = new Date(now.getTime())

  switch (selectedFilter.value) {
    case 'week':
      startDate.setDate(startDate.getDate() - 7)
      break
    case 'month':
      startDate.setMonth(startDate.getMonth() - 1)
      break
    case 'quarter':
      startDate.setMonth(startDate.getMonth() - 3)
      break
    case 'year':
      startDate.setFullYear(startDate.getFullYear() - 1)
      break
  }

  return props.data
    .filter(d => new Date(d.date) >= startDate)
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
})

// 监听筛选变化
watch(selectedFilter, (newFilter) => {
  emit('filter-change', newFilter)
  nextTick(() => {
    if (chartData.value.length > 0 && !chart) {
      initChart()
    } else {
      updateChart()
    }
  })
})

// 初始化图表
function initChart() {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)
  updateChart()

  window.addEventListener('resize', handleResize)
}

// 更新图表
function updateChart() {
  if (!chart) return

  // 如果没有数据，清空图表
  if (chartData.value.length === 0) {
    chart.clear()
    return
  }

  const data = chartData.value
  const minValue = Math.min(...data.map(d => d.min))
  const base = Math.min(0, minValue - 0.1)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        animation: false,
        label: {
          backgroundColor: props.color,
          borderColor: props.color,
          borderWidth: 1,
          color: '#fff'
        }
      },
      formatter: (params: any) => {
        const dateIndex = params[2]?.dataIndex ?? -1
        if (dateIndex < 0 || dateIndex >= data.length) return ''

        const item = data[dateIndex]
        const dateObj = new Date(item.date)
        const dateStr = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}-${String(dateObj.getDate()).padStart(2, '0')}`

        return `
          <div style="padding: 8px 12px;">
            <div style="font-weight: 600; margin-bottom: 8px;">${dateStr}</div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: ${props.color};"></span>
              <span>平均: ¥${item.avg.toFixed(2)}${unitSuffix.value}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
              <span style="display: inline-block; width: 12px; height: 12px; background-color: ${props.color}33; border-radius: 2px;"></span>
              <span>范围: ¥${item.min.toFixed(2)} - ¥${item.max.toFixed(2)}${unitSuffix.value}</span>
            </div>
            ${item.count ? `<div style="margin-top: 4px; color: #999; font-size: 12px;">记录数: ${item.count}</div>` : ''}
          </div>
        `
      }
    },
    grid: {
      left: '5%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date),
      boundaryGap: false,
      axisLabel: {
        formatter: (value: string) => {
          const parts = value.split('-')
          if (parts.length === 3) {
            return `${parts[1]}/${parts[2]}`
          }
          return value
        }
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value: number) => `¥${value.toFixed(2)}`
      },
      splitLine: {
        lineStyle: {
          type: 'dashed',
          color: '#e5e5e5'
        }
      },
      axisPointer: {
        label: {
          formatter: (params: any) => {
            return `¥${params.value.toFixed(2)}${unitSuffix.value}`
          }
        }
      }
    },
    series: [
      // 下限线（透明，用于堆叠）
      {
        name: 'L',
        type: 'line',
        data: data.map(d => d.min - base),
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        symbol: 'none',
        showSymbol: false
      },
      // 上限区域（置信区间带）
      {
        name: 'U',
        type: 'line',
        data: data.map(d => d.max - d.min),
        lineStyle: { opacity: 0 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: `${props.color}66` },
              { offset: 1, color: `${props.color}1a` }
            ]
          }
        },
        stack: 'confidence-band',
        symbol: 'none',
        showSymbol: false
      },
      // 平均值线
      {
        name: '平均',
        type: 'line',
        data: data.map(d => d.avg),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: props.color,
          width: 2.5
        },
        itemStyle: {
          color: props.color,
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          scale: true,
          itemStyle: {
            color: props.color,
            borderColor: '#fff',
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: `${props.color}80`
          }
        }
      }
    ]
  }

  chart.setOption(option)
}

// 响应式调整
function handleResize() {
  chart?.resize()
}

// 监听数据变化（图表 DOM 不再被销毁，只需更新或首次初始化）
watch(() => props.data, (newData) => {
  if (newData?.length) {
    if (!hasEverHadData.value) hasEverHadData.value = true
    nextTick(() => {
      if (!chart) {
        initChart()
      } else {
        updateChart()
      }
    })
  }
}, { deep: true })

// loading 结束后只需调整尺寸，无需重建图表（DOM 未被销毁）
watch(() => props.loading, () => {
  if (!props.loading && chart) {
    nextTick(() => {
      chart.resize()
      updateChart()
    })
  }
})

// 生命周期
onMounted(() => {
  nextTick(initChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.price-trend-chart {
  margin: 0;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.filter-buttons {
  flex-shrink: 0;
}

/* 移动端适配 */
@media (max-width: 600px) {
  .chart-container {
    height: 250px;
  }

  .filter-buttons {
    margin-top: 8px;
    width: 100%;
  }
}
</style>
