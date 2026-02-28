<template>
  <div class="admin-panel">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>后台管理</h1>
    </header>

    <div class="admin-dashboard">
      <div class="admin-stats">
        <div class="stat-card">
          <h3>用户总数</h3>
          <p class="stat-number">{{ stats.users }}</p>
        </div>
        <div class="stat-card">
          <h3>价格记录数</h3>
          <p class="stat-number">{{ stats.products }}</p>
        </div>
        <div class="stat-card">
          <h3>菜谱数</h3>
          <p class="stat-number">{{ stats.recipes }}</p>
        </div>
        <div class="stat-card">
          <h3>地点数</h3>
          <p class="stat-number">{{ stats.locations }}</p>
        </div>
      </div>

      <div class="admin-actions">
        <div class="action-section">
          <h2>用户管理</h2>
          <div class="action-buttons">
            <button @click="goToUserManagement" class="btn-admin">管理用户</button>
            <button @click="goToInviteCodeManagement" class="btn-admin">邀请码管理</button>
            <button @click="toggleInviteCodeRequirement" class="btn-admin">
              {{ inviteCodeRequired ? '禁用' : '启用' }}邀请码注册
            </button>
          </div>
        </div>

        <div class="action-section">
          <h2>数据管理</h2>
          <div class="action-buttons">
            <button @click="goToRecipeImport" class="btn-admin">导入菜谱</button>
            <button @click="goToIngredientManagement" class="btn-admin">原料管理</button>
            <button @click="backupData" class="btn-admin">备份数据</button>
            <button @click="restoreData" class="btn-admin">恢复数据</button>
            <button @click="exportReports" class="btn-admin">导出报表</button>
          </div>
        </div>

        <div class="action-section">
          <h2>系统配置</h2>
          <div class="action-buttons">
            <button @click="viewLogs" class="btn-admin">查看日志</button>
            <button @click="systemSettings" class="btn-admin">系统设置</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'
import { useRouter } from 'vue-router'

interface Stats {
  users: number
  products: number
  recipes: number
  locations: number
}

const router = useRouter()
const stats = ref<Stats>({
  users: 0,
  products: 0,
  recipes: 0,
  locations: 0
})

const inviteCodeRequired = ref(false)

onMounted(async () => {
  await loadStats()
  await loadConfig()
})

async function loadStats() {
  try {
    // 获取管理员统计数据
    const statsResponse = await api.get<any>('/admin/stats')
    stats.value = {
      users: statsResponse.users || 0,
      products: statsResponse.products || 0,
      recipes: statsResponse.recipes || 0,
      locations: statsResponse.locations || 0
    }
  } catch (error) {
    console.error('Failed to load stats:', error)
    alert('加载统计数据失败')
  }
}

async function loadConfig() {
  try {
    const config = await api.get<any>('/auth/config')
    inviteCodeRequired.value = config.require_invite_code || false
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

async function toggleInviteCodeRequirement() {
  try {
    const newValue = !inviteCodeRequired.value
    await api.post('/auth/config', {
      require_invite_code: newValue
    })
    inviteCodeRequired.value = newValue
    alert(`已${newValue ? '启用' : '禁用'}邀请码注册`)
  } catch (error) {
    console.error('Failed to update config:', error)
    alert('更新配置失败')
  }
}

function goToUserManagement() {
  router.push('/admin/users')
}

function goToInviteCodeManagement() {
  router.push('/admin/invite-codes')
}

function goToRecipeImport() {
  router.push('/admin/recipe-import')
}

function goToIngredientManagement() {
  router.push('/admin/ingredients')
}

function backupData() {
  alert('数据备份功能将在后续版本中实现')
}

function restoreData() {
  alert('数据恢复功能将在后续版本中实现')
}

function exportReports() {
  alert('报表导出功能将在后续版本中实现')
}

function viewLogs() {
  alert('日志查看功能将在后续版本中实现')
}

function systemSettings() {
  alert('系统设置功能将在后续版本中实现')
}
</script>

<style scoped>
.admin-panel {
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

.admin-dashboard {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.admin-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
}

.stat-card h3 {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: bold;
  color: #42b883;
}

.admin-actions {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.action-section {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.action-section h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.btn-admin {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-admin:hover {
  background: #5a6fd8;
}
</style>