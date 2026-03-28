<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">
      <div class="d-flex align-center ga-2">
        <span class="text-truncate">{{ recipe?.name || '菜谱详情' }}</span>
        <v-chip size="x-small" variant="tonal" color="primary">菜谱</v-chip>
      </div>
    </v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadData" />
    </template>
  </v-app-bar>

  <v-container fluid class="pa-0">
    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="ma-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadData">重试</v-btn>
      </template>
    </v-alert>

    <template v-else-if="recipe">
      <!-- 菜谱图片 -->
      <v-card v-if="recipe.images?.length" elevation="0" class="ma-4 overflow-hidden">
        <!-- 主图片 -->
        <v-img
          :src="getImageUrl(recipe.images[selectedImageIndex])"
          height="200"
          cover
          class="bg-surface-variant cursor-pointer"
          @click="openLightbox(selectedImageIndex)"
        >
          <template #placeholder>
            <div class="d-flex align-center justify-center fill-height bg-surface-variant">
              <v-progress-circular indeterminate color="primary" />
            </div>
          </template>
          <template #error>
            <div class="d-flex align-center justify-center fill-height bg-surface-variant">
              <v-icon size="64" color="medium-emphasis">mdi-food</v-icon>
            </div>
          </template>
          <!-- 图片数量角标 -->
          <div v-if="recipe.images.length > 1" class="position-absolute bottom-0 right-0 pa-2">
            <v-chip size="small" color="black" variant="flat" opacity="0.7">
              <v-icon start size="small">mdi-image-multiple</v-icon>
              {{ recipe.images.length }}
            </v-chip>
          </div>
        </v-img>
        <!-- 缩略图列表 -->
        <div v-if="recipe.images.length > 1" class="d-flex ga-2 pa-2 overflow-x-auto">
          <v-img
            v-for="(img, index) in recipe.images"
            :key="index"
            :src="getImageUrl(img)"
            width="60"
            height="60"
            cover
            class="rounded cursor-pointer thumbnail-item"
            :class="{ 'thumbnail-active': index === selectedImageIndex }"
            @click="selectedImageIndex = index"
          >
            <template #placeholder>
              <div class="d-flex align-center justify-center fill-height bg-surface-variant">
                <v-progress-circular indeterminate size="small" color="primary" />
              </div>
            </template>
            <template #error>
              <div class="d-flex align-center justify-center fill-height bg-surface-variant">
                <v-icon size="small" color="medium-emphasis">mdi-food</v-icon>
              </div>
            </template>
          </v-img>
        </div>
      </v-card>

      <!-- 成本信息卡片 -->
      <v-card elevation="0" class="ma-4" v-if="costData">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="tertiary">mdi-currency-cny</v-icon>
          成本估算
        </v-card-title>
        <v-divider />
        <v-card-text class="text-center py-6">
          <div class="text-h3 font-weight-bold text-tertiary">
            ¥{{ formatCost(costData.total_cost) }}
          </div>
        </v-card-text>
      </v-card>

      <!-- 成本趋势图表 -->
      <PriceTrendChart
        v-if="recipe"
        title="成本趋势"
        icon="mdi-chart-timeline-variant"
        icon-color="tertiary"
        unit="份"
        empty-text="暂无成本历史数据"
        :data="chartData"
        :loading="loadingCostHistory"
        color="#ff9800"
        class="ma-4"
      />

      <!-- 原料列表卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-food-apple-outline</v-icon>
          原料列表
          <v-chip size="small" class="ml-2" v-if="recipe.ingredients?.length">
            {{ recipe.ingredients.length }}
          </v-chip>
        </v-card-title>
        <v-divider />

        <v-card-text v-if="recipe.ingredients?.length" class="pa-0">
          <div
            v-for="(ingredient, index) in recipe.ingredients"
            :key="ingredient.id"
            class="ingredient-item"
            :class="{ 'mb-2': index < recipe.ingredients.length - 1 }"
          >
            <div class="d-flex align-center py-2">
              <!-- 名称：左对齐（可点击） -->
              <div
                class="ingredient-name flex-grow-1 text-body-2 ingredient-clickable"
                @click="goToIngredient(ingredient.ingredient_id)"
              >
                {{ ingredient.name }}
                <v-chip v-if="ingredient.is_optional" size="x-small" color="info" variant="flat" class="ml-1">可选</v-chip>
                <v-icon size="x-small" class="ml-1">mdi-chevron-right</v-icon>
              </div>
              <!-- 用量：右对齐 -->
              <div class="ingredient-quantity text-body-2 text-right mr-4" style="min-width: 80px">
                <span v-if="ingredient.quantity">{{ ingredient.quantity }} {{ ingredient.unit }}</span>
                <span v-else-if="ingredient.quantity_range">
                  {{ ingredient.quantity_range.min }}-{{ ingredient.quantity_range.max }} {{ ingredient.unit }}
                </span>
                <span v-else>-</span>
              </div>
              <!-- 成本：右对齐 -->
              <div class="ingredient-cost text-body-2 text-right d-flex align-center justify-end" style="min-width: 60px">
                <template v-if="getIngredientFallbackChain(ingredient)">
                  <v-tooltip location="top">
                    <template #activator="{ props }">
                      <v-icon
                        v-bind="props"
                        size="small"
                        color="info"
                        class="mr-1"
                      >
                        mdi-information
                      </v-icon>
                    </template>
                    <div>
                      <div class="text-caption">根据以下食材计算成本：</div>
                      <div class="text-body-2 font-weight-bold">{{ getIngredientFallbackChain(ingredient) }}</div>
                    </div>
                  </v-tooltip>
                </template>
                <span>¥{{ formatIngredientCost(ingredient) }}</span>
              </div>
            </div>
            <!-- 备注另起一行 -->
            <div v-if="ingredient.note" class="text-caption text-medium-emphasis pl-2 pb-1">
              备注：{{ ingredient.note }}
            </div>
          </div>
        </v-card-text>

        <v-card-text v-else class="text-center py-4 text-medium-emphasis">
          暂无原料数据
        </v-card-text>
      </v-card>

      <!-- 做法步骤卡片 -->
      <v-card elevation="0" class="ma-4" v-if="recipe.cooking_steps?.length">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-chef-hat</v-icon>
          做法步骤
        </v-card-title>
        <v-divider />

        <v-card-text>
          <v-timeline align="start" density="compact">
            <v-timeline-item
              v-for="(step, index) in recipe.cooking_steps"
              :key="index"
              size="small"
            >
              <template #icon>
                <v-avatar :color="getColorByIndex(index)" size="32">
                  {{ index + 1 }}
                </v-avatar>
              </template>

              <div class="step-content">
                {{ typeof step === 'object' ? step.content : step }}
              </div>
            </v-timeline-item>
          </v-timeline>
        </v-card-text>
      </v-card>

      <!-- 做法步骤空状态 -->
      <v-card elevation="0" class="ma-4" v-else>
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-chef-hat</v-icon>
          做法步骤
        </v-card-title>
        <v-divider />
        <v-card-text class="text-center py-4 text-medium-emphasis">
          暂无做法数据
        </v-card-text>
      </v-card>

      <!-- 营养信息卡片 -->
      <v-card elevation="0" class="ma-4" v-if="nutritionData">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="success">mdi-food-apple-outline</v-icon>
          营养成分（每份）
          <v-spacer />
          <v-btn
            v-if="otherNutrientsCount > 0"
            size="small"
            variant="text"
            color="primary"
            class="text-caption"
            @click="showAllNutrients = !showAllNutrients"
          >
            {{ showAllNutrients ? '收起' : `展开 +${otherNutrientsCount} 项` }}
            <v-icon :icon="showAllNutrients ? 'mdi-chevron-up' : 'mdi-chevron-down'" end />
          </v-btn>
        </v-card-title>
        <v-divider />

        <v-card-text class="pa-0">
          <div class="nutrition-header d-flex py-2 border-bottom">
            <div class="text-caption text-medium-emphasis ps-4 flex-grow-1">营养素</div>
            <div class="text-caption text-medium-emphasis text-end pe-4" style="min-width: 80px">数量</div>
            <div class="text-caption text-medium-emphasis text-end pe-4" style="min-width: 60px">NRV%</div>
          </div>
          <div
            v-for="item in displayNutritionItems"
            :key="item.key"
            class="nutrition-row d-flex py-2"
            :class="{ 'border-bottom': item.key !== displayNutritionItems[displayNutritionItems.length - 1].key }"
          >
            <div class="text-body-2 ps-4 flex-grow-1">{{ item.label }}</div>
            <div class="text-body-2 text-end pe-4" style="min-width: 80px">
              {{ formatNutritionValue(getNutritionValue(item), getNutritionUnit(item) || item.unit) }}
            </div>
            <div class="text-body-2 text-end pe-4" style="min-width: 60px">
              {{ getNutritionNRV(item) }}%
            </div>
          </div>

          <div class="mt-4 text-caption text-medium-emphasis ps-4">
            NRV = 营养素参考值百分比
          </div>
        </v-card-text>
      </v-card>

      <!-- 操作按钮 -->
      <div class="pa-4">
        <v-btn
          color="primary"
          variant="tonal"
          block
          prepend-icon="mdi-arrow-left"
          @click="goBack"
        >
          返回列表
        </v-btn>
      </div>
    </template>

    <!-- 图片灯箱 -->
    <v-dialog
      v-model="lightboxOpen"
      max-width="95vw"
      max-height="95vh"
      content-class="lightbox-dialog"
    >
      <v-card class="lightbox-card">
        <!-- 关闭按钮 -->
        <v-btn
          icon="mdi-close"
          variant="text"
          color="white"
          class="lightbox-close"
          @click="lightboxOpen = false"
        />

        <!-- 图片计数 -->
        <div v-if="recipe?.images && recipe.images.length > 1" class="lightbox-counter">
          {{ lightboxIndex + 1 }} / {{ recipe.images.length }}
        </div>

        <!-- 主图片 -->
        <img
          v-if="recipe?.images?.length"
          :src="getImageUrl(recipe.images[lightboxIndex])"
          class="lightbox-image"
          @click.stop
        />

        <!-- 左右切换按钮 -->
        <template v-if="recipe?.images && recipe.images.length > 1">
          <v-btn
            icon="mdi-chevron-left"
            variant="flat"
            color="black"
            opacity="0.5"
            class="lightbox-nav lightbox-prev"
            @click="prevImage"
          />
          <v-btn
            icon="mdi-chevron-right"
            variant="flat"
            color="black"
            opacity="0.5"
            class="lightbox-nav lightbox-next"
            @click="nextImage"
          />
        </template>

        <!-- 缩略图导航 -->
        <div v-if="recipe?.images && recipe.images.length > 1" class="lightbox-thumbnails">
          <v-img
            v-for="(img, index) in recipe.images"
            :key="index"
            :src="getImageUrl(img)"
            width="48"
            height="48"
            cover
            class="rounded cursor-pointer"
            :class="{ 'lightbox-thumbnail-active': index === lightboxIndex }"
            @click="lightboxIndex = index"
          >
            <template #placeholder>
              <div class="d-flex align-center justify-center fill-height bg-surface-variant">
                <v-progress-circular indeterminate size="x-small" color="primary" />
              </div>
            </template>
            <template #error>
              <div class="d-flex align-center justify-center fill-height bg-surface-variant">
                <v-icon size="x-small" color="medium-emphasis">mdi-food</v-icon>
              </div>
            </template>
          </v-img>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import PriceTrendChart from '@/components/charts/PriceTrendChart.vue'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { NUTRITION_LABEL_MAP, ENGLISH_TO_CHINESE_MAP } from '@/utils/nutritionLabels'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

