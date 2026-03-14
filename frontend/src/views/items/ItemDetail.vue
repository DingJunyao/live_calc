<template>
  <PageHeader :title="itemName" :show-back="true">
    <template #extra>
      <button
        v-if="type === 'product'"
        @click="goToEdit"
        class="btn-square edit-btn"
        title="编辑"
      >
        <i class="mdi mdi-pencil"></i>
      </button>
    </template>
  </PageHeader>

  <div class="item-detail" v-if="!loading">
    <!-- 加载错误提示 -->
    <div v-if="error" class="error-message">
      <i class="mdi mdi-alert-circle"></i>
      <span>{{ error }}</span>
      <button @click="loadItemData" class="btn-retry">
        <i class="mdi mdi-refresh"></i> 重试
      </button>
    </div>

    <template v-else>
      <!-- 基本信息 -->
      <InfoCard v-if="item" :item="item" :type="type" @edit="handleEditInfo" />

      <PriceChartSection v-if="item && type === 'product'"
        :records="priceRecords"
        :filter="priceFilter"
        @filter-change="handleFilterChange"
      />
      <PriceHistoryList v-if="item && type === 'product'"
        :records="priceRecords"
        :pagination="pricePagination"
        @page-change="handlePricePageChange"
      />

      <!-- 营养数据 -->
      <NutritionDisplaySection v-if="item"
        :nutrition="nutritionData"
        :type="type"
        @edit="goToNutritionEdit"
      />

      <!-- 层级关系（仅原料） -->
      <HierarchyTreeSection v-if="item && type === 'ingredient'"
        @add-relation="handleAddRelation"
        @delete-relation="handleDeleteRelation"
        @edit-strength="handleEditStrength"
      />

      <!-- 归属关系 -->
      <AssociationList v-if="item"
        :associations="associations"
        :type="type"
        @edit="goToAssociationManage"
      />
    </template>
  </div>

  <!-- 加载状态 -->
  <div v-else class="loading-container">
    <div class="loading-spinner"></div>
    <p>加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import InfoCard from './components/InfoCard.vue'
import PriceChartSection from './components/PriceChartSection.vue'
import PriceHistoryList from './components/PriceHistoryList.vue'
import NutritionDisplaySection from './components/NutritionDisplaySection.vue'
import HierarchyTreeSection from './components/HierarchyTreeSection.vue'
import AssociationList from './components/AssociationList.vue'
import { api } from '@/api/client'
import type { Item, PriceRecord, NutritionData, HierarchyRelations, Association } from './types'

const route = useRoute()
const router = useRouter()

// 状态
const loading = ref(true)
const error = ref<string | null>(null)
const type = computed(() => route.params.type as 'product' | 'ingredient')
const itemId = computed(() => parseInt(route.params.id as string))

const item = ref<Item | null>(null)
const priceRecords = ref<PriceRecord[]>([])
const nutritionData = ref<NutritionData | null>(null)
const hierarchyRelations = ref<HierarchyRelations | null>(null)
const associations = ref<Association[]>([])

const priceFilter = ref<'week' | 'month' | 'quarter' | 'year'>('month')
const pricePagination = ref({ page: 1, pageSize: 20, total: 0 })

// 计算属性
const itemName = computed(() => item.value?.name || '详情')

// 加载商品/原料数据
async function loadItemData() {
  loading.value = true
  error.value = null

  try {
    // 并行加载所有数据
    await Promise.all([
      loadBaseInfo(),
      loadNutritionData(),
      loadHierarchyRelations(),
      loadAssociations()
    ])

    // 如果是商品，加载价格记录
    if (type.value === 'product') {
      await loadPriceHistory()
    }
  } catch (e) {
    error.value = '加载数据失败，请重试'
    console.error('加载数据失败:', e)
  } finally {
    loading.value = false
  }
}

// 加载基本信息
async function loadBaseInfo() {
  const endpoint = type.value === 'product'
    ? `/products/entity/${itemId.value}`
    : `/nutrition/ingredients/${itemId.value}`

  const response = await api.get(endpoint)
  if (response) {
    item.value = response
  }
}

