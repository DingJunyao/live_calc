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
            @click="currentImageIndex = index"
          >
            <img
              :src="getImageUrl(image)"
              :alt="`${recipe.name} 缩略图 ${index + 1}`"
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
            <span class="value" v-if="recipe.costData">¥{{ recipe.costData.total_cost }}</span>
            <span class="value" v-else>¥{{ recipe.estimated_cost || 0 }}</span>
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
            <div class="ingredient-main">
              <span class="ingredient-name">{{ item.name }}</span>
              <span v-if="item.is_optional" class="optional-badge">可选</span>
            </div>
            <div class="ingredient-amount">
              <span v-if="item.quantity">{{ item.quantity }} {{ item.unit }}</span>
              <span v-else-if="item.quantity_range && typeof item.quantity_range === 'object'">
                {{ item.quantity_range.min }} - {{ item.quantity_range.max }} {{ item.unit }}
              </span>
              <span v-else>{{ item.quantity || '' }} {{ item.unit || '' }}</span>
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
            <span class="step-number">{{ index + 1 }}</span>
            <span class="step-content">{{ typeof stepItem === 'object' ? stepItem.content : stepItem }}</span>
          </div>
        </div>
        <div v-else class="empty-text">暂无做法数据</div>
      </div>

      <!-- 营养成分 -->
      <div class="info-card" v-if="recipe.nutrition && recipe.nutrition.per_serving_nutrition && recipe.nutrition.per_serving_nutrition.core_nutrients">
        <h2>营养成分（每份）</h2>
        <div class="info-grid">
          <div
            v-for="nutrientName in standardNutrientOrder"
            :key="nutrientName"
            v-if="recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]"
            class="info-item nutrition-item"
          >
            <div class="nutrient-info">
              <span class="label">{{ nutrientName }}:</span>
              <span class="value">
                {{ recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]?.value || 0 }}
                {{ recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]?.unit || getDefaultUnit(nutrientName) }}
              </span>
            </div>
            <NutritionProgressBar
              v-if="recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName]?.nrp_pct"
              :percentage="recipe.nutrition.per_serving_nutrition.core_nutrients[nutrientName].nrp_pct"
              size="small"
              :show-percentage="true"
            />
          </div>
          <!-- 显示其他不在标准顺序中的营养素 -->
          <div
            v-for="[nutrientName, nutrientData] in getNonStandardNutrients()"
            :key="nutrientName"
            class="info-item nutrition-item"
          >
            <div class="nutrient-info">
              <span class="label">{{ nutrientName }}:</span>
              <span class="value">
                {{ nutrientData?.value || 0 }}
                {{ nutrientData?.unit || getDefaultUnit(nutrientName) }}
              </span>
            </div>
            <NutritionProgressBar
              v-if="nutrientData?.nrp_pct"
              :percentage="nutrientData.nrp_pct"
              size="small"
              :show-percentage="true"
            />
          </div>
        </div>
        <div class="nrp-legend">
          <span class="legend-icon">📊</span>
          <span class="legend-text">NRV = 营养素参考值百分比</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import NutritionProgressBar from '@/components/NutritionProgressBar.vue'

const route = useRoute()
const recipe = ref<any>(null)
const loading = ref(true)
const currentImageIndex = ref(0)

onMounted(async () => {
  await loadRecipe()
  // 监听键盘事件
  window.addEventListener('keydown', handleKeydown)
})

// 组件卸载时移除键盘监听
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

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
      recipe.value.nutrition = nutritionData
    } catch (e) {
      // 营养数据可能不存在，忽略错误
      console.log('No nutrition data available')
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

function getNonStandardNutrients() {
  if (!recipe.value?.nutrition?.per_serving_nutrition?.core_nutrients) return []

  const coreNutrients = recipe.value.nutrition.per_serving_nutrition.core_nutrients
  return Object.entries(coreNutrients).filter(([name]) => !standardNutrientOrder.includes(name))
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
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  padding: 0.5rem;
  gap: 0.5rem;
  background: #f9f9f9;
  border-radius: 0.25rem;
}

.ingredient-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
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
}

.ingredient-note {
  background: #f9f9f9;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
  width: 100%;
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

  .ingredient-name {
    font-size: 0.875rem;
  }

  .optional-badge {
    font-size: 0.5625rem;
    padding: 0.125rem 0.25rem;
  }

  .ingredient-amount {
    font-size: 0.8125rem;
  }

  .ingredient-note {
    font-size: 0.75rem;
    padding: 0.375rem 0.5rem;
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
</style>