interface CostHistoryRecord {
  date: string
  min_cost: number
  max_cost: number
  avg_cost: number
}

interface Recipe {
  id: number
  name: string
  description?: string
  category?: string
  difficulty?: 'simple' | 'medium' | 'hard'
  cooking_steps?: (string | { content: string })[]
  total_time_minutes?: number
  servings?: number
  tips?: string[]
  images?: string[]
  result_ingredient_id?: number
  created_at?: string
  updated_at?: string
  source?: string
  ingredients?: RecipeIngredient[]
}

interface RecipeIngredient {
  id: number
  ingredient_id: number
  name: string
  quantity?: number
  quantity_range?: { min: number; max: number }
  unit?: string
  is_optional?: boolean
  note?: string
}

interface CostBreakdownItem {
  ingredient_name: string
  original_ingredient_name?: string
  ingredient_id: number
  recipe_ingredient_id: number
  quantity: string
  unit_price: number
  cost: number
  fallback_chain?: string
}

interface CostData {
  total_cost: number | string
  per_serving_cost?: number | string
  cost_breakdown?: CostBreakdownItem[]
}

interface NutrientItem {
  value: number
  unit: string
  key?: string
  nrp_pct?: number
  standard?: string
}

interface PerServingNutrition {
  core_nutrients: Record<string, NutrientItem>
  all_nutrients?: Record<string, NutrientItem>
}

