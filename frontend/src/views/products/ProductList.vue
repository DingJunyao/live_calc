<template>
  <div class="product-list">
    <PageHeader title="价格记录" :show-back="true">
      <template #extra>
        <button
          @click="openAddModal"
          class="btn-square add-btn"
          title="添加记录"
          :disabled="loading || merchantsLoading || allProducts.length === 0 || allMerchants.length === 0"
          :class="{ 'btn-disabled': loading || merchantsLoading || allProducts.length === 0 || allMerchants.length === 0 }"
        >
          <i class="mdi mdi-plus"></i>
        </button>
      </template>
    </PageHeader>

    <!-- 检查商品和商家是否存在，如果不存在则显示提示 -->
    <div v-if="(!loading && allProducts.length === 0) || (!merchantsLoading && allMerchants.length === 0)" class="notification-banner full-width">
      <i class="mdi mdi-alert-outline"></i>
      <span>
        <template v-if="(!loading && allProducts.length === 0) && (!merchantsLoading && allMerchants.length === 0)">
          尚未创建商品和商家，请先
          <a href="#" @click.prevent="goToProductsManage()">创建商品</a>
          和
          <a href="#" @click.prevent="goToLocations()">创建商家</a>
        </template>
        <template v-else-if="!loading && allProducts.length === 0">
          尚未创建商品，无法记录价格。请先<a href="#" @click.prevent="goToProductsManage()">创建商品</a>
        </template>
        <template v-else-if="!merchantsLoading && allMerchants.length === 0">
          尚未创建商家，无法记录商品价格。请先<a href="#" @click.prevent="goToLocations()">创建商家</a>
        </template>
      </span>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="products.length === 0" class="empty-state">
      暂无价格记录
    </div>
    <div v-else class="product-grid">
      <div v-for="product in products" :key="product.id" class="product-card">
        <h3>{{ product.product_name }}</h3>
        <div class="product-info">
          <p>价格: ¥{{ product.price }}</p>
          <p>数量: {{ product.original_quantity }} {{ product.original_unit }}</p>
          <p>标准单位: {{ product.standard_quantity }} {{ product.standard_unit }}</p>
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
    <div v-if="showAddModal" class="modal-overlay" @click="closeModal">
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
                placeholder="搜索并选择商品"
                @input="onProductInput"
                @focus="showProductSuggestions = true"
                @keydown="handleKeydown"
              />
              <ul v-if="showProductSuggestions && filteredSuggestions.length > 0" class="suggestions-list">
                <li
                  v-for="(suggestion, index) in filteredSuggestions"
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
            <label for="price">价格 (元):</label>
            <input v-model.number="newProduct.price" type="number" id="price" step="0.01" min="0" required />
          </div>
          <div class="form-group">
            <label for="quantity">数量:</label>
            <input v-model.number="newProduct.quantity" type="number" id="quantity" min="0" step="any" required />
          </div>
          <div class="form-group">
            <label for="unit">单位:</label>
            <input v-model="newProduct.unit" type="text" id="unit" placeholder="如: kg, g, 个" required />
          </div>
          <div class="form-group">
            <label for="location">商家:</label>
            <div class="autocomplete-container">
              <input
                v-model="newProduct.merchant_name"
                type="text"
                id="location"
                placeholder="搜索并选择商家"
                @input="onLocationInput"
                @focus="showLocationSuggestions = true"
                @keydown="handleLocationKeydown"
              />
              <ul v-if="showLocationSuggestions && filteredLocationSuggestions.length > 0" class="suggestions-list">
                <li
                  v-for="(suggestion, index) in filteredLocationSuggestions"
                  :key="suggestion.id"
                  :class="{ 'suggestion-selected': index === selectedLocationIndex }"
                  @click="selectLocation(suggestion)"
                >
                  {{ suggestion.name }}
                  <span v-if="suggestion.address" class="address">({{ suggestion.address }})</span>
                </li>
              </ul>
            </div>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">添加</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productAPI, api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

