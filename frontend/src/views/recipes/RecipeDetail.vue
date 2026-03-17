<template>
  <PageHeader :title="recipe?.name || '菜谱详情'" :show-back="true">
    <template #extra v-if="recipe && !isImportedRecipe(recipe)">
      <button @click="editRecipe" class="btn-square" title="编辑">
        <i class="mdi mdi-pencil"></i>
      </button>
    </template>
  </PageHeader>

  <div class="recipe-detail">
    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="!recipe" class="empty-state">
      菜谱不存在
    </div>

    <div v-else class="recipe-content">
      <!-- 菜谱图片画廊 -->
      <div v-if="recipe.images && recipe.images.length > 0" class="recipe-gallery">
        <!-- 大图区域 -->
        <div class="gallery-main" @click="openFullscreen">
          <img
            :src="getImageUrl(recipe.images[currentImageIndex])"
            :alt="`${recipe.name} 图片 ${currentImageIndex + 1}`"
            class="main-image"
            @error="handleImageError"
          />
          <div class="gallery-counter">{{ currentImageIndex + 1 }} / {{ recipe.images.length }}</div>
          <button class="gallery-btn prev" @click.stop="prevImage" v-if="recipe.images.length > 1">
            <i class="mdi mdi-chevron-left"></i>
          </button>
          <button class="gallery-btn next" @click.stop="nextImage" v-if="recipe.images.length > 1">
            <i class="mdi mdi-chevron-right"></i>
          </button>
        </div>

        <!-- 缩略图区域 -->
        <div class="gallery-thumbnails">
          <div
            v-for="(image, index) in recipe.images"
            :key="index"
            class="thumbnail"
            :class="{ active: index === currentImageIndex }"
            @click="currentImageIndex = index as number"
          >
            <img
              :src="getImageUrl(image)"
              :alt="`${recipe.name} 缩略图 ${Number(index) + 1}`"
              @error="handleThumbnailError"
            />
          </div>
        </div>
      </div>

      <!-- 基本信息 -->
      <div class="info-card">
        <h2>基本信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">预计成本:</span>
            <span class="value" v-if="recipe.costData">¥{{ parseFloat(parseFloat(recipe.costData.total_cost).toFixed(2)) }}</span>
            <span class="value" v-else>¥{{ recipe.estimated_cost ? parseFloat(parseFloat(recipe.estimated_cost).toFixed(2)) : '0' }}</span>
          </div>
          <div class="info-item">
            <span class="label">分类:</span>
            <span class="value">{{ recipe.category || '自定义' }}</span>
          </div>
          <div class="info-item">
            <span class="label">难度:</span>
            <span class="value">{{ getDifficultyText(recipe.difficulty) }}</span>
          </div>
          <div class="info-item">
            <span class="label">总用时:</span>
            <span class="value">{{ recipe.total_time_minutes || '-' }} 分钟</span>
          </div>
        </div>
        <div v-if="isImportedRecipe(recipe)" class="recipe-label">
          <span class="label-imported">导入菜谱</span>
        </div>
      </div>

      <!-- 原料列表 -->
      <div class="info-card">
        <h2>原料</h2>
        <div class="servings-info" v-if="recipe.servings">
          <span class="label">份量:</span>
          <span class="value">{{ recipe.servings }} 人份</span>
        </div>
        <div v-if="recipe.ingredients && recipe.ingredients.length > 0" class="ingredient-list">
          <div v-for="item in recipe.ingredients" :key="item.id" class="ingredient-item">
            <div class="ingredient-row">
              <div class="ingredient-name-col">
                <router-link :to="`/items/ingredient/${item.ingredient_id}`" class="ingredient-link" v-if="item.ingredient_id">
                  <span class="ingredient-name">{{ item.name }}</span>
                </router-link>
                <span class="ingredient-name" v-else>{{ item.name }}</span>
                <span v-if="item.is_optional" class="optional-badge">可选</span>
              </div>
              <div class="ingredient-amount-col">
                <span class="ingredient-amount">
                  <span v-if="item.quantity && item.quantity !== 'null' && item.quantity !== 'None' && item.quantity !== 'undefined'">{{ item.quantity }} {{ item.unit }}</span>
                  <span v-else-if="item.quantity_range && typeof item.quantity_range === 'object'">
                    {{ item.quantity_range.min }} - {{ item.quantity_range.max }} {{ item.unit }}
                  </span>
                  <span v-else>-</span>
                </span>
              </div>
              <div class="ingredient-cost-col">
                <div class="cost-wrapper" v-if="item.costInfo && item.costInfo.cost !== undefined && item.costInfo.cost !== null && item.quantity !== 'None' && item.quantity !== 'null' && item.quantity !== null && item.quantity !== undefined">
                  <!-- 回退标记 -->
                  <span
                    v-if="item.costInfo.fallback_chain"
                    class="fallback-icon"
                    @click.stop="showFallbackTooltip(item.costInfo.fallback_chain, $event)"
                    title="点击查看价格来源"
                  >
                    <i class="mdi mdi-information-outline"></i>
                  </span>
                  <span class="cost-value">¥{{ parseFloat(item.costInfo.cost).toFixed(2) }}</span>
                </div>
                <div class="cost-wrapper" v-else-if="item.costInfo && item.costInfo.cost === 0 && item.quantity !== 'None' && item.quantity !== 'null' && item.quantity !== null && item.quantity !== undefined">
                  <span class="cost-value">¥0.00</span>
                </div>
                <span class="cost-unavailable" v-else>-</span>
              </div>
            </div>
            <div v-if="item.note" class="ingredient-note">{{ item.note }}</div>
          </div>
        </div>
        <div v-else class="empty-text">暂无原料数据</div>
      </div>

      <!-- 做法 -->
      <div class="info-card">
        <h2>做法</h2>
        <div v-if="recipe.cooking_steps && recipe.cooking_steps.length > 0" class="cooking-steps">
          <div v-for="(stepItem, index) in recipe.cooking_steps" :key="index" class="step-item">
            <span class="step-number">{{ Number(index) + 1 }}</span>
            <span class="step-content">{{ typeof stepItem === 'object' ? stepItem.content : stepItem }}</span>
          </div>
        </div>
        <div v-else class="empty-text">暂无做法数据</div>
      </div>

      <!-- 成本趋势 -->
      <CostChartSection v-if="costHistoryRecords.length > 0" :records="costHistoryRecords || []" />

      <!-- 营养成分 -->
      <div class="info-card" v-if="recipe && recipe.nutrition && recipe.nutrition.per_serving_nutrition && recipe.nutrition.per_serving_nutrition.core_nutrients">
        <h2>营养成分（每份）</h2>
        <div class="info-grid">
          <template
            v-for="nutrientName in standardNutrientOrder"
            :key="nutrientName"
          >
            <div
              v-if="recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]"
              class="info-item nutrition-item"
            >
              <div class="nutrient-info">
                <span class="label">{{ nutrientName }}:</span>
                <div class="nutrient-value-wrapper">
                  <!-- 营养回退标记 -->
                  <span
                    v-if="checkNutrientUsedFallback(nutrientName)"
                    class="fallback-icon nutrient-fallback-icon"
                    @click.stop="showNutrientTooltip(`使用回退食材数据：${nutrientName}`, $event)"
                    title="点击查看数据来源"
                  >
                    <i class="mdi mdi-information-outline"></i>
                  </span>
                  <span class="value">
                    {{ recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]?.value !== undefined ? parseFloat(parseFloat(recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName].value).toFixed(3)) : '0' }}
                    {{ recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]?.unit || getDefaultUnit(nutrientName) }}
                  </span>
                </div>
              </div>
              <div class="nutrient-actions">
                <NutritionProgressBar
                  v-if="recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]"
                  :percentage="recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName].nrp_pct || 0"
                  :show-percentage="true"
                />
              </div>
            </div>
          </template>

          <!-- 显示其他不在标准顺序中的营养素 -->
          <div
            v-for="(nonStdItem, idx) in getNonStandardNutrients()"
            :key="idx"
            class="info-item nutrition-item"
          >
            <div class="nutrient-info">
              <span class="label">{{ nonStdItem[0] }}:</span>
              <span class="value">
                {{ (nonStdItem[1] as any)?.value !== undefined ? parseFloat(parseFloat((nonStdItem[1] as any).value).toFixed(3)) : '0' }}
                {{ (nonStdItem[1] as any)?.unit || getDefaultUnit(nonStdItem[0]) }}
              </span>
            </div>
            <div class="nutrient-actions">
              <NutritionProgressBar
                v-if="nonStdItem[1]"
                :percentage="(nonStdItem[1] as any)?.nrp_pct || 0"
                :show-percentage="true"
              />
            </div>
          </div>
        </div>
        <div class="nrp-legend">
          <span class="legend-icon">📊</span>
          <span class="legend-text">NRV = 营养素参考值百分比</span>
        </div>
      </div>
    </div>

    <!-- 回退 tooltip -->
    <div
      v-if="fallbackTooltip.show"
      class="fallback-tooltip"
      @click="closeTooltip"
    >
      <div class="tooltip-container" :style="{ left: fallbackTooltip.x + 'px', top: fallbackTooltip.y + 'px' }">
        <div class="tooltip-content">
          <i class="mdi mdi-information-outline"></i>
          <span>{{ fallbackTooltip.message }}</span>
        </div>
        <div class="tooltip-arrow"></div>
      </div>
    </div>

    <!-- 营养回退 tooltip -->
    <div
      v-if="nutrientTooltip.show"
      class="fallback-tooltip"
      @click="closeTooltip"
    >
      <div class="tooltip-container" :style="{ left: nutrientTooltip.x + 'px', top: nutrientTooltip.y + 'px' }">
        <div class="tooltip-content">
          <i class="mdi mdi-information-outline"></i>
          <span>{{ nutrientTooltip.message }}</span>
        </div>
        <div class="tooltip-arrow"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api, recipeAPI, type CostRangeRecord } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import NutritionProgressBar from '@/components/NutritionProgressBar.vue'
