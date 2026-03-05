<template>
  <div class="product-manage">
    <PageHeader title="商品管理" :show-back="true">
      <template #extra>
        <button @click="showAddModal = true" class="btn-square add-btn" title="添加商品">
          <i class="mdi mdi-plus"></i>
        </button>
      </template>
    </PageHeader>

    <!-- 搜索和筛选 -->
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

    <!-- 商品列表 -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="products.length === 0" class="empty-state">
      <p>暂无商品数据</p>
      <button @click="showAddModal = true" class="btn-primary">添加商品</button>
    </div>
    <div v-else class="product-grid">
      <div
        v-for="product in products"
        :key="product.id"
        class="product-card"
        @click="viewProduct(product)"
      >
        <div class="product-image">
          <img
            v-if="product.image_url"
            :src="product.image_url"
            :alt="product.name"
          />
          <div v-else class="placeholder-image">
            <i class="mdi mdi-package-variant"></i>
          </div>
        </div>
        <h3>{{ product.name }}</h3>
        <div class="product-info">
          <p v-if="product.brand">
            <i class="mdi mdi-tag"></i> {{ product.brand }}
          </p>
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
        <div class="product-actions">
          <button
            @click.stop="editProduct(product)"
            class="btn-edit"
            title="编辑"
          >
            <i class="mdi mdi-pencil"></i>
          </button>
          <button
            @click.stop="addPriceRecord(product)"
            class="btn-add-price"
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { productAPI } from '@/api/client'
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

const router = useRouter()
const products = ref<Product[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const searchTerm = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  loadProducts()
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
  // TODO: 跳转到商品详情页
  console.log('View product:', product)
}

function editProduct(product: Product) {
  // TODO: 打开编辑模态框
  console.log('Edit product:', product)
}

function addPriceRecord(product: Product) {
  router.push(`/products/record/${product.id}`)
}

async function deleteProduct(product: Product) {
  if (confirm(`确定要删除商品 "${product.name}" 吗？`)) {
    try {
      await productAPI.delete(product.id)
      await loadProducts()
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
  border-color: #667eea;
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

.btn-square {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
  transition: background-color 0.2s;
}

.btn-square:hover {
  background: #5568d3;
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
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.btn-primary:hover {
  background: #5568d3;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.product-card {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}

.product-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.product-image {
  width: 100%;
  height: 200px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder-image {
  font-size: 4rem;
  color: #ccc;
}

.product-card h3 {
  margin: 0;
  padding: 1rem 1rem 0.5rem;
  font-size: 1rem;
  color: #333;
}

.product-info {
  padding: 0 1rem 0.5rem;
}

.product-info p {
  margin: 0.25rem 0;
  font-size: 0.875rem;
  color: #666;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.tag {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background: #e8f4fd;
  color: #0066cc;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  margin-right: 0.25rem;
}

.product-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 1rem 1rem;
}

.product-actions button {
  flex: 1;
  padding: 0.5rem;
  background: #f5f5f5;
  color: #333;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.product-actions button:hover {
  background: #e0e0e0;
}

.btn-edit:hover {
  background: #e3f2fd;
  color: #0066cc;
}

.btn-add-price:hover {
  background: #e8f5e9;
  color: #2e7d32;
}

.btn-delete:hover {
  background: #ffebee;
  color: #c62828;
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

  .product-actions {
    padding: 0.5rem 0.75rem 0.75rem;
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

  .product-image {
    height: 180px;
  }
}
</style>
