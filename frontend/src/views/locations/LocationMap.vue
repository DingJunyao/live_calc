<template>
  <div class="location-map">
    <header class="page-header">
      <h1>地点管理</h1>
      <button @click="showAddModal = true" class="btn-primary">
        + 添加地点
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

const locations = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)

onMounted(async () => {
  await loadLocations()
})

async function loadLocations() {
  loading.value = true
  try {
    const data = await api.get<{ items: any[] }>('/locations/')
    locations.value = data.items || []
  } catch (error) {
    console.error('Failed to load locations:', error)
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
.location-map {
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
</style>
