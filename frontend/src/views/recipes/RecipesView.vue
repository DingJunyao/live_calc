<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">菜谱管理</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadRecipes" />
    </template>
  </v-app-bar>

  <v-container fluid class="list-grid-container">
    <!-- 搜索栏 + 筛选器（桌面端同行） -->
    <div class="d-flex ga-2 mb-4 align-center">
      <v-text-field
        v-model="searchQuery"
        label="搜索菜谱..."
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        class="flex-grow-1"
        @update:model-value="debouncedSearch"
      />
      <FilterBar
        :filters="recipeFilters"
        :mobile="mdAndDown"
        @change="onFilterChange"
      />
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadRecipes">重试</v-btn>
      </template>
    </v-alert>

    <!-- 菜谱网格 -->
    <v-row v-else>
      <v-col
        v-for="recipe in recipes"
        :key="recipe.id"
        cols="6"
        sm="6"
        md="4"
        lg="3"
        xl="2"
      >
        <v-card
          class="recipe-card"
          @click="goToDetail(recipe.id)"
          hover
        >
          <!-- 菜谱图片或占位符 -->
          <v-img
            v-if="pendingImages(recipe) && pendingImages(recipe).length > 0"
            :src="getImageUrl(pendingImages(recipe)[0])"
            height="140"
            cover
          />
          <div
            v-else
            class="d-flex align-center justify-center"
            style="height: 140px; background: rgb(var(--v-theme-primary-container))"
          >
            <v-icon size="64" color="primary">
              mdi-food
            </v-icon>
          </div>

          <!-- 菜谱名称（始终显示在图片/占位符下方） -->
          <div class="text-center pa-2 text-subtitle-1">
            {{ pendingName(recipe) }}
            <v-chip
              v-if="recipe.user_id === userStore.user?.id && !recipe.is_public && !recipe.source"
              size="x-small"
              color="warning"
              variant="tonal"
              class="ms-1"
            >未发布</v-chip>
            <v-chip
              v-if="hasPending(['recipe', 'recipe_edit'], recipe.id)"
              size="x-small"
              color="info"
              variant="tonal"
              class="ms-1"
            >修改待审</v-chip>
          </div>

          <v-card-text class="text-center pa-2">
            <div class="d-flex justify-center align-center ga-2 text-body-2">
              <span class="font-weight-bold text-tertiary">
                {{ getDisplayCost(recipe) }}
              </span>
              <span class="text-caption text-medium-emphasis">·</span>
              <span class="text-caption text-medium-emphasis">
                {{ getDisplayCalories(recipe) }}
              </span>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 空状态 -->
      <v-col v-if="recipes.length === 0 && !loading" cols="12">
        <div class="text-center py-16 text-medium-emphasis">
          <v-icon size="80" color="medium-emphasis">mdi-book-open-variant</v-icon>
          <div class="text-h6 mt-4">暂无菜谱</div>
          <div class="text-body-2 mt-2">点击下方按钮添加第一个菜谱</div>
        </div>
      </v-col>
    </v-row>

    <!-- 分页器 -->
    <div v-if="total > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
      <v-pagination
        :model-value="currentPage"
        :length="totalPages"
        :total-visible="totalVisible"
        rounded="circle"
        density="comfortable"
        @update:model-value="onPageChange"
      />
      <div class="d-flex align-center ga-2">
        <v-select
          v-model="pageSize"
          :items="[10, 20, 50, 100]"
          label="每页"
          variant="outlined"
          density="compact"
          hide-details
          style="max-width: 90px"
          @update:model-value="handlePageSizeChange"
        />
        <span class="text-caption text-medium-emphasis">共 {{ total }} 条</span>
      </div>
    </div>

    <!-- FAB 浮动添加按钮 -->
    <v-btn
      icon="mdi-plus"
      color="primary"
      size="large"
      elevation="8"
      class="position-fixed"
      style="bottom: 80px; right: 24px"
      @click="showAddDialog = true"
    />

    <!-- 添加菜谱对话框 -->
    <v-dialog v-model="showAddDialog" max-width="500" @click:outside="resetCreateForm">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="primary">mdi-plus-circle-outline</v-icon>
          创建菜谱
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <v-text-field
            v-model="createForm.name"
            label="菜谱名称 *"
            variant="outlined"
            density="compact"
            maxlength="200"
            :error-messages="createErrors.name"
            hide-details="auto"
            class="mb-3"
          />
          <v-row>
            <v-col cols="6">
              <v-select
                v-model="createForm.category"
                label="分类 *"
                variant="outlined"
                density="compact"
                :items="categoryOptions"
                item-title="title"
                item-value="value"
                hide-details
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="createForm.difficulty"
                label="难度 *"
                variant="outlined"
                density="compact"
                :items="difficultyOptions"
                item-title="label"
                item-value="value"
                hide-details
              />
            </v-col>
          </v-row>

          <!-- 错误提示 -->
          <v-alert
            v-if="createError"
            type="error"
            variant="tonal"
            density="compact"
            class="mt-3"
            closable
            @click:close="createError = ''"
          >{{ createError }}</v-alert>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn
            variant="text"
            @click="closeCreateDialog"
            :disabled="creating"
          >取消</v-btn>
          <v-btn
            color="primary"
            variant="tonal"
            :loading="creating"
            :disabled="!createForm.name || !createForm.category"
            @click="handleCreate"
          >创建</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { useUserUnits } from '@/composables/useUserUnits'