interface NutritionData {
  calories?: number
  protein?: number
  fat?: number
  carbs?: number
  fiber?: number
  sodium?: number
  per_serving_nutrition?: PerServingNutrition
}

const route = useRoute()
const router = useRouter()

const recipeId = computed(() => Number(route.params.id))

const recipe = ref<Recipe | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const costData = ref<CostData | null>(null)
const nutritionData = ref<NutritionData | null>(null)

// 图片灯箱相关
const selectedImageIndex = ref(0)
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

// 成本历史数据
const costHistoryRecords = ref<CostHistoryRecord[]>([])
const loadingCostHistory = ref(false)

// 核心营养素配置（默认显示的营养素）
const coreNutritionItems = [
  { key: '能量', label: '能量', unit: 'kcal' },
  { key: '蛋白质', label: '蛋白质', unit: 'g' },
  { key: '脂肪', label: '脂肪', unit: 'g' },
  { key: '碳水化合物', label: '碳水化合物', unit: 'g' },
  { key: '钠', label: '钠', unit: 'mg' }
]

// 营养素排序顺序（展开时这些营养素排在前面）
const nutrientSortOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '钠',
  '膳食纤维', '钙', '铁', '钾',
  '维生素A', '维生素B1', '维生素B2', '维生素B12', '维生素C',
  '维生素D', '维生素E', '维生素K'
]

