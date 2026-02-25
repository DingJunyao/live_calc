<template>
  <div class="product-list">
    <header class="page-header">
      <h1>商品记录</h1>
      <button @click="showAddModal = true" class="btn-primary">
        + 添加记录
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

const products = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)

onMounted(async () => {
  await loadProducts()
})

async function loadProducts() {
  loading.value = true
  try {
    const data = await api.get<{ items: any[] }>('/products/')
    products.value = data.items || []
  } catch (error) {
    console.error('Failed to load products:', error)
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
.product-list {
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
</style>
