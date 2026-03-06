<template>
  <div class="product-manage">
    <PageHeader title="商品管理" :show-back="true">
      <template #extra>
        <button @click="openAddModal" class="btn-square add-btn" title="添加商品">
          <i class="mdi mdi-plus"></i>
        </button>
      </template>
    </PageHeader>

    <!-- 搜索和筛选 -->
    <div class="search-filter-wrapper">
      <!-- 检查是否有商家存在，如果不存在则显示提示 -->
      <div v-if="!merchantsLoading && allMerchants && allMerchants.length === 0" class="notification-banner full-width">
        <i class="mdi mdi-alert-outline"></i>
        <span>
          尚未创建商家，无法记录商品价格。
          请先<a href="#" @click.prevent="goToLocations()">创建商家</a>
        </span>
      </div>
      <div class="search-filter">
        <div class="search-box">
          <input
            v-model="searchTerm"
            placeholder="搜索商品名称、品牌、条码..."
            class="search-input"
            @input="debounceSearch"
          />
        </div>
        <button @click="loadProducts" class="btn-search">
          <i class="mdi mdi-magnify"></i> 搜索
        </button>
      </div>
    </div>

    <!-- 商品列表 -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="products.length === 0" class="empty-state">
      <p>暂无商品数据</p>
      <button @click="openAddModal" class="btn-primary">添加商品</button>
    </div>
    <div v-else class="product-grid">
      <div
        v-for="product in products"
        :key="product.id"
        class="product-card"
        @click="viewProduct(product)"
      >
        <div class="product-header">
          <h3>
            {{ product.name }}
            <span v-if="product.brand" class="brand-tag">{{ product.brand }}</span>
          </h3>
          <div class="product-actions">
            <button
              @click.stop="openEditModal(product)"
              class="btn-edit"
              title="编辑"
            >
              <i class="mdi mdi-pencil"></i>
            </button>
            <button
              @click.stop="addPriceRecord(product)"
              class="btn-add-price"
              :class="{ 'btn-disabled': merchantsLoading || allMerchants.length === 0 }"
              :disabled="merchantsLoading || allMerchants.length === 0"
              title="添加价格记录"
            >
              <i class="mdi mdi-currency-cny"></i>
            </button>
            <button
              @click.stop="deleteProduct(product)"
              class="btn-delete"
              title="删除"
            >
              <i class="mdi mdi-delete"></i>
            </button>
          </div>
        </div>

        <div class="product-info">
          <p v-if="product.ingredient_name">
            <i class="mdi mdi-grain"></i> {{ product.ingredient_name }}
          </p>
          <p v-if="product.barcode">
            <i class="mdi mdi-barcode"></i> {{ product.barcode }}
          </p>
          <p v-if="product.tags && product.tags.length > 0">
            <span
              v-for="tag in product.tags"
              :key="tag"
              class="tag"
            >
              {{ tag }}
            </span>
          </p>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <Pagination
      v-if="total > 0"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @change-page="handlePageChange"
      @change-page-size="handlePageSizeChange"
    />

    <!-- 添加/编辑商品模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingProduct ? '编辑商品' : '添加商品' }}</h2>
        <form @submit.prevent="saveProduct">
          <div class="form-group">
            <label for="productName">商品名称:</label>
            <input
              v-model="newProduct.name"
              type="text"
              id="productName"
              required
              placeholder="输入商品名称"
            />
          </div>
          <div class="form-group">
            <label for="productBrand">品牌:</label>
            <input
              v-model="newProduct.brand"
              type="text"
              id="productBrand"
              placeholder="输入品牌名称（可选）"
            />
          </div>
          <div class="form-group">
            <label for="productBarcode">条码:</label>
            <input
              v-model="newProduct.barcode"
              type="text"
              id="productBarcode"
              placeholder="输入商品条码（可选）"
            />
          </div>
          <div class="form-group">
            <label for="productIngredient">关联原料:</label>
            <div class="autocomplete-container">
              <input
                v-model="ingredientSearchTerm"
                type="text"
                id="productIngredient"
                placeholder="搜索并选择原料"
                @input="searchIngredients"
                @focus="showIngredientSuggestions = true"
                @keydown="handleIngredientKeydown"
              />
              <ul v-if="showIngredientSuggestions && ingredientSuggestions.length > 0" class="suggestions-list">
                <li
                  v-for="(suggestion, index) in ingredientSuggestions"
                  :key="suggestion.id"
                  :class="{ 'suggestion-selected': index === selectedIngredientIndex }"
                  @click="selectIngredient(suggestion)"
                >
                  {{ suggestion.name }}
                  <span v-if="suggestion.category_name" class="category-hint">({{ suggestion.category_name }})</span>
                </li>
              </ul>
            </div>
            <p v-if="newProduct.ingredient_id" class="selected-hint">
              已选择: {{ getIngredientName(newProduct.ingredient_id) }}
            </p>
          </div>
          <div class="form-group">
            <label for="productTags">标签 (用逗号分隔):</label>
            <input
              v-model="newProduct.tagsText"
              type="text"
              id="productTags"
              placeholder="例如: 有机, 进口, 促销"
            />
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">{{ editingProduct ? '更新' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { productAPI, api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

