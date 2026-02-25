<template>
  <div class="recipe-list">
    <header class="page-header">
      <h1>菜谱管理</h1>
      <button @click="showAddModal = true" class="btn-primary">
        + 创建菜谱
      </button>
    </header>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="recipes.length === 0" class="empty-state">
      暂无菜谱
    </div>

    <div v-else class="recipe-grid">
      <div v-for="recipe in recipes" :key="recipe.id" class="recipe-card">
        <h3>{{ recipe.name }}</h3>
        <div class="recipe-info">
          <p>预计成本: ¥{{ recipe.estimated_cost || 0 }}</p>
          <p>热量: {{ recipe.calories }} kcal</p>
          <p>蛋白质: {{ recipe.protein }} g</p>
          <p>更新时间: {{ formatDate(recipe.updated_at) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

const recipes = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)

onMounted(async () => {
  await loadRecipes()
})

async function loadRecipes() {
  loading.value = true
  try {
    const data = await api.get<{ items: any[] }>('/recipes/')
    recipes.value = data.items || []
  } catch (error) {
    console.error('Failed to load recipes:', error)
  } finally {
    loading.value = false
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.recipe-list {
  padding: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 1.5rem;
  color: #333;
}

.btn-primary {
  padding: 0.5rem 1rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
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

.recipe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.recipe-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.recipe-card h3 {
  font-size: 1.125rem;
  color: #333;
  margin-bottom: 1rem;
}

.recipe-info p {
  margin: 0.25rem 0;
  color: #666;
  font-size: 0.875rem;
}
</style>