const { energyUnit, toDisplayCalorie } = useUserUnits()
import { ref, computed, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { api } from '@/api/client'
import { getErrorMessage } from '@/utils/errorHandler'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useUserStore } from '@/stores/user'
import FilterBar from '@/components/common/FilterBar.vue'
import type { FilterConfig } from '@/components/common/FilterBar.vue'
import { usePendingProposals } from '@/composables/usePendingProposals'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { smAndDown, mdAndDown, md, lgAndUp } = useDisplay()

const route = useRoute()

interface Recipe {
  id: number
  name: string
  user_id?: number
  description?: string
  category?: string
  difficulty?: string
  cooking_time?: number
  servings?: number
  estimated_cost?: number | string
  calories?: number
  images?: string[]
  is_public?: boolean
  source?: string
  created_at?: string
}

const router = useRouter()
const userStore = useUserStore()

const recipes = ref<Recipe[]>([])
// 待审提议标记（菜谱编辑 entity_type=recipe_edit，发布=recipe，两种都查）
const { load: loadPendingProposals, has: hasPending, getPayload: getPendingPayload } = usePendingProposals()
// 待审草稿覆盖：普通用户提交后，列表显示提议中的新值（name/images）
const pendingName = (recipe: Recipe) => {
  const p = getPendingPayload(['recipe', 'recipe_edit'], recipe.id)
  return p?.name ?? recipe.name
}
const pendingImages = (recipe: Recipe) => {
  const p = getPendingPayload(['recipe', 'recipe_edit'], recipe.id)
  if (Array.isArray(p?.images)) return p.images
  return recipe.images
}
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref((route.query.search as string) || '')
const showAddDialog = ref(false)

// 懒加载的成本和卡路里数据
const costMap = ref<Record<number, { estimated_cost?: number; calories?: number }>>({})
const loadingCosts = ref(false)

// 分页相关（从 URL 查询参数初始化）
const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(Number(route.query.pageSize) || 20)
const total = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const totalVisible = computed(() => lgAndUp.value ? 7 : md.value ? 5 : 3)

// 同步分页状态到 URL 查询参数
const syncToUrl = () => {
  router.replace({
    query: {
      ...route.query,
      page: String(currentPage.value),
      pageSize: String(pageSize.value),
      ...(searchQuery.value ? { search: searchQuery.value } : {}),
    }
  })
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    syncToUrl()
    loadRecipes()
  }, 300)
}

