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

    <div v-else>
      <!-- 图表区域 -->
      <div ref="chartRef" class="chart-container"></div>

      <!-- 关系列表 -->
      <div class="relations-list">
        <div v-if="relations.parent_relations.length > 0" class="relation-group">
          <h3 class="group-title">父级食材</h3>
          <div class="relation-list-body">
            <div
              v-for="relation in relations.parent_relations"
              :key="relation.id"
              class="relation-item"
            >
              <span class="relation-name">{{ relation.parent_name }}</span>
              <div class="relation-actions">
                <span class="relation-info">{{ relation.relation_type }} · 强度 {{ relation.strength }}</span>
                <button
                  @click="handleDeleteRelation(relation.id)"
                  class="btn-icon btn-delete"
                  title="删除关系"
                >
                  <i class="mdi mdi-delete"></i>
                </button>
                <button
                  @click="handleEditStrength(relation)"
                  class="btn-icon btn-edit"
                  title="修改强度"
                >
                  <i class="mdi mdi-pencil"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="relations.child_relations.length > 0" class="relation-group">
          <h3 class="group-title">子级食材</h3>
          <div class="relation-list-body">
            <div
              v-for="relation in relations.child_relations"
              :key="relation.id"
              class="relation-item"
            >
              <span class="relation-name">{{ relation.child_name }}</span>
              <div class="relation-actions">
                <span class="relation-info">{{ relation.relation_type }} · 强度 {{ relation.strength }}</span>
                <button
                  @click="handleDeleteRelation(relation.id)"
                  class="btn-icon btn-delete"
                  title="删除关系"
                >
                  <i class="mdi mdi-delete"></i>
                </button>
                <button
                  @click="handleEditStrength(relation)"
                  class="btn-icon btn-edit"
                  title="修改强度"
                >
                  <i class="mdi mdi-pencil"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加关系模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">添加层级关系</h3>
          <button @click="showAddModal = false" class="btn-close">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">关系类型</label>
            <select v-model="newRelation.relation_type" class="form-select">
              <option value="contains">包含（父级）</option>
              <option value="substitutable">替代</option>
              <option value="fallback">回退</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">目标食材</label>
            <div class="autocomplete-container">
              <input
                v-model="ingredientSearchTerm"
                type="text"
                class="form-input"
                placeholder="搜索并选择食材"
                @input="searchIngredients"
                @focus="showIngredientSuggestions = true"
                @keydown="handleIngredientKeydown"
              />
              <ul v-if="showIngredientSuggestions && ingredientSuggestions.length > 0" class="suggestions-list">
                <li
                  v-for="(suggestion, index) in ingredientSuggestions"
                  :key="suggestion.id"
                  :class="{ 'suggestion-selected': index === selectedIngredientIndex }"
                  @click="selectIngredient(suggestion)"
                >
                  {{ suggestion.name }}
                  <span v-if="suggestion.category_name" class="category-hint">({{ suggestion.category_name }})</span>
                </li>
              </ul>
            </div>
            <p v-if="newRelation.target_id" class="selected-hint">
              已选择: {{ getIngredientName(newRelation.target_id) }}
            </p>
          </div>
          <div class="form-group">
            <label class="form-label">关系强度</label>
            <input
              v-model.number="newRelation.strength"
              type="number"
              min="1"
              max="100"
              class="form-input"
              placeholder="1-100"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showAddModal = false" class="btn btn-cancel">取消</button>
          <button @click="handleAddRelation" class="btn btn-primary">添加</button>
        </div>
      </div>
    </div>

    <!-- 修改强度模态框 -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">修改关系强度</h3>
          <button @click="showEditModal = false" class="btn-close">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">关系信息</label>
            <div class="relation-info-display">
              <p><strong>食材：</strong>{{ editingRelation?.child_name || editingRelation?.parent_name }}</p>
              <p><strong>当前类型：</strong>{{ editingRelation?.relation_type }}</p>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">关系强度 (1-100)</label>
            <input
              v-model.number="editStrengthValue"
              type="number"
              min="1"
              max="100"
              class="form-input"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showEditModal = false" class="btn btn-cancel">取消</button>
          <button @click="confirmEditStrength" class="btn btn-primary">保存</button>
        </div>
      </div>
    </div>

    <!-- 删除确认模态框 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">确认删除</h3>
          <button @click="showDeleteModal = false" class="btn-close">
            <i class="mdi mdi-close"></i>
          </button>
        </div>
        <div class="modal-body">
          <p class="delete-warning">确定要删除这条层级关系吗？</p>
          <p class="delete-info">
            <strong>{{ deletingRelation?.child_name || deletingRelation?.parent_name }}</strong>
          </p>
        </div>
        <div class="modal-footer">
          <button @click="showDeleteModal = false" class="btn btn-cancel">取消</button>
          <button @click="confirmDeleteRelation" class="btn btn-danger">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts/core'
import { TreeChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent } from 'echarts/components'
import { UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import type { HierarchyRelations, HierarchyRelation } from '../types'
import { api } from '@/api/client'

// 注册必需的组件
echarts.use([TreeChart, TitleComponent, TooltipComponent, UniversalTransition, CanvasRenderer])

const props = defineProps<{
  relations: HierarchyRelations | null
  ingredientId: number
}>()

const emit = defineEmits<{
  'add-relation': [data: any]
  'delete-relation': [relationId: number]
  'edit-strength': [data: any]
}>()

const chartRef = ref<HTMLElement>()
const showAddModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const editingRelation = ref<HierarchyRelation | null>(null)
const deletingRelation = ref<HierarchyRelation | null>(null)
const editStrengthValue = ref(50)
let chart: any = null

// 食材自动完成相关状态
const ingredients = ref<any[]>([])
const ingredientSearchTerm = ref('')
const ingredientSuggestions = ref<any[]>([])
const showIngredientSuggestions = ref(false)
const selectedIngredientIndex = ref(-1)
let ingredientSearchTimeout: any = null

const newRelation = ref({
  relation_type: 'contains',
  target_name: '',
  target_id: null as number | null,
  strength: 50
})

// 监听relations变化，重新初始化图表
watch(() => props.relations, () => {
  nextTick(() => {
    initChart()
  })
})

function initChart() {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data as any
        let result = data.name
        if (data.relation_type) {
          result += `\n关系: ${data.relation_type}`
        }
        if (data.strength) {
          result += `\n强度: ${data.strength}`
        }
        return result
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
  if (!props.relations) {
    return [{
      name: '当前食材',
      value: props.ingredientId,
      children: []
    }]
  }

  const { parent_relations, child_relations } = props.relations

  // 按关系类型分组
  const containsParents = parent_relations
    .filter(rel => rel.relation_type === 'contains')
    .map(rel => ({
      name: rel.parent_name,
      value: rel.parent_id,
      relation_type: rel.relation_type,
      strength: rel.strength,
      itemStyle: { color: '#91cc75' }
    }))

  const containsChildren = child_relations
    .filter(rel => rel.relation_type === 'contains')
    .map(rel => ({
      name: rel.child_name,
      value: rel.child_id,
      relation_type: rel.relation_type,
      strength: rel.strength,
      itemStyle: { color: '#42b883' },
      children: []
    }))

  const substitutableParents = parent_relations
    .filter(rel => rel.relation_type === 'substitutable')
    .map(rel => ({
      name: rel.parent_name,
      value: rel.parent_id,
      relation_type: rel.relation_type,
      strength: rel.strength,
      itemStyle: { color: '#ff9800' }
    }))

  const substitutableChildren = child_relations
    .filter(rel => rel.relation_type === 'substitutable')
    .map(rel => ({
      name: rel.child_name,
      value: rel.child_id,
      relation_type: rel.relation_type,
      strength: rel.strength,
      itemStyle: { color: '#ff9800' },
      children: []
    }))

  const fallbackParents = parent_relations
    .filter(rel => rel.relation_type === 'fallback')
    .map(rel => ({
      name: rel.parent_name,
      value: rel.parent_id,
      relation_type: rel.relation_type,
      strength: rel.strength,
      itemStyle: { color: '#9c27b0' }
    }))

  const fallbackChildren = child_relations
    .filter(rel => rel.relation_type === 'fallback')
    .map(rel => ({
      name: rel.child_name,
      value: rel.child_id,
      relation_type: rel.relation_type,
      strength: rel.strength,
      itemStyle: { color: '#9c27b0' },
      children: []
    }))

  // 构建树形结构的子节点
  const children: any[] = []

  // 父级食材（只包含 contains 关系）
  if (containsParents.length > 0) {
    children.push({
      name: '父级食材（包含）',
      itemStyle: { color: '#f59e0b' },
      children: containsParents
    })
  }

  // 子级食材（只包含 contains 关系）
  if (containsChildren.length > 0) {
    children.push({
      name: '子级食材（包含）',
      itemStyle: { color: '#42b883' },
      children: containsChildren
    })
  }

  // 替代食材
  if (substitutableParents.length > 0 || substitutableChildren.length > 0) {
    children.push({
      name: '替代食材',
      itemStyle: { color: '#ff9800' },
      children: [...substitutableParents, ...substitutableChildren]
    })
  }

  // 回退食材
  if (fallbackParents.length > 0 || fallbackChildren.length > 0) {
    children.push({
      name: '回退食材',
      itemStyle: { color: '#9c27b0' },
      children: [...fallbackParents, ...fallbackChildren]
    })
  }

  // 构建树形结构：当前食材 -> 按关系类型分组
  const treeData: any[] = [{
    name: '当前食材',
    value: props.ingredientId,
    itemStyle: { color: '#667eea' },
    children
  }]

  // 如果没有任何关系，返回简化的树
  if (children.length === 0) {
    return [{
      name: '当前食材',
      value: props.ingredientId,
      itemStyle: { color: '#667eea' }
    }]
  }

  return treeData
}

// 处理添加关系
function handleAddRelation() {
  if (!newRelation.value.target_id) {
    alert('请选择目标食材')
    return
  }

  if (!newRelation.value.relation_type) {
    alert('请选择关系类型')
    return
  }

  if (!newRelation.value.strength || newRelation.value.strength < 1 || newRelation.value.strength > 100) {
    alert('请输入有效的关系强度（1-100）')
    return
  }

  emit('add-relation', {
    relation_type: newRelation.value.relation_type,
    target_name: ingredientSearchTerm.value,
    strength: newRelation.value.strength
  })

  // 重置表单并关闭模态框
  newRelation.value = {
    relation_type: 'contains',
    target_name: '',
    target_id: null,
    strength: 50
  }
  ingredientSearchTerm.value = ''
  ingredientSuggestions.value = []
  showIngredientSuggestions.value = false
  selectedIngredientIndex.value = -1
}

// 食材自动完成相关函数
async function loadIngredients() {
  try {
    const response = await api.get('/ingredients?limit=500')

    // 处理分页响应格式
    let items: any[]

    if (response.items && response.total !== undefined) {
      // 分页响应格式
      items = response.items
    } else if (Array.isArray(response)) {
      // 直接数组格式
      items = response
    } else {
      // 默认处理
      items = response || []
    }

    ingredients.value = items
  } catch (error) {
    console.error('Failed to load ingredients:', error)
  }
}

function searchIngredients() {
  if (ingredientSearchTimeout) {
    clearTimeout(ingredientSearchTimeout)
  }
  ingredientSearchTimeout = setTimeout(() => {
    filterIngredients()
  }, 300)
}

function filterIngredients() {
  if (!ingredientSearchTerm.value.trim()) {
    ingredientSuggestions.value = ingredients.value.slice(0, 10)
  } else {
    const search = ingredientSearchTerm.value.toLowerCase()
    ingredientSuggestions.value = ingredients.value
      .filter(ing =>
        ing.name.toLowerCase().includes(search) ||
        (ing.aliases && ing.aliases.some((alias: string) => alias.toLowerCase().includes(search)))
      )
      .slice(0, 10)
  }
  showIngredientSuggestions.value = ingredientSuggestions.value.length > 0
  selectedIngredientIndex.value = -1
}

function selectIngredient(ingredient: any) {
  newRelation.value.target_id = ingredient.id
  newRelation.value.target_name = ingredient.name
  ingredientSearchTerm.value = ingredient.name
  showIngredientSuggestions.value = false
  selectedIngredientIndex.value = -1
}

function handleIngredientKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedIngredientIndex.value = Math.min(selectedIngredientIndex.value + 1, ingredientSuggestions.value.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedIngredientIndex.value = Math.max(selectedIngredientIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedIngredientIndex.value >= 0) {
    event.preventDefault()
    selectIngredient(ingredientSuggestions.value[selectedIngredientIndex.value])
  } else if (event.key === 'Escape') {
    showIngredientSuggestions.value = false
    selectedIngredientIndex.value = -1
  }
}

function getIngredientName(ingredientId: number): string {
  const ing = ingredients.value.find((i: any) => i.id === ingredientId)
  return ing ? ing.name : ''
}

function getCategoryName(categoryId: number | null | undefined): string {
  // 这里可以简化处理，暂不获取分类名称
  return ''
}

// 处理删除关系
function handleDeleteRelation(relationId: number) {
  const relation = findRelationById(relationId)
  if (relation) {
    deletingRelation.value = relation
    showDeleteModal.value = true
  }
}

// 查找关系
function findRelationById(id: number): HierarchyRelation | null {
  if (!props.relations) return null

  const { parent_relations, child_relations } = props.relations
  return [...parent_relations, ...child_relations].find(r => r.id === id) || null
}

// 确认删除关系
function confirmDeleteRelation() {
  if (deletingRelation.value) {
    emit('delete-relation', deletingRelation.value.id)
    showDeleteModal.value = false
    deletingRelation.value = null
  }
}

// 处理修改强度
function handleEditStrength(relation: HierarchyRelation) {
  editingRelation.value = relation
  editStrengthValue.value = relation.strength
  showEditModal.value = true
}

// 确认修改强度
function confirmEditStrength() {
  if (editingRelation.value) {
    const newStrength = editStrengthValue.value
    if (!newStrength || newStrength < 1 || newStrength > 100) {
      alert('请输入有效的关系强度（1-100）')
      return
    }

    emit('edit-strength', {
      id: editingRelation.value.id,
      strength: newStrength
    })

    showEditModal.value = false
    editingRelation.value = null
  }
}

onMounted(() => {
  nextTick(() => {
    initChart()
  })
  loadIngredients()
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
  margin-bottom: 20px;
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

/* 关系列表 */
.relations-list {
  margin-top: 20px;
}

.relation-group {
  margin-bottom: 24px;
}

.group-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #666;
}

.relation-list-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.relation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #f9f9f9;
  border-radius: 6px;
  border-left: 4px solid #42b883;
}

.relation-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.relation-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.relation-info {
  font-size: 13px;
  color: #666;
}

.btn-icon {
  background-color: white;
  border: 1px solid #e5e5e5;
  color: #666;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.3s;
}

.btn-icon:hover {
  border-color: #42b883;
  color: #42b883;
}

.btn-delete:hover {
  border-color: #c33;
  color: #c33;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e5e5;
}

.modal-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 4px;
  transition: all 0.3s;
}

