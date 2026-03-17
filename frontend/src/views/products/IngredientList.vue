<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useUserStore } from '@/stores/user'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

const route = useRoute()
const router = useRouter()

const userStore = useUserStore()

interface Ingredient {
  id: number
  name: string
  category_id?: number
  category_name?: string
  density?: number
  default_unit?: string
  aliases: string[]
  is_imported?: boolean
  created_at: string
}

interface IngredientCategory {
  id: number
  name: string
  display_name: string
  parent_category_id?: number
  sort_order: number
  description?: string
}

interface Unit {
  id: number
  name: string
  abbreviation: string
  plural_form?: string
  unit_type: string
  si_factor?: number
  is_si_base: boolean
  is_common: boolean
  display_order: number
}

interface NewIngredient {
  name: string
  category_id?: number
  aliasesText: string
  density?: number
  default_unit?: string
}

interface HierarchyData {
  parent_relations: Array<{
    id: number
    parent_id: number
    parent_name: string
    child_id: number
    child_name: string
    relation_type: string
    strength: number
    created_at: string
  }>
  child_relations: Array<{
    id: number
    parent_id: number
    parent_name: string
    child_id: number
    child_name: string
    relation_type: string
    strength: number
    created_at: string
  }>
}

interface Alternative {
  id: number
  name: string
  category_id?: number
  category_name?: string
  density?: number
  default_unit?: string
  aliases: string[]
}

const ingredients = ref<Ingredient[]>([])
const categories = ref<IngredientCategory[]>([])
const units = ref<Unit[]>([])
const loading = ref(false)
const hierarchyLoading = ref(false)
const alternativesLoading = ref(false)
const showAddModal = ref(false)
const showHierarchyModal = ref(false)
const showAlternativesModal = ref(false)
const showConvertModal = ref(false)
const showMergeModalFlag = ref(false)
const editingIngredient = ref<Ingredient | null>(null)
const searchTerm = ref('')
const selectedCategory = ref('')

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const newIngredient = ref<NewIngredient>({
  name: '',
  aliasesText: '',
  density: undefined,
  default_unit: ''
})

const selectedIngredient = ref<Ingredient | null>(null)
const hierarchyData = ref<HierarchyData | null>(null)
const alternativesData = ref<Alternative[]>([])

// 存储原料的最近价格
const ingredientPrices = ref<Map<number, { average_price: number | null; unit: string | null }>>(new Map())

// 计算名称输入框是否禁用
// 导入的原料只有管理员可以编辑名称
const isNameInputDisabled = computed(() => {
  if (!editingIngredient.value) return false
  // 编辑模式下：导入原料非管理员禁用
  if (editingIngredient.value.is_imported && !userStore.user?.is_admin) {
    return true
  }
  return false
})
const conversionValue = ref<number | null>(null)
const fromUnit = ref<string>('')
const toUnit = ref<string>('')
const conversionResult = ref<number | null>(null)

// 合并功能相关
const mergeSource = ref<Ingredient | null>(null)
const mergeTargetId = ref<number | null>(null)
const mergeLoading = ref(false)
const showAllIngredients = ref(false)

// 层级关系管理相关
const showManageHierarchyModal = ref(false)
const hierarchyParentId = ref<number | null>(null)
const hierarchyChildId = ref<number | null>(null)
const hierarchyRelationType = ref<string>('contains')
const hierarchyStrength = ref<number>(50)

// 可合并的原料列表
const mergeableIngredients = computed(() => {
  if (!mergeSource.value) return []

  let candidates = ingredients.value.filter(ing => ing.id !== mergeSource.value!.id)

  // 如果不显示全部，只显示相似原料
  if (!showAllIngredients.value) {
    candidates = candidates.filter(ing => isSimilarName(mergeSource.value!.name, ing.name))
  }

  // 权限控制：非管理员只能合并非导入原料
  if (!userStore.user?.is_admin) {
    candidates = candidates.filter(ing => !ing.is_imported)
  }

  // 导入原料只能合并到同样为导入的原料
  if (mergeSource.value.is_imported) {
    candidates = candidates.filter(ing => ing.is_imported)
  }

  return candidates
})

// 分页处理函数
function handlePageChange(page: number) {
  currentPage.value = page
  loadIngredients()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadIngredients()
}

// 简单的名称相似度判断（前端预筛选）
function isSimilarName(name1: string, name2: string): boolean {
  const n1 = name1.toLowerCase()
  const n2 = name2.toLowerCase()
  // 包含关系
  if (n1.includes(n2) || n2.includes(n1)) return true
  // 首字符相同
  if (n1[0] === n2[0]) return true
  // 超过50%字符相同
  let sameCount = 0
  const minLen = Math.min(n1.length, n2.length)
  for (let i = 0; i < minLen; i++) {
    if (n1[i] === n2[i]) sameCount++
  }
  return sameCount / minLen >= 0.5
}