import CostChartSection from './components/CostChartSection.vue'

const route = useRoute()
const recipe = ref<any>(null)
const loading = ref(true)
const currentImageIndex = ref(0)

// 食材贡献分解功能状态
const showIngredientBreakdown = ref(false)  // 全局显示/隐藏
const expandedNutrients = ref<Record<string, boolean>>({})  // 各营养素展开状态

// 回退 tooltip 状态
const fallbackTooltip = ref({
  show: false,
  message: '',
  x: 0,
  y: 0
})

// 营养回退 tooltip 状态
const nutrientTooltip = ref({
  show: false,
  message: '',
  x: 0,
  y: 0
}) as any

// 成本历史数据
const costHistoryRecords = ref<CostRangeRecord[]>([])
const loadingCostHistory = ref(false)

// 加载成本历史数据
async function loadCostHistory(recipeId: string) {
  loadingCostHistory.value = true
  try {
    costHistoryRecords.value = await recipeAPI.getCostHistoryRange(Number(recipeId), 90)
    console.log('成本历史数据:', costHistoryRecords.value)
  } catch (error) {
    console.error('Failed to load cost history:', error)
    costHistoryRecords.value = []
  } finally {
    loadingCostHistory.value = false
  }
}

onMounted(async () => {
  const recipeId = route.params.id as string
  await loadRecipe()
  await loadCostHistory(recipeId)
  // 监听键盘事件
  window.addEventListener('keydown', handleKeydown)
  // 点击外部关闭 tooltip
  document.addEventListener('click', handleOutsideClick)
})

