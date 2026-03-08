<template>
  <PageHeader title="商家管理" :show-back="true">
    <template #extra>
      <button @click="showAddModal = true" class="btn-square add-btn" title="添加商家">
        <i class="mdi mdi-plus"></i>
      </button>
    </template>
  </PageHeader>

  <div class="merchant-map">
    <div class="search-filter">
      <div class="search-box">
        <input v-model="searchTerm" placeholder="搜索商家名称或地址..." class="search-input" />
      </div>
      <button @click="loadMerchants" class="btn-search" title="搜索">
        <i class="mdi mdi-magnify"></i>
      </button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="merchants.length === 0" class="empty-state">
      暂无商家记录
    </div>

    <div v-else class="merchant-list">
      <div v-for="merchant in merchants" :key="merchant.id" class="merchant-card">
        <h3>{{ merchant.name }}</h3>
        <div class="merchant-info">
          <p v-if="merchant.address">地址: {{ merchant.address }}</p>
          <p>纬度: {{ merchant.latitude }}</p>
          <p>经度: {{ merchant.longitude }}</p>
          <p>添加时间: {{ formatDate(merchant.created_at) }}</p>
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

    <!-- 添加商家模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
      <div class="modal-content" @click.stop>
        <h2>添加商家</h2>
        <form @submit.prevent="addMerchant">
          <div class="form-group">
            <label for="merchantName">商家名称:</label>
            <input v-model="newMerchant.name" type="text" id="merchantName" required />
          </div>
          <div class="form-group">
            <label for="address">地址:</label>
            <input v-model="newMerchant.address" type="text" id="address" />
          </div>
          <div class="form-group">
            <label for="latitude">纬度:</label>
            <input v-model.number="newMerchant.latitude" type="number" id="latitude" step="any" required />
          </div>
          <div class="form-group">
            <label for="longitude">经度:</label>
            <input v-model.number="newMerchant.longitude" type="number" id="longitude" step="any" required />
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
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

const merchants = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const searchTerm = ref('')
const newMerchant = ref({
  name: '',
  address: '',
  latitude: 0,
  longitude: 0
})

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

onMounted(async () => {
  await loadMerchants()
})

async function loadMerchants() {
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    let url = `/merchants?offset=${offset}&limit=${pageSize.value}`
    if (searchTerm.value) {
      url += `&search=${encodeURIComponent(searchTerm.value)}`
    }
    const data = await api.get<any[]>(url)
    merchants.value = data || []
    // TODO: 需要后端支持返回总数
    total.value = merchants.value.length
  } catch (error) {
    console.error('Failed to load merchants:', error)
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadMerchants()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadMerchants()
}

async function addMerchant() {
  try {
    await api.post('/merchants', newMerchant.value)
    showAddModal.value = false
    // 重置表单
    newMerchant.value = {
      name: '',
      address: '',
      latitude: 0,
      longitude: 0
    }
    // 重新加载数据
    await loadMerchants()
  } catch (error) {
    console.error('Failed to add merchant:', error)
    alert('添加商家失败，请重试')
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.merchant-map {
  padding-left: 1rem;
  padding-right: 1rem;
}

.search-filter {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  padding: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.btn-search {
  padding: 0.5rem;
  background: #667eea;
  color: white;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-search:hover {
  background: #5a6fd8;
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

.merchant-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.merchant-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.merchant-card h3 {
  font-size: 1.125rem;
  color: #333;
  margin-bottom: 1rem;
}

.merchant-info p {
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

/* 移动端优化 */
@media (max-width: 768px) {
  .merchant-map {
    padding: 0.75rem;
  }

  .add-btn {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .merchant-list {
    gap: 0.75rem;
  }

  .merchant-card {
    padding: 1rem;
  }

  .merchant-card h3 {
    font-size: 1rem;
  }

  .merchant-info p {
    font-size: 0.8125rem;
  }

  .modal-content {
    padding: 1.5rem;
  }

  .modal-content h2 {
    font-size: 1.25rem;
  }

  .form-group {
    margin-bottom: 0.75rem;
  }

  .form-group input {
    font-size: 0.875rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .merchant-map {
    padding: 0.5rem;
  }

  .add-btn {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .merchant-list {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .merchant-card {
    padding: 0.75rem;
  }

  .merchant-card h3 {
    font-size: 0.9375rem;
  }

  .merchant-info p {
    font-size: 0.75rem;
  }

  .modal-content {
    padding: 1rem;
    max-width: calc(100% - 1rem);
  }

  .btn-fab {
    width: 2.75rem;
    height: 2.75rem;
    bottom: 1rem;
    right: 1rem;
    font-size: 1rem;
  }
}
</style>
