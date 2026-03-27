<template>
  <v-container fluid class="pa-0">
    <!-- 顶部导航 -->
    <v-app-bar elevation="0" color="background">
      <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
      <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
      <v-app-bar-title class="text-h6 text-truncate">
        {{ recipe?.name || '菜谱详情' }}
      </v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadData" />
      </template>
    </v-app-bar>

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
          <div class="text-caption text-medium-emphasis mt-2">
            每份约 ¥{{ formatCost(costData.per_serving_cost) }}
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

        <v-list lines="two" v-if="recipe.ingredients?.length">
          <v-list-item
            v-for="ingredient in recipe.ingredients"
            :key="ingredient.id"
          >
            <template #prepend>
              <v-avatar color="secondary" size="40">
                <span class="text-white font-weight-bold">{{ ingredient.name?.charAt(0) }}</span>
              </v-avatar>
            </template>

            <v-list-item-title>{{ ingredient.name }}</v-list-item-title>
            <v-list-item-subtitle>
              <span v-if="ingredient.quantity">{{ ingredient.quantity }} {{ ingredient.unit }}</span>
              <span v-else-if="ingredient.quantity_range">
                {{ ingredient.quantity_range.min }} - {{ ingredient.quantity_range.max }} {{ ingredient.unit }}
              </span>
              <span v-else>-</span>
              <v-chip v-if="ingredient.is_optional" size="x-small" color="info" variant="flat" class="ml-2">可选</v-chip>
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>

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
        </v-card-title>
        <v-divider />

        <v-card-text>
          <v-row dense>
            <v-col
              v-for="item in nutritionItems"
              :key="item.key"
              cols="6"
              sm="4"
            >
              <div class="nutrition-item pa-3 rounded">
                <div class="text-caption text-medium-emphasis">{{ item.label }}</div>
                <div class="text-h6 font-weight-bold">
                  {{ formatNutritionValue(nutritionData[item.key], item.unit) }}
                </div>
              </div>
            </v-col>
          </v-row>

          <div class="mt-4 text-caption text-medium-emphasis">
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import PriceTrendChart from '@/components/charts/PriceTrendChart.vue'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'

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

interface CostData {
  total_cost: number | string
  per_serving_cost: number | string
}

interface NutritionData {
  calories?: number
  protein?: number
  fat?: number
  carbs?: number
  fiber?: number
  sodium?: number
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

const nutritionItems = [
  { key: 'calories', label: '热量', unit: 'kcal' },
  { key: 'protein', label: '蛋白质', unit: 'g' },
  { key: 'fat', label: '脂肪', unit: 'g' },
  { key: 'carbs', label: '碳水', unit: 'g' },
  { key: 'fiber', label: '膳食纤维', unit: 'g' },
  { key: 'sodium', label: '钠', unit: 'mg' }
]

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
    nutritionData.value = response.per_serving || response
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

const getColorByIndex = (index: number) => {
  const colors = ['primary', 'secondary', 'tertiary', 'success', 'warning']
  return colors[index % colors.length] || 'primary'
}

const goBack = () => {
  router.push('/recipes')
}

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