// 组件卸载时移除监听器
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', handleOutsideClick)
})

// 点击外部关闭 tooltip
function handleOutsideClick(event: MouseEvent) {
  if (fallbackTooltip.value.show) {
    closeTooltip()
  }
}

// 查找食材ID
async function findIngredientId(ingredientName: string) {
  try {
    // 尝试使用 ingredients API 获取ID
    const searchResponse = await api.get(`/ingredients/search-by-name/${encodeURIComponent(ingredientName)}`)
    if (searchResponse && Array.isArray(searchResponse) && searchResponse.length > 0) {
      return searchResponse[0].id
    }

    // 如果上面的方法没找到，尝试使用 nutrition API
    const nutritionSearch = await api.get(`/nutrition/search?q=${encodeURIComponent(ingredientName)}&limit=1`)
    if (nutritionSearch && Array.isArray(nutritionSearch) && nutritionSearch.length > 0) {
      return nutritionSearch[0].id
    }

    return null
  } catch (error) {
    console.error(`Failed to find ingredient ID for ${ingredientName}:`, error)
    return null
  }
}

async function loadRecipe() {
  loading.value = true
  try {
    const recipeId = route.params.id
    const data = await api.get(`/recipes/${recipeId}`)
    recipe.value = data

    // 尝试获取营养数据
    try {
      const nutritionData = await api.get(`/recipes/${recipeId}/nutrition`)
      recipe.value.nutrition = nutritionData

      // 加载成本数据
      try {
        const costData = await api.get(`/recipes/${recipeId}/cost`)
        recipe.value.costData = costData
        console.log('菜谱成本数据:', costData) // 调试SB问题
      } catch (error) {
        console.error('Failed to load cost data:', error)
        recipe.value.costData = null
        // 不设置默认值，让模板显示备用值
      }

      // 加载成本历史数据
      await loadCostHistory(recipeId)
    } catch (e) {
      // 营养数据可能不存在，忽略错误
      console.log('No nutrition data available')
    }

    // 加载原料成本数据并匹配到食材上
    try {
      if (recipe.value.ingredients && recipe.value.costData && recipe.value.costData.cost_breakdown) {
        // 先将成本数据匹配到相应食材上
        // 修改匹配逻辑：后端现在返回recipe_ingredient_id，我们应该利用这个信息
        const updatedIngredients = []
        for (const ingredient of recipe.value.ingredients) {
          // 查找成本数据时，如果有recipe_ingredient_id，优先使用它
          // 否则回退到原来的名称匹配
          let costInfo = null

          // 如果ingredient对象上有id（这应该是recipe_ingredient的id），则优先匹配
          if (ingredient.id) {
            costInfo = recipe.value.costData.cost_breakdown.find((cost: any) =>
              cost.recipe_ingredient_id === ingredient.id
            )
          }

          // 如果没找到，尝试按名称匹配（保持向后兼容）
          if (!costInfo) {
            costInfo = recipe.value.costData.cost_breakdown.find((cost: any) =>
              cost.ingredient_name === ingredient.name
            )
          }

          updatedIngredients.push({
            ...ingredient as any,
            ingredient_id: null, // 先设为null，稍后再更新
            costInfo: costInfo || null
          })
        }
        
        recipe.value.ingredients = updatedIngredients

        // 异步获取食材ID以提高性能
        for (let i = 0; i < recipe.value.ingredients.length; i++) {
          const ingredientId = await findIngredientId(recipe.value.ingredients[i].name)
          if (ingredientId) {
            recipe.value.ingredients[i].ingredient_id = ingredientId
          }
        }
      }
    } catch (e) {
      console.error('Failed to match cost data to ingredients:', e)
    }
  } catch (error) {
    console.error('Failed to load recipe:', error)
  } finally {
    loading.value = false
  }
}

const standardNutrientOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '膳食纤维',
  '钙', '铁', '钠', '钾', '维生素A', '维生素C',
  '维生素B1', '维生素B2', '维生素B12', '维生素D',
  '维生素E', '维生素K'
]

function getDefaultUnit(nutrientName: string): string {
  const defaultUnits: Record<string, string> = {
    '能量': 'kJ',
    '蛋白质': 'g',
    '脂肪': 'g',
    '碳水化合物': 'g',
    '膳食纤维': 'g',
    '钙': 'mg',
    '铁': 'mg',
    '钠': 'mg',
    '钾': 'mg',
    '维生素A': 'μg',
    '维生素C': 'mg',
    '维生素B1': 'mg',
    '维生素B2': 'mg',
    '维生素B12': 'μg',
    '维生素D': 'μg',
    '维生素E': 'mg',
    '维生素K': 'μg'
  }
  return defaultUnits[nutrientName] || 'g'
}

function getNonStandardNutrients(): Array<[string, any]> {
  if (!recipe.value?.nutrition?.per_serving_nutrition?.core_nutrients) return []

  const coreNutrients = recipe.value.nutrition.per_serving_nutrition.core_nutrients
  return Object.entries(coreNutrients).filter(([name]) => !standardNutrientOrder.includes(name))
}

