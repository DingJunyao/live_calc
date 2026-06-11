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
      <v-btn
        icon="mdi-delete-outline"
        variant="text"
        color="error"
        :disabled="!recipe || deleting"
        @click="showDeleteDialog = true"
      />
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
      <!-- 上部分：图片、菜谱介绍、成本估算、成本趋势 响应式重排 -->
      <template v-if="recipe.images?.length">
        <!-- 有图片：左列=图片+介绍，右列=成本+趋势 -->
        <div class="recipe-top-grid has-images">
          <div class="recipe-left-col">
            <!-- 图片 -->
            <div class="grid-image">
              <v-card elevation="0" class="ma-4 overflow-hidden">
                <!-- 主图片 -->
                <v-img
                  :src="getImageUrl(recipe.images[selectedImageIndex])"
                  height="max(320px, 33vh)"
                  cover
                  class="bg-surface-variant cursor-pointer recipe-main-img"
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
            </div>

            <!-- 菜谱介绍 -->
            <div class="grid-description">
              <RecipeBasicCard
                :recipe="recipe"
                @saved="onBasicInfoSaved"
                @images-changed="onImagesChanged"
              />
            </div>
          </div>

          <div class="recipe-right-col">
            <!-- 成本估算 -->
            <div v-if="costData || loadingCostData" class="grid-cost">
              <v-card elevation="0" class="ma-4">
                <v-card-title class="d-flex align-center pb-2">
                  <v-icon start color="tertiary">mdi-currency-cny</v-icon>
                  成本估算
                </v-card-title>
                <v-divider />
                <v-card-text class="text-center py-6">
                  <div v-if="loadingCostData" class="text-h6 text-medium-emphasis">
                    <v-progress-circular indeterminate size="24" class="mr-2" />
                    计算中...
                  </div>
                  <div v-else class="text-h3 font-weight-bold text-tertiary">
                    ¥{{ formatCost((costData?.total_cost ?? 0) * servingRatio) }}
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <!-- 成本趋势 -->
            <div class="grid-trend">
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
                @filter-change="onCostTrendFilterChange"
              />
            </div>
          </div>
        </div>
      </template>
      <template v-else>
        <!-- 无图片：左列=成本+介绍，右列=趋势(占两行) -->
        <div class="recipe-top-grid no-images">
          <div class="recipe-left-col">
            <!-- 成本估算 -->
            <div v-if="costData || loadingCostData" class="grid-cost">
              <v-card elevation="0" class="ma-4">
                <v-card-title class="d-flex align-center pb-2">
                  <v-icon start color="tertiary">mdi-currency-cny</v-icon>
                  成本估算
                </v-card-title>
                <v-divider />
                <v-card-text class="text-center py-6">
                  <div v-if="loadingCostData" class="text-h6 text-medium-emphasis">
                    <v-progress-circular indeterminate size="24" class="mr-2" />
                    计算中...
                  </div>
                  <div v-else class="text-h3 font-weight-bold text-tertiary">
                    ¥{{ formatCost((costData?.total_cost ?? 0) * servingRatio) }}
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <!-- 菜谱介绍 -->
            <div class="grid-description">
              <RecipeBasicCard
                :recipe="recipe"
                @saved="onBasicInfoSaved"
                @images-changed="onImagesChanged"
              />
            </div>
          </div>

          <div class="recipe-right-col">
            <!-- 成本趋势 -->
            <div class="grid-trend">
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
                @filter-change="onCostTrendFilterChange"
              />
            </div>
          </div>
        </div>
      </template>

      <v-row no-gutters>
        <v-col cols="12" md="6">
          <RecipeIngredientCard
            :recipe="recipe"
            :cost-breakdown="costData?.cost_breakdown as any[]"
            :display-servings="displayServings"
            :servings="recipe.servings"
            @saved="onRecipeSaved"
          />
        </v-col>
        <v-col cols="12" md="6">
          <RecipeStepCard
            :recipe="recipe"
            @saved="onRecipeSaved"
          />
        </v-col>
      </v-row>

      <!-- Row 4: 营养成分 | 小贴士 -->
      <v-row no-gutters>
        <v-col cols="12" md="6">
          <!-- 营养信息卡片 -->
          <v-card elevation="0" class="ma-4" v-if="nutritionData || loadingNutritionData">
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
              <div v-if="loadingNutritionData" class="text-center py-6">
                <v-progress-circular indeterminate size="28" class="mb-2" />
                <div class="text-body-2 text-medium-emphasis">计算中...</div>
              </div>
              <template v-else>
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
              </template>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <RecipeTipCard
            :recipe="recipe"
            @saved="onRecipeSaved"
          />
        </v-col>
      </v-row>

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
      <!-- 删除确认对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center text-error">
          <v-icon start color="error">mdi-alert-circle-outline</v-icon>
          删除菜谱
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <p>确定要删除「{{ recipe?.name }}」吗？</p>
          <p class="text-caption text-medium-emphasis mt-1">此操作将软删除菜谱，可在后台恢复。</p>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false" :disabled="deleting">取消</v-btn>
          <v-btn
            color="error"
            variant="tonal"
            :loading="deleting"
            @click="handleDelete"
          >删除</v-btn>
        </v-card-actions>
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
import { usePageTitle } from '@/composables/usePageTitle'
import { NUTRITION_LABEL_MAP, ENGLISH_TO_CHINESE_MAP } from '@/utils/nutritionLabels'
import RecipeBasicCard from '@/components/recipes/RecipeBasicCard.vue'
import RecipeIngredientCard from '@/components/recipes/RecipeIngredientCard.vue'
import RecipeStepCard from '@/components/recipes/RecipeStepCard.vue'
import RecipeTipCard from '@/components/recipes/RecipeTipCard.vue'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { setDetailTitle } = usePageTitle()

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
  quantity?: number | string
  quantity_range?: { min: number; max: number }
  original_quantity?: string
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
  aggregation_chain?: string
  cost_source?: string
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
const loadingCostData = ref(false)
const loadingNutritionData = ref(false)
const displayServings = ref(1)
const servingRatio = computed(() => {
  const orig = recipe.value?.servings || 1
  return displayServings.value / orig
})