// 展开状态
const showAllNutrients = ref(false)

// 营养素排序辅助函数
const sortNutrients = (items: any[]) => {
  return items.sort((a, b) => {
    const indexA = nutrientSortOrder.indexOf(a.key)
    const indexB = nutrientSortOrder.indexOf(b.key)

    // 如果都在排序列表中，按排序顺序
    if (indexA !== -1 && indexB !== -1) {
      return indexA - indexB
    }
    // 如果只有A在排序列表中，A排在前面
    if (indexA !== -1) {
      return -1
    }
    // 如果只有B在排序列表中，B排在前面
    if (indexB !== -1) {
      return 1
    }
    // 都不在排序列表中，按原顺序
    return 0
  })
}

// 根据展开状态返回要显示的营养素列表
const displayNutritionItems = computed(() => {
  if (!nutritionData.value?.per_serving_nutrition) return []

  const coreNutrients = nutritionData.value.per_serving_nutrition.core_nutrients || {}
  const allNutrients = nutritionData.value.per_serving_nutrition.all_nutrients || {}

  // 默认显示的5个营养素
  const defaultItems = coreNutritionItems
    .filter(item => coreNutrients[item.key])
    .map(item => ({
      key: item.key,
      label: item.label,
      unit: (coreNutrients[item.key] as any).unit || item.unit,
      isCore: true
    }))

  if (!showAllNutrients.value) {
    return defaultItems
  }

  // 获取默认显示的5个营养素的键集合
  const defaultKeys = new Set(coreNutritionItems.map(ci => ci.key))

  // 获取 core_nutrients 中的其他营养素（如膳食纤维、钙、铁等）
  const otherCoreNutrients = Object.keys(coreNutrients)
    .filter(key => !defaultKeys.has(key))
    .map(key => ({
      key: key,
      label: NUTRITION_LABEL_MAP[key] || key,
      unit: (coreNutrients[key] as any).unit || '',
      isCore: true
    }))

  // 获取 all_nutrients 中的其他营养素
  // 先按照中文名称分组，合并同一中文名称的多个英文键名的值
  const chineseKeyGroups = new Map<string, { keys: string[], totalValue: number, unit: string }>()

  Object.keys(allNutrients)
    .filter(key => {
      const data = allNutrients[key]
      return data && typeof data === 'object' && 'value' in data
    })
    .filter(key => {
      // 将英文键名转换为中文键名，然后检查是否是核心营养素
      const chineseKey = ENGLISH_TO_CHINESE_MAP[key] || key
      return !defaultKeys.has(chineseKey) // 排除默认显示的5个
    })
    .forEach(key => {
      const chineseKey = ENGLISH_TO_CHINESE_MAP[key] || key
      const data = allNutrients[key] as any

      if (!chineseKeyGroups.has(chineseKey)) {
        chineseKeyGroups.set(chineseKey, {
          keys: [],
          totalValue: 0,
          unit: data.unit || ''
        })
      }

      const group = chineseKeyGroups.get(chineseKey)!
      group.keys.push(key)
      group.totalValue += (data.value || 0)
      // 使用第一个遇到的单位
      if (!group.unit && data.unit) {
        group.unit = data.unit
      }
    })

  // 将分组后的数据转换为项目数组
  const otherAllNutrients = Array.from(chineseKeyGroups.entries())
    .map(([chineseKey, group]) => {
      // 使用第一个出现的英文键名作为 key
      const firstKey = group.keys[0]
      return {
        key: firstKey,
        label: NUTRITION_LABEL_MAP[chineseKey] || chineseKey,
        value: group.totalValue, // 使用合并后的值
        unit: group.unit,
        isCore: false
      }
    })

  // 合并其他营养素
  const otherItems = [...otherCoreNutrients, ...otherAllNutrients]

  // 排序
  const sortedOtherItems = sortNutrients(otherItems)

  return [...defaultItems, ...sortedOtherItems]
})

