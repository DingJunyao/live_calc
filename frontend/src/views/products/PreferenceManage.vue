<template>
  <div class="preference-manage">
    <PageHeader title="食材偏好管理" :show-back="true" />

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="preferences.length === 0" class="empty-state">
      <p>暂无偏好设置</p>
      <button @click="showAddModal = true" class="btn-primary">添加偏好</button>
    </div>

    <div v-else>
      <div class="preference-grid">
        <div
          v-for="pref in preferences"
          :key="pref.id"
          class="preference-card"
        >
          <div class="preference-header">
            <h3>{{ getIngredientName(pref.ingredient_id) }}</h3>
            <div class="preference-badges">
              <span
                v-if="pref.is_favorite"
                class="badge badge-favorite"
              >
                <i class="mdi mdi-star"></i> 收藏
              </span>
              <span class="badge badge-type">
                {{ pref.preference_type === 'product' ? '商品' : '菜谱' }}
              </span>
            </div>
          </div>
          <div class="preference-details">
            <p v-if="pref.default_product_id">
              <i class="mdi mdi-package"></i>
              默认商品: {{ getProductName(pref.default_product_id) }}
            </p>
            <p v-if="pref.default_recipe_id">
              <i class="mdi mdi-food"></i>
              默认菜谱: {{ getRecipeName(pref.default_recipe_id) }}
            </p>
          </div>
          <div class="preference-actions">
            <button @click="editPreference(pref)" class="btn-sm btn-edit">
              <i class="mdi mdi-pencil"></i> 编辑
            </button>
            <button @click="deletePreference(pref)" class="btn-sm btn-delete">
              <i class="mdi mdi-delete"></i> 删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <Pagination
      v-if="total > 0"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @change-page="handlePageChange"
      @change-page-size="handlePageSizeChange"
    />

    <!-- 添加/编辑偏好模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingPref ? '编辑偏好' : '添加偏好' }}</h2>
        <form @submit.prevent="savePreference">
          <div class="form-group">
            <label for="ingredient">食材 *</label>
            <select
              v-model="formData.ingredient_id"
              id="ingredient"
              required
            >
              <option value="">请选择食材</option>
              <option
                v-for="ingredient in ingredients"
                :key="ingredient.id"
                :value="ingredient.id"
              >
                {{ ingredient.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label for="prefType">偏好类型 *</label>
            <select
              v-model="formData.preference_type"
              id="prefType"
              required
            >
              <option value="product">商品</option>
              <option value="recipe">菜谱</option>
            </select>
          </div>
          <div class="form-group" v-if="formData.preference_type === 'product'">
            <label for="defaultProduct">默认商品</label>
            <select
              v-model="formData.default_product_id"
              id="defaultProduct"
            >
              <option value="">请选择商品</option>
              <option
                v-for="product in products"
                :key="product.id"
                :value="product.id"
              >
                {{ product.name }}
              </option>
            </select>
          </div>
          <div class="form-group" v-if="formData.preference_type === 'recipe'">
            <label for="defaultRecipe">默认菜谱</label>
            <select
              v-model="formData.default_recipe_id"
              id="defaultRecipe"
            >
              <option value="">请选择菜谱</option>
              <option
                v-for="recipe in recipes"
                :key="recipe.id"
                :value="recipe.id"
              >
                {{ recipe.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>
              <input
                v-model="formData.is_favorite"
                type="checkbox"
                id="favorite"
              />
              设为收藏
            </label>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">{{ editingPref ? '更新' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { preferenceAPI, api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

interface Ingredient {
  id: number
  name: string
}

interface Product {
  id: number
  name: string
}

interface Recipe {
  id: number
  name: string
}

interface Preference {
  id: number
  user_id: number
  ingredient_id: number
  default_product_id: number | null
  default_recipe_id: number | null
  preference_type: string
  is_favorite: boolean
  created_at: string
  updated_at: string
  is_active: boolean
}

const preferences = ref<Preference[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const editingPref = ref<Preference | null>(null)

const ingredients = ref<Ingredient[]>([])
const products = ref<Product[]>([])
const recipes = ref<Recipe[]>([])

const formData = ref({
  ingredient_id: 0,
  default_product_id: null as number | null,
  default_recipe_id: null as number | null,
  preference_type: 'product',
  is_favorite: false
})

const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(async () => {
  await loadPreferences()
  await loadIngredients()
  await loadProducts()
  await loadRecipes()
})

async function loadPreferences() {
  loading.value = true
  try {
    const response = await preferenceAPI.list({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    })
    preferences.value = response as Preference[]
    total.value = preferences.value.length
  } catch (error) {
    console.error('Failed to load preferences:', error)
    alert('加载偏好数据失败')
  } finally {
    loading.value = false
  }
}

async function loadIngredients() {
  try {
    const response = await api.get<Ingredient[]>('/ingredients')
    ingredients.value = response || []
  } catch (error) {
    console.error('Failed to load ingredients:', error)
  }
}

async function loadProducts() {
  try {
    const response = await api.get<Product[]>('/products/entity?limit=100')
    products.value = response || []
  } catch (error) {
    console.error('Failed to load products:', error)
  }
}

async function loadRecipes() {
  try {
    const response = await api.get<Recipe[]>('/recipes?limit=100')
    recipes.value = response || []
  } catch (error) {
    console.error('Failed to load recipes:', error)
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadPreferences()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadPreferences()
}

function getIngredientName(ingredientId: number): string {
  const ingredient = ingredients.value.find(i => i.id === ingredientId)
  return ingredient?.name || `食材 ${ingredientId}`
}

function getProductName(productId: number): string {
  const product = products.value.find(p => p.id === productId)
  return product?.name || `商品 ${productId}`
}

function getRecipeName(recipeId: number): string {
  const recipe = recipes.value.find(r => r.id === recipeId)
  return recipe?.name || `菜谱 ${recipeId}`
}

function editPreference(pref: Preference) {
  editingPref.value = pref
  formData.value = {
    ingredient_id: pref.ingredient_id,
    default_product_id: pref.default_product_id,
    default_recipe_id: pref.default_recipe_id,
    preference_type: pref.preference_type,
    is_favorite: pref.is_favorite
  }
  showAddModal.value = true
}

function closeModal() {
  showAddModal.value = false
  editingPref.value = null
  formData.value = {
    ingredient_id: 0,
    default_product_id: null,
    default_recipe_id: null,
    preference_type: 'product',
    is_favorite: false
  }
}

async function savePreference() {
  try {
    if (editingPref.value) {
      await preferenceAPI.update(editingPref.value.ingredient_id, formData.value)
      alert('偏好已更新')
    } else {
      await preferenceAPI.set(formData.value)
      alert('偏好已添加')
    }
    closeModal()
    await loadPreferences()
  } catch (error) {
    console.error('Failed to save preference:', error)
    alert(editingPref.value ? '更新偏好失败' : '添加偏好失败')
  }
}

async function deletePreference(pref: Preference) {
  if (confirm(`确定要删除对 "${getIngredientName(pref.ingredient_id)}" 的偏好吗？`)) {
    try {
      await preferenceAPI.delete(pref.ingredient_id)
      await loadPreferences()
      alert('偏好已删除')
    } catch (error) {
      console.error('Failed to delete preference:', error)
      alert('删除偏好失败')
    }
  }
}
</script>

<style scoped>
.preference-manage {
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

.empty-state p {
  margin-bottom: 1rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary:hover {
  background: #5568d3;
}

.preference-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.preference-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s, transform 0.2s;
}

.preference-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.preference-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #eee;
}

.preference-header h3 {
  margin: 0;
  font-size: 1.125rem;
  color: #333;
}

.preference-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.badge-favorite {
  background: #fff3e0;
  color: #f5a623;
}

.badge-type {
  background: #e8f4fd;
  color: #0066cc;
}

.preference-details {
  margin-bottom: 1rem;
}

.preference-details p {
  margin: 0.5rem 0;
  color: #666;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.preference-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-sm {
  flex: 1;
  padding: 0.5rem;
  background: #f5f5f5;
  color: #333;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}

.btn-sm:hover {
  background: #e0e0e0;
}

.btn-edit:hover {
  background: #e3f2fd;
  color: #0066cc;
}

.btn-delete:hover {
  background: #ffebee;
  color: #c62828;
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
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 500px;
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
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.form-group select,
.form-group input[type="checkbox"] {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group select:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 0.5rem;
}

.form-group label input[type="checkbox"] {
  display: inline-block;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .preference-manage {
    padding: 1rem;
  }

  .preference-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1rem;
  }

  .preference-card {
    padding: 1rem;
  }

  .preference-header h3 {
    font-size: 1rem;
  }

  .preference-badges {
    flex-direction: column;
    align-items: flex-end;
  }

  .modal-content {
    padding: 1.5rem;
    max-width: calc(100% - 2rem);
  }

  .modal-content h2 {
    font-size: 1.25rem;
  }
}

@media (max-width: 480px) {
  .preference-grid {
    grid-template-columns: 1fr;
  }

  .preference-header {
    flex-direction: column;
    gap: 0.5rem;
  }

  .preference-badges {
    align-items: flex-start;
  }

  .modal-content {
    padding: 1rem;
    max-width: calc(100% - 1rem);
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
    padding: 0.625rem;
  }
}
</style>