interface Product {
  id: number
  name: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id: number
  ingredient_name?: string
  tags?: string[]
  created_at: string
  updated_at?: string
  is_active: boolean
}

interface Ingredient {
  id: number
  name: string
  category_id?: number
  category_name?: string
  density?: number
  default_unit?: string
  aliases?: string[]
}

interface Merchant {
  id: number
  name: string
  address?: string
}

const router = useRouter()
const products = ref<Product[]>([])
const ingredients = ref<Ingredient[]>([])
const allMerchants = ref<Merchant[]>([])
const loading = ref(false)
const merchantsLoading = ref(true)  // 添加商家加载状态
const ingredientsLoading = ref(true)  // 添加原料加载状态
const showAddModal = ref(false)
const searchTerm = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 模态框相关
const editingProduct = ref<Product | null>(null)
const newProduct = ref({
  name: '',
  brand: '',
  barcode: '',
  ingredient_id: 0,
  tagsText: ''
})

// 原料自动完成相关
const ingredientSearchTerm = ref('')
const ingredientSuggestions = ref<Ingredient[]>([])
const showIngredientSuggestions = ref(false)
const selectedIngredientIndex = ref(-1)

let searchTimeout: ReturnType<typeof setTimeout> | null = null
let ingredientSearchTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  loadProducts()
  loadIngredients()
  loadLocations()
})

async function loadProducts() {
  loading.value = true
  try {
    const response = await productAPI.list({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      search: searchTerm.value || undefined
    })
    products.value = response as Product[]
    total.value = products.value.length
  } catch (error) {
    console.error('Failed to load products:', error)
  } finally {
    loading.value = false
  }
}

async function loadIngredients() {
  try {
    const response = await api.get('/ingredients?limit=500')
    ingredients.value = response.map((item: any) => ({
      ...item,
      category_name: getCategoryName(item.category_id)
    }))
  } catch (error) {
    console.error('Failed to load ingredients:', error)
  } finally {
    ingredientsLoading.value = false  // 更新加载状态
  }
}

async function loadLocations() {
  try {
    const response = await api.get<Merchant[]>('/merchants')  // 移除末尾斜杠
    allMerchants.value = response || []
  } catch (error) {
    console.error('Failed to load merchants:', error)
  } finally {
    merchantsLoading.value = false  // 更新加载状态
  }
}

function goToLocations() {
  router.push('/merchants')
}

function getCategoryName(categoryId?: number): string {
  if (!categoryId) return ''
  // 简单返回，实际可以从分类列表获取
  return ''
}

function debounceSearch() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadProducts()
  }, 300)
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadProducts()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadProducts()
}

function viewProduct(product: Product) {
  // 点击卡片可以查看详情或展开操作
  console.log('View product:', product)
}

// 模态框操作
function openAddModal() {
  editingProduct.value = null
  newProduct.value = {
    name: '',
    brand: '',
    barcode: '',
    ingredient_id: 0,
    tagsText: ''
  }
  ingredientSearchTerm.value = ''
  showAddModal.value = true
}

function openEditModal(product: Product) {
  editingProduct.value = product
  newProduct.value = {
    name: product.name,
    brand: product.brand || '',
    barcode: product.barcode || '',
    ingredient_id: product.ingredient_id,
    tagsText: product.tags ? product.tags.join(', ') : ''
  }
  ingredientSearchTerm.value = product.ingredient_name || ''
  showAddModal.value = true
}

function closeModal() {
  showAddModal.value = false
  editingProduct.value = null
  showIngredientSuggestions.value = false
}

async function saveProduct() {
  try {
    const tags = newProduct.value.tagsText
      ? newProduct.value.tagsText.split(',').map(s => s.trim()).filter(s => s)
      : []

    const productData: any = {
      name: newProduct.value.name,
      brand: newProduct.value.brand || null,
      barcode: newProduct.value.barcode || null,
      ingredient_id: newProduct.value.ingredient_id,
      tags: tags
    }

    if (editingProduct.value) {
      await productAPI.update(editingProduct.value.id, productData)
      alert('商品更新成功')
    } else {
      await productAPI.create(productData)
      alert('商品添加成功')
    }

    closeModal()
    await loadProducts()
  } catch (error: any) {
    console.error('Failed to save product:', error)
    alert(error.message || '保存失败')
  }
}

// 原料搜索和选择
function searchIngredients() {
  if (ingredientSearchTimeout) {
    clearTimeout(ingredientSearchTimeout)
  }
  ingredientSearchTimeout = setTimeout(() => {
    filterIngredients()
  }, 300)
}

function filterIngredients() {
  if (!ingredientSearchTerm.value.trim()) {
    ingredientSuggestions.value = ingredients.value.slice(0, 10)
  } else {
    const search = ingredientSearchTerm.value.toLowerCase()
    ingredientSuggestions.value = ingredients.value
      .filter(ing =>
        ing.name.toLowerCase().includes(search) ||
        (ing.aliases && ing.aliases.some(alias => alias.toLowerCase().includes(search)))
      )
      .slice(0, 10)
  }
  showIngredientSuggestions.value = ingredientSuggestions.value.length > 0
  selectedIngredientIndex.value = -1
}