.btn-close:hover {
  background-color: #f5f5f5;
  color: #666;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
  transition: all 0.3s;
}

/* 自动完成样式 */
.autocomplete-container {
  position: relative;
}

.suggestions-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: white;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 0.5rem 0.5rem;
  max-height: 200px;
  overflow-y: auto;
  z-index: 1001;
  list-style: none;
  margin: 0;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.suggestions-list li {
  padding: 0.75rem 1rem;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.suggestions-list li:last-child {
  border-bottom: none;
}

.suggestions-list li:hover,
.suggestions-list li.suggestion-selected {
  background-color: #e8f5e9;
}

.category-hint {
  font-size: 12px;
  color: #999;
  font-weight: normal;
}

.selected-hint {
  margin-top: 8px;
  font-size: 13px;
  color: #42b883;
  font-weight: 500;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #42b883;
  box-shadow: 0 0 0 3px rgba(66, 184, 131, 0.1);
}

.relation-info-display {
  background-color: #f9f9f9;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
}

.relation-info-display p {
  margin: 4px 0;
  font-size: 14px;
  color: #333;
}

.delete-warning {
  margin: 0 0 16px;
  font-size: 14px;
  color: #666;
}

.delete-info {
  font-size: 16px;
  color: #333;
  padding: 12px;
  background-color: #fff3f3;
  border-radius: 4px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e5e5e5;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-cancel {
  background-color: #f5f5f5;
  color: #666;
}

.btn-cancel:hover {
  background-color: #e5e5e5;
}

.btn-primary {
  background-color: #42b883;
  color: white;
}

.btn-primary:hover {
  background-color: #3aa876;
}

.btn-danger {
  background-color: #c33;
  color: white;
}

.btn-danger:hover {
  background-color: #aa0000;
}

@media (max-width: 768px) {
  .hierarchy-tree-section {
    padding: 12px;
  }

  .chart-container {
    height: 300px;
  }

  .modal-content {
    width: 95%;
  }

  .relation-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .relation-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
