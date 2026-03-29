<template>
  <div class="recipe-list">
    <div class="section-header">
      <h2 class="section-title">关联菜谱</h2>
      <div class="recipe-count">{{ recipes.length }} 道菜谱</div>
    </div>

    <div v-if="recipes.length === 0" class="no-data">
      <i class="mdi mdi-book-open-variant"></i>
      <p>暂无关联菜谱</p>
    </div>

    <div v-else class="recipe-items">
      <div
        v-for="recipe in recipes"
        :key="recipe.id"
        class="recipe-item"
        @click="handleRecipeClick(recipe)"
      >
        <div class="recipe-icon">
          <i class="mdi mdi-silverware-fork-knife"></i>
        </div>
        <div class="recipe-info">
          <div class="recipe-name">{{ recipe.name }}</div>
          <div class="recipe-meta">
            <span v-if="recipe.category" class="recipe-category">{{ recipe.category }}</span>
            <span v-if="recipe.servings" class="recipe-servings">{{ recipe.servings }} 人份</span>
            <span v-if="recipe.total_time_minutes" class="recipe-time">
              <i class="mdi mdi-clock-outline"></i> {{ recipe.total_time_minutes }} 分钟
            </span>
          </div>
        </div>
        <div class="recipe-arrow">
          <i class="mdi mdi-chevron-right"></i>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Recipe {
  id: number
  name: string
  source?: string
  category?: string
  servings?: number
  total_time_minutes?: number
  difficulty?: string
  tags?: string[]
  created_at: string
  updated_at: string
}

const props = defineProps<{
  recipes: Recipe[]
}>()

const emit = defineEmits<{
  click: [recipe: Recipe]
}>()

function handleRecipeClick(recipe: Recipe) {
  console.log('RecipeList - 点击菜谱:', recipe)
  emit('click', recipe)
}
</script>

<style scoped>
.recipe-list {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.recipe-count {
  font-size: 13px;
  color: #999;
}

.recipe-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recipe-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: #f9f9f9;
  border-radius: 6px;
  transition: background-color 0.3s;
  cursor: pointer;
}

.recipe-item:hover {
  background-color: #f0f0f0;
}

.recipe-icon {
  width: 40px;
  height: 40px;
  background-color: #fff3e0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ff9800;
  font-size: 20px;
  flex-shrink: 0;
}

.recipe-info {
  flex: 1;
}

.recipe-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.recipe-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.recipe-meta > span {
  font-size: 12px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 4px;
}

.recipe-category {
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 2px 8px;
  border-radius: 4px;
}

.recipe-time {
  display: flex;
  align-items: center;
  gap: 2px;
}

.recipe-arrow {
  color: #999;
  font-size: 18px;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
}

.no-data i {
  font-size: 48px;
  margin-bottom: 12px;
  color: #e5e5e5;
}

.no-data p {
  margin: 0;
  font-size: 14px;
}

@media (max-width: 768px) {
  .recipe-list {
    padding: 12px;
  }

  .recipe-icon {
    width: 36px;
    height: 36px;
    font-size: 18px;
  }

  .recipe-name {
    font-size: 13px;
  }

  .recipe-meta > span {
    font-size: 11px;
  }

  .recipe-arrow {
    font-size: 16px;
  }
}
</style>