// 加载价格历史
async function loadPriceHistory() {
  try {
    // 计算日期范围
    const now = new Date()
    let startDate = new Date()

    switch (priceFilter.value) {
      case 'week':
        startDate.setDate(now.getDate() - 7)
        break
      case 'month':
        startDate.setMonth(now.getMonth() - 1)
        break
      case 'quarter':
        startDate.setMonth(now.getMonth() - 3)
        break
      case 'year':
        startDate.setFullYear(now.getFullYear() - 1)
        break
    }

    // 构建查询参数
    const params = new URLSearchParams({
      product_id: String(itemId.value),
      skip: String((pricePagination.value.page - 1) * pricePagination.value.pageSize),
      limit: String(pricePagination.value.pageSize),
      start_date: startDate.toISOString(),
      end_date: now.toISOString()
    })

    // 调用价格记录 API
    const response = await api.get(`/products/?${params.toString()}`)

    // 处理不同的响应格式
    if (response && response.items) {
      priceRecords.value = response.items
      pricePagination.value.total = response.total
    } else if (Array.isArray(response)) {
      priceRecords.value = response
      pricePagination.value.total = response.length
    } else {
      priceRecords.value = []
      pricePagination.value.total = 0
    }
  } catch (e) {
    console.error('加载价格历史失败:', e)
    priceRecords.value = []
    pricePagination.value.total = 0
  }
}

// 加载营养数据
async function loadNutritionData() {
  const endpoint = type.value === 'product'
    ? `/nutrition/products/${itemId.value}/nutrition`
    : `/nutrition/ingredients/${itemId.value}/nutrition`

  try {
    const response = await api.get(endpoint)
    nutritionData.value = response
  } catch (e) {
    // 营养数据不存在时设置为 null
    nutritionData.value = null
  }
}

// 加载层级关系（仅原料）
async function loadHierarchyRelations() {
  if (type.value !== 'ingredient') return

  try {
    const response = await api.get(`/ingredients/${itemId.value}/hierarchy`)
    hierarchyRelations.value = response
  } catch (e) {
    hierarchyRelations.value = null
  }
}

// 加载归属关系
async function loadAssociations() {
  try {
    if (type.value === 'product') {
      // 商品：获取关联的原料信息
      const response = await api.get(`/products/entity/${itemId.value}`)
      if (response && response.ingredient) {
        associations.value = [{
          id: response.ingredient.id,
          name: response.ingredient.name,
          type: 'ingredient',
          created_at: response.created_at
        }]
      } else {
        associations.value = []
      }
    } else {
      // 原料：获取关联的商品列表
      const params = new URLSearchParams({
        ingredient_id: String(itemId.value),
        limit: '50'
      })
      const response = await api.get(`/products/entity?${params.toString()}`)

      // 处理不同的响应格式
      let items = []
      if (response && response.items) {
        items = response.items
      } else if (Array.isArray(response)) {
        items = response
      }

      associations.value = items.map((product: any) => ({
        id: product.id,
        name: product.name,
        brand: product.brand,
        type: 'product',
        created_at: product.created_at
      }))
    }
  } catch (e) {
    console.error('加载归属关系失败:', e)
    associations.value = []
  }
}

// 事件处理
function handleFilterChange(filter: 'week' | 'month' | 'quarter' | 'year') {
  priceFilter.value = filter
  pricePagination.value.page = 1
  loadPriceHistory()
}

function handlePricePageChange(page: number) {
  pricePagination.value.page = page
  loadPriceHistory()
}

function handleEditInfo() {
  goToEdit()
}

function goToEdit() {
  // TODO: 实现编辑功能
  console.log('编辑功能待实现')
}

function goToNutritionEdit() {
  router.push({
    name: 'nutrition-edit',
    params: { type: type.value, id: itemId.value }
  })
}

function goToAssociationManage() {
  router.push({
    name: 'association-manage',
    params: { type: type.value, id: itemId.value }
  })
}

function handleAddRelation(data: any) {
  loadHierarchyRelations()
}

function handleDeleteRelation(relationId: number) {
  loadHierarchyRelations()
}

function handleEditStrength(data: any) {
  loadHierarchyRelations()
}

// 生命周期
onMounted(() => {
  loadItemData()
})
</script>

<style scoped>
.item-detail {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.edit-btn {
  background-color: #42b883;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.edit-btn:hover {
  background-color: #3aa876;
}

.error-message {
  background-color: #fee;
  color: #c33;
  padding: 16px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-retry {
  background-color: #42b883;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: auto;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #42b883;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-container p {
  margin-top: 16px;
  color: #666;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .item-detail {
    padding: 12px;
  }
}
</style>