function showMergeModal(ingredient: Ingredient) {
  mergeSource.value = ingredient
  mergeTargetId.value = null
  showAllIngredients.value = false
  showMergeModalFlag.value = true
}

function closeMergeModal() {
  showMergeModalFlag.value = false
  mergeSource.value = null
  mergeTargetId.value = null
}

async function performMerge() {
  if (!mergeSource.value || !mergeTargetId.value) return

  // 前端权限检查
  if (mergeSource.value.is_imported && !userStore.user?.is_admin) {
    alert('导入的原料只能由管理员执行合并操作')
    return
  }

  const target = ingredients.value.find(ing => ing.id === mergeTargetId.value)
  if (!target) {
    alert('目标原料不存在')
    return
  }

  // 导入原料只能合并到同样为导入的原料
  if (mergeSource.value.is_imported && !target.is_imported) {
    alert('导入的原料只能合并到同样为导入的原料')
    return
  }

  if (!confirm(`确定要将"${mergeSource.value.name}"合并到"${target.name}"吗？此操作不可撤销。`)) {
    return
  }

  mergeLoading.value = true
  try {
    // 调用后端合并API，修正请求体格式
    await api.post('/ingredients/merge', {
      source_ingredient_ids: [mergeSource.value.id],
      target_ingredient_id: mergeTargetId.value
    })
    alert('合并成功')
    closeMergeModal()
    await loadIngredients()
  } catch (error: any) {
    console.error('Failed to merge ingredients:', error)
    alert(error.message || '合并失败')
  } finally {
    mergeLoading.value = false
  }
}

onMounted(async () => {
  await loadCategories()
  await loadUnits()
  await loadIngredients()

  // 检查 URL 中的 edit 参数，如果有则打开编辑模态框
  const editId = route.query.edit as string
  if (editId) {
    nextTick(() => {
      const ingredientToEdit = ingredients.value.find(i => i.id === parseInt(editId))
      if (ingredientToEdit) {
        editIngredient(ingredientToEdit)
      }
    })
  }
})

async function loadCategories() {
  try {
    const response = await api.get('/ingredients/categories')
    categories.value = response
  } catch (error) {
    console.error('Failed to load categories:', error)
  }
}

async function loadUnits() {
  try {
    const response = await api.get('/units/')
    units.value = (response as any).items || response || []
  } catch (error) {
    console.error('Failed to load units:', error)
  }
}

async function loadIngredients() {
  loading.value = true
  try {
    // 构建查询参数
    const params = new URLSearchParams()
    params.append('skip', String((currentPage.value - 1) * pageSize.value))
    params.append('limit', String(pageSize.value))
    if (searchTerm.value) {
      params.append('q', searchTerm.value)
    }
    if (selectedCategory.value) {
      params.append('category_id', selectedCategory.value)
    }

    const url = `/ingredients?${params.toString()}`

    // 解析分页响应
    const response = await api.get<any>(url)

    // 处理新旧两种响应格式
    let items: any[]
    let totalCount = 0  // 使用不同的变量名避免与 ref 冲突

    if (response.items && response.total !== undefined) {
      // 新的 PaginatedResponse 格式
      items = response.items
      totalCount = response.total
    } else if (Array.isArray(response)) {
      // 旧的 List 格式
      items = response
      // 如果是第一页且没有搜索/筛选条件，用这个数据量作为 totalCount
      if (currentPage.value === 1 && !searchTerm.value && !selectedCategory.value) {
        totalCount = items.length
      }
    }

    ingredients.value = items.map((item: any) => ({
      ...item,
      aliases: item.aliases || [],
      category_name: getCategoryName(item.category_id)
    }))
    total.value = totalCount

    // 加载原料的最近价格
    await loadIngredientPrices(ingredients.value.map((ing: Ingredient) => ing.id))
  } catch (error) {
    console.error('Failed to load ingredients:', error)
    ingredients.value = []
  } finally {
    loading.value = false
  }
}

// 直接使用 ingredients，过滤已由后端完成
const filteredIngredients = computed(() => ingredients.value)

function getCategoryName(categoryId?: number) {
  if (!categoryId) return ''
  const category = categories.value.find(cat => cat.id === categoryId)
  return category ? category.display_name : ''
}

