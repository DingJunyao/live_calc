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
  expanded_relations?: ExpandedIngredientRelations[]
}

interface ExpandedIngredientRelations {
  ingredient_id: number
  ingredient_name: string
  parent_relations: HierarchyRelation[]
  child_relations: HierarchyRelation[]
}

interface IngredientNode {
  id: number
  name: string
  category: number // 0=当前原料, 1=一级关系, 2=二级关系
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

// 节点样式配置（按级别）
const nodeStyles: Record<number, {
  symbolSize: number
  color: string
  borderColor: string
  borderWidth: number
  fontSize: number
  fontWeight: string
}> = {
  0: { symbolSize: 70, color: '#E91E63', borderColor: '#fff', borderWidth: 3, fontSize: 14, fontWeight: 'bold' },
  1: { symbolSize: 50, color: '#2196F3', borderColor: '#2196F3', borderWidth: 2, fontSize: 12, fontWeight: 'normal' },
  2: { symbolSize: 35, color: '#90CAF9', borderColor: '#90CAF9', borderWidth: 1, fontSize: 10, fontWeight: 'normal' }
}

/**
 * 根据关系信息添加一条边，返回是否成功
 */
function addLink(
  rel: { relation_type: string; id: number; strength: number },
  source: number,
  target: number,
  links: any[],
  edgeCounts: Map<string, number>,
  edgeIndices: Map<string, number>,
  opacity: number = 0.8
): void {
  const rt = rel.relation_type as keyof typeof relationTypes
  const config = relationTypes[rt] || { label: rel.relation_type, color: '#666', lineStyle: 'solid' }

  // 边唯一键
  const edgeKey = `${Math.min(source, target)}-${Math.max(source, target)}-${rel.relation_type}`
  const directionKey = `${source}-${target}`

  if (!edgeCounts.has(directionKey)) edgeCounts.set(directionKey, 0)
  const count = edgeCounts.get(directionKey)!
  edgeCounts.set(directionKey, count + 1)

  if (!edgeIndices.has(edgeKey)) edgeIndices.set(edgeKey, 0)
  const index = edgeIndices.get(edgeKey)!
  edgeIndices.set(edgeKey, index + 1)

  // 同方向多条边分散弯曲度
  const totalEdges = edgeCounts.get(directionKey)!
  let curveness = 0.2
  if (totalEdges > 1) {
    const offset = (index - (totalEdges - 1) / 2) * 0.15
    curveness = 0.2 + offset
  }

  // 根据关系类型决定标签
  let label: string
  if (rel.relation_type === 'contains') {
    label = '包含'
  } else if (rel.relation_type === 'fallback') {
    label = '回退到'
  } else if (rel.relation_type === 'substitutable') {
    label = '可替代'
  } else {
    label = rel.relation_type
  }

  links.push({
    id: `edge-${rel.id}`,
    source: String(source),
    target: String(target),
    name: label,
    relationType: rel.relation_type,
    strength: rel.strength,
    level: opacity < 0.8 ? 2 : 1,
    lineStyle: {
      color: config.color,
      type: config.lineStyle,
      width: opacity < 0.8 ? 1 : 2,
      curveness,
      opacity
    },
    label: {
      show: opacity >= 0.8,
      fontSize: opacity < 0.8 ? 9 : 11,
      formatter: label,
      color: '#666'
    },
    symbolSize: opacity < 0.8 ? 6 : 8
  })
}

// 构建图表数据
const buildChartData = () => {
  if (!props.hierarchyData) return { nodes: [], links: [] }

  const nodes: Map<number, IngredientNode> = new Map()
  const links: any[] = []
  const edgeCounts = new Map<string, number>()
  const edgeIndices = new Map<string, number>()

  // 添加当前原料节点（中心节点）
  nodes.set(props.ingredientId, {
    id: props.ingredientId,
    name: props.ingredientName,
    category: 0
  })

  // ---- 一级关系 ----
  const allRelations = [
    ...(props.hierarchyData.parent_relations || []).map(r => ({ ...r, direction: 'in' })),
    ...(props.hierarchyData.child_relations || []).map(r => ({ ...r, direction: 'out' }))
  ]

  allRelations.forEach(rel => {
    const otherId = rel.direction === 'in' ? rel.parent_id : rel.child_id
    const otherName = rel.direction === 'in' ? rel.parent_name : rel.child_name

    if (!nodes.has(otherId)) {
      nodes.set(otherId, { id: otherId, name: otherName, category: 1 })
    }

    let source: number, target: number
    if (rel.relation_type === 'contains') {
      source = rel.direction === 'in' ? rel.parent_id : props.ingredientId
      target = rel.direction === 'in' ? props.ingredientId : rel.child_id
    } else if (rel.relation_type === 'fallback') {
      source = rel.direction === 'in' ? props.ingredientId : rel.child_id
      target = rel.direction === 'in' ? rel.parent_id : props.ingredientId
    } else if (rel.relation_type === 'substitutable') {
      source = props.ingredientId
      target = rel.direction === 'in' ? rel.parent_id : rel.child_id
    } else {
      source = rel.parent_id
      target = rel.child_id
    }

    addLink(rel, source, target, links, edgeCounts, edgeIndices, 0.8)
  })

  // ---- 二级关系（expanded_relations） ----
  const expanded = props.hierarchyData.expanded_relations || []
  expanded.forEach(exp => {
    // 展开节点的自身关系
    const expRels = [
      ...exp.parent_relations.map(r => ({ ...r, direction: 'in' })),
      ...exp.child_relations.map(r => ({ ...r, direction: 'out' }))
    ]

    expRels.forEach(rel => {
      const otherId = rel.direction === 'in' ? rel.parent_id : rel.child_id
      const otherName = rel.direction === 'in' ? rel.parent_name : rel.child_name

      if (!nodes.has(otherId)) {
        nodes.set(otherId, { id: otherId, name: otherName, category: 2 })
      }

      let source: number, target: number
      if (rel.relation_type === 'contains') {
        source = rel.direction === 'in' ? rel.parent_id : exp.ingredient_id
        target = rel.direction === 'in' ? exp.ingredient_id : rel.child_id
      } else if (rel.relation_type === 'fallback') {
        source = rel.direction === 'in' ? exp.ingredient_id : rel.child_id
        target = rel.direction === 'in' ? rel.parent_id : exp.ingredient_id
      } else if (rel.relation_type === 'substitutable') {
        source = exp.ingredient_id
        target = rel.direction === 'in' ? rel.parent_id : rel.child_id
      } else {
        source = rel.parent_id
        target = rel.child_id
      }

      addLink(rel, source, target, links, edgeCounts, edgeIndices, 0.4)
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
          const style = nodeStyles[params.data.category]
          const levelLabel = params.data.category === 0 ? '当前原料' : params.data.category === 1 ? '一级关系' : '二级关系'
          return `<strong>${params.data.name}</strong><br/>${levelLabel}`
        } else if (params.dataType === 'edge') {
          const levelLabel = params.data.level === 2 ? '（二级）' : ''
          return `<strong>${params.data.sourceName}</strong> ${params.data.name} <strong>${params.data.targetName}</strong>${levelLabel}<br/>类型: ${params.data.relationType}<br/>强度: ${params.data.strength}%`
        }
        return ''
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes.map(node => {
          const style = nodeStyles[node.category] || nodeStyles[1]
          return {
            id: String(node.id),
            name: node.name,
            category: node.category,
            symbolSize: style.symbolSize,
            itemStyle: {
              color: style.color,
              borderColor: style.borderColor,
              borderWidth: style.borderWidth
            },
            label: {
              show: true,
              fontSize: style.fontSize,
              fontWeight: style.fontWeight as 'bold' | 'normal',
              color: '#333'
            }
          }
        }),
        links: links.map((link) => {
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
