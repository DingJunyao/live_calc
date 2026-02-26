<template>
  <div class="product-list">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>商品记录</h1>
      <button @click="showAddModal = true" class="btn-square add-btn" title="添加记录">
        <i class="mdi mdi-plus"></i>
      </button>
    </header>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="products.length === 0" class="empty-state">
      暂无商品记录
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

    <!-- 添加商品记录模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
      <div class="modal-content" @click.stop>
        <h2>添加商品记录</h2>
        <form @submit.prevent="addProduct">
          <div class="form-group">
            <label for="productName">商品名称:</label>
            <input v-model="newProduct.product_name" type="text" id="productName" required />
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
import { api } from '@/api/client'

const products = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const newProduct = ref({
  product_name: '',
  price: 0,
  quantity: 1,
  unit: ''
})

onMounted(async () => {
  await loadProducts()
})

async function loadProducts() {
  loading.value = true
  try {
    const data = await api.get<any[]>('/products/')
    products.value = data || []
  } catch (error) {
    console.error('Failed to load products:', error)
  } finally {
    loading.value = false
  }
}

async function addProduct() {
  try {
    await api.post('/products/', newProduct.value)
    showAddModal.value = false
    // 重置表单
    newProduct.value = {
      product_name: '',
      price: 0,
      quantity: 1,
      unit: ''
    }
    // 重新加载数据
    await loadProducts()
  } catch (error) {
    console.error('Failed to add product:', error)
    alert('添加商品记录失败，请重试')
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.product-list {
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

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.product-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.product-card h3 {
  font-size: 1.125rem;
  color: #333;
  margin-bottom: 1rem;
}

.product-info p {
  margin: 0.25rem 0;
  color: #666;
  font-size: 0.875rem;
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