// 图片灯箱相关
const selectedImageIndex = ref(0)
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

// 成本历史数据
const costHistoryRecords = ref<CostHistoryRecord[]>([])
const loadingCostHistory = ref(false)

// 已加载的最大天数（从 0 开始，每次加载成功后更新）
const maxDaysLoaded = ref(0)

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
    const response = await api.get(`/recipes/${recipeId.value}`)
    recipe.value = response
    setDetailTitle(response.name, '菜谱', '菜谱详情')
    displayServings.value = response.servings || 1
    // 基本数据到位，立即渲染页面
    loading.value = false

    // 后台分别加载成本、营养和成本历史，互不影响
    loadCostData()
    loadNutritionData()
    loadCostHistoryInBatches()
  } catch (e: any) {
    console.error('加载菜谱失败', e)
    error.value = e.message || '加载失败'
    loading.value = false
  }
}

const loadCostData = async () => {
  loadingCostData.value = true
  try {
    const response = await api.get(`/recipes/${recipeId.value}/cost`)
    costData.value = response
  } catch (e) {
    console.error('加载成本失败', e)
    costData.value = null
  } finally {
    loadingCostData.value = false
  }
}

const loadNutritionData = async () => {
  loadingNutritionData.value = true
  try {
    const response = await api.get(`/recipes/${recipeId.value}/nutrition`)
    nutritionData.value = response
  } catch (e) {
    console.error('加载营养失败', e)
    nutritionData.value = null
  } finally {
    loadingNutritionData.value = false
  }
}

// 已尝试过的加载范围（避免空结果重复请求）
const attemptedRanges = new Set<string>()

// 串行队列：确保同时只有一个成本历史加载请求在跑
let costHistoryQueue = Promise.resolve()

