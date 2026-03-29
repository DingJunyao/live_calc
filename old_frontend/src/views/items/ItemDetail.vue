<template>
  <PageHeader :title="itemName" :show-back="true">
    <template #extra>
      <button
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
      <InfoCard v-if="item" :item="item" :type="type" @edit="handleEditInfo" @merge="openMergeModal" @ingredient-click="handleIngredientClick" />

      <!-- 价格历史 -->
      <PriceChartSection v-if="item && priceRecords.length > 0"
        :records="priceRecords"
        :filter="priceFilter"
        :default-unit="item.default_unit_name"
        @filter-change="handleFilterChange"
      />
      <PriceHistoryList v-if="item && priceRecords.length > 0"
        :records="priceRecords"
        :type="type"
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
      <HierarchyTreeSection
        v-if="item && type === 'ingredient'"
        :relations="hierarchyRelations"
        :ingredient-id="itemId"
        @add-relation="handleAddRelation"
        @delete-relation="handleDeleteRelation"
        @edit-strength="handleEditStrength"
      />

      <!-- 关联商品（仅原料） -->
      <AssociationList v-if="item && type === 'ingredient' && associations.length > 0"
        :associations="associations"
        :type="type"
        @edit="goToAssociationManage"
        @click="handleAssociationClick"
      />

      <!-- 关联菜谱（仅原料） -->
      <RecipeList v-if="item && type === 'ingredient'"
        :recipes="recipes"
        @click="handleRecipeClick"
      />
    </template>
  </div>

  <!-- 加载状态 -->
  <div v-else class="loading-container">
    <div class="loading-spinner"></div>
    <p>加载中...</p>
  </div>

  <!-- 编辑模态框 -->
  <div v-if="showEditModal" class="modal-overlay">
    <div class="modal-content">
      <h2>{{ type === 'ingredient' ? '编辑原料' : '编辑商品' }}</h2>

      <div class="form-row">
        <div class="form-group">
          <label for="edit-name">名称 *</label>
          <input
            id="edit-name"
            v-model="editForm.name"
            type="text"
            class="input-field"
            placeholder="请输入名称"
          />
        </div>
      </div>

      <div class="form-row" v-if="type === 'ingredient'">
        <div class="form-group">
          <label for="edit-category">类别</label>
          <select id="edit-category" v-model="editForm.category_id" class="select-field">
            <option value="">未分类</option>
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ cat.display_name }}
            </option>
          </select>
        </div>
      </div>

      <div class="form-row" v-if="type === 'ingredient'">
        <div class="form-group">
          <label for="edit-unit">默认单位</label>
          <select id="edit-unit" v-model="editForm.default_unit_id" class="select-field">
            <option value="0">无默认单位</option>
            <option v-for="unit in units" :key="unit.id" :value="unit.id">
              {{ unit.name }}{{ unit.name !== unit.abbreviation ? ` (${unit.abbreviation})` : '' }}
            </option>
          </select>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="edit-aliases">别名 (用逗号分隔)</label>
          <textarea
            id="edit-aliases"
            v-model="editForm.aliasesText"
            rows="2"
            class="input-field"
            placeholder="请输入别名，用逗号分隔"
          ></textarea>
        </div>
      </div>

      <div class="form-actions">
        <button @click="closeEditModal" class="btn-secondary">取消</button>
        <button @click="saveEdit" class="btn-primary">保存</button>
      </div>
    </div>
  </div>

  <!-- 合并原料模态框 -->
  <div v-if="showMergeModal" class="modal-overlay">
    <div class="modal-content">
      <h2>合并原料</h2>
      <p class="merge-info">
        将 <strong>{{ item?.name }}</strong> 合并到以下原料：
      </p>

      <div class="form-group">
        <label for="merge-target">目标原料 *</label>
        <input
          ref="mergeTargetInputRef"
          v-model="mergeSearchTerm"
          type="text"
          id="merge-target"
          placeholder="搜索并选择目标原料"
          @input="onMergeSearchInput"
          @focus="showMergeSuggestions = true"
          @keydown="handleMergeKeydown"
          class="input-field"
        />
        <ul v-if="showMergeSuggestions && mergeSuggestions.length > 0" class="suggestions-list">
          <li
            v-for="(suggestion, index) in mergeSuggestions"
            :key="suggestion.id"
            :class="{ 'suggestion-selected': selectedMergeIndex === index }"
            @click="selectMergeTarget(suggestion)"
          >
            {{ suggestion.name }}
            <span v-if="suggestion.matched_alias" class="suggestion-alias">({{ suggestion.matched_alias }})</span>
          </li>
        </ul>
        <p v-if="selectedMergeTarget" class="selected-hint">
          已选择: {{ selectedMergeTarget.name }}
        </p>
      </div>

      <div class="merge-warning">
        <i class="mdi mdi-alert-circle"></i>
        <div>
          <p><strong>合并后将执行以下操作：</strong></p>
          <ul>
            <li>菜谱中的原料引用将更新为目标原料</li>
            <li>相关商品和价格记录将迁移到目标原料</li>
            <li>当前原料的名称和别名将添加到目标原料</li>
            <li>当前原料将被删除，此操作不可恢复</li>
          </ul>
        </div>
      </div>

      <div class="form-actions">
        <button @click="closeMergeModal" class="btn-secondary">取消</button>
        <button
          @click="confirmMerge"
          class="btn-danger"
          :disabled="!selectedMergeTarget || merging"
        >
          {{ merging ? '合并中...' : '确认合并' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 二次确认模态框 -->
  <div v-if="showConfirmModal" class="modal-overlay">
    <div class="modal-content modal-confirm">
      <h3>⚠️ 确认操作</h3>
      <p class="confirm-message">{{ confirmMessage }}</p>

      <div class="form-actions">
        <button @click="cancelConfirm" class="btn-secondary">取消</button>
        <button @click="proceedWithAction" class="btn-danger">确认</button>
      </div>
    </div>
  </div>

  <!-- 顶部通知提示 -->
  <div v-if="notification" :class="['notification', 'notification-' + notification.type]">
    {{ notification.message }}
    <button @click="hideNotification" class="notification-close">×</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import InfoCard from './components/InfoCard.vue'
import PriceChartSection from './components/PriceChartSection.vue'
import PriceHistoryList from './components/PriceHistoryList.vue'
import NutritionDisplaySection from './components/NutritionDisplaySection.vue'
import HierarchyTreeSection from './components/HierarchyTreeSection.vue'
import AssociationList from './components/AssociationList.vue'
import RecipeList from './components/RecipeList.vue'
import { api } from '@/api/client'
import type { Item, PriceRecord, NutritionData, HierarchyRelations, Association } from './types'

const route = useRoute()
const router = useRouter()

// 状态
const loading = ref(true)
const error = ref<string | null>(null)
const type = computed(() => (route.params.type || 'product') as 'product' | 'ingredient')
const itemId = computed(() => parseInt((route.params.id || '0') as string))

const item = ref<Item | null>(null)
const priceRecords = ref<PriceRecord[]>([])
const nutritionData = ref<NutritionData | null>(null)
const hierarchyRelations = ref<HierarchyRelations | null>(null)
const associations = ref<Association[]>([])
const recipes = ref<any[]>([])

const priceFilter = ref<'week' | 'month' | 'quarter' | 'year'>('month')
const pricePagination = ref({ page: 1, pageSize: 20, total: 0 })

// 编辑相关状态
const showEditModal = ref(false)
const editing = ref(false)
const editForm = ref({
  name: '',
  category_id: 0,
  default_unit_id: 0,
  aliasesText: ''
})
const units = ref<any[]>([])
const categories = ref<any[]>([])

// 合并原料相关状态
const showMergeModal = ref(false)
const mergeSearchTerm = ref('')
const mergeSuggestions = ref<any[]>([])
const showMergeSuggestions = ref(false)
const selectedMergeIndex = ref(-1)
const selectedMergeTarget = ref<any | null>(null)
const merging = ref(false)
const mergeTargetInputRef = ref<HTMLInputElement | null>(null)
let mergeSearchTimeout: ReturnType<typeof setTimeout> | null = null

// 新增：确认模态框相关状态
const showConfirmModal = ref(false)
const confirmMessage = ref('')
const confirmCallback = ref<Function | null>(null)

// 新增：通知提示相关状态
const notification = ref<{ message: string, type: string } | null>(null)

// 强制刷新标记
const forceRefresh = ref(0)

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
      loadAssociations(),
      loadPriceHistory(),
      loadRecipes()
    ])
  } catch (e) {
    error.value = '加载数据失败，请重试'
    console.error('加载数据失败:', e)
  } finally {
    loading.value = false
  }
}