function selectIngredient(ingredient: Ingredient) {
  newProduct.value.ingredient_id = ingredient.id
  ingredientSearchTerm.value = ingredient.name
  showIngredientSuggestions.value = false
  selectedIngredientIndex.value = -1
}

function handleIngredientKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedIngredientIndex.value = Math.min(selectedIngredientIndex.value + 1, ingredientSuggestions.value.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedIngredientIndex.value = Math.max(selectedIngredientIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedIngredientIndex.value >= 0) {
    event.preventDefault()
    selectIngredient(ingredientSuggestions.value[selectedIngredientIndex.value])
  } else if (event.key === 'Escape') {
    showIngredientSuggestions.value = false
    selectedIngredientIndex.value = -1
  }
}

function getIngredientName(ingredientId: number): string {
  const ing = ingredients.value.find(i => i.id === ingredientId)
  return ing ? ing.name : ''
}

// 价格记录和删除
function addPriceRecord(product: Product) {
  // 跳转到添加价格记录页面，带上商品信息
  router.push({
    path: '/products',
    query: { product_id: product.id, product_name: product.name }
  })
}

async function deleteProduct(product: Product) {
  if (confirm(`确定要删除商品 "${product.name}" 吗？此操作会软删除数据。`)) {
    try {
      await productAPI.delete(product.id)
      await loadProducts()
      alert('商品已删除')
    } catch (error) {
      console.error('Failed to delete product:', error)
      alert('删除失败')
    }
  }
}
</script>

<style scoped>
.product-manage {
  padding: 1rem;
}

.search-filter {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.search-box {
  flex: 1;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 0.875rem;
}

.search-input:focus {
  outline: none;
  border-color: #42b883;
}

.btn-search {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.btn-search:hover {
  background: #5568d3;
}

.btn-square.add-btn {
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
  transition: background-color 0.2s;
}

.btn-square.add-btn:hover {
  background: #36996d;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty-state p {
  margin-bottom: 1rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.btn-primary:hover {
  background: #36996d;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.product-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-left: 4px solid #667eea;
  display: flex;
  flex-direction: column;
}

.product-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.product-header h3 {
  font-size: 1.125rem;
  color: #333;
  margin: 0;
  flex-grow: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.brand-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 500;
}

.product-actions {
  display: flex;
  gap: 0.5rem;
}

.product-actions button {
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

.btn-edit, .btn-add-price {
  background: #667eea;
  color: white;
}

.btn-edit:hover, .btn-add-price:hover {
  background: #5a6fd8;
}

.btn-delete {
  background: #de350b;
  color: white;
}

.btn-delete:hover {
  background: #bc2e0b;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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

.form-group input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #42b883;
}

.autocomplete-container {
  position: relative;
}

.suggestions-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 0.5rem 0.5rem;
  max-height: 200px;
  overflow-y: auto;
  z-index: 1001;
  list-style: none;
  margin: 0;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.suggestions-list li {
  padding: 0.75rem 1rem;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
}

.suggestions-list li:last-child {
  border-bottom: none;
}

.suggestions-list li:hover,
.suggestions-list li.suggestion-selected {
  background-color: #e8f5e9;
}

.category-hint {
  color: #999;
  font-size: 0.8125rem;
  margin-left: 0.5rem;
}

.selected-hint {
  font-size: 0.75rem;
  color: #42b883;
  margin-top: 0.25rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .product-manage {
    padding: 0.75rem;
  }

  .product-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 0.75rem;
  }

  .product-card h3 {
    font-size: 0.875rem;
  }

  .product-info p {
    font-size: 0.8125rem;
  }

  .product-actions button {
    font-size: 0.75rem;
    padding: 0.375rem;
  }
}

@media (max-width: 480px) {
  .search-filter {
    flex-direction: column;
  }

  .search-input {
    padding: 0.625rem 0.875rem;
    font-size: 0.8125rem;
  }

  .btn-search {
    width: 100%;
    padding: 0.625rem;
  }

  .product-grid {
    grid-template-columns: 1fr;
  }

  .modal-content {
    padding: 1.5rem;
  }

  .form-actions {
    flex-direction: column;
  }

  .form-actions button {
    width: 100%;
  }
}

/* 按钮禁用样式 */
.btn-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* 通知横幅样式 */
.notification-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  margin: 0 0 1.5rem 0; /* 上右下左：保持一致边距 */
  font-size: 0.875rem;
}

.notification-banner.full-width {
  width: 100%; /* 让其占用全部宽度，内部通过padding实现对齐 */
  box-sizing: border-box;
}

.notification-banner a {
  color: #667eea;
  text-decoration: underline;
  font-weight: 500;
}

.notification-banner a:hover {
  color: #5568d3;
}

.search-filter-wrapper {
  margin-bottom: 1.5rem;
}
</style>