<template>
  <div class="ingredient-list">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>原料管理</h1>
      <button @click="showAddModal = true" class="btn-square add-btn" title="添加原料">
        <i class="mdi mdi-plus"></i>
      </button>
    </header>

    <div class="search-filter">
      <div class="search-box">
        <input v-model="searchTerm" placeholder="搜索原料名称或别名..." class="search-input" />
      </div>
      <div class="filter-options">
        <select v-model="selectedCategory" class="filter-select">
          <option value="">所有分类</option>
          <option v-for="category in categories" :key="category.id" :value="category.id">
            {{ category.display_name }}
          </option>
        </select>
      </div>
      <button @click="loadIngredients" class="btn-search">
        <i class="mdi mdi-magnify"></i> 搜索
      </button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="filteredIngredients.length === 0" class="empty-state">
      <p>暂无原料数据</p>
      <button @click="showAddModal = true" class="btn-primary">添加原料</button>
    </div>

    <div v-else class="ingredient-grid">
      <div v-for="ingredient in filteredIngredients" :key="ingredient.id" class="ingredient-card">
        <div class="ingredient-header">
          <h3>
            {{ ingredient.name }}
            <span v-if="ingredient.is_imported" class="imported-badge" title="导入菜谱时顺带导入">导入</span>
          </h3>
          <div class="ingredient-actions">
            <button @click="editIngredient(ingredient)" class="btn-edit" title="编辑">
              <i class="mdi mdi-pencil"></i>
            </button>
            <button @click="deleteIngredient(ingredient)" class="btn-delete" title="删除">
              <i class="mdi mdi-delete"></i>
            </button>
          </div>
        </div>

        <div class="ingredient-info">
          <p v-if="ingredient.category_name">
            <strong>分类:</strong> {{ ingredient.category_name }}
          </p>
          <p v-if="ingredient.aliases && ingredient.aliases.length > 0">
            <strong>别名:</strong> {{ ingredient.aliases.join(', ') }}
          </p>
          <p v-if="ingredient.density">
            <strong>密度:</strong> {{ ingredient.density }} g/mL
          </p>
          <p v-if="ingredient.default_unit">
            <strong>默认单位:</strong> {{ ingredient.default_unit }}
          </p>
          <p>
            <i class="mdi mdi-calendar"></i> 创建时间: {{ formatDate(ingredient.created_at) }}
          </p>
        </div>

        <div class="ingredient-actions-secondary">
          <button @click="showMergeModal(ingredient)" class="btn-action">
            <i class="mdi mdi-merge"></i> 合并
          </button>
          <button @click="showHierarchy(ingredient)" class="btn-action">
            <i class="mdi mdi-sitemap"></i> 层级关系
          </button>
          <button @click="showAlternatives(ingredient)" class="btn-action">
            <i class="mdi mdi-shuffle-variant"></i> 替代品
          </button>
          <button @click="showConvertUnits(ingredient)" class="btn-action">
            <i class="mdi mdi-scale"></i> 单位转换
          </button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑原料模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeAddModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingIngredient ? '编辑原料' : '添加原料' }}</h2>
        <form @submit.prevent="saveIngredient">
          <div class="form-row">
            <div class="form-group">
              <label for="ingredientName">原料名称:</label>
              <input
                v-model="newIngredient.name"
                type="text"
                id="ingredientName"
                required
                :disabled="isNameInputDisabled"
              />
            </div>
            <div class="form-group">
              <label for="ingredientCategory">分类:</label>
              <select v-model="newIngredient.category_id" id="ingredientCategory" class="select-input">
                <option value="">请选择分类</option>
                <option v-for="category in categories" :key="category.id" :value="category.id">
                  {{ category.display_name }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label for="ingredientAliases">别名 (用逗号分隔):</label>
            <input
              v-model="newIngredient.aliasesText"
              type="text"
              id="ingredientAliases"
              placeholder="例如: 土豆, 马铃薯, Potato"
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="ingredientDensity">密度 (g/mL):</label>
              <input
                v-model="newIngredient.density"
                type="number"
                step="any"
                id="ingredientDensity"
                placeholder="例如: 1.0 (水), 0.57 (面粉)"
              />
            </div>
            <div class="form-group">
              <label for="ingredientDefaultUnit">默认单位:</label>
              <select v-model="newIngredient.default_unit" id="ingredientDefaultUnit" class="select-input">
                <option value="">请选择单位</option>
                <option v-for="unit in units" :key="unit.abbreviation" :value="unit.abbreviation">
                  {{ unit.name }} ({{ unit.abbreviation }})
                </option>
              </select>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeAddModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">{{ editingIngredient ? '更新' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 层级关系模态框 -->
    <div v-if="showHierarchyModal" class="modal-overlay" @click="closeHierarchyModal">
      <div class="modal-content large-modal" @click.stop>
        <h2>{{ selectedIngredient?.name }} - 层级关系</h2>

        <div v-if="hierarchyLoading" class="loading">加载中...</div>

        <div v-else-if="hierarchyData">
          <div v-if="hierarchyData.parents && hierarchyData.parents.length > 0">
            <h3>父级原料</h3>
            <div class="hierarchy-item" v-for="parent in hierarchyData.parents" :key="parent.id">
              <span>{{ parent.name }}</span>
              <span class="confidence">置信度: {{ parent.confidence }}</span>
            </div>
          </div>

          <div v-if="hierarchyData.children && hierarchyData.children.length > 0">
            <h3>子级原料</h3>
            <div class="hierarchy-item" v-for="child in hierarchyData.children" :key="child.id">
              <span>{{ child.name }}</span>
              <span class="confidence">置信度: {{ child.confidence }}</span>
            </div>
          </div>

          <div v-if="!(hierarchyData.parents && hierarchyData.parents.length > 0) && !(hierarchyData.children && hierarchyData.children.length > 0)">
            <p>暂无层级关系数据</p>
          </div>
        </div>

        <div class="form-actions">
          <button @click="closeHierarchyModal" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 替代品模态框 -->
    <div v-if="showAlternativesModal" class="modal-overlay" @click="closeAlternativesModal">
      <div class="modal-content medium-modal" @click.stop>
        <h2>{{ selectedIngredient?.name }} - 替代品</h2>

        <div v-if="alternativesLoading" class="loading">加载中...</div>

        <div v-else-if="alternativesData && alternativesData.length > 0" class="alternative-list">
          <div class="alternative-item" v-for="alt in alternativesData" :key="alt.id">
            <h4>{{ alt.name }}</h4>
            <p v-if="alt.category_name"><strong>分类:</strong> {{ alt.category_name }}</p>
            <p v-if="alt.aliases && alt.aliases.length > 0"><strong>别名:</strong> {{ alt.aliases.join(', ') }}</p>
            <p v-if="alt.density"><strong>密度:</strong> {{ alt.density }} g/mL</p>
            <p v-if="alt.default_unit"><strong>默认单位:</strong> {{ alt.default_unit }}</p>
          </div>
        </div>

        <div v-else>
          <p>暂无替代品数据</p>
        </div>

        <div class="form-actions">
          <button @click="closeAlternativesModal" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 单位转换模态框 -->
    <div v-if="showConvertModal" class="modal-overlay" @click="closeConvertModal">
      <div class="modal-content medium-modal" @click.stop>
        <h2>{{ selectedIngredient?.name }} - 单位转换</h2>

        <div class="conversion-section">
          <div class="form-row">
            <div class="form-group">
              <label>数量:</label>
              <input v-model.number="conversionValue" type="number" step="any" placeholder="输入数值" />
            </div>
            <div class="form-group">
              <label>从单位:</label>
              <select v-model="fromUnit" class="select-input">
                <option v-for="unit in units" :key="`${unit.id}-from`" :value="unit.abbreviation">
                  {{ unit.name }} ({{ unit.abbreviation }})
                </option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>到单位:</label>
              <select v-model="toUnit" class="select-input">
                <option v-for="unit in units" :key="`${unit.id}-to`" :value="unit.abbreviation">
                  {{ unit.name }} ({{ unit.abbreviation }})
                </option>
              </select>
            </div>
            <div class="form-group" style="display: flex; align-items: flex-end;">
              <button @click="performConversion" class="btn-primary">转换</button>
            </div>
          </div>

          <div v-if="conversionResult !== null" class="conversion-result">
            <h4>转换结果:</h4>
            <p>{{ conversionValue }} {{ fromUnit }} = {{ conversionResult }} {{ toUnit }}</p>
          </div>
        </div>

        <div class="form-actions">
          <button @click="closeConvertModal" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 合并原料模态框 -->
    <div v-if="showMergeModalFlag" class="modal-overlay" @click="closeMergeModal">
      <div class="modal-content medium-modal" @click.stop>
        <h2>合并原料 - {{ mergeSource?.name }}</h2>

        <div class="merge-info">
          <p>选择要合并到的目标原料。合并后，源原料将被软删除，所有关联数据将迁移到目标原料。</p>
        </div>

        <div class="form-group">
          <label>
            <input type="checkbox" v-model="showAllIngredients" />
            显示全部原料（默认只显示相似原料）
          </label>
        </div>

        <div class="form-group">
          <label for="mergeTarget">目标原料:</label>
          <select v-model="mergeTargetId" id="mergeTarget" class="select-input">
            <option value="">请选择目标原料</option>
            <option v-for="ing in mergeableIngredients" :key="ing.id" :value="ing.id">
              {{ ing.name }}
              <span v-if="ing.is_imported">(导入)</span>
            </option>
          </select>
        </div>

        <div v-if="mergeLoading" class="loading">处理中...</div>

        <div class="form-actions">
          <button @click="closeMergeModal" class="btn-secondary">取消</button>
          <button @click="performMerge" class="btn-primary" :disabled="!mergeTargetId || mergeLoading">确认合并</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api/client'
import { useUserStore } from '@/stores/user'

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
  ingredient: {
    id: number
    name: string
    category_id?: number
    density?: number
    default_unit?: string
    aliases: string[]
  }
  parents: Array<{
    id: number
    name: string
    relationship_type: string
    confidence: number
  }>
  children: Array<{
    id: number
    name: string
    relationship_type: string
    confidence: number
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
const newIngredient = ref<NewIngredient>({
  name: '',
  aliasesText: '',
  density: undefined,
  default_unit: ''
})

const selectedIngredient = ref<Ingredient | null>(null)
const hierarchyData = ref<HierarchyData | null>(null)
const alternativesData = ref<Alternative[]>([])

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
    await api.post('/ingredients/merge', {
      source_id: mergeSource.value.id,
      target_id: mergeTargetId.value
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
    const response = await api.get('/ingredients/units')
    units.value = response
  } catch (error) {
    console.error('Failed to load units:', error)
  }
}

async function loadIngredients() {
  loading.value = true
  try {
    // 构建查询参数
    const params = new URLSearchParams()
    if (searchTerm.value) {
      params.append('q', searchTerm.value)
    }
    if (selectedCategory.value) {
      params.append('category_id', selectedCategory.value)
    }

    const queryString = params.toString()
    const url = queryString ? `/ingredients?${queryString}` : '/ingredients'

    const response = await api.get(url)
    ingredients.value = response.map((item: any) => ({
      ...item,
      aliases: item.aliases || [],
      category_name: getCategoryName(item.category_id)
    }))
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

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
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

async function showHierarchy(ingredient: Ingredient) {
  selectedIngredient.value = ingredient
  hierarchyLoading.value = true
  try {
    const response = await api.get(`/ingredients/hierarchy/${ingredient.id}`)
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
    const response = await api.get(`/ingredients/alternatives/${ingredient.id}`)
    alternativesData.value = response.map((alt: any) => ({
      ...alt,
      aliases: alt.aliases || [],
      category_name: getCategoryName(alt.category_id)
    }))
    showAlternativesModal.value = true
  } catch (error) {
    console.error('Failed to load alternatives:', error)
    alert('加载替代品失败')
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
</script>

<style scoped>
.ingredient-list {
  padding: 2rem;
  position: relative;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.nav-buttons {
  display: flex;
  gap: 0.5rem;
}

.btn-square {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
}

.btn-square:hover {
  background: #e0e0e0;
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

.page-header h1 {
  font-size: 1.5rem;
  color: #333;
}

.search-filter {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.filter-options {
  display: flex;
  gap: 1rem;
}

.filter-select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  background: white;
  font-size: 1rem;
  min-width: 140px;
}

.btn-search {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
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
}

.ingredient-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-edit, .btn-delete {
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
  font-size: 0.875rem;
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
</style>