<template>
  <div class="recipe-list">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>菜谱管理</h1>
      <button @click="showAddModal = true" class="btn-square add-btn" title="创建菜谱">
        <i class="mdi mdi-plus"></i>
      </button>
    </header>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="recipes.length === 0" class="empty-state">
      暂无菜谱
    </div>

    <div v-else class="recipe-grid">
      <div v-for="recipe in recipes" :key="recipe.id" class="recipe-card">
        <div class="recipe-header">
          <h3 :class="{ 'imported-recipe': isImportedRecipe(recipe) }">{{ recipe.name }}</h3>
          <div class="recipe-actions" v-if="!isImportedRecipe(recipe)">
            <button @click="editRecipe(recipe)" class="btn-edit" title="编辑">
              <i class="mdi mdi-pencil"></i>
            </button>
            <button @click="deleteRecipe(recipe)" class="btn-delete" title="删除">
              <i class="mdi mdi-delete"></i>
            </button>
          </div>
        </div>

        <div class="recipe-info">
          <p>预计成本: ¥{{ recipe.estimated_cost || 0 }}</p>
          <p>热量: {{ recipe.calories }} kcal</p>
          <p>蛋白质: {{ recipe.protein }} g</p>
          <p>来源: {{ getRecipeSource(recipe) }}</p>
          <p>更新时间: {{ formatDate(recipe.updated_at) }}</p>
        </div>

        <div v-if="isImportedRecipe(recipe)" class="recipe-label">
          <span class="label-imported">导入菜谱</span>
        </div>
      </div>
    </div>

    <!-- 添加菜谱模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
      <div class="modal-content" @click.stop>
        <h2>创建菜谱</h2>
        <form @submit.prevent="addRecipe">
          <div class="form-group">
            <label for="recipeName">菜谱名称:</label>
            <input v-model="newRecipe.name" type="text" id="recipeName" required />
          </div>
          <div class="form-group">
            <label for="estimatedCost">预计成本:</label>
            <input v-model.number="newRecipe.estimated_cost" type="number" id="estimatedCost" step="0.01" min="0" />
          </div>
          <div class="form-group">
            <label for="calories">热量(kcal):</label>
            <input v-model.number="newRecipe.calories" type="number" id="calories" min="0" />
          </div>
          <div class="form-group">
            <label for="protein">蛋白质(g):</label>
            <input v-model.number="newRecipe.protein" type="number" id="protein" min="0" />
          </div>
          <div class="form-actions">
            <button type="button" @click="showAddModal = false" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">创建</button>
          </div>
        </form>
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
const newRecipe = ref({
  name: '',
  estimated_cost: 0,
  calories: 0,
  protein: 0
})

onMounted(async () => {
  await loadRecipes()
})

async function loadRecipes() {
  loading.value = true
  try {
    const data = await api.get<any[]>('/recipes')
    recipes.value = data || []
  } catch (error) {
    console.error('Failed to load recipes:', error)
  } finally {
    loading.value = false
  }
}

async function addRecipe() {
  try {
    await api.post('/recipes', newRecipe.value)
    showAddModal.value = false
    // 重置表单
    newRecipe.value = {
      name: '',
      estimated_cost: 0,
      calories: 0,
      protein: 0
    }
    // 重新加载数据
    await loadRecipes()
  } catch (error) {
    console.error('Failed to add recipe:', error)
    alert('创建菜谱失败，请重试')
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

function isImportedRecipe(recipe: any) {
  // 检查菜谱是否有来源信息但不是当前用户创建的
  return recipe.source && !recipe.user_id;
}

function getRecipeSource(recipe: any) {
  if (recipe.source) {
    return recipe.source;
  }
  return '个人创建';
}

function editRecipe(recipe: any) {
  // 编辑菜谱的逻辑
  console.log('Editing recipe:', recipe);
  alert('编辑功能将在后续版本中实现');
}

async function deleteRecipe(recipe: any) {
  if (confirm(`确定要删除菜谱 "${recipe.name}" 吗？此操作不可撤销。`)) {
    try {
      await api.delete(`/recipes/${recipe.id}`)
      await loadRecipes()
      alert('菜谱删除成功')
    } catch (error) {
      console.error('Failed to delete recipe:', error)
      alert('菜谱删除失败')
    }
  }
}
</script>

<style scoped>
.recipe-list {
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

.add-btn {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
}

.add-btn:hover {
  background: #36966d;
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

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #e0e0e0;
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
  position: relative;
}

.recipe-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.recipe-header h3 {
  font-size: 1.125rem;
  color: #333;
  margin: 0;
  flex-grow: 1;
}

.recipe-header h3.imported-recipe {
  color: #666;
  font-style: italic;
}

.recipe-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-edit, .btn-delete {
  width: 2rem;
  height: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-edit {
  background: #667eea;
  color: white;
}

.btn-edit:hover {
  background: #5a6fd8;
}

.btn-delete {
  background: #de350b;
  color: white;
}

.btn-delete:hover {
  background: #bc2e0b;
}

.recipe-info p {
  margin: 0.25rem 0;
  color: #666;
  font-size: 0.875rem;
}

.recipe-info p:nth-child(1) {
  font-weight: 500;
  color: #333;
}

.recipe-label {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
}

.label-imported {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}
</style>