// 食材贡献分解功能
// 切换全局食材贡献显示
function toggleIngredientBreakdown() {
  showIngredientBreakdown.value = !showIngredientBreakdown.value
}

// 切换特定营养素的展开状态
function toggleNutrientBreakdown(nutrientName: string) {
  expandedNutrients.value[nutrientName] = !expandedNutrients.value[nutrientName]
}

// 计算各食材对特定营养素的贡献
function getNutrientContributions(nutrientName: string) {
  // 从 nutrition.ingredient_details 获取数据
  const ingredientDetails = recipe.value?.nutrition?.ingredient_details || []

  // 计算贡献百分比并排序
  const contributions = ingredientDetails.map((detail: any) => {
    const contribution = detail.nutrition_contribution?.[nutrientName] || {}
    return {
      recipe_ingredient_id: detail.recipe_ingredient_id,  // 添加recipe_ingredient_id
      ingredient_name: detail.ingredient_name,
      quantity: detail.quantity,
      unit: detail.unit,
      value: contribution.value || 0,
      value_unit: contribution.unit || '',
      percentage: contribution.nrp_pct || 0
    }
  })

  // 过滤掉贡献为0的项目并按贡献百分比从高到低排序
  return contributions
    .filter((item: any) => item.percentage > 0 || item.value > 0)
    .sort((a: any, b: any) => b.percentage - a.percentage)
}

function isImportedRecipe(recipe: any) {
  return recipe.source && !recipe.user_id
}

function getRecipeSource(recipe: any) {
  if (recipe.source) {
    return recipe.source
  }
  return '个人创建'
}

function getDifficultyText(difficulty: string | undefined) {
  const difficultyMap: { [key: string]: string } = {
    'simple': '简单',
    'medium': '中等',
    'hard': '困难'
  }
  return difficultyMap[difficulty || '未知']
}

function editRecipe() {
  alert('编辑功能将在后续版本中实现')
}

function getImageUrl(imagePath: string) {
  // 如果是本地静态文件路径（/static/images/），转换为完整 URL
  if (imagePath.startsWith('/static/images/')) {
    return `/api/v1${imagePath}`;
  }
  // 如果是相对路径，转换为 GitHub raw URL
  if (imagePath.startsWith('images/')) {
    return `https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out/${imagePath}`;
  }
  return imagePath;
}

function handleImageError(event: Event) {
  const target = event.target as HTMLImageElement;
  if (target) {
    target.style.display = 'none';
  }
}

function handleThumbnailError(event: Event) {
  const target = event.target as HTMLImageElement;
  const parent = target.parentElement;
  if (parent) {
    parent.style.display = 'none';
  }
}

function nextImage() {
  if (recipe.value && recipe.value.images) {
    currentImageIndex.value = (currentImageIndex.value + 1) % recipe.value.images.length
  }
}

