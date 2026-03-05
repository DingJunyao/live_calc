<template>
  <div class="location-map">
    <PageHeader title="地点管理" :show-back="true">
      <template #extra>
        <button @click="showAddModal = true" class="btn-square add-btn" title="添加地点">
          <i class="mdi mdi-plus"></i>
        </button>
      </template>
    </PageHeader>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="locations.length === 0" class="empty-state">
      暂无地点记录
    </div>

    <div v-else class="location-list">
      <div v-for="location in locations" :key="location.id" class="location-card">
        <h3>{{ location.name }}</h3>
        <div class="location-info">
          <p v-if="location.address">地址: {{ location.address }}</p>
          <p>纬度: {{ location.latitude }}</p>
          <p>经度: {{ location.longitude }}</p>
          <p>添加时间: {{ formatDate(location.created_at) }}</p>
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

    <!-- 添加地点模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
      <div class="modal-content" @click.stop>
        <h2>添加地点</h2>
        <form @submit.prevent="addLocation">
          <div class="form-group">
            <label for="locationName">地点名称:</label>
            <input v-model="newLocation.name" type="text" id="locationName" required />
          </div>
          <div class="form-group">
            <label for="address">地址:</label>
            <input v-model="newLocation.address" type="text" id="address" />
          </div>
          <div class="form-group">
            <label for="latitude">纬度:</label>
            <input v-model.number="newLocation.latitude" type="number" id="latitude" step="any" required />
          </div>
          <div class="form-group">
            <label for="longitude">经度:</label>
            <input v-model.number="newLocation.longitude" type="number" id="longitude" step="any" required />
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

const locations = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const newLocation = ref({
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
  await loadLocations()
})

async function loadLocations() {
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const data = await api.get<any[]>(`/locations?offset=${offset}&limit=${pageSize.value}`)
    locations.value = data || []
    // TODO: 需要后端支持返回总数
    total.value = locations.value.length
  } catch (error) {
    console.error('Failed to load locations:', error)
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadLocations()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadLocations()
}

async function addLocation() {
  try {
    await api.post('/locations', newLocation.value)
    showAddModal.value = false
    // 重置表单
    newLocation.value = {
      name: '',
      address: '',
      latitude: 0,
      longitude: 0
    }
    // 重新加载数据
    await loadLocations()
  } catch (error) {
    console.error('Failed to add location:', error)
    alert('添加地点失败，请重试')
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.location-map {
  padding: 2rem;
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

.location-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.location-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.location-card h3 {
  font-size: 1.125rem;
  color: #333;
  margin-bottom: 1rem;
}

.location-info p {
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
  .location-map {
    padding: 0.75rem;
  }

  .add-btn {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .location-list {
    gap: 0.75rem;
  }

  .location-card {
    padding: 1rem;
  }

  .location-card h3 {
    font-size: 1rem;
  }

  .location-info p {
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
  .location-map {
    padding: 0.5rem;
  }

  .add-btn {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .location-list {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .location-card {
    padding: 0.75rem;
  }

  .location-card h3 {
    font-size: 0.9375rem;
  }

  .location-info p {
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
