<template>
  <div class="recipe-detail">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>{{ recipe?.name || '菜谱详情' }}</h1>
      <div class="action-buttons" v-if="recipe && !isImportedRecipe(recipe)">
        <button @click="editRecipe" class="btn-square" title="编辑">
          <i class="mdi mdi-pencil"></i>
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="!recipe" class="empty-state">
      菜谱不存在
    </div>

    <div v-else class="recipe-content">
      <!-- 基本信息 -->
      <div class="info-card">
        <h2>基本信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">预计成本:</span>
            <span class="value">¥{{ recipe.estimated_cost || 0 }}</span>
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
            <span class="ingredient-name">{{ item.name }}</span>
            <span class="ingredient-amount">{{ item.quantity || item.amount || '' }} {{ item.unit || '' }}</span>
          </div>
        </div>
        <div v-else class="empty-text">暂无原料数据</div>
      </div>

      <!-- 做法 -->
      <div class="info-card">
        <h2>做法</h2>
        <div v-if="recipe.cooking_steps && recipe.cooking_steps.length > 0" class="cooking-steps">
          <div v-for="(step, index) in recipe.cooking_steps" :key="index" class="step-item">
            <span class="step-number">{{ index + 1 }}</span>
            <span class="step-content">{{ typeof step === 'object' ? step.content : step }}</span>
          </div>
        </div>
        <div v-else class="empty-text">暂无做法数据</div>
      </div>

      <!-- 营养成分 -->
      <div class="info-card">
        <h2>营养成分（每份）</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">能量:</span>
            <span class="value">{{ recipe.calories || recipe.nutrition?.calories || 0 }} kcal</span>
          </div>
          <div class="info-item">
            <span class="label">蛋白质:</span>
            <span class="value">{{ recipe.protein || recipe.nutrition?.protein || 0 }} g</span>
          </div>
          <div class="info-item">
            <span class="label">脂肪:</span>
            <span class="value">{{ recipe.fat || recipe.nutrition?.fat || 0 }} g</span>
          </div>
          <div class="info-item">
            <span class="label">碳水化合物:</span>
            <span class="value">{{ recipe.carbs || recipe.nutrition?.carbs || 0 }} g</span>
          </div>
          <div class="info-item">
            <span class="label">钠:</span>
            <span class="value">{{ nutritionDetails?.sodium || 0 }} mg</span>
          </div>
          <div class="info-item">
            <span class="label">膳食纤维:</span>
            <span class="value">{{ nutritionDetails?.fiber || 0 }} g</span>
          </div>
          <div class="info-item">
            <span class="label">维生素A:</span>
            <span class="value">{{ nutritionDetails?.vitamin_a || 0 }} μg</span>
          </div>
          <div class="info-item">
            <span class="label">维生素C:</span>
            <span class="value">{{ nutritionDetails?.vitamin_c || 0 }} mg</span>
          </div>
          <div class="info-item">
            <span class="label">钙:</span>
            <span class="value">{{ nutritionDetails?.calcium || 0 }} mg</span>
          </div>
          <div class="info-item">
            <span class="label">铁:</span>
            <span class="value">{{ nutritionDetails?.iron || 0 }} mg</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'

const route = useRoute()
const recipe = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  await loadRecipe()
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

const nutritionDetails = computed(() => {
  if (!recipe.value) return null
  // 优先使用从 API 获取的营养数据
  const nutrition = recipe.value.nutrition || recipe.value
  return {
    fiber: nutrition.fiber,
    vitamin_a: nutrition.vitamin_a,
    vitamin_c: nutrition.vitamin_c,
    calcium: nutrition.calcium,
    iron: nutrition.iron,
    sodium: nutrition.sodium
  }
})

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
</script>

<style scoped>
.recipe-detail {
  padding: 2rem;
  position: relative;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
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

.page-header h1 {
  font-size: 1.5rem;
  color: #333;
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
  justify-content: space-between;
  padding: 0.5rem;
  background: #f9f9f9;
  border-radius: 0.25rem;
}

.ingredient-name {
  color: #333;
}

.ingredient-amount {
  color: #666;
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
</style>