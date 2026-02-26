<template>
  <div class="ingredient-list">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>原料管理</h1>
      <button @click="showAddModal = true" class="btn-square add-btn" title="添加原料">
        <i class="mdi mdi-plus"></i>
      </button>
    </header>

    <div class="search-filter">
      <div class="search-box">
        <input v-model="searchTerm" placeholder="搜索原料名称..." class="search-input" />
      </div>
      <button @click="loadIngredients" class="btn-refresh">刷新</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="filteredIngredients.length === 0" class="empty-state">
      <p>暂无原料数据</p>
      <button @click="showAddModal = true" class="btn-primary">添加原料</button>
    </div>

    <div v-else class="ingredient-grid">
      <div v-for="ingredient in filteredIngredients" :key="ingredient.id" class="ingredient-card">
        <div class="ingredient-header">
          <h3>{{ ingredient.name }}</h3>
          <div class="ingredient-actions">
            <button @click="editIngredient(ingredient)" class="btn-edit" title="编辑">
              <i class="mdi mdi-pencil"></i>
            </button>
            <button @click="deleteIngredient(ingredient)" class="btn-delete" title="删除">
              <i class="mdi mdi-delete"></i>
            </button>
          </div>
        </div>

        <div class="ingredient-info">
          <p v-if="ingredient.aliases && ingredient.aliases.length > 0">
            <strong>别名:</strong> {{ ingredient.aliases.join(', ') }}
          </p>
          <p>
            <i class="mdi mdi-calendar"></i> 创建时间: {{ formatDate(ingredient.created_at) }}
          </p>
        </div>
      </div>
    </div>

    <!-- 添加/编辑原料模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeAddModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingIngredient ? '编辑原料' : '添加原料' }}</h2>
        <form @submit.prevent="saveIngredient">
          <div class="form-group">
            <label for="ingredientName">原料名称:</label>
            <input
              v-model="newIngredient.name"
              type="text"
              id="ingredientName"
              required
              :disabled="!!editingIngredient"
            />
          </div>
          <div class="form-group">
            <label for="ingredientAliases">别名 (用逗号分隔):</label>
            <input
              v-model="newIngredient.aliasesText"
              type="text"
              id="ingredientAliases"
              placeholder="例如: 土豆, 马铃薯, Potato"
            />
          </div>
          <div class="form-actions">
            <button type="button" @click="closeAddModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">{{ editingIngredient ? '更新' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api/client'

interface Ingredient {
  id: number
  name: string
  aliases: string[]
  created_at: string
}

interface NewIngredient {
  name: string
  aliasesText: string
}

const ingredients = ref<Ingredient[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const editingIngredient = ref<Ingredient | null>(null)
const searchTerm = ref('')
const newIngredient = ref<NewIngredient>({
  name: '',
  aliasesText: ''
})

onMounted(async () => {
  await loadIngredients()
})

async function loadIngredients() {
  loading.value = true
  try {
    // 这里需要后端API支持获取原料列表
    const response = await fetch(`${import.meta.env.VITE_API_URL || '/api/v1'}/nutrition/ingredients`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      ingredients.value = data.items || data
    } else {
      // 如果API不存在，使用模拟数据
      console.warn('获取原料列表API不存在，使用空数组')
      ingredients.value = []
    }
  } catch (error) {
    console.error('Failed to load ingredients:', error)
    alert('加载原料数据失败')
  } finally {
    loading.value = false
  }
}

const filteredIngredients = computed(() => {
  if (!searchTerm.value) {
    return ingredients.value
  }
  const term = searchTerm.value.toLowerCase()
  return ingredients.value.filter(ingredient =>
    ingredient.name.toLowerCase().includes(term) ||
    ingredient.aliases.some(alias => alias.toLowerCase().includes(term))
  )
})

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

function editIngredient(ingredient: Ingredient) {
  editingIngredient.value = ingredient
  newIngredient.value = {
    name: ingredient.name,
    aliasesText: ingredient.aliases.join(', ')
  }
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
  editingIngredient.value = null
  newIngredient.value = {
    name: '',
    aliasesText: ''
  }
}

async function saveIngredient() {
  try {
    const aliases = newIngredient.value.aliasesText
      ? newIngredient.value.aliasesText.split(',').map(s => s.trim()).filter(s => s)
      : []

    const ingredientData = {
      name: newIngredient.value.name,
      aliases: aliases
    }

    if (editingIngredient.value) {
      // 更新原料
      await api.put(`/nutrition/ingredients/${editingIngredient.value.id}`, ingredientData)
    } else {
      // 添加新原料
      await api.post('/nutrition/ingredients', ingredientData)
    }

    closeAddModal()
    await loadIngredients()
    alert(editingIngredient.value ? '原料更新成功' : '原料添加成功')
  } catch (error) {
    console.error('Failed to save ingredient:', error)
    alert(`原料${editingIngredient.value ? '更新' : '添加'}失败: ${(error as Error).message}`)
  }
}

async function deleteIngredient(ingredient: Ingredient) {
  if (confirm(`确定要删除原料 "${ingredient.name}" 吗？此操作不可撤销。`)) {
    try {
      await api.delete(`/nutrition/ingredients/${ingredient.id}`)
      await loadIngredients()
      alert('原料删除成功')
    } catch (error) {
      console.error('Failed to delete ingredient:', error)
      alert('原料删除失败')
    }
  }
}
</script>

<style scoped>
.ingredient-list {
  padding: 2rem;
  position: relative;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
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

.search-filter {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  align-items: center;
}

.search-box {
  flex: 1;
  max-width: 300px;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.btn-refresh {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  margin-left: 1rem;
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

.empty-state button {
  margin-top: 1rem;
}

.ingredient-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.ingredient-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-left: 4px solid #667eea;
}

.ingredient-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.ingredient-header h3 {
  font-size: 1.125rem;
  color: #333;
  margin: 0;
  flex-grow: 1;
}

.ingredient-actions {
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

.ingredient-info p {
  margin: 0.5rem 0;
  color: #666;
  font-size: 0.875rem;
  line-height: 1.4;
}

.ingredient-info strong {
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
  overflow-y: auto;
  padding: 1rem;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  max-height: 90vh;
  overflow-y: auto;
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

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}
</style>