// 加载原料的最近价格
async function loadIngredientPrices(ingredientIds: number[]) {
  try {
    // 并行请求所有原料的价格
    const pricePromises = ingredientIds.map(id =>
      api.get(`/nutrition/ingredients/${id}/latest-price`).catch(() => ({ average_price: null, unit: null }))
    )

    const priceResults = await Promise.all(pricePromises)

    // 更新价格数据
    ingredientIds.forEach((id, index) => {
      ingredientPrices.value.set(id, priceResults[index])
    })
  } catch (error) {
    console.error('加载原料价格失败:', error)
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

function viewIngredient(ingredient: Ingredient) {
  // 跳转到原料详情页
  router.push(`/items/ingredient/${ingredient.id}`)
}


function editIngredient(ingredient: Ingredient) {
  editingIngredient.value = ingredient
  newIngredient.value = {
    name: ingredient.name,
    category_id: ingredient.category_id,
    aliasesText: (ingredient.aliases || []).join(', '),
    density: ingredient.density,
    default_unit: ingredient.default_unit
  }
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
  editingIngredient.value = null
  newIngredient.value = {
    name: '',
    aliasesText: '',
    density: undefined,
    default_unit: ''
  }
}

async function saveIngredient() {
  try {
    const aliases = newIngredient.value.aliasesText
      ? newIngredient.value.aliasesText.split(',').map(s => s.trim()).filter(s => s)
      : []

    const ingredientData: any = {
      name: newIngredient.value.name,
      aliases: aliases
    }

    if (newIngredient.value.category_id) {
      ingredientData.category_id = newIngredient.value.category_id
    }
    if (newIngredient.value.density !== undefined) {
      ingredientData.density = newIngredient.value.density
    }
    if (newIngredient.value.default_unit) {
      ingredientData.default_unit = newIngredient.value.default_unit
    }

    if (editingIngredient.value) {
      await api.put(`/ingredients/${editingIngredient.value.id}`, ingredientData)
    } else {
      await api.post('/ingredients', ingredientData)
    }

    const isEditing = !!editingIngredient.value
    closeAddModal()
    await loadIngredients()
    alert(isEditing ? '原料更新成功' : '原料添加成功')
  } catch (error) {
    console.error('Failed to save ingredient:', error)
    alert(`原料${editingIngredient.value ? '更新' : '添加'}失败: ${(error as Error).message}`)
  }
}

async function deleteIngredient(ingredient: Ingredient) {
  if (confirm(`确定要删除原料 "${ingredient.name}" 吗？此操作会软删除数据，可在后台恢复。`)) {
    try {
      await api.delete(`/ingredients/${ingredient.id}`)
      await loadIngredients()
      alert('原料已软删除')
    } catch (error) {
      console.error('Failed to delete ingredient:', error)
      alert('原料删除失败')
    }
  }
}

function viewNutrition(ingredient: Ingredient) {
  // 导航到营养详情页面，传入原料ID
  router.push(`/nutrition/ingredient/${ingredient.id}`)
}

async function showHierarchy(ingredient: Ingredient) {
  selectedIngredient.value = ingredient
  hierarchyLoading.value = true
  try {
    // 调用后端层级关系API
    const response = await api.get(`/ingredients/${ingredient.id}/hierarchy`)
    hierarchyData.value = response
    showHierarchyModal.value = true
  } catch (error) {
    console.error('Failed to load hierarchy:', error)
    alert('加载层级关系失败')
  } finally {
    hierarchyLoading.value = false
  }
}

function closeHierarchyModal() {
  showHierarchyModal.value = false
  selectedIngredient.value = null
  hierarchyData.value = null
}

async function showAlternatives(ingredient: Ingredient) {
  selectedIngredient.value = ingredient
  alternativesLoading.value = true
  try {
    // 先尝试获取合并状态
    const mergeStatus = await api.get(`/ingredients/${ingredient.id}/merge-status`)
    if (mergeStatus.is_merged) {
      // 如果已合并，显示相关信息
      alert(`${ingredient.name} 已合并到 ${mergeStatus.merged_into_name}`)
      alternativesLoading.value = false
      return
    }

    // 如果未合并，获取替代品信息（可以根据层级关系推断替代品）
    // 这里可以进一步扩展逻辑，获取可能的替代品信息
    alternativesData.value = []  // 暂时返回空数组
    showAlternativesModal.value = true
  } catch (error) {
    console.error('Failed to load alternatives or merge status:', error)
    alert('加载替代品信息失败')
  } finally {
    alternativesLoading.value = false
  }
}

function closeAlternativesModal() {
  showAlternativesModal.value = false
  selectedIngredient.value = null
  alternativesData.value = []
}

function showConvertUnits(ingredient: Ingredient) {
  selectedIngredient.value = ingredient
  fromUnit.value = ingredient.default_unit || 'g'
  toUnit.value = ingredient.default_unit ? (ingredient.default_unit === 'g' ? 'kg' : 'g') : 'kg'
  showConvertModal.value = true
}

function closeConvertModal() {
  showConvertModal.value = false
  selectedIngredient.value = null
  conversionValue.value = null
  conversionResult.value = null
}

async function performConversion() {
  if (!conversionValue.value || !fromUnit.value || !toUnit.value) {
    alert('请填写完整的转换参数')
    return
  }

  try {
    const response = await api.get(`/ingredients/unit-conversion/${conversionValue}/${fromUnit.value}/${toUnit.value}?ingredient_name=${selectedIngredient.value?.name || ''}`)
    conversionResult.value = response
  } catch (error) {
    console.error('Failed to perform conversion:', error)
    alert('单位转换失败')
  }
}

// 获取合并历史记录
async function getMergeHistory() {
  try {
    const response = await api.get('/ingredients/merge-history')
    return response.records || []
  } catch (error) {
    console.error('Failed to fetch merge history:', error)
    return []
  }
}

// 显示层级关系管理模态框
function showManageHierarchyModalFunc(ingredient: Ingredient) {
  selectedIngredient.value = ingredient
  hierarchyParentId.value = null
  hierarchyChildId.value = null
  hierarchyRelationType.value = 'contains'
  hierarchyStrength.value = 50

  // 先加载层级关系数据
  hierarchyLoading.value = true
  api.get(`/ingredients/${ingredient.id}/hierarchy`)
    .then(response => {
      hierarchyData.value = response
      showManageHierarchyModal.value = true
    })
    .catch(error => {
      console.error('Failed to load hierarchy:', error)
      alert('加载层级关系失败')
    })
    .finally(() => {
      hierarchyLoading.value = false
    })
}

// 关闭层级关系管理模态框
function closeManageHierarchyModal() {
  showManageHierarchyModal.value = false
  selectedIngredient.value = null
  hierarchyParentId.value = null
  hierarchyChildId.value = null
  hierarchyData.value = null
}

// 创建新的层级关系
async function createNewHierarchyRelation() {
  if (!hierarchyParentId.value || !hierarchyChildId.value) {
    alert('请选择父级和子级原料')
    return
  }

  if (hierarchyParentId.value === hierarchyChildId.value) {
    alert('父级和子级原料不能相同')
    return
  }

  try {
    await createHierarchyRelation(hierarchyParentId.value, hierarchyChildId.value, hierarchyRelationType.value, hierarchyStrength.value)
    // 重新加载层级关系数据
    if (selectedIngredient.value) {
      await showHierarchy(selectedIngredient.value) // 刷新hierarchyData
      // 也需要更新管理模态框的数据
      const response = await api.get(`/ingredients/${selectedIngredient.value.id}/hierarchy`)
      hierarchyData.value = response
    }
  } catch (error) {
    console.error('Failed to create hierarchy relation:', error)
  }
}

// 添加创建层级关系的功能
async function createHierarchyRelation(parentId: number, childId: number, relationType: string = 'contains', strength: number = 50) {
  try {
    const response = await api.post('/ingredients/hierarchy', {
      parent_id: parentId,
      child_id: childId,
      relation_type: relationType,
      strength: strength
    })
    alert('层级关系创建成功')
    // 重新加载层级关系数据
    if (selectedIngredient.value) {
      await showHierarchy(selectedIngredient.value)
    }
    return true
  } catch (error) {
    console.error('Failed to create hierarchy relation:', error)
    alert(error.response?.data?.detail || '创建层级关系失败')
    return false
  }
}

// 添加删除层级关系的功能
async function deleteHierarchyRelation(relationId: number) {
  if (!confirm('确定要删除这个层级关系吗？此操作不可撤销。')) {
    return
  }

  try {
    await api.delete(`/ingredients/hierarchy/${relationId}`)
    alert('层级关系删除成功')
    // 重新加载层级关系数据
    if (selectedIngredient.value) {
      await showHierarchy(selectedIngredient.value)
      // 更新管理模态框的数据
      const response = await api.get(`/ingredients/${selectedIngredient.value.id}/hierarchy`)
      hierarchyData.value = response
    }
    return true
  } catch (error: any) {
    console.error('Failed to delete hierarchy relation:', error)
    alert(error.response?.data?.detail || '删除层级关系失败')
    return false
  }
}
</script>

<template>
  <PageHeader title="原料管理" subtitle="管理食材及其属性" :show-back="true" />
  <div class="ingredient-list">

    <!-- 搜索和筛选 -->
    <div class="search-filter">
      <div class="search-box">
        <input
          v-model="searchTerm"
          @keyup.enter="loadIngredients"
          type="text"
          placeholder="搜索原料..."
          class="search-input"
        />
      </div>
      <div class="filter-options">
        <select v-model="selectedCategory" @change="loadIngredients" class="filter-select">
          <option value="">所有类别</option>
          <option v-for="category in categories" :key="category.id" :value="category.id">
            {{ category.display_name }}
          </option>
        </select>
        <button @click="loadIngredients" class="btn-search">
          <i class="mdi mdi-magnify"></i>
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="ingredients.length === 0" class="empty-state">
      <p>暂无原料数据</p>
      <button @click="showAddModal = true" class="btn-primary">添加原料</button>
    </div>

    <!-- 原料列表 -->
    <div v-else class="ingredient-grid">
      <div v-for="ingredient in ingredients" :key="ingredient.id" class="ingredient-card" @click="viewIngredient(ingredient)">
        <div class="ingredient-header">
          <h3>
            {{ ingredient.name }}
            <span v-if="ingredient.is_imported" class="imported-badge">导入</span>
            <span v-if="ingredient.category_name" class="category-tag">{{ ingredient.category_name }}</span>
            <span v-if="ingredient.default_unit" class="unit-tag">{{ ingredient.default_unit }}</span>
          </h3>
          <div class="ingredient-actions">
            <button @click="deleteIngredient(ingredient)" class="btn-delete" title="删除">
              <i class="mdi mdi-trash-can"></i>
            </button>
          </div>
        </div>

        <div class="ingredient-info">
          <p v-if="ingredient.aliases && ingredient.aliases.length > 0">
            <strong>别名：</strong>{{ ingredient.aliases.join(', ') }}
          </p>
          <p v-if="ingredient.density">
            <strong>密度：</strong>{{ ingredient.density }} g/ml
          </p>
          <p>
            <strong>价格：</strong>
            <span v-if="ingredientPrices.get(ingredient.id)?.average_price">
              ¥{{ ingredientPrices.get(ingredient.id)?.average_price }} / {{ ingredientPrices.get(ingredient.id)?.unit }}
            </span>
            <span v-else style="color: #333;">暂无价格</span>
          </p>
        </div>

      </div>
    </div>

    <!-- 分页 -->
    <Pagination
      v-if="total > 0"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @change-page="handlePageChange"
      @change-page-size="handlePageSizeChange"
    />

    <!-- 添加/编辑模态框 -->
    <div v-if="showAddModal" class="modal-overlay">
      <div class="modal-content">
        <h2>{{ editingIngredient ? '编辑原料' : '添加原料' }}</h2>

        <div class="form-row">
          <div class="form-group">
            <label for="name">名称 *</label>
            <input
              id="name"
              v-model="newIngredient.name"
              :disabled="isNameInputDisabled"
              type="text"
              class="select-input"
              :placeholder="isNameInputDisabled ? '导入原料名称无法编辑' : '请输入原料名称'"
            />
            <p v-if="isNameInputDisabled" style="color: #999; font-size: 0.8rem; margin-top: 0.25rem;">
              导入的原料只有管理员可以编辑名称
            </p>
          </div>

          <div class="form-group">
            <label for="category">类别</label>
            <select id="category" v-model="newIngredient.category_id" class="select-input">
              <option value="">未分类</option>
              <option v-for="category in categories" :key="category.id" :value="category.id">
                {{ category.display_name }}
              </option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="density">密度 (g/ml)</label>
            <input
              id="density"
              v-model.number="newIngredient.density"
              type="number"
              step="0.01"
              min="0"
              class="select-input"
              placeholder="0.00"
            />
          </div>

          <div class="form-group">
            <label for="default-unit">默认单位</label>
            <select
              id="default-unit"
              v-model="newIngredient.default_unit"
              class="select-input"
            >
              <option value="">无默认单位</option>
              <option v-for="unit in units" :key="unit.id" :value="unit.name">
                {{ unit.name }}
              </option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="aliases">别名 (用逗号分隔)</label>
          <textarea
            id="aliases"
            v-model="newIngredient.aliasesText"
            rows="2"
            class="select-input"
            placeholder="请输入原料的别名，用逗号分隔"
          ></textarea>
        </div>

        <div class="form-actions">
          <button @click="closeAddModal" class="btn-secondary">取消</button>
          <button @click="saveIngredient" class="btn-primary">
            {{ editingIngredient ? '更新' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 层级关系模态框 -->
    <div v-if="showHierarchyModal" class="modal-overlay">
      <div class="modal-content large-modal">
        <h2>{{ selectedIngredient?.name }} 的层级关系</h2>

        <div v-if="hierarchyLoading" class="loading">
          <p>加载中...</p>
        </div>

        <div v-else-if="hierarchyData">
          <div v-if="hierarchyData.parent_relations.length > 0">
            <h3>上级关系</h3>
            <div class="hierarchy-list">
              <div v-for="relation in hierarchyData.parent_relations" :key="'parent-' + relation.id" class="hierarchy-item">
                <span>{{ relation.parent_name }} ({{ relation.relation_type }})</span>
                <span class="confidence">强度: {{ relation.strength }}%</span>
              </div>
            </div>
          </div>

          <div v-if="hierarchyData.child_relations.length > 0">
            <h3>下级关系</h3>
            <div class="hierarchy-list">
              <div v-for="relation in hierarchyData.child_relations" :key="'child-' + relation.id" class="hierarchy-item">
                <span>{{ relation.child_name }} ({{ relation.relation_type }})</span>
                <span class="confidence">强度: {{ relation.strength }}%</span>
              </div>
            </div>
          </div>

          <div v-if="hierarchyData.parent_relations.length === 0 && hierarchyData.child_relations.length === 0">
            <p>暂无层级关系</p>
          </div>
        </div>

        <div class="form-actions">
          <button @click="closeHierarchyModal" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 替代品模态框 -->
    <div v-if="showAlternativesModal" class="modal-overlay">
      <div class="modal-content">
        <h2>{{ selectedIngredient?.name }} 的替代品</h2>

        <div v-if="alternativesLoading" class="loading">
          <p>加载中...</p>
        </div>

        <div v-else-if="alternativesData.length > 0">
          <div class="alternative-list">
            <div v-for="alt in alternativesData" :key="alt.id" class="alternative-item">
              <h4>{{ alt.name }}</h4>
              <p v-if="alt.category_name">{{ alt.category_name }}</p>
              <p v-if="alt.aliases && alt.aliases.length > 0">
                <strong>别名：</strong>{{ alt.aliases.join(', ') }}
              </p>
            </div>
          </div>
        </div>

        <div v-else>
          <p>暂无替代品信息</p>
        </div>

        <div class="form-actions">
          <button @click="closeAlternativesModal" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 单位转换模态框 -->
    <div v-if="showConvertModal" class="modal-overlay">
      <div class="modal-content medium-modal">
        <h2>{{ selectedIngredient?.name }} 单位转换</h2>

        <div class="conversion-section">
          <div class="form-row">
            <div class="form-group">
              <label>数值</label>
              <input
                v-model.number="conversionValue"
                type="number"
                step="any"
                class="select-input"
                placeholder="输入数值"
              />
            </div>

            <div class="form-group">
              <label>从单位</label>
              <input
                v-model="fromUnit"
                type="text"
                class="select-input"
                placeholder="例如: g, kg, ml"
              />
            </div>

            <div class="form-group">
              <label>到单位</label>
              <input
                v-model="toUnit"
                type="text"
                class="select-input"
                placeholder="例如: g, kg, ml"
              />
            </div>
          </div>

          <div class="form-actions">
            <button @click="performConversion" class="btn-primary">转换</button>
          </div>

          <div v-if="conversionResult !== null" class="conversion-result">
            <h4>转换结果</h4>
            <p>{{ conversionValue }} {{ fromUnit }} = {{ conversionResult }} {{ toUnit }}</p>
          </div>
        </div>

        <div class="form-actions">
          <button @click="closeConvertModal" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 合并模态框 -->
    <div v-if="showMergeModalFlag" class="modal-overlay">
      <div class="modal-content medium-modal">
        <h2>合并原料</h2>

        <div class="merge-info">
          <p>将 <strong>{{ mergeSource?.name }}</strong> 合并到另一个原料</p>
        </div>

        <div class="form-group">
          <label>
            <input
              v-model="showAllIngredients"
              type="checkbox"
              @change="loadIngredients"
            />
            显示所有原料（否则只显示相似名称的原料）
          </label>
        </div>

        <div class="form-group">
          <label>选择目标原料</label>
          <select v-model="mergeTargetId" class="select-input">
            <option value="">请选择目标原料</option>
            <option
              v-for="ingredient in mergeableIngredients"
              :key="ingredient.id"
              :value="ingredient.id"
            >
              {{ ingredient.name }} {{ ingredient.is_imported ? '(导入)' : '' }}
            </option>
          </select>
        </div>

        <div class="form-actions">
          <button @click="closeMergeModal" class="btn-secondary">取消</button>
          <button
            @click="performMerge"
            :disabled="!mergeTargetId || mergeLoading"
            class="btn-primary"
          >
            {{ mergeLoading ? '合并中...' : '执行合并' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 管理层级关系模态框 -->
    <div v-if="showManageHierarchyModal" class="modal-overlay">
      <div class="modal-content large-modal">
        <h2>管理层级关系</h2>

        <div class="form-row">
          <div class="form-group">
            <label>父级原料 (如: 鸡肉)</label>
            <select v-model="hierarchyParentId" class="select-input">
              <option value="">请选择父级原料</option>
              <option
                v-for="ingredient in ingredients"
                :key="ingredient.id"
                :value="ingredient.id"
              >
                {{ ingredient.name }} {{ ingredient.is_imported ? '(导入)' : '' }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>子级原料 (如: 鸡胸肉)</label>
            <select v-model="hierarchyChildId" class="select-input">
              <option value="">请选择子级原料</option>
              <option
                v-for="ingredient in ingredients"
                :key="ingredient.id"
                :value="ingredient.id"
              >
                {{ ingredient.name }} {{ ingredient.is_imported ? '(导入)' : '' }}
              </option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>关系类型</label>
            <select v-model="hierarchyRelationType" class="select-input">
              <option value="contains">包含 (contains)</option>
              <option value="substitutable">可替代 (substitutable)</option>
              <option value="fallback">备选 (fallback)</option>
            </select>
          </div>

          <div class="form-group">
            <label>关系强度 (%)</label>
            <input
              v-model.number="hierarchyStrength"
              type="number"
              min="0"
              max="100"
              class="select-input"
              placeholder="0-100"
            />
          </div>
        </div>

        <div class="form-actions">
          <button @click="createNewHierarchyRelation" class="btn-primary">
            创建层级关系
          </button>
        </div>

        <hr style="margin: 1.5rem 0;" />

        <h3>当前层级关系</h3>
        <div v-if="hierarchyData && (hierarchyData.parent_relations.length > 0 || hierarchyData.child_relations.length > 0)">
          <div v-if="hierarchyData.parent_relations.length > 0">
            <h4>作为子级的关系</h4>
            <div class="relations-list">
              <div v-for="relation in hierarchyData.parent_relations" :key="'parent-' + relation.id" class="relation-item">
                <span>{{ relation.parent_name }} → {{ selectedIngredient?.name }} ({{ relation.relation_type }} - {{ relation.strength }}%)</span>
                <button @click="deleteHierarchyRelation(relation.id)" class="btn-delete" style="padding: 0.25rem 0.5rem; font-size: 0.875rem;">删除</button>
              </div>
            </div>
          </div>

          <div v-if="hierarchyData.child_relations.length > 0">
            <h4>作为父级的关系</h4>
            <div class="relations-list">
              <div v-for="relation in hierarchyData.child_relations" :key="'child-' + relation.id" class="relation-item">
                <span>{{ selectedIngredient?.name }} → {{ relation.child_name }} ({{ relation.relation_type }} - {{ relation.strength }}%)</span>
                <button @click="deleteHierarchyRelation(relation.id)" class="btn-delete" style="padding: 0.25rem 0.5rem; font-size: 0.875rem;">删除</button>
              </div>
            </div>
          </div>
        </div>
        <div v-else>
          <p>暂无层级关系</p>
        </div>

        <div class="form-actions">
          <button @click="closeManageHierarchyModal" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ingredient-list {
  position: relative;
  padding-left: 1rem;
  padding-right: 1rem;
}

.add-btn {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
}

.add-btn:hover {
  background: #36966d;
}

.search-filter {
  display: flex;
  align-items: stretch;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  padding: 0.5rem;
  width: 100%;
  box-sizing: border-box;
}

.search-box {
  flex: 2;
  min-width: 0;
}

.search-input {
  width: 100%;
  height: 100%;
  padding: 0.375rem 0.625rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
  line-height: 1.5;
}

.filter-options {
  display: flex;
  gap: 0.5rem;
  flex: 0 0 auto;
}

.filter-select {
  flex: 1;
  min-width: 80px;
  max-width: 140px;
  height: 100%;
  padding: 0.375rem 2rem 0.375rem 0.625rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  background: white;
  font-size: 1rem;
  box-sizing: border-box;
  line-height: 1.5;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
  background-size: 12px 12px;
  padding-right: 2rem;
}

.filter-select:focus {
  outline: none;
  border-color: #667eea;
}

.btn-search {
  flex: 0 0 auto;
  aspect-ratio: 1;
  min-width: 44px;
  max-width: 48px;
  background: #667eea;
  color: white;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: background-color 0.2s;
}

.btn-search:hover {
  background: #5a6fd8;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 4rem;
  color: #999;
}

.empty-state button {
  margin-top: 1rem;
}

.ingredient-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.ingredient-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-left: 4px solid #667eea;
  display: flex;
  flex-direction: column;
}

.ingredient-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.ingredient-header h3 {
  font-size: 1.125rem;
  color: #333;
  margin: 0;
  flex-grow: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.ingredient-tags {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.category-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 500;
}

.unit-tag {
  background: #f3e5f5;
  color: #7c3aed;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 500;
}

.ingredient-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-edit, .btn-delete, .btn-nutrition {
  width: 2rem;
  height: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-edit {
  background: #667eea;
  color: white;
}

.btn-edit:hover {
  background: #5a6fd8;
}

.btn-nutrition {
  background: #66bb6a;
  color: white;
}

.btn-nutrition:hover {
  background: #4caf50;
}

.btn-delete {
  background: #de350b;
  color: white;
}

.btn-delete:hover {
  background: #bc2e0b;
}

.ingredient-info p {
  margin: 0.5rem 0;
  color: #666;
  line-height: 1.4;
}

.ingredient-info strong {
  color: #333;
}

.ingredient-actions-secondary {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}

.btn-action {
  background: #f0f0f0;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.btn-action:hover {
  background: #e0e0e0;
}

.btn-primary {
  padding: 0.5rem 1rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  overflow-y: auto;
  padding: 1rem;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  width: 90%;
  max-width: 600px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.large-modal {
  max-width: 900px;
}

.medium-modal {
  max-width: 700px;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
  font-size: 1.5rem;
}

.form-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.form-group {
  flex: 1;
  min-width: 200px;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.select-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  background: white;
}

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.hierarchy-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
}

.confidence {
  color: #666;
  font-size: 0.875rem;
}

.alternative-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.alternative-item {
  border: 1px solid #eee;
  border-radius: 0.5rem;
  padding: 1rem;
}

.alternative-item h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #333;
}

.conversion-section {
  margin-bottom: 1.5rem;
}

.conversion-result {
  margin-top: 1rem;
  padding: 1rem;
  background: #f0f9ff;
  border-radius: 0.5rem;
  border: 1px solid #bae6fd;
}

.conversion-result h4 {
  margin-top: 0;
  color: #0369a1;
}

.conversion-result p {
  font-size: 1.2rem;
  font-weight: bold;
  color: #0ea5e9;
}

.imported-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 0.5rem;
  vertical-align: middle;
}

.merge-info {
  margin-bottom: 1rem;
  padding: 0.5rem;
  background: #f9f9f9;
  border-radius: 0.25rem;
}

.merge-info p {
  margin: 0;
  color: #666;
  font-size: 0.875rem;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .ingredient-list {
    padding: 0.75rem;
  }

  .add-btn {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .ingredient-header h3 {
    font-size: 1rem;
  }

  .category-tag,
  .unit-tag {
    padding: 0.125rem 0.3125rem;
    font-size: 0.625rem;
  }

  .search-filter {
    gap: 0.375rem;
  }

  .filter-select {
    min-width: 60px;
    max-width: 100px;
    padding: 0.5rem 1.5rem 0.5rem 0.625rem;
    font-size: 0.875rem;
  }

  .btn-search {
    min-width: 40px;
    max-width: 44px;
  }

  .search-input {
    padding: 0.5rem 0.625rem;
    font-size: 0.875rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .ingredient-list {
    padding: 0.5rem;
  }

  .add-btn {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .ingredient-header h3 {
    font-size: 0.9375rem;
  }

  .category-tag,
  .unit-tag {
    padding: 0.125rem 0.25rem;
    font-size: 0.5625rem;
  }

  .search-filter {
    gap: 0.25rem;
  }

  .filter-select {
    min-width: 50px;
    max-width: 80px;
    padding: 0.375rem 1.25rem 0.375rem 0.5625rem;
    font-size: 0.8125rem;
  }

  .btn-search {
    min-width: 36px;
    max-width: 40px;
  }

  .search-input {
    padding: 0.375rem 0.5625rem;
    font-size: 0.8125rem;
  }
}

/* 层级关系列表样式 */
.relations-list {
  margin-top: 1rem;
}

.relation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
  background: #fafafa;
  border-radius: 0.25rem;
  margin-bottom: 0.5rem;
}
</style>