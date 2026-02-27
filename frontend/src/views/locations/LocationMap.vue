<template>
  <div class="location-map">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>地点管理</h1>
      <button @click="showAddModal = true" class="btn-square add-btn" title="添加地点">
        <i class="mdi mdi-plus"></i>
      </button>
    </header>

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

const locations = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const newLocation = ref({
  name: '',
  address: '',
  latitude: 0,
  longitude: 0
})

onMounted(async () => {
  await loadLocations()
})

async function loadLocations() {
  loading.value = true
  try {
    const data = await api.get<any[]>('/locations')
    locations.value = data || []
  } catch (error) {
    console.error('Failed to load locations:', error)
  } finally {
    loading.value = false
  }
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
</style>
