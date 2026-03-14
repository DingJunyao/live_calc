<template>
  <div class="hierarchy-tree-section">
    <div class="section-header">
      <h2 class="section-title">层级关系</h2>
      <button @click="showAddModal = true" class="btn-add">
        <i class="mdi mdi-plus"></i> 添加关系
      </button>
    </div>

    <div v-if="!relations || (relations.parent_relations.length === 0 && relations.child_relations.length === 0)" class="no-data">
      <i class="mdi mdi-sitemap"></i>
      <p>暂无层级关系</p>
    </div>

    <div v-else ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import type { HierarchyRelations } from '../types'

defineProps<{
  relations: HierarchyRelations | null
  ingredientId: number
}>()

defineEmits<{
  'add-relation': [data: any]
  'delete-relation': [relationId: number]
  'edit-strength': [data: any]
}>()

const chartRef = ref<HTMLElement>()
const showAddModal = ref(false)
let chart: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return params.name
      }
    },
    series: [{
      type: 'tree',
      data: buildTreeData(),
      top: '10%',
      left: '10%',
      bottom: '10%',
      right: '20%',
      symbolSize: 10,
      symbol: 'circle',
      edgeShape: 'curve',
      edgeForkPosition: '63%',
      initialTreeDepth: 3,
      lineStyle: {
        color: '#ccc',
        width: 1.5
      },
      label: {
        position: 'left',
        verticalAlign: 'middle',
        align: 'right',
        fontSize: 14
      },
      leaves: {
        label: {
          position: 'right',
          verticalAlign: 'middle',
          align: 'left'
        }
      },
      expandAndCollapse: true,
      animationDuration: 550,
      animationDurationUpdate: 750
    }]
  }

  chart.setOption(option)
  window.addEventListener('resize', () => chart?.resize())
}

function buildTreeData() {
  // TODO: 实现树形数据构建
  return [{
    name: '当前食材',
    children: []
  }]
}

onMounted(() => {
  nextTick(() => {
    initChart()
  })
})

onBeforeUnmount(() => {
  chart?.dispose()
})
</script>

<style scoped>
.hierarchy-tree-section {
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
  margin-bottom: 16px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.btn-add {
  background-color: #42b883;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-add:hover {
  background-color: #3aa876;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
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

@media (max-width: 768px) {
  .hierarchy-tree-section {
    padding: 12px;
  }

  .chart-container {
    height: 300px;
  }
}
</style>
