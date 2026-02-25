<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <h1>欢迎回来，{{ user?.username }}！</h1>
      <button @click="handleLogout" class="btn-logout">退出</button>
    </header>

    <div class="stats-grid">
      <div class="stat-card">
        <h3>本月支出</h3>
        <p class="stat-value">¥{{ monthlyExpense.toFixed(2) }}</p>
      </div>

      <div class="stat-card">
        <h3>记录数量</h3>
        <p class="stat-value">{{ recordCount }}</p>
      </div>

      <div class="stat-card">
        <h3>菜谱数量</h3>
        <p class="stat-value">{{ recipeCount }}</p>
      </div>
    </div>

    <div class="quick-actions">
      <router-link to="/products/new" class="action-card">
        <span class="icon">📝</span>
        <span>记录商品</span>
      </router-link>
      <router-link to="/recipes/new" class="action-card">
        <span class="icon">🍳</span>
        <span>创建菜谱</span>
      </router-link>
      <router-link to="/locations/new" class="action-card">
        <span class="icon">📍</span>
        <span>添加地点</span>
      </router-link>
      <router-link to="/reports" class="action-card">
        <span class="icon">📊</span>
        <span>查看报告</span>
      </router-link>
    </div>

    <div class="recent-records">
      <h2>最近记录</h2>
      <div v-if="recentRecords.length === 0" class="empty-state">
        暂无记录，开始添加吧！
      </div>
      <div v-else class="record-list">
        <div v-for="record in recentRecords" :key="record.id" class="record-item">
          <div class="record-info">
            <span class="record-name">{{ record.product_name }}</span>
            <span class="record-date">{{ formatDate(record.recorded_at) }}</span>
          </div>
          <span class="record-price">¥{{ record.price }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const user = computed(() => userStore.user)
const monthlyExpense = ref(0)
const recordCount = ref(0)
const recipeCount = ref(0)
const recentRecords = ref<any[]>([])

onMounted(async () => {
  if (!user.value) {
    router.push('/login')
    return
  }

  await loadDashboardData()
})

async function loadDashboardData() {
  // Mock data for now - will be replaced with real API calls
  monthlyExpense.value = 1250.50
  recordCount.value = 42
  recipeCount.value = 15
  recentRecords.value = [
    {
      id: 1,
      product_name: '有机鸡蛋',
      price: '12.50',
      recorded_at: '2024-01-15T10:30:00'
    }
  ]
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

function handleLogout() {
  userStore.logout()
}
</script>

<style scoped>
.dashboard {
  padding: 2rem;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  font-size: 1.5rem;
  color: #333;
}

.btn-logout {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.stat-card h3 {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #42b883;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.action-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
  text-decoration: none;
  color: #333;
  transition: transform 0.2s, box-shadow 0.2s;
}

.action-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.action-card .icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 0.5rem;
}

.recent-records {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.empty-state {
  color: #999;
  text-align: center;
  padding: 2rem;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

.record-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.record-name {
  font-weight: 500;
  color: #333;
}

.record-date {
  font-size: 0.75rem;
  color: #999;
}

.record-price {
  font-weight: bold;
  color: #42b883;
}
</style>
