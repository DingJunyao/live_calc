<template>
  <PageHeader :title="`欢迎回来，${user?.username}！`" :show-home="false" />

  <div class="dashboard">

    <div v-if="loading" class="loading">
      加载中...
    </div>

    <template v-else>
      <div class="quick-actions">
        <router-link to="/products" class="action-card">
          <i class="mdi mdi-clipboard-text mdi-24px icon"></i>
          <span>价格</span>
        </router-link>
        <router-link to="/products/manage" class="action-card">
          <i class="mdi mdi-package mdi-24px icon"></i>
          <span>商品</span>
        </router-link>
        <router-link to="/ingredients" class="action-card">
          <i class="mdi mdi-food mdi-24px icon"></i>
          <span>原料</span>
        </router-link>
        <router-link to="/preferences" class="action-card">
          <i class="mdi mdi-heart mdi-24px icon"></i>
          <span>偏好</span>
        </router-link>
        <router-link to="/recipes" class="action-card">
          <i class="mdi mdi-food mdi-24px icon"></i>
          <span>菜谱</span>
        </router-link>
        <router-link to="/merchants" class="action-card">
          <i class="mdi mdi-map-marker mdi-24px icon"></i>
          <span>商家</span>
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
            <span class="record-name">{{ record.product_name || '未知商品' }}</span>
            <span class="record-date">{{ formatDate(record.recorded_at) }}</span>
          </div>
          <div class="record-price-container">
            <div class="total-price">¥{{ record.price || '0.00' }}</div>
            <div class="unit-price">
              ¥{{ calculateUnitPrice(record) }} {{ record.original_quantity || '0' }} {{ record.original_unit || '' }}
            </div>
          </div>
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
import PageHeader from '@/components/PageHeader.vue'

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

    // 获取个人统计信息（使用新API获取准确计数）
    try {
      const statsResponse = await api.get<any>('/auth/personal-stats')
      recordCount.value = statsResponse.record_count || 0
      recipeCount.value = statsResponse.recipe_count || 0
    } catch (error) {
      console.error('Failed to load personal stats:', error)
      // 如果新的API失败，回退到原来的逻辑
      try {
        const productsResponse = await api.get<any>('/products')
        recordCount.value = productsResponse?.total || productsResponse?.items?.length || 0
      } catch (error2) {
        console.error('Failed to load record count:', error2)
        recordCount.value = 0
      }

      try {
        const recipesResponse = await api.get<any>('/recipes?limit=1&include_cost=false')
        // 检查是否有分页格式的total
        if (recipesResponse?.total !== undefined) {
          recipeCount.value = recipesResponse.total || 0
        } else {
          // 如果没有分页格式，假定是数组格式
          recipeCount.value = Array.isArray(recipesResponse) ? recipesResponse.length : 0
        }
      } catch (error2) {
        console.error('Failed to load recipe count:', error2)
        recipeCount.value = 0
      }
    }

    // 获取最近记录
    try {
      const recentData = await api.get<any>('/products?limit=10')
      // 处理分页格式，从items里取数据
      recentRecords.value = recentData?.items || recentData || []
    } catch (error) {
      console.error('Failed to load recent records:', error)
      recentRecords.value = []
    }
  } finally {
    loading.value = false
  }
}

function formatDate(dateString: string) {
  if (!dateString) return '未知时间'
  const date = new Date(dateString)
  // 检查日期是否有效
  if (isNaN(date.getTime())) return '无效日期'
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 计算单价（总价除以数量）
function calculateUnitPrice(record: any) {
  if (!record.price || !record.original_quantity || record.original_quantity === 0) {
    return '0.00'
  }
  const price = Number(record.price) || 0
  const quantity = Number(record.original_quantity) || 1
  const unitPrice = price / quantity
  return unitPrice.toFixed(2)
}
</script>

<style scoped>
.dashboard {
  padding-left: 1rem;
  padding-right: 1rem;
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

.record-price-container {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.total-price {
  font-weight: bold;
  color: #42b883;
  font-size: 1.125rem;
}

.unit-price {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .dashboard {
    padding: 1rem;
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

@media (max-width: 480px) {
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .recent-records {
    padding: 1rem;
  }

  .stat-card {
    padding: 1rem;
  }
}
</style>