// 其他营养素数量（用于按钮文案）
const otherNutrientsCount = computed(() => {
  if (!nutritionData.value?.per_serving_nutrition) return 0

  const coreNutrients = nutritionData.value.per_serving_nutrition.core_nutrients || {}
  const allNutrients = nutritionData.value.per_serving_nutrition.all_nutrients || {}

  // 获取默认显示的5个营养素的键集合
  const defaultKeys = new Set(coreNutritionItems.map(ci => ci.key))

  // 计算 core_nutrients 中的其他营养素数量（如膳食纤维、钙、铁等）
  const otherCoreCount = Object.keys(coreNutrients).filter(key => !defaultKeys.has(key)).length

  // 计算 all_nutrients 中的其他营养素数量
  const seenChineseKeys = new Set<string>()
  const otherAllCount = Object.keys(allNutrients).filter(key => {
    const data = allNutrients[key]
    if (!data || typeof data !== 'object' || !('value' in data)) return false
    // 将英文键名转换为中文键名，然后检查是否是核心营养素
    const chineseKey = ENGLISH_TO_CHINESE_MAP[key] || key
    if (!defaultKeys.has(chineseKey) && !seenChineseKeys.has(chineseKey)) {
      seenChineseKeys.add(chineseKey)
      return true
    }
    return false
  }).length

  return otherCoreCount + otherAllCount
})

// 从后端返回的嵌套结构中提取营养值
// 注意：对于非核心营养素（isCore=false），displayItems 中已包含合并后的 value 和 unit
const getNutritionValue = (item: any) => {
  if (item.isCore) {
    // 核心营养素从 core_nutrients 获取完整数据（包括 NRP）
    if (!nutritionData.value?.per_serving_nutrition) return null
    const nutrient = nutritionData.value.per_serving_nutrition.core_nutrients?.[item.key]
    return nutrient?.value
  }

  // 其他营养素直接使用合并后的值
  return item.value
}