// 加载成本历史数据（纯数据加载，不控制 loadingCostHistory）
const loadCostHistory = async (days = 90, offsetDays = 0) => {
  const response = await api.get(`/recipes/${recipeId.value}/cost-history-range`, {
    params: { days, offset_days: offsetDays }
  })
  // 转换数据格式
  const records = (response || []).map((record: any) => ({
    date: record.date,
    min_cost: record.min_cost,
    max_cost: record.max_cost,
    avg_cost: record.avg_cost
  }))
  if (records.length === 0) return  // 无数据时只标记已尝试，不更新 maxDaysLoaded
  // 合并到已有的历史数据中
  if (offsetDays > 0) {
    costHistoryRecords.value = [...records, ...costHistoryRecords.value]
  } else {
    costHistoryRecords.value = records
  }
  // 更新已加载天数范围（仅在获取到数据后更新）
  maxDaysLoaded.value = Math.max(maxDaysLoaded.value, offsetDays + days)
}

// 通过串行队列执行加载（参数为目标总天数，运行时会动态算还差多少）
const enqueueCostHistory = async (targetDays: number, showLoading: boolean) => {
  const rangeKey = `target_${targetDays}`
  if (targetDays <= maxDaysLoaded.value) return
  if (attemptedRanges.has(rangeKey)) {
    // 已在加载中，但仍需等待结果（让调用方显示转圈）
    await costHistoryQueue
    return
  }
  attemptedRanges.add(rangeKey)

  const promise = costHistoryQueue.then(async () => {
    // 动态计算还需要加载多少天
    const remaining = targetDays - maxDaysLoaded.value
    if (remaining <= 0) return
    if (showLoading) loadingCostHistory.value = true
    try {
      await loadCostHistory(remaining, maxDaysLoaded.value)
    } catch (e) {
      console.error('加载成本历史失败', e)
    } finally {
      if (showLoading) loadingCostHistory.value = false
    }
  })
  costHistoryQueue = promise
  return promise
}

// 首次加载30天（显示loading），不再预加载后续数据
// 用户点「季」「年」时按需加载
const loadCostHistoryInBatches = async () => {
  await enqueueCostHistory(30, true)
}

// 成本趋势筛选切换时，按需加载更多数据
const onCostTrendFilterChange = async (filter: 'week' | 'month' | 'quarter' | 'year') => {
  const targetDays: Record<string, number> = {
    week: 7,
    month: 30,
    quarter: 90,
    year: 365,
  }
  const days = targetDays[filter] || 90
  if (days > maxDaysLoaded.value) {
    loadingCostHistory.value = true  // 立即显示转圈
    await enqueueCostHistory(days, true)
  }
  // 请求完成或已在队列中等候完成，停止转圈
  loadingCostHistory.value = false
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
  return `${import.meta.env.VITE_DATA_REPO_IMAGE_BASE || 'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out'}/${imagePath}`
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

// 保存事件处理：更新本地 recipe 数据并重设标题
const onRecipeSaved = (updatedRecipe: any) => {
  if (recipe.value) {
    recipe.value = { ...recipe.value, ...updatedRecipe }
  }
  // 重新加载成本数据（原料变更影响成本）
  loadCostData()
}

// 基本信息保存事件
const onBasicInfoSaved = (updatedRecipe: any) => {
  if (recipe.value) {
    recipe.value = { ...recipe.value, ...updatedRecipe }
    if (updatedRecipe.name) {
      setDetailTitle(updatedRecipe.name, '菜谱', '菜谱详情')
    }
  }
}

// 图片列表变更时刷新 recipe 数据（保持图片区域同步）
const onImagesChanged = () => {
  loadData()
}

// 删除菜谱
const showDeleteDialog = ref(false)
const deleting = ref(false)

const handleDelete = async () => {
  deleting.value = true
  try {
    await api.delete(`/recipes/${recipeId.value}`)
    showDeleteDialog.value = false
    router.push('/recipes')
  } catch (e: any) {
    console.error('删除菜谱失败', e)
  } finally {
    deleting.value = false
  }
}

const goBack = () => {
  router.back()
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

/* 上部分 Flex 布局 — 桌面端两列独立排列 */
@media (min-width: 960px) {
  .recipe-top-grid {
    display: flex;
    flex-direction: row;
  }

  .recipe-top-grid > div {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .recipe-top-grid.has-images {
    align-items: flex-start;
  }

  .recipe-top-grid.no-images {
    align-items: stretch;
  }

  .recipe-top-grid.no-images .grid-trend {
    flex: 1;
  }
}
</style>
