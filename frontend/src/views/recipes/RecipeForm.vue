<template>
  <div class="recipe-form">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>{{ isEditing ? '编辑菜谱' : '新建菜谱' }}</h1>
    </header>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="form-container">
      <form @submit.prevent="handleSubmit">
        <div class="form-section">
          <h2>基本信息</h2>
          <div class="form-row">
            <div class="form-group">
              <label for="name">菜谱名称 *</label>
              <input
                id="name"
                v-model="form.name"
                type="text"
                required
                maxlength="200"
                placeholder="请输入菜谱名称"
              />
            </div>
            <div class="form-group">
              <label for="category">分类</label>
              <select id="category" v-model="form.category" class="select-input">
                <option value="">请选择分类</option>
                <option v-for="cat in categories" :key="cat.value" :value="cat.value">
                  {{ cat.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label for="difficulty">难度</label>
              <select id="difficulty" v-model="form.difficulty" class="select-input">
                <option value="">请选择难度</option>
                <option value="simple">简单</option>
                <option value="medium">中等</option>
                <option value="hard">困难</option>
              </select>
            </div>
            <div class="form-group">
              <label for="servings">份量</label>
              <input
                id="servings"
                v-model.number="form.servings"
                type="number"
                min="1"
                placeholder="请输入份量"
              />
            </div>
            <div class="form-group">
              <label for="total_time_minutes">预计用时（分钟）</label>
              <input
                id="total_time_minutes"
                v-model.number="form.total_time_minutes"
                type="number"
                min="1"
                placeholder="请输入预计用时"
              />
            </div>
          </div>
        </div>

        <div class="form-section">
          <h2>原料</h2>
          <div class="ingredient-inputs">
            <div v-for="(ingredient, index) in form.ingredients" :key="index" class="ingredient-row">
              <label>原料 {{ index + 1 }}</label>
              <div class="ingredient-input-wrapper">
                <select
                  v-model="ingredient.ingredient_id"
                  @focus="showSuggestions(index)"
                  @change="onIngredientChange(index)"
                  class="ingredient-select"
                >
                  <option value="">请选择原料</option>
                  <option v-for="item in availableIngredients" :key="item.id" :value="item.id">
                    {{ item.name }} {{ item.aliases && item.aliases.length > 0 ? `(${item.aliases.join(', ')})` : '' }}
                  </option>
                </select>
                <input
                  v-model="ingredient.name"
                  type="text"
                  placeholder="或直接输入原料名称"
                  @input="onIngredientNameInput(index)"
                />
                <div class="suggestions" v-if="showSuggestions[index]">
                  <div
                    v-for="item in suggestionItems[index]"
                    :key="item.id"
                    @click="selectIngredient(index, item)"
                    class="suggestion-item"
                  >
                    {{ item.name }} <span v-if="item.aliases && item.aliases.length > 0">({{ item.aliases.join(', ') }})</span>
                  </div>
                </div>
              </div>
              <div class="input-group">
                <label>数量</label>
                <input
                  v-model="ingredient.quantity"
                  type="text"
                  placeholder="如：200克"
                />
              </div>
              <div class="input-group">
                <label>单位</label>
                <select v-model="ingredient.unit" class="select-input">
                  <option value="">请选择单位</option>
                  <option v-for="unit in units" :key="unit.value" :value="unit.value">
                    {{ unit.label }}
                  </option>
                </select>
              </div>
              <button type="button" @click="removeIngredient(index)" class="btn-remove">
                <i class="mdi mdi-minus"></i>
              </button>
            </div>
          </div>
          <button type="button" @click="addIngredient" class="btn-add">
            <i class="mdi mdi-plus"></i> 添加原料
          </button>
        </div>

        <div class="form-section">
          <h2>烹饪步骤</h2>
          <div v-for="(step, index) in form.cooking_steps" :key="index" class="step-row">
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-content">
              <div class="input-group">
                <input
                  v-model="step.content"
                  type="text"
                  placeholder="步骤描述"
                  required
                />
                <div class="step-controls">
                  <button type="button" @click="removeStep(index)" class="btn-remove">
                    <i class="mdi mdi-minus"></i>
                  </button>
                  <button type="button" @click="moveStep(index, -1)" class="btn-move">
                    <i class="mdi mdi-arrow-up"></i>
                  </button>
                  <button type="button" @click="moveStep(index, 1)" class="btn-move">
                    <i class="mdi mdi-arrow-down"></i>
                  </button>
                </div>
              </div>
              <div class="input-group">
                <label>时长（分钟）</label>
                <input
                  v-model.number="step.duration_minutes"
                  type="number"
                  min="0"
                  placeholder="可选"
                />
              </div>
            </div>
          </div>
          <button type="button" @click="addStep" class="btn-add">
            <i class="mdi mdi-plus"></i> 添加步骤
          </button>
        </div>

        <div class="form-section">
          <h2>小贴士</h2>
          <textarea v-model="form.tips" placeholder="可选：添加烹饪小贴士，每行一条" rows="4"></textarea>
        </div>

        <div class="form-actions">
          <button type="button" @click="$router.go(-1)" class="btn-secondary">取消</button>
          <button type="submit" class="btn-primary" :disabled="saving">
            {{ saving ? '保存中...' : (isEditing ? '更新' : '保存') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isEditing = computed(() => route.params.id !== undefined)

const categories = [
  { value: '荤菜', label: '荤菜' },
  { value: '素菜', label: '素菜' },
  { value: '水产', label: '水产' },
  { value: '主食', label: '主食' },
  { value: '汤与粥', label: '汤与粥' },
  { value: '早餐', label: '早餐' },
  { value: '甜品', label: '甜品' },
  { value: '调料', label: '调料' },
  { value: '半成品', label: '半成品' },
  { value: '小食', label: '小食' }
]

const units = [
  { value: 'g', label: '克' },
  { value: 'kg', label: '千克' },
  { value: 'mg', label: '毫克' },
  { value: 'ml', label: '毫升' },
  { value: 'l', label: '升' },
  { value: '个', label: '个' },
  { value: '片', label: '片' },
  { value: '勺', label: '勺' },
  { value: '杯', label: '杯' },
  { value: '碗', label: '碗' },
  { value: '根', label: '根' },
  { value: '把', label: '把' },
  { value: '瓣', label: '瓣' },
  { value: '条', label: '条' },
  { value: '块', label: '块' },
  { value: '段', label: '段' },
  { value: '适量', label: '适量' }
]

const form = reactive({
  name: '',
  category: '',
  difficulty: 'simple',
  servings: 1,
  total_time_minutes: null,
  ingredients: [
    { ingredient_id: '', name: '', quantity: '', unit: '' }
  ],
  cooking_steps: [
    { content: '', duration_minutes: null }
  ],
  tips: ''
})

const loading = ref(true)
const saving = ref(false)
const availableIngredients = ref<any[]>([])
const suggestionItems = ref<any[][]>([[]])
const showSuggestions = ref<boolean[]>([[]])

async function loadIngredients() {
  try {
    // 搜索所有原料
    const response = await api.get('/ingredients')
    availableIngredients.value = response.data || []
  } catch (error) {
    console.error('Failed to load ingredients:', error)
  }
}

async function loadRecipe() {
  if (!isEditing.value) return

  try {
    const response = await api.get(`/recipes/${route.params.id}`)
    const data = response.data

    form.name = data.name
    form.category = data.category || ''
    form.difficulty = data.difficulty || 'simple'
    form.servings = data.servings || 1
    form.total_time_minutes = data.total_time_minutes
    form.tips = data.tips?.join('\n') || ''

    // 原料
    form.ingredients = (data.ingredients || []).map((item: any) => ({
      ingredient_id: item.ingredient_id,
      name: item.name,
      quantity: item.quantity || '',
      unit: item.unit || ''
    }))

    // 步骤
    form.cooking_steps = (data.cooking_steps || []).map((step: any) => ({
      content: step.content || '',
      duration_minutes: step.duration_minutes || null
    }))
  } catch (error) {
    console.error('Failed to load recipe:', error)
  }
}

async function searchIngredients(keyword: string) {
  if (!keyword.trim()) {
    suggestionItems.value = [[]]
    return
  }

  try {
    const response = await api.get(`/ingredients?search=${encodeURIComponent(keyword)}`)
    const results = response.data || []

    suggestionItems.value[0] = results.slice(0, 10)
  } catch (error) {
    console.error('Failed to search ingredients:', error)
  }
}

function onIngredientNameInput(index: number) {
  showSuggestions.value[index] = false
  const ingredient = form.ingredients[index]
  form.ingredients[index] = {
    ingredient_id: ingredient.ingredient_id,
    name: ingredient.name,
    quantity: ingredient.quantity,
    unit: ingredient.unit
  }
}

function onIngredientChange(index: number) {
  const ingredient = availableIngredients.value.find(i => i.id === form.ingredients[index].ingredient_id)
  if (ingredient) {
    form.ingredients[index].name = ingredient.name
    form.ingredients[index].unit = ingredient.unit || ''
  }
  suggestionItems.value[index] = []
}

function selectIngredient(index: number, item: any) {
  form.ingredients[index] = {
    ingredient_id: item.id,
    name: item.name,
    quantity: form.ingredients[index].quantity,
    unit: form.ingredients[index].unit
  }
  suggestionItems.value[index] = []
}

function addIngredient() {
  form.ingredients.push({
    ingredient_id: '',
    name: '',
    quantity: '',
    unit: ''
  })
}

function removeIngredient(index: number) {
  form.ingredients.splice(index, 1)
}

function addStep() {
  form.cooking_steps.push({
    content: '',
    duration_minutes: null
  })
}

function removeStep(index: number) {
  form.cooking_steps.splice(index, 1)
}

function moveStep(index: number, direction: number) {
  const newIndex = index + direction
  if (newIndex >= 0 && newIndex < form.cooking_steps.length) {
    const step = form.cooking_steps[index]
    form.cooking_steps.splice(index, 1)
    form.cooking_steps.splice(newIndex, 0, step)
  }
}

async function handleSubmit() {
  if (saving.value) return

  saving.value = true
  try {
    const payload = {
      name: form.name,
      source: 'custom',
      category: form.category,
      tags: [],
      ingredients: form.ingredients.filter(i => i.name.trim()), // 过滤空名称的原料
      cooking_steps: form.cooking_steps.filter(s => s.content.trim()),
      total_time_minutes: form.total_time_minutes || null,
      difficulty: form.difficulty,
      servings: form.servings,
      tips: form.tips ? form.tips.split('\n').filter(t => t.trim()) : []
    }

    if (isEditing.value) {
      await api.put(`/recipes/${route.params.id}`, payload)
    } else {
      await api.post('/recipes', payload)
    }

    router.push('/recipes')
  } catch (error) {
    console.error('Failed to save recipe:', error)
    alert('保存失败：' + (error.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadIngredients()
  if (isEditing.value) {
    loadRecipe()
  }
})
</script>

<style scoped>
.recipe-form {
  padding: 2rem;
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.form-container {
  background: white;
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.form-section {
  margin-bottom: 1.5rem;
}

.form-section h2 {
  margin-bottom: 1rem;
  color: #333;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 2rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #1976d2;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.ingredient-inputs {
  margin-bottom: 1.5rem;
}

.ingredient-row {
  display: grid;
  grid-template-columns: 1fr auto 100px 100px;
  gap: 0.5rem;
  align-items: start;
}

.ingredient-row label {
  font-weight: 500;
}

.ingredient-input-wrapper {
  position: relative;
}

.ingredient-select {
  width: 100%;
}

.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.suggestion-item {
  padding: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.suggestion-item:hover {
  background-color: #f5f5f5;
}

.input-group {
  display: flex;
  gap: 0.5rem;
}

.input-group input,
.input-group select {
  flex: 1;
}

.btn-remove {
  padding: 0.5rem;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.btn-add {
  padding: 0.75rem 1rem;
  background: #1976d2;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.step-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem;
  align-items: center;
}

.step-number {
  font-weight: bold;
  color: #666;
}

.step-content {
  display: flex;
  gap: 0.5rem;
}

.step-controls {
  display: flex;
  gap: 0.25rem;
}
</style>
