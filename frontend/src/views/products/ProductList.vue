<template>
  <div class="product-list">
    <PageHeader title="价格记录" :show-back="true">
      <template #extra>
        <button @click="showAddModal = true" class="btn-square add-btn" title="添加记录">
          <i class="mdi mdi-plus"></i>
        </button>
      </template>
    </PageHeader>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="products.length === 0" class="empty-state">
      暂无价格记录
    </div>
    <div v-else class="product-grid">
      <div v-for="product in products" :key="product.id" class="product-card">
        <h3>{{ product.product_name }}</h3>
        <div class="product-info">
          <p>价格: ¥{{ product.price }}</p>
          <p>数量: {{ product.quantity }}</p>
          <p>单位: {{ product.unit }}</p>
          <p>记录时间: {{ formatDate(product.recorded_at) }}</p>
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

    <!-- 添加价格记录模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
      <div class="modal-content" @click.stop>
        <h2>添加价格记录</h2>
        <form @submit.prevent="addProduct">
          <div class="form-group">
            <label for="productName">商品:</label>
            <div class="autocomplete-container">
              <input
                v-model="newProduct.product_name"
                type="text"
                id="productName"
                required
                @input="onProductInput"
                @focus="showProductSuggestions = true"
                @keydown="handleKeydown"
              />
              <ul v-if="showProductSuggestions && productSuggestions.length > 0" class="suggestions-list">
                <li
                  v-for="(suggestion, index) in productSuggestions"
                  :key="suggestion.id"
                  :class="{ 'suggestion-selected': index === selectedIndex }"
                  @click="selectProduct(suggestion)"
                >
                  {{ suggestion.name }}
                  <span v-if="suggestion.brand" class="brand">({{ suggestion.brand }})</span>
                </li>
              </ul>
            </div>
          </div>
          <div class="form-group">
            <label for="price">价格:</label>
            <input v-model.number="newProduct.price" type="number" id="price" step="0.01" min="0" required />
          </div>
          <div class="form-group">
            <label for="quantity">数量:</label>
            <input v-model.number="newProduct.quantity" type="number" id="quantity" min="0" required />
          </div>
          <div class="form-group">
            <label for="unit">单位:</label>
            <input v-model="newProduct.unit" type="text" id="unit" required />
          </div>
          <div class="form-actions">
            <button type="button" @click="showAddModal = false" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">添加</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { productAPI, type ProductResponse } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

const products = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const newProduct = ref({
  product_id: 0,
  price: 0,
  quantity: 1,
  unit: ''
})

const productSuggestions = ref<ProductResponse[]>([])
const showProductSuggestions = ref(false)
const selectedIndex = ref(-1)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  await loadProducts()
  await loadAllProducts()
})

async function loadProducts() {
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const data = await (await fetch(`/api/v1/products?offset=${offset}&limit=${pageSize.value}`)).json()
    products.value = data
    total.value = products.value.length
  } catch (error) {
    console.error('Failed to load products:', error)
  } finally {
    loading.value = false
  }
}

async function loadAllProducts() {
  try {
    const response = await productAPI.list({ limit: 100 })
    productSuggestions.value = response as ProductResponse[]
  } catch (error) {
    console.error('Failed to load products:', error)
  }
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

async function addProduct() {
  try {
    // 找到选中的商品
    const selectedProduct = productSuggestions.value.find(p => p.name === newProduct.value.product_name)
    if (!selectedProduct) {
      alert('请选择有效的商品')
      return
    }

    // 使用 product_id 提交
    await fetch('/api/v1/products/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        product_id: selectedProduct.id,
        price: newProduct.value.price,
        original_quantity: newProduct.value.quantity,
        original_unit: newProduct.value.unit
      })
    })

    showAddModal.value = false
    // 重置表单
    newProduct.value = {
      product_id: 0,
      price: 0,
      quantity: 1,
      unit: ''
    }
    await loadProducts()
  } catch (error) {
    console.error('Failed to add product:', error)
    alert('添加价格记录失败，请重试')
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

function onProductInput() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    filterProducts()
  }, 300)
}

function filterProducts() {
  if (!newProduct.value.product_name.trim()) {
    productSuggestions.value = []
    showProductSuggestions.value = false
    return
  }

  const searchTerm = newProduct.value.product_name.toLowerCase()
  productSuggestions.value = (productSuggestions.value as any[]).filter((p: any) =>
    p.name.toLowerCase().includes(searchTerm)
  ).slice(0, 10)

  showProductSuggestions.value = productSuggestions.value.length > 0
  selectedIndex.value = -1
}

function selectProduct(product: ProductResponse) {
  newProduct.value.product_name = product.name
  showProductSuggestions.value = false
  selectedIndex.value = -1
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, productSuggestions.value.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedIndex.value >= 0) {
    event.preventDefault()
    selectProduct(productSuggestions.value[selectedIndex.value])
  } else if (event.key === 'Escape') {
    showProductSuggestions.value = false
    selectedIndex.value = -1
  }
}
</script>

<style scoped>
.product-list {
  padding: 2rem;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-secondary:hover {
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
  transition: background-color 0.2s;
}

.add-btn:hover {
  background: #36996d;
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

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.product-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s, transform 0.2s;
}

.product-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.product-card h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.25rem;
  color: #333;
}

.product-info p {
  margin: 0.5rem 0;
  color: #666;
  font-size: 0.875rem;
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
  border-radius: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
  z-index: 1000;
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
  background-color: #f5f5f5;
}

.suggestions-list .brand {
  color: #999;
  font-size: 0.8125rem;
  margin-left: 0.5rem;
}

.suggestions-list li:hover .brand,
.suggestions-list li.suggestion-selected .brand {
  color: #666;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s;
}

.btn-primary:hover {
  background: #36996d;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .product-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1rem;
  }

  .modal-content {
    padding: 1.5rem;
  }

  .add-btn {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }
}

@media (max-width: 480px) {
  .product-grid {
    grid-template-columns: 1fr;
  }

  .modal-content {
    padding: 1rem;
    max-width: calc(100% - 2rem);
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