interface ProductSuggestion {
  id: number
  name: string
  brand?: string
}

interface PriceRecord {
  id: number
  product_id: number
  product_name: string
  price: number
  original_quantity: number
  original_unit: string
  standard_quantity: number
  standard_unit: string
  recorded_at: string
}

interface Merchant {
  id: number
  name: string
  address?: string
}

const route = useRoute()
const router = useRouter()
const products = ref<PriceRecord[]>([])
const allProducts = ref<ProductSuggestion[]>([])
const allMerchants = ref<Merchant[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const newProduct = ref({
  product_id: 0,
  product_name: '',
  price: 0,
  quantity: 1,
  unit: '',
  merchant_id: 0,
  merchant_name: ''
})

const showProductSuggestions = ref(false)
const selectedIndex = ref(-1)
const showLocationSuggestions = ref(false)
const selectedLocationIndex = ref(-1)

// 添加商家加载状态
const merchantsLoading = ref(true)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

// 过滤后的建议列表
const filteredSuggestions = computed(() => {
  if (!newProduct.value.product_name.trim()) {
    return allProducts.value.slice(0, 10)
  }
  const search = newProduct.value.product_name.toLowerCase()
  return allProducts.value
    .filter(p => p.name.toLowerCase().includes(search))
    .slice(0, 10)
})

// 过滤后的商家建议列表
const filteredLocationSuggestions = computed(() => {
  if (!newProduct.value.merchant_name.trim()) {
    return allMerchants.value.slice(0, 10)
  }
  const search = newProduct.value.merchant_name.toLowerCase()
  return allMerchants.value
    .filter(l => l.name.toLowerCase().includes(search) ||
               (l.address && l.address.toLowerCase().includes(search)))
    .slice(0, 10)
})

onMounted(async () => {
  await loadProducts()
  await loadAllProducts()
  await loadAllMerchants()

  // 检查是否有从商品管理页面传来的参数
  const productId = route.query.product_id
  const productName = route.query.product_name as string
  if (productId && productName) {
    newProduct.value.product_id = Number(productId)
    newProduct.value.product_name = productName
    // 如果有路由参数，则检查是否有足够数据（商家），但不强制跳转
    // 如果商家为空，则直接打开模态框，让用户可以选择商家或被提示
    showAddModal.value = true
  }
})

async function loadProducts() {
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const data = await api.get<PriceRecord[]>(`/products?offset=${offset}&limit=${pageSize.value}`)
    products.value = data || []
    total.value = products.value.length
  } catch (error) {
    console.error('Failed to load products:', error)
  } finally {
    loading.value = false
  }
}

async function loadAllProducts() {
  try {
    const response = await productAPI.list({ limit: 200 })
    allProducts.value = response as ProductSuggestion[]
  } catch (error) {
    console.error('Failed to load products:', error)
  }
}

async function loadAllMerchants() {
  try {
    const response = await api.get<Merchant[]>('/merchants')  // 移除末尾斜杠
    allMerchants.value = response || []
  } catch (error) {
    console.error('Failed to load merchants:', error)
  } finally {
    merchantsLoading.value = false  // 更新加载状态
  }
}

function openAddModal() {
  // 检查按钮是否被禁用，如果是，则不执行任何操作
  if (loading.value || merchantsLoading.value || allProducts.value.length === 0 || allMerchants.value.length === 0) {
    return;
  }

  // 初始化表单并显示模态框
  newProduct.value = {
    product_id: 0,
    product_name: '',
    price: 0,
    quantity: 1,
    unit: '',
    merchant_id: 0,
    merchant_name: ''
  }
  showAddModal.value = true
}