// 加载基本信息
async function loadBaseInfo(skipReload: boolean = false) {
  const endpoint = type.value === 'product'
    ? `/products/entity/${itemId.value}`
    : `/nutrition/ingredients/${itemId.value}`

  // 添加时间戳避免缓存
  const response = await api.get(`${endpoint}${skipReload ? '' : '?_t=' + Date.now()}`)
  console.log('loadBaseInfo - 响应数据:', response)
  console.log('loadBaseInfo - 响应字段:', response ? Object.keys(response) : null)
  console.log('loadBaseInfo - default_unit_id:', response?.default_unit_id)
  console.log('loadBaseInfo - default_unit_name:', response?.default_unit_name)
  if (response) {
    item.value = response
  }
}

// 加载单位列表
async function loadUnits() {
  try {
    const response = await api.get('/units/')
    units.value = (response as any).items || response || []
  } catch (error) {
    console.error('加载单位失败:', error)
  }
}

// 加载分类列表
async function loadCategories() {
  try {
    const response = await api.get('/ingredients/categories')
    categories.value = response || []
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

// 加载价格历史
async function loadPriceHistory() {
  try {
    // 计算日期范围
    const now = new Date()
    const startDate = new Date(now.getTime())

    switch (priceFilter.value) {
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

    // 构建查询参数
    const params = new URLSearchParams()

    if (type.value === 'product') {
      params.append('product_id', String(itemId.value))
    } else {
      // 原料类型：通过 ingredient_id 查询关联商品的价格记录
      params.append('ingredient_id', String(itemId.value))
    }
    // 添加目标单位参数（用于价格单位转换）
    if (item.value && item.value.default_unit_name && type.value === 'ingredient') {
      params.append('target_unit', item.value.default_unit_name)
    }

    params.append('skip', String((pricePagination.value.page - 1) * pricePagination.value.pageSize))
    params.append('limit', String(pricePagination.value.pageSize))
    params.append('start_date', startDate.toISOString())
    // 结束时间设置为当天的最后一刻（23:59:59.999），确保包含今天整天的记录
    const endDate = new Date(now)
    endDate.setHours(23, 59, 59, 999)
    params.append('end_date', endDate.toISOString())

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
// 加载归属关系
async function loadAssociations() {
  try {
    if (type.value === 'product') {
      // 商品：获取关联的原料信息
      console.log('准备调用商品详情API:', `/products/entity/${itemId.value}`)
      const response = await api.get(`/products/entity/${itemId.value}`)
      console.log('商品关联原料响应:', response)
      console.log('商品详情是否有 ingredient 字段:', response && 'ingredient' in response)
      console.log('商品详情是否有 ingredient_id 字段:', response && 'ingredient_id' in response)

      if (response && response.ingredient) {
        // 如果有嵌套的 ingredient 对象，直接使用
        associations.value = [{
          id: response.ingredient.id,
          name: response.ingredient.name,
          type: 'ingredient',
          created_at: response.created_at || new Date().toISOString()
        }]
        console.log('使用嵌套 ingredient 对象设置关联数据')
      } else if (response && response.ingredient_id) {
        // 如果没有嵌套对象但有 ingredient_id，需要单独查询
        console.log('使用 ingredient_id 单独查询原料信息:', response.ingredient_id)
        const ingredientResponse = await api.get(`/nutrition/ingredients/${response.ingredient_id}`)
        console.log('原料详情响应:', ingredientResponse)

        if (ingredientResponse) {
          associations.value = [{
            id: ingredientResponse.id,
            name: ingredientResponse.name,
            type: 'ingredient',
            created_at: ingredientResponse.created_at || new Date().toISOString()
          }]
          console.log('设置关联数据成功')
        } else {
          associations.value = []
          console.log('原料详情为空，设置空数组')
        }
      } else {
        associations.value = []
        console.log('商品详情没有 ingredient 信息')
      }
    } else {
      // 原料：获取关联的商品列表
      const params = new URLSearchParams({
        ingredient_id: String(itemId.value),
        limit: '50'
      })
      const response = await api.get(`/products/entity?${params.toString()}`)
      console.log('原料关联商品响应:', response)

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
        created_at: product.created_at || new Date().toISOString()
      }))
    }
    console.log('最终关联数据:', associations.value)
  } catch (e) {
    console.error('加载归属关系失败:', e)
    console.error('错误详细信息:', e.message || e.stack)
    associations.value = []
  }
}

// 加载关联菜谱（仅原料）
async function loadRecipes() {
  if (type.value !== 'ingredient') return

  try {
    const params = new URLSearchParams({
      skip: '0',
      limit: '50'
    })
    const response = await api.get(`/nutrition/ingredients/${itemId.value}/recipes?${params.toString()}`)
    console.log('原料关联菜谱响应:', response)

    // 处理不同的响应格式
    if (response && response.items) {
      recipes.value = response.items
    } else if (Array.isArray(response)) {
      recipes.value = response
    } else {
      recipes.value = []
    }
  } catch (e) {
    console.error('加载关联菜谱失败:', e)
    recipes.value = []
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

function handleIngredientClick(ingredientId: number) {
  console.log('点击关联原料:', ingredientId)
  // 跳转到原料详情页面
  router.push({
    name: 'item-detail',
    params: { type: 'ingredient', id: ingredientId }
  })
}

function goToEdit() {
  if (!item.value) return
  // 初始化表单数据
  editForm.value.name = item.value.name || ''
  editForm.value.category_id = (item.value as any).category_id || 0
  editForm.value.default_unit_id = item.value.default_unit_id || 0
  editForm.value.aliasesText = (item.value.aliases || []).join(', ')
  editing.value = true
  showEditModal.value = true
}

function closeEditModal() {
  console.log('closeEditModal - 关闭对话框，item.default_unit_id:', item.value?.default_unit_id)
  showEditModal.value = false
  editForm.value = {
    name: '',
    category_id: 0,
    default_unit_id: 0,
    aliasesText: ''
  }
  editing.value = false

  // 关闭对话框后不重新加载，保持直接更新的数据
  // nextTick(() => {
  //   loadBaseInfo(true)
  // })
}

async function saveEdit() {
  console.log('saveEdit - 开始保存')
  console.log('saveEdit - 当前表单:', JSON.parse(JSON.stringify(editForm.value)))
  console.log('saveEdit - 当前 item.default_unit_id:', item.value?.default_unit_id)

  if (!editForm.value.name) {
    showNotification('请输入名称', 'error')
    return
  }

  try {
    // 解析别名
    const aliases = editForm.value.aliasesText
      .split(',')
      .map(a => a.trim())
      .filter(a => a.length > 0)

    const data: any = {
      name: editForm.value.name
    }

    if (editForm.value.category_id > 0) {
      data.category_id = editForm.value.category_id
    }

    // 默认单位：发送 0 表示取消默认单位
    if (type.value === 'ingredient') {
      data.default_unit_id = editForm.value.default_unit_id || null
      console.log('saveEdit - 发送 default_unit_id:', data.default_unit_id)
    }

    if (aliases.length > 0) {
      data.aliases = aliases
    }

    console.log('saveEdit - 发送数据:', data)
    console.log('saveEdit - API endpoint:', type.value === 'ingredient' ? `/ingredients/${itemId.value}` : `/products/entity/${itemId.value}`)

    if (type.value === 'ingredient') {
      await api.put(`/ingredients/${itemId.value}`, data)
    } else {
      await api.put(`/products/entity/${itemId.value}`, data)
    }

    console.log('saveEdit - API 调用完成')

    // 直接更新 item 数据
    if (item.value) {
      // 更新名称
      item.value.name = data.name

      if (type.value === 'ingredient') {
        item.value.default_unit_id = data.default_unit_id
        // 重新获取单位名称
        if (data.default_unit_id) {
          const unit = units.value.find((u: any) => u.id === data.default_unit_id)
          item.value.default_unit_name = unit?.name || ''
        } else {
          item.value.default_unit_name = ''
        }
        // 更新别名
        item.value.aliases = aliases
        // 更新分类
        if (data.category_id !== undefined) {
          (item.value as any).category_id = data.category_id
        }
        console.log('saveEdit - 更新后的 item.default_unit_id:', item.value.default_unit_id)
        console.log('saveEdit - 更新后的 item.default_unit_name:', item.value.default_unit_name)
        console.log('saveEdit - 更新后的 item.aliases:', item.value.aliases)
      }
    }

    showNotification('更新成功', 'success')
    closeEditModal()

    // 不重新加载数据，只依赖直接更新
    // await loadBaseInfo(true)
  } catch (error: any) {
    console.error('更新失败:', error)
    console.error('更新失败详情:', error.response?.data || error.message)
    showNotification(`更新失败: ${error.message || '未知错误'}`, 'error')
  }
}

// ==================== 通用模态框和通知相关函数 ====================

function showConfirmation(message: string, callback: Function) {
  confirmMessage.value = message;
  confirmCallback.value = callback;
  showConfirmModal.value = true;
}

function cancelConfirm() {
  showConfirmModal.value = false;
  confirmMessage.value = '';
  confirmCallback.value = null;
}

function proceedWithAction() {
  if (confirmCallback.value) {
    confirmCallback.value();
  }
  cancelConfirm();
}

function showNotification(message: string, type: string = 'info') {
  notification.value = { message, type };
  // 3秒后自动隐藏通知
  setTimeout(() => {
    hideNotification();
  }, 3000);
}

function hideNotification() {
  notification.value = null;
}

// ==================== 合并原料相关函数 ====================

function openMergeModal() {
  if (type.value !== 'ingredient') return
  showMergeModal.value = true
  mergeSearchTerm.value = ''
  selectedMergeTarget.value = null
  mergeSuggestions.value = []
  showMergeSuggestions.value = false
}

function closeMergeModal() {
  showMergeModal.value = false
  mergeSearchTerm.value = ''
  selectedMergeTarget.value = null
  mergeSuggestions.value = []
  showMergeSuggestions.value = false
  selectedMergeIndex.value = -1
}

function onMergeSearchInput() {
  if (mergeSearchTimeout) {
    clearTimeout(mergeSearchTimeout)
  }
  mergeSearchTimeout = setTimeout(() => {
    searchMergeTargets()
  }, 300)
}

async function searchMergeTargets() {
  const search = mergeSearchTerm.value.trim()

  if (!search || search.length < 1) {
    mergeSuggestions.value = []
    showMergeSuggestions.value = false
    return
  }

  try {
    const response = await api.get(`/ingredients?q=${encodeURIComponent(search)}&limit=20`)
    const items = (response as any).items || (Array.isArray(response) ? response : [])

    // 过滤掉当前原料和已合并的原料
    mergeSuggestions.value = items
      .filter((ing: any) => ing.id !== itemId.value && !ing.is_merged)
      .map((ing: any) => {
        // 计算匹配的别名
        let matchedAlias: string | undefined = undefined
        if (ing.aliases) {
          const searchLower = search.toLowerCase()
          for (const alias of ing.aliases) {
            if (alias.toLowerCase().includes(searchLower)) {
              matchedAlias = alias
              break
            }
          }
        }
        return {
          ...ing,
          matched_alias: matchedAlias
        }
      })

    showMergeSuggestions.value = mergeSuggestions.value.length > 0
    selectedMergeIndex.value = -1
  } catch (error) {
    console.error('搜索原料失败:', error)
    mergeSuggestions.value = []
    showMergeSuggestions.value = false
  }
}

function selectMergeTarget(suggestion: any) {
  selectedMergeTarget.value = suggestion
  mergeSearchTerm.value = suggestion.name
  showMergeSuggestions.value = false
  selectedMergeIndex.value = -1
}

function handleMergeKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedMergeIndex.value = Math.min(selectedMergeIndex.value + 1, mergeSuggestions.value.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedMergeIndex.value = Math.max(selectedMergeIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedMergeIndex.value >= 0) {
    event.preventDefault()
    selectMergeTarget(mergeSuggestions.value[selectedMergeIndex.value])
  } else if (event.key === 'Escape') {
    showMergeSuggestions.value = false
    selectedMergeIndex.value = -1
  }
}

async function confirmMerge() {
  console.log('确认合并按钮被点击')
  if (!selectedMergeTarget.value) {
    console.log('没有选择目标原料')
    return
  }

  const targetName = selectedMergeTarget.value.name
  const sourceName = item.value?.name
  const targetId = selectedMergeTarget.value.id  // 先保存目标ID
  const sourceId = itemId.value

  console.log('合并信息:', { sourceId, sourceName, targetId, targetName })

  // 使用页面内确认模态框替代原生 confirm
  const confirmationMessage = `"${sourceName}" → "${targetName}"\n\n⚠️ 此操作不可撤销！\n\n将执行：\n• 更新菜谱中的原料引用\n• 迁移相关商品和价格记录\n• 合并别名到目标原料\n• 删除源原料"${sourceName}"\n\n确认继续？`;

  showConfirmation(confirmationMessage, async () => {
    console.log('用户确认了合并操作')
    console.log('开始执行合并...')
    merging.value = true
    try {
      const response = await api.post('/ingredients/merge', {
        source_id: sourceId,
        target_id: targetId
      })

      console.log('合并成功响应:', response)
      showNotification((response as any).message || '合并成功', 'success')
      closeMergeModal()

      // 跳转到目标原料详情页
      router.push(`/items/ingredient/${targetId}`)
    } catch (error: any) {
      console.error('合并失败:', error)
      console.error('错误详情:', error.response || error.message)
      showNotification(error.message || '合并失败，请重试', 'error')
    } finally {
      console.log('合并操作结束，设置merging为false')
      merging.value = false
    }
  });
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

function handleAssociationClick(assoc: Association) {
  console.log('点击关联项:', assoc)
  console.log('当前 type:', type.value)
  console.log('当前 itemId:', itemId.value)

  // 跳转到关联项的详情页面
  router.push({
    name: 'item-detail',
    params: { type: assoc.type, id: assoc.id }
  }).then(() => {
    console.log('路由跳转成功')
  }).catch(err => {
    console.error('路由跳转失败:', err)
  })
}

function handleRecipeClick(recipe: any) {
  console.log('点击菜谱:', recipe)
  // 跳转到菜谱详情页面
  router.push({
    name: 'recipe-detail',
    params: { id: recipe.id }
  }).then(() => {
    console.log('路由跳转成功')
  }).catch(err => {
    console.error('路由跳转失败:', err)
  })
}

async function handleAddRelation(data: any) {
  try {
    // 由于 HierarchyTreeSection.vue 已经通过搜索选择了 target_id，这里只需要调用 API
    // 判断当前食材是父级还是子级
    // 如果关系类型是 contains，当前食材是父级
    const isParent = data.relation_type === 'contains'

    // 注意：HierarchyTreeSection 会在 emit 数据时包含 target_id（如果有选择的话）
    // 但为了向后兼容，我们仍然通过 target_name 搜索一次来确保 ID 正确
    const searchResponse = await api.get(`/ingredients/search-by-name/${encodeURIComponent(data.target_name)}?limit=1`)

    if (!searchResponse || searchResponse.length === 0) {
      showNotification(`未找到食材"${data.target_name}"`, 'error')
      return
    }

    const targetId = searchResponse[0].id
    const parentId = isParent ? itemId.value : targetId
    const childId = isParent ? targetId : itemId.value

    // 调用创建层级关系 API
    await api.post('/ingredients/hierarchy', {
      parent_id: parentId,
      child_id: childId,
      relation_type: data.relation_type,
      strength: data.strength
    })

    // 添加成功后重新加载层级关系
    loadHierarchyRelations()
    showNotification('添加关系成功', 'success')
  } catch (e: any) {
    console.error('添加关系失败:', e)
    showNotification(e.message || '添加关系失败，请重试', 'error')
  }
}

async function handleDeleteRelation(relationId: number) {
  try {
    // 调用删除层级关系 API
    await api.delete(`/ingredients/hierarchy/${relationId}`)

    // 删除成功后重新加载层级关系
    loadHierarchyRelations()
  } catch (e: any) {
    console.error('删除关系失败:', e)
    showNotification(e.message || '删除关系失败，请重试', 'error')
  }
}

async function handleEditStrength(data: any) {
  try {
    // 调用修改层级关系强度 API
    await api.put(`/ingredients/hierarchy/${data.id}`, data.strength)

    // 修改成功后重新加载层级关系
    loadHierarchyRelations()
  } catch (e: any) {
    console.error('修改关系强度失败:', e)
    showNotification(e.message || '修改关系强度失败，请重试', 'error')
  }
}

// 生命周期
onMounted(() => {
  loadItemData()
  loadUnits()
  loadCategories()
})

// 监听路由参数变化，重新加载数据
watch(
  () => [route.params.type, route.params.id],
  () => {
    loadItemData()
  }
)
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

/* 通知提示样式 */
.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 16px 24px;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  z-index: 1001;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 300px;
  max-width: 500px;
  animation: slideInRight 0.3s ease-out;
}

.notification-info {
  background-color: #2196f3;
}

.notification-success {
  background-color: #4caf50;
}

.notification-error {
  background-color: #f44336;
}

.notification-warning {
  background-color: #ff9800;
  color: #333;
}

.notification-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 20px;
  cursor: pointer;
  margin-left: 16px;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* 确认模态框样式 */
.modal-confirm {
  max-width: 400px;
}

.confirm-message {
  margin: 1.25rem 0;
  white-space: pre-line;
  line-height: 1.6;
  color: #333;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .notification {
    right: 10px;
    left: 10px;
    top: 10px;
    min-width: auto;
  }

  .modal-confirm {
    width: 90%;
    max-width: 350px;
  }
}

/* 编辑模态框样式 */
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
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin: 0 0 1.5rem;
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  padding-top: 0;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.form-group label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.input-field,
.select-field {
  padding: 10px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
  transition: border-color 0.3s;
}

.input-field:focus,
.select-field:focus {
  outline: none;
  border-color: #42b883;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.25rem;
  padding: 0 2rem 2rem;
}

.btn-primary {
  background-color: #42b883;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary:hover {
  background-color: #3aa876;
}

.btn-secondary {
  background-color: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-secondary:hover {
  background-color: #e0e0e0;
}

.btn-danger {
  background-color: #e53935;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-danger:hover {
  background-color: #c62828;
}

.btn-danger:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

/* 合并模态框样式 */
.merge-info {
  margin-bottom: 20px;
  color: #666;
}

.merge-info strong {
  color: #333;
}

.merge-warning {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background-color: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  margin-bottom: 20px;
}

.merge-warning i {
  color: #ff9800;
  font-size: 24px;
}

.merge-warning p {
  margin: 0 0 8px 0;
}

.merge-warning ul {
  margin: 0;
  padding-left: 20px;
}

.merge-warning li {
  margin: 4px 0;
  font-size: 13px;
  color: #666;
}

.suggestions-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 4px 4px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 1001;
  list-style: none;
  margin: 0;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.suggestions-list li {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}

.suggestions-list li:last-child {
  border-bottom: none;
}

.suggestions-list li:hover,
.suggestions-list li.suggestion-selected {
  background-color: #e8f5e9;
}

.suggestion-alias {
  color: #999;
  font-size: 12px;
  margin-left: 8px;
}

.selected-hint {
  font-size: 12px;
  color: #42b883;
  margin-top: 4px;
}
</style>
