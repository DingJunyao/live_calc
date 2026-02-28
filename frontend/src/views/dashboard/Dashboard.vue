<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <h1>欢迎回来，{{ user?.username }}！</h1>
      <button @click="handleLogout" class="btn-logout">退出</button>
    </header>

    <div v-if="loading" class="loading">
      加载中...
    </div>

    <template v-else>
      <div class="quick-actions">
        <router-link to="/products" class="action-card">
          <i class="mdi mdi-clipboard-text mdi-24px icon"></i>
          <span>价格</span>
        </router-link>
        <router-link to="/ingredients" class="action-card">
          <i class="mdi mdi-food mdi-24px icon"></i>
          <span>原料</span>
        </router-link>
        <router-link to="/recipes" class="action-card">
          <i class="mdi mdi-food mdi-24px icon"></i>
          <span>菜谱</span>
        </router-link>
        <router-link to="/locations" class="action-card">
          <i class="mdi mdi-map-marker mdi-24px icon"></i>
          <span>地点</span>
        </router-link>
        <router-link to="/reports" class="action-card">
          <i class="mdi mdi-chart-bar mdi-24px icon"></i>
          <span>报告</span>
        </router-link>
        <router-link v-if="user?.is_admin" to="/admin" class="action-card admin-action">
          <i class="mdi mdi-cog mdi-24px icon"></i>
          <span>后台管理</span>
        </router-link>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <h3>本月支出</h3>
          <p class="stat-value">¥{{ typeof monthlyExpense === 'number' ? monthlyExpense.toFixed(2) : '0.00' }}</p>
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
    </template>

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
import { api } from '@/api/client'

const router = useRouter()
const userStore = useUserStore()

const user = computed(() => userStore.user)
const monthlyExpense = ref(0)
const recordCount = ref(0)
const recipeCount = ref(0)
const recentRecords = ref<any[]>([])
const loading = ref(false)

onMounted(async () => {
  if (!user.value) {
    router.push('/login')
    return
  }

  await loadDashboardData()
})

async function loadDashboardData() {
  loading.value = true
  try {
    // 获取本月支出统计
    const today = new Date()
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
    const startDate = firstDay.toISOString().split('T')[0]
    const endDate = today.toISOString().split('T')[0]

    try {
      const expenseReport = await api.get<any>(
        `/reports/expense?start_date=${startDate}&end_date=${endDate}`
      )
      monthlyExpense.value = (expenseReport && typeof expenseReport.total_expense !== 'undefined' && expenseReport.total_expense !== null)
        ? Number(expenseReport.total_expense) || 0
        : 0
    } catch (error) {
      console.error('Failed to load expense report:', error)
      monthlyExpense.value = 0
    }

    // 获取记录数量
    try {
      const productsResponse = await api.get<any[]>('/products')
      recordCount.value = productsResponse.length || 0
    } catch (error) {
      console.error('Failed to load record count:', error)
      recordCount.value = 0
    }

    // 获取菜谱数量
    try {
      const recipesResponse = await api.get<any[]>('/recipes')
      recipeCount.value = recipesResponse.length || 0
    } catch (error) {
      console.error('Failed to load recipe count:', error)
      recipeCount.value = 0
    }

    // 获取最近记录
    try {
      const recentData = await api.get<any[]>('/products?limit=10')
      recentRecords.value = recentData || []
    } catch (error) {
      console.error('Failed to load recent records:', error)
      recentRecords.value = []
    }
  } finally {
    loading.value = false
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
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

/* 为页面中的主要组件之间添加垂直间距 */
.quick-actions {
  margin-bottom: 2rem;
}

.stats-grid {
  margin-bottom: 2rem;
}

.recent-records {
  margin-top: 1rem;
}

.dashboard-header h1 {
  font-size: 1.5rem;
  color: #333;
}

.btn-logout {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-logout:hover {
  background: #e0e0e0;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: #666;
  font-size: 1.125rem;
}

/* 优化网格布局以便在移动端尽可能显示在一行 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr); /* 调整最小宽度以适应移动设备 */
  gap: 1rem; /* 减小间隙 */
}

.stat-card {
  background: white;
  padding: 1.25rem; /* 减小内边距 */
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
  grid-template-columns: repeat(4, 1fr); /* 调整最小宽度以适应移动设备 */
  gap: 0.75rem; /* 减小间隙 */
}

.action-card {
  background: white;
  padding: 1.25rem; /* 减小内边距 */
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
  text-decoration: none;
  color: #333;
  transition: transform 0.2s, box-shadow 0.2s;
}

.action-card.admin-action {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-card.admin-action .icon {
  color: white;
}

.action-card.admin-action span:not(.icon) {
  color: white;
}

.action-card.admin-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.action-card .icon {
  font-size: 1.75rem; /* 减小图标大小 */
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

/* 移动端优化 */
@media (max-width: 768px) {
  .dashboard {
    padding: 1rem;
  }

  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .stats-grid {
    gap: 0.75rem;
  }

  .stat-card {
    padding: 1rem;
  }

  .quick-actions {
    gap: 0.5rem;
  }

  .action-card {
    padding: 1rem;
  }

  .recent-records {
    padding: 1rem;
  }
}
</style>
