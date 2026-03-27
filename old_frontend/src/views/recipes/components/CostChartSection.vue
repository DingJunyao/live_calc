<template>
  <div class="cost-chart-section">
    <div class="section-header">
      <h2 class="section-title">成本趋势</h2>
    </div>

    <div v-if="records.length === 0" class="no-data">
      <i class="mdi mdi-chart-line"></i>
      <p>暂无成本记录</p>
    </div>

    <div v-else ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'
import { UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import type { CostRangeRecord } from '@/api/client'

// 注册必需的组件
echarts.use([LineChart, TitleComponent, TooltipComponent, GridComponent, UniversalTransition, CanvasRenderer])

const props = defineProps<{
  records: CostRangeRecord[]
}>()

const chartRef = ref<HTMLElement>()
let chart: any = null

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

  // 直接使用后端返回的数据，无需聚合计算
  const dailyData = props.records.map(record => ({
    date: record.date,
    dateObj: new Date(`${record.date}T00:00:00`),
    min: record.min_cost,
    max: record.max_cost,
    avg: record.avg_cost,
    count: 1  // 固定为1，因为是API已计算好的区间
  }))

  if (dailyData.length === 0) {
    chart.setOption({
      series: []
    })
    return
  }

  const minCostInDataset = Math.min(...dailyData.map(d => d.min))
  const base = Math.min(0, minCostInDataset - 0.1)

  const option: EChartsOption = {
    title: {
      text: '成本趋势（元）',
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
              <span>平均成本: ¥${data.avg.toFixed(2)}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
              <span style="display: inline-block; width: 12px; height: 12px; background-color: rgba(66, 184, 131, 0.3); border-radius: 2px;"></span>
              <span>成本范围: ¥${data.min.toFixed(2)} - ¥${data.max.toFixed(2)}</span>
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
            return `¥${params.value.toFixed(2)}`
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
      // 平均成本线
      {
        name: '平均成本',
        type: 'line',
        data: dailyData.map(d => d.avg),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#66b883',
          width: 2.5
        },
        itemStyle: {
          color: '#66b883',
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          scale: true,
          itemStyle: {
            color: '#66b883',
            borderColor: '#fff',
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: 'rgba(102, 184, 131, 0.5)'
          }
        }
      }
    ]
  }

  chart.setOption(option)
}

// 处理窗口大小调整
function handleResize() {
  chart?.resize()
}

// 监听数据变化
watch(() => props.records, () => {
  updateChart()
}, { deep: true })

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
.cost-chart-section {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  padding: 20px;
}

.section-header {
  margin-bottom: 20px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
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
  .cost-chart-section {
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
