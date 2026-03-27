<template>
  <v-card>
    <v-card-title v-if="title" class="d-flex align-center pb-2">
      <v-icon v-if="icon" :start :color="iconColor">{{ icon }}</v-icon>
      {{ title }}
    </v-card-title>
    <v-divider v-if="title" />
    <v-card-text class="pa-0">
      <div ref="chartRef" class="hierarchy-chart" :style="{ height: height }"></div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, PropType } from 'vue'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption, ECharts } from 'echarts/core'

echarts.use([
  GraphChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer
])

interface HierarchyRelation {
  id: number
  parent_id: number
  parent_name: string
  child_id: number
  child_name: string
  relation_type: string
  strength: number
}

interface HierarchyData {
  parent_relations: HierarchyRelation[]
  child_relations: HierarchyRelation[]
}

interface IngredientNode {
  id: number
  name: string
  category: number // 0=当前原料, 1=相关原料
}

const props = defineProps({
  title: String,
  icon: String,
  iconColor: {
    type: String,
    default: 'primary'
  },
  ingredientId: {
    type: Number,
    required: true
  },
  ingredientName: {
    type: String,
    required: true
  },
  hierarchyData: {
    type: Object as PropType<HierarchyData | null>,
    default: null
  },
  height: {
    type: String,
    default: '400px'
  }
})

const chartRef = ref<HTMLElement | null>(null)
let chart: ECharts | null = null

// 关系类型配置
const relationTypes = {
  contains: {
    label: '包含',
    color: '#2196F3',
    lineStyle: 'solid'
  },
  fallback: {
    label: '可回退',
    color: '#FF9800',
    lineStyle: 'dashed'
  },
  substitutable: {
    label: '可替代',
    color: '#4CAF50',
    lineStyle: 'dotted'
  }
}

// 构建图表数据
const buildChartData = () => {
  if (!props.hierarchyData) return { nodes: [], links: [] }

  const nodes: Map<number, IngredientNode> = new Map()
  const links: any[] = []

  // 添加当前原料节点（中心节点）
  nodes.set(props.ingredientId, {
    id: props.ingredientId,
    name: props.ingredientName,
    category: 0
  })

  // 处理所有关系
  const allRelations = [
    ...(props.hierarchyData.parent_relations || []).map(r => ({ ...r, direction: 'in' })),
    ...(props.hierarchyData.child_relations || []).map(r => ({ ...r, direction: 'out' }))
  ]

  // 统计同一对节点之间的边数
  const edgeCounts = new Map<string, number>()
  const edgeIndices = new Map<string, number>()

  allRelations.forEach(rel => {
    const otherId = rel.direction === 'in' ? rel.parent_id : rel.child_id
    const otherName = rel.direction === 'in' ? rel.parent_name : rel.child_name

    // 添加相关节点
    if (!nodes.has(otherId)) {
      nodes.set(otherId, {
        id: otherId,
        name: otherName,
        category: 1
      })
    }

    // 根据关系类型确定边的方向和标签
    let source: number, target: number, label: string

    if (rel.relation_type === 'contains') {
      // 包含关系：parent → child
      if (rel.direction === 'in') {
        // 当前是child，显示 parent → 当前
        source = rel.parent_id
        target = props.ingredientId
        label = '包含'
      } else {
        // 当前是parent，显示 当前 → child
        source = props.ingredientId
        target = rel.child_id
        label = '包含'
      }
    } else if (rel.relation_type === 'fallback') {
      // 回退关系：child 可回退到 parent
      // 箭头指向 parent（数据来源方向）
      if (rel.direction === 'in') {
        // 当前是child，可回退到 parent
        source = props.ingredientId
        target = rel.parent_id
        label = '回退到'
      } else {
        // 当前是parent，child 可回退到当前
        source = rel.child_id
        target = props.ingredientId
        label = '回退到'
      }
    } else if (rel.relation_type === 'substitutable') {
      // 可替代关系：双向箭头
      // 始终从当前指向其他（表示可以相互替代）
      if (rel.direction === 'in') {
        source = props.ingredientId
        target = rel.parent_id
      } else {
        source = props.ingredientId
        target = rel.child_id
      }
      label = '可替代'
    } else {
      // 默认：按照数据库存储的方向
      source = rel.parent_id
      target = rel.child_id
      label = rel.relation_type
    }

    // 生成边的唯一键
    const edgeKey = `${Math.min(source, target)}-${Math.max(source, target)}-${rel.relation_type}`

    // 统计同一方向的边数
    const directionKey = `${source}-${target}`
    if (!edgeCounts.has(directionKey)) {
      edgeCounts.set(directionKey, 0)
    }
    const count = edgeCounts.get(directionKey)!
    edgeCounts.set(directionKey, count + 1)

    if (!edgeIndices.has(edgeKey)) {
      edgeIndices.set(edgeKey, 0)
    }
    const index = edgeIndices.get(edgeKey)!
    edgeIndices.set(edgeKey, index + 1)

    // 计算curveness：同一方向的边使用不同的弯曲度
    const totalEdges = edgeCounts.get(directionKey)!
    const baseCurveness = 0.2
    // 如果同一方向有多条边，分散它们的弯曲度
    let curveness = baseCurveness
    if (totalEdges > 1) {
      const offset = (index - (totalEdges - 1) / 2) * 0.15
      curveness = baseCurveness + offset
    }

    links.push({
      id: `edge-${rel.id}`, // 添加唯一ID
      source: String(source),
      target: String(target),
      name: label,
      relationType: rel.relation_type,
      strength: rel.strength,
      lineStyle: {
        color: relationTypes[rel.relation_type as keyof typeof relationTypes]?.color || '#666',
        type: relationTypes[rel.relation_type as keyof typeof relationTypes]?.lineStyle || 'solid',
        width: 2,
        curveness: curveness,
        opacity: 0.8
      },
      label: {
        show: true,
        fontSize: 11,
        formatter: label,
        color: '#666'
      },
      symbolSize: 8
    })
  })

  return {
    nodes: Array.from(nodes.values()),
    links
  }
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)
  updateChart()

  // 响应式调整大小
  const resizeObserver = new ResizeObserver(() => {
    chart?.resize()
  })
  resizeObserver.observe(chartRef.value)
}