function prevImage() {
  if (recipe.value && recipe.value.images) {
    currentImageIndex.value = (currentImageIndex.value - 1 + recipe.value.images.length) % recipe.value.images.length
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (!recipe.value || !recipe.value.images || recipe.value.images.length <= 1) return

  switch (event.key) {
    case 'ArrowLeft':
      prevImage()
      break
    case 'ArrowRight':
      nextImage()
      break
  }
}

function openFullscreen() {
  const img = document.querySelector('.main-image') as HTMLImageElement;
  if (img && img.requestFullscreen) {
    img.requestFullscreen();
  }
}

// 显示回退 tooltip
function showFallbackTooltip(fallbackChain: string, event: MouseEvent) {
  console.log('showFallbackTooltip called', fallbackChain, event)
  const icon = event.currentTarget as HTMLElement
  const rect = icon.getBoundingClientRect()
  console.log('icon rect:', rect)

  // 计算 tooltip 的位置（居中于图标上方）
  const tooltipWidth = 240
  const tooltipHeight = 40
  const screenPadding = 10

  // 默认居中
  let x = rect.left + rect.width / 2 - tooltipWidth / 2
  let y = rect.top - tooltipHeight - 8 // 在图标上方

  // 防止超出屏幕左边界
  if (x < screenPadding) {
    x = screenPadding
  }

  // 防止超出屏幕右边界
  if (x + tooltipWidth > window.innerWidth - screenPadding) {
    x = window.innerWidth - tooltipWidth - screenPadding
  }

  // 如果上方空间不足，改为显示在下方
  if (y < screenPadding) {
    y = rect.bottom + 8
  }

  fallbackTooltip.value = {
    show: true,
    message: `使用回退食材价格：${fallbackChain}`,
    x: x,
    y: y
  }
  console.log('tooltip position:', fallbackTooltip.value)
}

// 关闭 tooltip
function closeTooltip() {
  fallbackTooltip.value.show = false
  nutrientTooltip.value.show = false
}

// 显示营养回退 tooltip
function showNutrientTooltip(message: string, event: MouseEvent) {
  const icon = event.currentTarget as HTMLElement
  const rect = icon.getBoundingClientRect()

  nutrientTooltip.value = {
    show: true,
    message: message,
    x: rect.left + rect.width / 2 - 120, // 居中，tooltip 宽度为 240px
    y: rect.top - 40 - 8 // 在图标上方
  }
}

// 检查某个营养素是否使用了回退数据
function checkNutrientUsedFallback(nutrientName: string): boolean {
  if (!recipe.value?.nutrition?.ingredient_details) {
    return false
  }

  // 检查所有食材，只要有任何一个食材的该营养素使用了回退，就返回 true
  return recipe.value.nutrition.ingredient_details.some((detail: any) => {
    const contribution = detail.nutrition_contribution?.[nutrientName]
    return contribution && contribution.used_fallback === true
  })
}
</script>

<style scoped>
.recipe-detail {
  padding: 2rem;
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

.recipe-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 图片画廊 */
.recipe-gallery {
  background: white;
  padding: 1rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.gallery-main {
  position: relative;
  width: 100%;
  height: 500px;
  background: #f5f5f5;
  border-radius: 0.75rem;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
}

.main-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: opacity 0.3s ease;
}

.gallery-counter {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 0.375rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  backdrop-filter: blur(4px);
}

.gallery-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 2.5rem;
  height: 2.5rem;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1.25rem;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: background 0.3s ease;
}

.gallery-btn:hover {
  background: rgba(0, 0, 0, 0.7);
}

.gallery-btn.prev {
  left: 1rem;
}

.gallery-btn.next {
  right: 1rem;
}

.gallery-thumbnails {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  overflow-x: auto;
  padding: 0.25rem;
  scrollbar-width: thin;
}

.gallery-thumbnails::-webkit-scrollbar {
  height: 6px;
}

.gallery-thumbnails::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 3px;
}