const getNutritionUnit = (item: any) => {
  if (item.isCore) {
    // 核心营养素从 core_nutrients 获取完整数据
    if (!nutritionData.value?.per_serving_nutrition) return null
    const nutrient = nutritionData.value.per_serving_nutrition.core_nutrients?.[item.key]
    return nutrient?.unit
  }

  // 其他营养素直接使用合并后的单位
  return item.unit
}

const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    // 加载菜谱详情
    const response = await api.get(`/recipes/${recipeId.value}`)
    recipe.value = response

    // 并行加载成本、营养和历史数据
    await Promise.all([
      loadCostData(),
      loadNutritionData(),
      loadCostHistory()
    ])
  } catch (e: any) {
    console.error('加载菜谱失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const loadCostData = async () => {
  try {
    const response = await api.get(`/recipes/${recipeId.value}/cost`)
    costData.value = response
  } catch (e) {
    console.error('加载成本失败', e)
    costData.value = null
  }
}

const loadNutritionData = async () => {
  try {
    const response = await api.get(`/recipes/${recipeId.value}/nutrition`)
    nutritionData.value = response
  } catch (e) {
    console.error('加载营养失败', e)
    nutritionData.value = null
  }
}

// 加载成本历史数据
const loadCostHistory = async () => {
  loadingCostHistory.value = true
  try {
    const response = await api.get(`/recipes/${recipeId.value}/cost-history-range?days=90`)
    // 转换数据格式
    costHistoryRecords.value = (response || []).map((record: any) => ({
      date: record.date,
      min_cost: record.min_cost,
      max_cost: record.max_cost,
      avg_cost: record.avg_cost
    }))
  } catch (e) {
    console.error('加载成本历史失败', e)
    costHistoryRecords.value = []
  } finally {
    loadingCostHistory.value = false
  }
}

// 转换为图表数据格式
const chartData = computed(() => {
  return costHistoryRecords.value.map(record => ({
    date: record.date,
    min: record.min_cost,
    max: record.max_cost,
    avg: record.avg_cost
  }))
})

const getImageUrl = (imagePath: string) => {
  if (imagePath.startsWith('http')) return imagePath
  if (imagePath.startsWith('/static/images/')) return `/api/v1${imagePath}`
  return `https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out/${imagePath}`
}

// 灯箱相关方法
const openLightbox = (index: number) => {
  lightboxIndex.value = index
  lightboxOpen.value = true
}

const prevImage = () => {
  if (recipe.value?.images && recipe.value.images.length > 0) {
    lightboxIndex.value = (lightboxIndex.value - 1 + recipe.value.images.length) % recipe.value.images.length
  }
}

const nextImage = () => {
  if (recipe.value?.images && recipe.value.images.length > 0) {
    lightboxIndex.value = (lightboxIndex.value + 1) % recipe.value.images.length
  }
}

const formatCost = (cost: number | string) => {
  const num = parseFloat(String(cost)) || 0
  return num.toFixed(2)
}

const formatNutritionValue = (value: number | undefined, unit: string) => {
  if (value === undefined || value === null) return '-'
  const num = parseFloat(String(value)) || 0
  return `${num.toFixed(1)} ${unit}`
}

// 格式化原料成本
const formatIngredientCost = (ingredient: RecipeIngredient) => {
  if (!costData.value?.cost_breakdown) return '-'
  const breakdown = costData.value.cost_breakdown as CostBreakdownItem[]
  // 使用 recipe_ingredient_id 来匹配，而不是 ingredient_id
  // 因为回退后的 ingredient_id 可能会变化，但 recipe_ingredient_id 保持不变
  const item = breakdown.find((b: CostBreakdownItem) => b.recipe_ingredient_id === ingredient.id)
  if (!item) return '-'
  return formatCost(item.cost || 0)
}

// 获取原料的回退链信息
const getIngredientFallbackChain = (ingredient: RecipeIngredient): string | null => {
  if (!costData.value?.cost_breakdown) return null
  const breakdown = costData.value.cost_breakdown as CostBreakdownItem[]
  // 使用 recipe_ingredient_id 来匹配，而不是 ingredient_id
  // 因为回退后的 ingredient_id 可能会变化，但 recipe_ingredient_id 保持不变
  const item = breakdown.find((b: CostBreakdownItem) => b.recipe_ingredient_id === ingredient.id)
  return item?.fallback_chain || null
}

// 获取原料的成本明细项
const getIngredientCostItem = (ingredient: RecipeIngredient): CostBreakdownItem | null => {
  if (!costData.value?.cost_breakdown) return null
  const breakdown = costData.value.cost_breakdown as CostBreakdownItem[]
  // 使用 recipe_ingredient_id 来匹配，而不是 ingredient_id
  // 因为回退后的 ingredient_id 可能会变化，但 recipe_ingredient_id 保持不变
  return breakdown.find((b: CostBreakdownItem) => b.recipe_ingredient_id === ingredient.id) || null
}

// 获取营养素NRV百分比
const getNutritionNRV = (item: any) => {
  if (!nutritionData.value?.per_serving_nutrition) return '-'

  let nutrient: any

  if (item.isCore) {
    nutrient = nutritionData.value.per_serving_nutrition.core_nutrients?.[item.key]
  } else {
    nutrient = nutritionData.value.per_serving_nutrition.all_nutrients?.[item.key]
  }

  if (!nutrient) return '-'

  // 如果 standard 是"无标准"或类似的，表示没有推荐摄入量，显示 "-"
  if (nutrient.standard === '无标准' || nutrient.standard === '无标准值') {
    return '-'
  }

  // 如果 nrp_pct 是 undefined 或 null，显示 "-"
  if (nutrient.nrp_pct === undefined || nutrient.nrp_pct === null) {
    return '-'
  }

  return nutrient.nrp_pct.toFixed(1)
}

const getColorByIndex = (index: number) => {
  const colors = ['primary', 'secondary', 'tertiary', 'success', 'warning']
  return colors[index % colors.length] || 'primary'
}

const goBack = () => {
  router.push('/recipes')
}

// 跳转到原料详情
const goToIngredient = (ingredientId: number) => {
  router.push(`/data/ingredients/${ingredientId}`)
}

// 监听路由参数变化，当菜谱 ID 变化时重新加载数据
watch(() => route.params.id, () => {
  if (route.params.id) {
    loadData()
  }
})

onMounted(loadData)
</script>

<style scoped>
.nutrition-item {
  background: rgb(var(--v-theme-surface-variant));
  text-align: center;
}

.step-content {
  line-height: 1.5;
  color: rgb(var(--v-theme-on-surface));
}

/* 原料列表样式 */
.ingredient-item {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
}

.ingredient-item:last-child {
  border-bottom: none;
}

/* 可点击的原料名称样式 */
.ingredient-clickable {
  cursor: pointer;
  transition: background-color 0.2s;
  padding: 4px 8px;
  margin: -4px -8px;
  border-radius: 4px;
}

.ingredient-clickable:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

/* 营养成分表格样式 */
.nutrition-header {
  background: rgb(var(--v-theme-surface-variant));
  font-weight: 500;
}

.nutrition-row:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

/* 缩略图样式 */
.thumbnail-item {
  flex-shrink: 0;
  border: 2px solid transparent;
  transition: border-color 0.2s, transform 0.2s;
}

.thumbnail-active {
  border-color: rgb(var(--v-theme-primary));
  transform: scale(1.05);
}

/* 灯箱样式 */
:deep(.lightbox-dialog) {
  margin: auto;
}

.lightbox-card {
  background: rgba(0, 0, 0, 0.95) !important;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px 20px;
  min-height: 300px;
}

.lightbox-close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
}

.lightbox-counter {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  color: white;
  font-size: 14px;
  z-index: 10;
}

.lightbox-image {
  max-width: 90vw;
  max-height: 70vh;
  object-fit: contain;
}

.lightbox-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  min-width: 48px;
  min-height: 48px;
}

.lightbox-prev {
  left: 12px;
}

.lightbox-next {
  right: 12px;
}

.lightbox-thumbnails {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  overflow-x: auto;
  max-width: 100%;
  padding: 8px 0;
}

.lightbox-thumbnail-active {
  border: 2px solid white !important;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
}

.cursor-pointer {
  cursor: pointer;
}
</style>