// 筛选器配置
const recipeFilters: FilterConfig[] = reactive([
  {
    key: 'categories',
    label: '分类',
    type: 'select',
    items: [
      { value: '荤菜', title: '荤菜' },
      { value: '素菜', title: '素菜' },
      { value: '水产', title: '水产' },
      { value: '主食', title: '主食' },
      { value: '汤与粥', title: '汤与粥' },
      { value: '早餐', title: '早餐' },
      { value: '甜品', title: '甜品' },
      { value: '调料', title: '调料' },
      { value: '半成品', title: '半成品' },
      { value: '小食', title: '小食' },
    ],
    minWidth: '140px',
    maxWidth: '200px',
  },
  {
    key: 'difficulties',
    label: '难度',
    type: 'select',
    items: [
      { value: 'simple', title: '简易' },
      { value: 'easy', title: '简单' },
      { value: 'medium', title: '中等' },
      { value: 'hard', title: '困难' },
      { value: 'expert', title: '专家' },
    ],
    minWidth: '120px',
    maxWidth: '160px',
  },
  {
    key: 'ingredient_ids',
    label: '所用食材',
    type: 'autocomplete',
    items: [],
    minWidth: '160px',
    maxWidth: '280px',
  },
  {
    key: 'special_conditions',
    label: '特殊条件',
    type: 'multicheck',
    items: [
      { value: 'has_unpriced_ingredient', title: '存在原料没有维护价格' },
      { value: 'has_unnourished_ingredient', title: '存在原料没有维护营养成分' },
    ],
    minWidth: '220px',
  },
])

const requestFilters = ref<Record<string, any>>({})

const onFilterChange = (filterState: Record<string, any>) => {
  currentPage.value = 1
  requestFilters.value = { ...filterState }
  loadRecipes()
}

// 菜谱创建相关
const createForm = ref({
  name: '',
  category: '荤菜',
  difficulty: 'easy',
})
const creating = ref(false)
const createError = ref('')
const createErrors = ref<Record<string, string>>({})

const categoryOptions = [
  { title: '荤菜', value: '荤菜' },
  { title: '素菜', value: '素菜' },
  { title: '水产', value: '水产' },
  { title: '主食', value: '主食' },
  { title: '汤与粥', value: '汤与粥' },
  { title: '早餐', value: '早餐' },
  { title: '甜品', value: '甜品' },
  { title: '调料', value: '调料' },
  { title: '半成品', value: '半成品' },
  { title: '小食', value: '小食' },
]

const difficultyOptions = [
  { label: '简易', value: 'simple' },
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
  { label: '专家', value: 'expert' },
]

const resetCreateForm = () => {
  createForm.value = { name: '', category: '荤菜', difficulty: 'easy' }
  createError.value = ''
  createErrors.value = {}
}

const closeCreateDialog = () => {
  showAddDialog.value = false
  resetCreateForm()
}

const handleCreate = async () => {
  // 验证
  if (!createForm.value.name.trim()) {
    createErrors.value = { name: '请输入菜谱名称' }
    return
  }
  createErrors.value = {}
  creating.value = true
  createError.value = ''

  try {
    const result = await api.post('/recipes', {
      name: createForm.value.name.trim(),
      category: createForm.value.category,
      difficulty: createForm.value.difficulty,
      cooking_steps: [],
      ingredients: [],
    })
    closeCreateDialog()
    router.push(`/recipes/${result.id}`)
  } catch (e: any) {
    console.error('创建菜谱失败', e)
    createError.value = e.response?.data?.detail || e.message || '创建失败，请重试'
  } finally {
    creating.value = false
  }
}