// 更新图表
const updateChart = () => {
  if (!chart) return

  const { nodes, links } = buildChartData()

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const isCurrent = params.data.category === 0
          return `<strong>${params.data.name}</strong><br/>${isCurrent ? '当前原料' : '相关原料'}`
        } else if (params.dataType === 'edge') {
          return `<strong>${params.data.sourceName}</strong> ${params.data.name} <strong>${params.data.targetName}</strong><br/>类型: ${params.data.relationType}<br/>强度: ${params.data.strength}%`
        }
        return ''
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes.map(node => ({
          id: String(node.id),
          name: node.name,
          category: node.category,
          symbolSize: node.category === 0 ? 70 : 50,
          itemStyle: {
            color: node.category === 0 ? '#E91E63' : '#2196F3',
            borderColor: node.category === 0 ? '#fff' : '#2196F3',
            borderWidth: node.category === 0 ? 3 : 2
          },
          label: {
            show: true,
            fontSize: node.category === 0 ? 14 : 12,
            fontWeight: node.category === 0 ? 'bold' : 'normal',
            color: '#333'
          }
        })),
        links: links.map((link, index) => {
          // 查找源和目标节点名称
          const sourceNode = nodes.find(n => String(n.id) === link.source)
          const targetNode = nodes.find(n => String(n.id) === link.target)

          return {
            ...link,
            sourceName: sourceNode?.name || link.source,
            targetName: targetNode?.name || link.target
          }
        }),
        roam: true,
        labelLayout: {
          hideOverlap: true
        },
        force: {
          repulsion: 400,
          edgeLength: 150,
          gravity: 0.1,
          friction: 0.6
        },
        lineStyle: {
          curveness: 0.2
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4
          },
          itemStyle: {
            borderWidth: 3
          }
        },
        edgeSymbol: ['circle', 'arrow'],
        edgeSymbolSize: [4, 10]
      }
    ]
  }

  chart.setOption(option, true)
}

// 监听数据变化
watch(() => props.hierarchyData, () => {
  updateChart()
}, { deep: true })

onMounted(() => {
  // 延迟初始化以确保容器已渲染
  setTimeout(() => {
    initChart()
  }, 100)
})

onUnmounted(() => {
  chart?.dispose()
})
</script>

<style scoped>
.hierarchy-chart {
  width: 100%;
  min-height: 300px;
}
</style>