.thumbnail {
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 0.5rem;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  opacity: 0.7;
}

.thumbnail:hover {
  opacity: 1;
  transform: scale(1.05);
}

.thumbnail.active {
  border-color: #667eea;
  opacity: 1;
  transform: scale(1.1);
}

.thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.info-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.info-card h2 {
  font-size: 1.25rem;
  color: #333;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
}

.info-item .label {
  color: #666;
}

.info-item .value {
  color: #333;
  font-weight: 500;
}

.recipe-label {
  margin-top: 1rem;
}

.label-imported {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.servings-info {
  margin-bottom: 1rem;
  padding: 0.5rem;
  background: #f0f7ff;
  border-radius: 0.25rem;
  font-size: 0.9rem;
}

.servings-info .label {
  font-weight: 500;
  margin-right: 0.5rem;
}

.servings-info .value {
  color: #1976d2;
}

.ingredient-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.ingredient-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #f9f9f9;
  border-radius: 0.25rem;
}

.ingredient-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.5rem;
  align-items: center;
}

.ingredient-name-col {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.ingredient-amount-col {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  text-align: right;
  flex: 1;
}

.ingredient-cost-col {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  text-align: right;
  flex: 1;
}

.cost-wrapper {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
}

.fallback-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  background: #ff9800;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.fallback-icon:hover {
  background: #f57c00;
  transform: scale(1.1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.nutrient-fallback-icon {
  margin-right: 0.5rem;
}

.nutrient-value-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fallback-tooltip {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10000;
  pointerEvents: none;
}

.tooltip-container {
  position: absolute;
  pointerEvents: auto;
}

.tooltip-arrow {
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid #323232;
  margin: 0 auto;
  pointerEvents: auto;
}

.tooltip-content {
  background: #323232;
  color: white;
  padding: 0.75rem 1.25rem;
  border-radius: 0.5rem;
  fontSize: 0.9rem;
  display: flex;
  alignItems: center;
  gap: 0.5rem;
  boxShadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 240px;
  whiteSpace: nowrap;
  pointerEvents: auto;
}

.tooltip-content i {
  color: #ff9800;
  flexShrink: 0;
}

.tooltip-arrow {
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid #323232;
  margin: 0 auto;
  pointerEvents: auto;
}

.ingredient-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.ingredient-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.ingredient-link:hover {
  text-decoration: underline;
}

.ingredient-name {
  color: #333;
}

.optional-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  font-weight: 500;
}

.ingredient-amount {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  flex: 1;
  text-align: right;
}

.ingredient-cost {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
  margin-left: 1rem;
  font-size: inherit; /* 与原料量的字体大小一致 */
  color: inherit; /* 与原料量的字体颜色一致 */
  font-weight: inherit; /* 使用相同的字重 */
  flex: 1;
}

.cost-label {
  display: none; /* 隐藏“成本:”文本 */
}

.cost-value {
  color: inherit; /* 与原料量的字体颜色一致 */
  font-weight: inherit; /* 使用相同的字重 */
}

.cost-unavailable {
  color: inherit; /* 与原料量的字体颜色一致 */
  font-style: italic;
}

.ingredient-note {
  background: #f9f9f9;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #666;
  width: 100%;
  margin-top: 0.25rem;
  box-sizing: border-box; /* 确保padding不会增加元素总宽度 */
}

.cooking-steps {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.step-item {
  display: flex;
  gap: 1rem;
}

.step-number {
  width: 2rem;
  height: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #667eea;
  color: white;
  border-radius: 50%;
  font-size: 0.875rem;
  font-weight: 500;
  flex-shrink: 0;
}

.step-content {
  color: #333;
  line-height: 2rem;
}

.empty-text {
  color: #999;
  text-align: center;
  padding: 2rem;
}

.nutrition-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nutrient-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nrp-legend {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
  padding: 0.75rem 1rem;
  background: #f0f7ff;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  color: #1976d2;
}

.legend-icon {
  font-size: 1.25rem;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .recipe-detail {
    padding: 0.75rem;
  }

  .recipe-gallery {
    padding: 0.75rem;
  }

  .gallery-main {
    height: 300px;
  }

  .info-card {
    padding: 1rem;
  }

  .info-card h2 {
    font-size: 1.125rem;
    margin-bottom: 0.75rem;
  }

  .info-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .info-item {
    font-size: 0.875rem;
  }

  .recipe-label {
    margin-top: 0.75rem;
  }

  .servings-info {
    font-size: 0.8125rem;
    padding: 0.375rem;
  }

  .ingredient-item {
    padding: 0.375rem;
    gap: 0.375rem;
  }

  .ingredient-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.25rem;
    align-items: center;
  }

  .ingredient-name-col,
  .ingredient-amount-col,
  .ingredient-cost-col {
    display: flex;
    justify-content: flex-start;
    text-align: left;
    min-width: 0; /* 允许收缩 */
    word-wrap: break-word; /* 允许文本换行 */
  }

  .ingredient-amount-col,
  .ingredient-cost-col {
    justify-content: flex-end;
    text-align: right;
  }

  .ingredient-name {
    font-size: 0.875rem;
  }

  .optional-badge {
    font-size: 0.5625rem;
    padding: 0.125rem 0.25rem;
  }

  .ingredient-amount,
  .cost-value {
    font-size: 0.8125rem;
  }

  .ingredient-note {
    font-size: 0.75rem;
    padding: 0.375rem 0.5rem;
    width: 100%;
  }

  .cooking-steps {
    gap: 0.75rem;
  }

  .step-item {
    gap: 0.75rem;
  }

  .step-number {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .step-content {
    font-size: 0.875rem;
    line-height: 1.6;
  }

  .thumbnail {
    width: 60px;
    height: 60px;
  }

  .gallery-btn {
    width: 2rem;
    height: 2rem;
  }

  .gallery-counter {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .recipe-detail {
    padding: 0.5rem;
  }

  .gallery-main {
    height: 250px;
  }

  .info-card h2 {
    font-size: 1rem;
  }

  .step-number {
    width: 1.5rem;
    height: 1.5rem;
    font-size: 0.75rem;
  }

  .step-content {
    font-size: 0.8125rem;
  }

  .thumbnail {
    width: 50px;
    height: 50px;
  }
}

/* 食材贡献分解相关样式 */
.ingredient-breakdown-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toggle-label {
  font-size: 0.875rem;
  color: #666;
}

.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #667eea;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

.nutrient-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.expand-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
  width: 24px;
  height: 24px;
}

.expand-btn:hover {
  background-color: #f0f0f0;
}

.expand-btn.expanded {
  background-color: #e0e0e0;
}

.ingredient-breakdown-details {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: #f9f9f9;
  border-radius: 0.5rem;
  width: 100%;
  font-size: 0.875rem;
}

.breakdown-header {
  margin-bottom: 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #eee;
  color: #333;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.breakdown-item:last-child {
  border-bottom: none;
}

.ingredient-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.ingredient-name {
  font-weight: 500;
  color: #333;
}

.ingredient-amount, .cost-value, .cost-unavailable {
  font-size: 0.75rem;
  color: #666;
}

.contribution-value {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
}

.contribution-amount {
  font-weight: 500;
  color: #333;
}

.contribution-percent {
  font-size: 0.75rem;
  color: #667eea;
  font-weight: 500;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .ingredient-breakdown-details {
    font-size: 0.8rem;
  }

  .breakdown-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .contribution-value {
    align-self: flex-end;
    margin-top: -1.5rem;
  }

  .nutrient-value-wrapper {
    gap: 0.25rem;
  }

  .nutrient-fallback-icon {
    width: 1rem;
    height: 1rem;
    font-size: 0.625rem;
  }

  .fallback-icon {
    width: 1rem;
    height: 1rem;
    font-size: 0.625rem;
  }
}
</style>