const loadRecipes = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = {
      skip,
      limit: pageSize.value,
      include_cost: false,  // 不计算成本，通过 batch-cost 懒加载
    }
    if (searchQuery.value) {
      params.search = searchQuery.value
    }
    // 筛选参数
    if (requestFilters.value.categories?.length) {
      params.categories = requestFilters.value.categories.join(',')
    }
    if (requestFilters.value.difficulties?.length) {
      params.difficulties = requestFilters.value.difficulties.join(',')
    }
    if (requestFilters.value.ingredient_ids?.length) {
      params.ingredient_ids = requestFilters.value.ingredient_ids.join(',')
    }
    // 特殊条件参数
    if (requestFilters.value.special_conditions?.length) {
      for (const cond of requestFilters.value.special_conditions) {
        params[cond] = 'true'
      }
    }

    const response = await api.get('/recipes', { params })
    recipes.value = response.items || []
    total.value = response.total || 0
    // 基础数据渲染后，后台加载成本
    loadCostsForVisibleRecipes()
  } catch (e: any) {
    console.error('加载菜谱失败', e)
    error.value = getErrorMessage(e, '加载失败')
  } finally {
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  syncToUrl()
  loadRecipes()
}

const onPageChange = (page: number) => {
  currentPage.value = page
  syncToUrl()
  loadRecipes()
}

const formatCost = (cost: any) => {
  const num = parseFloat(cost) || 0
  return num.toFixed(2)
}

// 从懒加载成本数据或列表原始数据中获取显示值
const getDisplayCost = (recipe: Recipe) => {
  const cost = costMap.value[recipe.id]?.estimated_cost ?? recipe.estimated_cost
  if (cost === null || cost === undefined) return '--'
  const servings = recipe.servings || 1
  return `¥${formatCost(cost)}/${servings}人份`
}

const getDisplayCalories = (recipe: Recipe) => {
  const cal = costMap.value[recipe.id]?.calories ?? recipe.calories
  if (cal === null || cal === undefined) return '-'
  const servings = recipe.servings || 1
  const perServing = Math.round(cal / servings)
  return `${toDisplayCalorie(perServing)} ${energyUnit.value}/份`
}

// 页面渲染完后台加载当前页菜谱的成本和卡路里
const loadCostsForVisibleRecipes = async () => {
  const ids = recipes.value.map(r => r.id)
  if (!ids.length) return

  loadingCosts.value = true
  try {
    const result = await api.post('/recipes/batch-cost', { ids })
    costMap.value = result || {}
  } catch (e) {
    console.error('加载成本失败', e)
    // 超时或失败：不显示错误，卡片保持 --
  } finally {
    loadingCosts.value = false
  }
}

const goToDetail = (id: number) => {
  router.push(`/recipes/${id}`)
}

// 加载全部食材（用于食材筛选器的 v-select 客户端搜索）
const loadIngredients = async () => {
  const ingFilter = recipeFilters.find(f => f.key === 'ingredient_ids')
  if (!ingFilter) return
  try {
    // 加载尽可能多的食材，用户通过 v-select 内置搜索过滤
    const response = await api.get('/ingredients', { params: { limit: 1000 } })
    const items = (response.items || []) as { id: number; name: string }[]
    ingFilter.items = items.map(ing => ({ value: ing.id, title: ing.name }))
  } catch (e: any) {
    console.error('加载食材列表失败', e)
  }
}

// 处理图片路径
const getImageUrl = (imagePath: string) => {
  if (imagePath.startsWith('http')) return imagePath
  if (imagePath.startsWith('/static/images/')) return `/api/v1${imagePath}`
  return `${import.meta.env.VITE_DATA_REPO_IMAGE_BASE || 'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out'}/${imagePath}`
}

onMounted(() => {
  loadRecipes()
  loadIngredients()
  loadPendingProposals()
  window.addEventListener('app-refresh', loadRecipes)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', loadRecipes)
})
</script>

<style scoped>
.recipe-card {
  cursor: pointer;
  height: 100%;
}
</style>