function closeModal() {
  showAddModal.value = false
  showProductSuggestions.value = false
  showLocationSuggestions.value = false
  selectedIndex.value = -1
  selectedLocationIndex.value = -1
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
    // 验证是否提供了商品
    let productId = newProduct.value.product_id
    if (!productId) {
      if (!newProduct.value.product_name) {
        alert('请先选择商品')
        return
      }
      const matched = allProducts.value.find(p => p.name === newProduct.value.product_name)
      if (matched) {
        productId = matched.id
      } else {
        alert('请选择有效的商品')
        return
      }
    }

    // 如果选择了商家ID，使用它；否则不发送merchant_id
    let merchantId = newProduct.value.merchant_id
    if (!merchantId && newProduct.value.merchant_name) {
      const matched = allMerchants.value.find(m => m.name === newProduct.value.merchant_name)
      if (matched) {
        merchantId = matched.id
      }
    }

    // 验证价格、数量等必填字段
    if (newProduct.value.price <= 0) {
      alert('请输入有效的价格')
      return
    }

    if (newProduct.value.quantity <= 0) {
      alert('请输入有效的数量')
      return
    }

    // 提交价格记录
    await api.post('/products/', {
      product_id: productId,
      price: newProduct.value.price,
      original_quantity: newProduct.value.quantity,
      original_unit: newProduct.value.unit,
      merchant_id: merchantId || undefined
    })

    closeModal()
    await loadProducts()
    alert('价格记录添加成功')
  } catch (error) {
    console.error('Failed to add product:', error)
    alert('添加价格记录失败，请重试')
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function onProductInput() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    // 重置选中的商品ID，因为用户可能正在修改
    if (!allProducts.value.find(p => p.name === newProduct.value.product_name)) {
      newProduct.value.product_id = 0
    }
    showProductSuggestions.value = true
    selectedIndex.value = -1
  }, 300)
}

function selectProduct(product: ProductSuggestion) {
  newProduct.value.product_id = product.id
  newProduct.value.product_name = product.name
  showProductSuggestions.value = false
  selectedIndex.value = -1
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, filteredSuggestions.value.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedIndex.value >= 0) {
    event.preventDefault()
    selectProduct(filteredSuggestions.value[selectedIndex.value])
  } else if (event.key === 'Escape') {
    showProductSuggestions.value = false
    selectedIndex.value = -1
  }
}

function onLocationInput() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    // 重置选中的地点ID，因为用户可能正在修改
    if (!allMerchants.value.find(l => l.name === newProduct.value.merchant_name)) {
      newProduct.value.merchant_id = 0
    }
    showLocationSuggestions.value = true
    selectedLocationIndex.value = -1
  }, 300)
}

function selectLocation(location: Merchant) {
  newProduct.value.merchant_id = location.id
  newProduct.value.merchant_name = location.name
  showLocationSuggestions.value = false
  selectedLocationIndex.value = -1
}

function handleLocationKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedLocationIndex.value = Math.min(selectedLocationIndex.value + 1, filteredLocationSuggestions.value.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedLocationIndex.value = Math.max(selectedLocationIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedLocationIndex.value >= 0) {
    event.preventDefault()
    selectLocation(filteredLocationSuggestions.value[selectedLocationIndex.value])
  } else if (event.key === 'Escape') {
    showLocationSuggestions.value = false
    selectedLocationIndex.value = -1
  }
}

function goToProductsManage() {
  router.push('/products/manage')
}

function goToLocations() {
  router.push('/merchants')
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

.suggestions-list .address {
  color: #999;
  font-size: 0.8125rem;
  margin-left: 0.5rem;
}

.suggestions-list li:hover .brand,
.suggestions-list li.suggestion-selected .brand {
  color: #666;
}

.suggestions-list li:hover .address,
.suggestions-list li.suggestion-selected .address {
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
  margin: 0 0 1.5rem 0; /* 上右下左：保持左边距，减少右边距 */
  font-size: 0.875rem;
}

.notification-banner.full-width {
  width: 100%; /* 让其占用全部宽度，内部通过padding实现对齐 */
  box-sizing: border-box;
}

.notification-banner i {
  font-size: 1.25rem;
}

.notification-banner a {
  color: #667eea;
  text-decoration: underline;
  font-weight: 500;
}

.notification-banner a:hover {
  color: #5568d3;
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

/* 按钮禁用样式 */
.btn-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}
</style>
