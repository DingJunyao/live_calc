<template>
  <div class="report-overview">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>报告统计</h1>
    </header>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="report-content">
      <div class="report-section">
        <h2>支出报告</h2>
        <div class="stats">
          <div class="stat-item">
            <h3>总支出</h3>
            <p>¥{{ typeof totalExpense.value === 'number' ? totalExpense.value.toFixed(2) : '0.00' }}</p>
          </div>
        </div>
      </div>

      <div class="report-section">
        <h2>价格趋势</h2>
        <div class="stats">
          <div class="stat-item">
            <h3>商品记录数</h3>
            <p>{{ productCount }}</p>
          </div>
          <div class="stat-item">
            <h3>菜谱数</h3>
            <p>{{ recipeCount }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

const totalExpense = ref(0)
const productCount = ref(0)
const recipeCount = ref(0)
const loading = ref(false)

onMounted(async () => {
  await loadReports()
})

async function loadReports() {
  loading.value = true
  try {
    // 获取支出报告
    const today = new Date()
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
    const startDate = firstDay.toISOString().split('T')[0]
    const endDate = today.toISOString().split('T')[0]

    const expenseReport = await api.get<any>(
      `/reports/expense?start_date=${startDate}&end_date=${endDate}`
    )
    totalExpense.value = (expenseReport && typeof expenseReport.total_expense !== 'undefined' && expenseReport.total_expense !== null)
      ? Number(expenseReport.total_expense) || 0
      : 0

    // 获取记录数
    const productsResponse = await api.get<{ total: number }>('/products/?limit=1')
    productCount.value = (productsResponse && typeof productsResponse.total !== 'undefined' && productsResponse.total !== null)
      ? Number(productsResponse.total) || 0
      : 0

    // 获取菜谱数
    const recipesResponse = await api.get<{ total: number }>('/recipes/?limit=1')
    recipeCount.value = (recipesResponse && typeof recipesResponse.total !== 'undefined' && recipesResponse.total !== null)
      ? Number(recipesResponse.total) || 0
      : 0
  } catch (error) {
    console.error('Failed to load reports:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.report-overview {
  padding: 2rem;
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

.page-header h1 {
  font-size: 1.5rem;
  color: #333;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: #666;
}

.report-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.report-section {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.report-section h2 {
  font-size: 1.25rem;
  color: #333;
  margin-bottom: 1rem;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.stat-item {
  background: #f5f5f5;
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.stat-item h3 {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-item p {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
}
</style>
