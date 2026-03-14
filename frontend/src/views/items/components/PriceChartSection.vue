<template>
  <div class="price-chart-section">
    <div class="section-header">
      <h2 class="section-title">价格趋势</h2>
      <div class="filter-buttons">
        <button
          v-for="filter in filters"
          :key="filter.value"
          @click="$emit('filter-change', filter.value)"
          class="filter-btn"
          :class="{ active: currentFilter === filter.value }"
        >
          {{ filter.label }}
        </button>
      </div>
    </div>

    <div v-if="records.length === 0" class="no-data">
      <i class="mdi mdi-chart-line"></i>
      <p>暂无价格数据</p>
    </div>

    <div v-else ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import type { PriceRecord } from '../types'

// 注册必需的组件
echarts.use([LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, UniversalTransition, CanvasRenderer])

const props = defineProps<{
  records: PriceRecord[]
  filter: 'week' | 'month' | 'quarter' | 'year'
}>()

defineEmits<{
  'filter-change': [filter: 'week' | 'month' | 'quarter' | 'year']
}>()

const chartRef = ref<HTMLElement>()
let chart: any = null

const filters = [
  { label: '周', value: 'week' as const },
  { label: '月', value: 'month' as const },
  { label: '季', value: 'quarter' as const },
  { label: '年', value: 'year' as const }
]

const currentFilter = ref(props.filter)

// 初始化图表
function initChart() {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  updateChart()

  // 响应式调整大小
  window.addEventListener('resize', handleResize)
}

// 更新图表数据
function updateChart() {
  if (!chart) return

  // 准备数据
  const dates = props.records.map(r => r.recorded_at)
  const prices = props.records.map(r => r.price)

  const option: EChartsOption = {
    title: {
      text: '价格趋势'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        const date = new Date(param.axisValue)
        const formattedDate = date.toLocaleDateString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
        return `${formattedDate}<br/>价格: ¥${param.value}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLabel: {
        formatter: (value: number) => {
          const date = new Date(value)
          return `${date.getMonth() + 1}/${date.getDate()}`
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '¥{value}'
      },
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [{
      name: '价格',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: dates.map((date, index) => [date, prices[index]]),
      lineStyle: {
        color: '#42b883',
        width: 2
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(66, 184, 131, 0.3)' },
            { offset: 1, color: 'rgba(66, 184, 131, 0.05)' }
          ]
        }
      },
      itemStyle: {
        color: '#42b883'
      }
    }]
  }
  chart.setOption(option)
}

// 处理窗口大小调整
function handleResize() {
  chart?.resize()
}

// 监听数据和过滤器变化
watch(() => props.records, () => {
  updateChart()
}, { deep: true })

watch(() => props.filter, (newFilter) => {
  currentFilter.value = newFilter
})

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.price-chart-section {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.filter-buttons {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 6px 16px;
  border: 1px solid #e5e5e5;
  background-color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.3s;
}

.filter-btn:hover {
  border-color: #42b883;
  color: #42b883;
}

.filter-btn.active {
  background-color: #42b883;
  border-color: #42b883;
  color: white;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #999;
}

.no-data i {
  font-size: 48px;
  margin-bottom: 12px;
  color: #e5e5e5;
}

.no-data p {
  margin: 0;
  font-size: 14px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .price-chart-section {
    padding: 12px;
    margin-bottom: 16px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .section-title {
    font-size: 16px;
  }

  .filter-buttons {
    width: 100%;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .filter-btn {
    flex: 1;
    white-space: nowrap;
    padding: 6px 12px;
    font-size: 13px;
  }

  .chart-container {
    height: 250px;
  }

  .no-data {
    padding: 40px 20px;
  }

  .no-data i {
    font-size: 36px;
  }
}
</style>
