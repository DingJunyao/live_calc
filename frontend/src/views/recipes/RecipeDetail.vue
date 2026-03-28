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
            @click="goToIngredient(ingredient.ingredient_id)"
          >
            <div class="d-flex align-center py-2">
              <!-- 名称：左对齐 -->
              <div class="ingredient-name flex-grow-1 text-body-2">
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
              <div class="ingredient-cost text-body-2 text-right" style="min-width: 60px">
                ¥{{ formatIngredientCost(ingredient) }}
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

// 定义所有营养素的中文名称映射
const nutritionLabelMap: Record<string, string> = {
  '蛋白质': '蛋白质',
  '脂肪': '脂肪',
  '碳水化合物': '碳水化合物',
  '膳食纤维': '膳食纤维',
  '钙': '钙',
  '铁': '铁',
  '钠': '钠',
  '钾': '钾',
  '镁': '镁',
  '磷': '磷',
  '锌': '锌',
  '铜': '铜',
  '锰': '锰',
  '硒': '硒',
  '维生素A': '维生素A',
  '维生素C': '维生素C',
  '维生素B1': '维生素B1',
  '维生素B2': '维生素B2',
  '维生素B3（烟酸）': '维生素B3（烟酸）',
  '维生素B3': '维生素B3（烟酸）',
  '维生素B5（泛酸）': '维生素B5（泛酸）',
  '维生素B5': '维生素B5（泛酸）',
  '维生素B6': '维生素B6',
  '维生素B12': '维生素B12',
  '维生素B12（强化）': '维生素B12（强化）',
  '维生素D': '维生素D',
  '维生素E': '维生素E',
  '维生素E（强化）': '维生素E（强化）',
  '维生素K': '维生素K',
  '叶酸': '叶酸',
  '生物素': '生物素',
  '胆碱': '胆碱',
  '饱和脂肪': '饱和脂肪',
  '单不饱和脂肪酸': '单不饱和脂肪',
  '多不饱和脂肪酸': '多不饱和脂肪',
  '反式脂肪酸': '反式脂肪',
  '胆固醇': '胆固醇',
  '总糖': '总糖',
  '蔗糖': '蔗糖',
  '葡萄糖': '葡萄糖',
  '果糖': '果糖',
  '半乳糖': '半乳糖',
  '乳糖': '乳糖',
  '麦芽糖': '麦芽糖',
  '淀粉': '淀粉',
  '水分': '水分',
  '灰分': '灰分',
  '酒精': '酒精',
  '咖啡因': '咖啡因',
  '可可碱': '可可碱',
  '视黄醇': '视黄醇',
  'α-胡萝卜素': 'α-胡萝卜素',
  'β-胡萝卜素': 'β-胡萝卜素',
  'β-隐黄质': 'β-隐黄质',
  '番茄红素': '番茄红素',
  '叶黄素和玉米黄质': '叶黄素和玉米黄质',
  'α-生育酚': 'α-生育酚',
  'β-生育酚': 'β-生育酚',
  'γ-生育酚': 'γ-生育酚',
  'δ-生育酚': 'δ-生育酚',
  'α-生育三烯酚': 'α-生育三烯酚',
  'β-生育三烯酚': 'β-生育三烯酚',
  'γ-生育三烯酚': 'γ-生育三烯酚',
  'δ-生育三烯酚': 'δ-生育三烯酚',
  '丁酸': '丁酸',
  '己酸': '己酸',
  '辛酸': '辛酸',
  '癸酸': '癸酸',
  '月桂酸': '月桂酸',
  '肉豆蔻酸': '肉豆蔻酸',
  '十五烷酸': '十五烷酸',
  '棕榈酸': '棕榈酸',
  '十七烷酸': '十七烷酸',
  '硬脂酸': '硬脂酸',
  '花生酸': '花生酸',
  '山嵛酸': '山嵛酸',
  '木焦油酸': '木焦油酸',
  '肉豆蔻油酸': '肉豆蔻油酸',
  '十五碳烯酸': '十五碳烯酸',
  '棕榈油酸': '棕榈油酸',
  '顺式-棕榈油酸': '棕榈油酸',
  '十七碳烯酸': '十七碳烯酸',
  '油酸': '油酸',
  '顺式-油酸': '油酸',
  '二十碳烯酸': '二十碳烯酸',
  '二十二碳烯酸': '二十二碳烯酸',
  '顺式-二十二碳烯酸': '二十二碳烯酸',
  '顺式-二十四碳烯酸': '二十四碳烯酸',
  '亚油酸': '亚油酸',
  '共轭亚油酸': '共轭亚油酸',
  '顺式-亚油酸': '亚油酸',
  '亚麻酸': '亚麻酸',
  'α-亚麻酸': 'α-亚麻酸',
  'γ-亚麻酸': 'γ-亚麻酸',
  '十八碳四烯酸': '十八碳四烯酸',
  '二十碳二烯酸': '二十碳二烯酸',
  '二十碳三烯酸': '二十碳三烯酸',
  '二高-γ-亚麻酸': '二高-γ-亚麻酸',
  '花生四烯酸': '花生四烯酸',
  '二十碳五烯酸': '二十碳五烯酸（EPA）',
  '二十二碳四烯酸': '二十二碳四烯酸',
  '二十二碳五烯酸': '二十二碳五烯酸（DPA）',
  '二十二碳六烯酸': '二十二碳六烯酸（DHA）',
  '反式-棕榈油酸': '反式-棕榈油酸',
  '反式-油酸': '反式-油酸',
  '反式-亚油酸': '反式-亚油酸',
  '反式-二十二碳烯酸': '反式-二十二碳烯酸',
  // 新增营养素映射
  '能量': '能量',
  'β-谷甾醇': 'β-谷甾醇',
  '丙氨酸': '丙氨酸',
  '丝氨酸': '丝氨酸',
  '二十一碳五烯酸': '二十一碳五烯酸',
  '亚油酸异构体': '亚油酸异构体',
  '亚麻酸异构体': '亚麻酸异构体',
  '亮氨酸': '亮氨酸',
  '十三烷酸': '十三烷酸',
  '单不饱和脂肪': '单不饱和脂肪',
  '单烯反式脂肪酸': '单烯反式脂肪酸',
  '反式-11-油酸': '反式-11-油酸',
  '反式-亚油酸二反式异构体': '反式-亚油酸二反式异构体',
  '多不饱和脂肪': '多不饱和脂肪',
  '多烯反式脂肪酸': '多烯反式脂肪酸',
  '天冬氨酸': '天冬氨酸',
  '异亮氨酸': '异亮氨酸',
  '植物固醇': '植物固醇',
  '氟': '氟',
  '甘氨酸': '甘氨酸',
  '甜菜碱': '甜菜碱',
  '精氨酸': '精氨酸',
  '组氨酸': '组氨酸',
  '维生素D2（麦角钙化醇）': '维生素D2（麦角钙化醇）',
  '维生素D3（胆钙化醇）': '维生素D3（胆钙化醇）',
  '维生素K1（二氢叶绿醌）': '维生素K1（二氢叶绿醌）',
  '维生素K2（甲萘醌-4）': '维生素K2（甲萘醌-4）',
  '缬氨酸': '缬氨酸',
  '羟脯氨酸': '羟脯氨酸',
  '胱氨酸': '胱氨酸',
  '脯氨酸': '脯氨酸',
  '色氨酸': '色氨酸',
  '苏氨酸': '苏氨酸',
  '苯丙氨酸': '苯丙氨酸',
  '菜油固醇': '菜油固醇',
  '蛋氨酸': '蛋氨酸',
  '谷氨酸': '谷氨酸',
  '豆固醇': '豆固醇',
  '赖氨酸': '赖氨酸',
  '酪氨酸': '酪氨酸'
}

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
      label: nutritionLabelMap[key] || key,
      unit: (coreNutrients[key] as any).unit || '',
      isCore: true
    }))

  // 获取 all_nutrients 中的其他营养素
  const otherAllNutrients = Object.keys(allNutrients)
    .filter(key => {
      const data = allNutrients[key]
      return data && typeof data === 'object' && 'value' in data
    })
    .filter(key => !defaultKeys.has(key)) // 排除默认显示的5个
    .map(key => ({
      key: key,
      label: nutritionLabelMap[key] || key,
      unit: (allNutrients[key] as any).unit || '',
      isCore: false
    }))

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
  const otherAllCount = Object.keys(allNutrients).filter(key => {
    const data = allNutrients[key]
    return data && typeof data === 'object' && 'value' in data && !defaultKeys.has(key)
  }).length

  return otherCoreCount + otherAllCount
})

// 从后端返回的嵌套结构中提取营养值
const getNutritionValue = (item: any) => {
  if (!nutritionData.value?.per_serving_nutrition) return null

  if (item.isCore) {
    const nutrient = nutritionData.value.per_serving_nutrition.core_nutrients?.[item.key]
    return nutrient?.value
  }

  const nutrient = nutritionData.value.per_serving_nutrition.all_nutrients?.[item.key]
  return nutrient?.value
}

const getNutritionUnit = (item: any) => {
  if (!nutritionData.value?.per_serving_nutrition) return null

  if (item.isCore) {
    const nutrient = nutritionData.value.per_serving_nutrition.core_nutrients?.[item.key]
    return nutrient?.unit
  }

  const nutrient = nutritionData.value.per_serving_nutrition.all_nutrients?.[item.key]
  return nutrient?.unit
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
  const breakdown = costData.value.cost_breakdown as any[]
  const item = breakdown.find((b: any) => b.ingredient_id === ingredient.ingredient_id)
  if (!item) return '-'
  return formatCost(item.cost || 0)
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
  cursor: pointer;
  transition: background-color 0.2s;
}

.ingredient-item:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.ingredient-item:last-child {
  border-bottom: none;
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
