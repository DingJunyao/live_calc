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
  defaultUnit?: string
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

// 检查日期是否有效
function isValidDate(date: Date): boolean {
  return !isNaN(date.getTime())
}

// 按日期聚合价格数据，计算每日的最小值、最大值和平均值
function aggregateDailyPrices(records: PriceRecord[]) {
  const dailyMap = new Map<string, number[]>()

  // 将记录按日期分组
  for (const record of records) {
    if (!record.recorded_at) {
      console.warn('PriceRecord 缺少 recorded_at 字段:', record)
      continue
    }

    const date = new Date(record.recorded_at)

    // 检查日期是否有效
    if (!isValidDate(date)) {
      console.warn('无效的日期格式:', record.recorded_at, record)
      continue
    }

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const dateKey = `${year}-${month}-${day}`

    // 计算单价（价格/数量）
    // 使用原始录入的数据，避免标准化后的单位转换导致价格计算错误
    const unitPrice = record.original_quantity > 0
      ? record.price / record.original_quantity
      : record.price

    if (!dailyMap.has(dateKey)) {
      dailyMap.set(dateKey, [])
    }
    dailyMap.get(dateKey)!.push(unitPrice)
  }

  // 计算每日统计值并按日期排序
  const dailyData = Array.from(dailyMap.entries())
    .map(([dateKey, prices]) => {
      // 检查 prices 数组有效性
      if (!prices || prices.length === 0) {
        return {
          date: dateKey,
          dateObj: new Date(`${dateKey}T00:00:00`),
          min: 0,
          max: 0,
          avg: 0,
          count: 0
        }
      }

      // 转换为数字数组，过滤无效值
      const numericPrices = prices.map(p => Number(p)).filter(p => !isNaN(p) && p !== null && p !== undefined)

      if (numericPrices.length === 0) {
        return {
          date: dateKey,
          dateObj: new Date(`${dateKey}T00:00:00`),
          min: 0,
          max: 0,
          avg: 0,
          count: prices.length
        }
      }

      const sortedPrices = numericPrices.sort((a, b) => a - b)
      const minPrice = sortedPrices[0]
      const maxPrice = sortedPrices[sortedPrices.length - 1]

      // 计算平均值
      const sum = sortedPrices.reduce((acc, p) => acc + p, 0)
      const avgPrice = sum / sortedPrices.length

      // 调试输出
      if (isNaN(avgPrice)) {
        console.error('计算平均值时出现 NaN:', { dateKey, prices, numericPrices, minPrice, maxPrice, sum, avgPrice })
      }

      return {
        date: dateKey,
        dateObj: new Date(`${dateKey}T00:00:00`),
        min: minPrice,
        max: maxPrice,
        avg: avgPrice,
        count: prices.length
      }
    })
    .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime())

  return dailyData
}

// 更新图表数据
function updateChart() {
  if (!chart) return

  // 聚合每日价格数据
  const dailyData = aggregateDailyPrices(props.records)

  if (dailyData.length === 0) {
    chart.setOption({
      series: []
    })
    return
  }

  // 获取实际使用的单位（从第一条有效记录的 original_unit）
  const actualUnit = props.records.length > 0 && props.records[0]?.original_unit
    ? props.records[0].original_unit
    : ''

  // 找到最小价格作为 base
  const minPriceInDataset = Math.min(...dailyData.map(d => d.min))
  const base = Math.min(0, minPriceInDataset - 0.1)

  // 调试日志
  console.log('Daily Price Data:', dailyData)
  console.log('Min price in dataset:', minPriceInDataset)
  console.log('Base value:', base)
  console.log('Actual unit:', actualUnit)

  const option: EChartsOption = {
    title: {
      text: `价格趋势${actualUnit ? `（${actualUnit}）` : ''}`,
      textStyle: {
        fontSize: 16,
        fontWeight: 600
      },
      left: 0
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        animation: false,
        label: {
          backgroundColor: '#42b883',
          borderColor: '#42b883',
          borderWidth: 1,
          color: '#fff'
        }
      },
      formatter: (params: any) => {
        const dateIndex = params[2]?.dataIndex ?? -1
        if (dateIndex < 0 || dateIndex >= dailyData.length) return ''
        const data = dailyData[dateIndex]
        const dateStr = data.dateObj.toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        })

        return `
          <div style="padding: 8px 12px;">
            <div style="font-weight: 600; margin-bottom: 8px;">${dateStr}</div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #42b883;"></span>
              <span>平均价格: ¥${data.avg.toFixed(2)}/${actualUnit}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
              <span style="display: inline-block; width: 12px; height: 12px; background-color: rgba(66, 184, 131, 0.3); border-radius: 2px;"></span>
              <span>价格范围: ¥${data.min.toFixed(2)} - ¥${data.max.toFixed(2)}/${actualUnit}</span>
            </div>
            <div style="margin-top: 4px; color: #999; font-size: 12px;">记录数: ${data.count}</div>
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
      data: dailyData.map(d => d.date),
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
            const unit = actualUnit ? `/${actualUnit}` : ''
            return `¥${params.value.toFixed(2)}${unit}`
          }
        }
      }
    },
    series: [
      // L 系列：下限
      {
        name: 'L',
        type: 'line',
        data: dailyData.map(d => d.min - base),
        lineStyle: {
          opacity: 0
        },
        stack: 'confidence-band',
        symbol: 'none',
        showSymbol: false
      },
      // U 系列：上限（使用 stack 堆叠，areaStyle 绘制范围带）
      {
        name: 'U',
        type: 'line',
        data: dailyData.map(d => d.max - d.min),
        lineStyle: {
          opacity: 0
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(66, 184, 131, 0.4)' },
              { offset: 1, color: 'rgba(66, 184, 131, 0.1)' }
            ]
          }
        },
        stack: 'confidence-band',
        symbol: 'none',
        showSymbol: false
      },
      // 平均价格线
      {
        name: '平均价格',
        type: 'line',
        data: dailyData.map(d => d.avg),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#42b883',
          width: 2.5
        },
        itemStyle: {
          color: '#42b883',
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          scale: true,
          itemStyle: {
            color: '#42b883',
            borderColor: '#fff',
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: 'rgba(66, 184, 131, 0.5)'
          }
        }
      }
    ]
  }

  // 调试：输出 series 数据
  console.log('L series data:', dailyData.map(d => d.min - base))
  console.log('U series data:', dailyData.map(d => d.max - d.min))
  console.log('Avg series data:', dailyData.map(d => d.avg))
  console.log('X axis data:', dailyData.map(d => d.date))

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

// 监听默认单位变化
watch(() => props.defaultUnit, () => {
  console.log('PriceChartSection - defaultUnit 变化:', props.defaultUnit)
  updateChart()
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
