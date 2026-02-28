<template>
  <div class="user-management">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>用户管理</h1>
    </header>

    <div class="user-controls">
      <div class="search-box">
        <input v-model="searchTerm" placeholder="搜索用户名或邮箱..." class="search-input" />
      </div>
      <button @click="filterUsers" class="btn-search">
        <i class="mdi mdi-magnify"></i> 搜索
      </button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="filteredUsers.length === 0" class="empty-state">
      暂无用户数据
    </div>

    <div v-else class="users-table-container">
      <table class="users-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>邮箱</th>
            <th>电话</th>
            <th>管理员</th>
            <th>邮箱验证</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td>{{ user.id }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.phone || '-' }}</td>
            <td>
              <span :class="['badge', user.is_admin ? 'badge-success' : 'badge-default']">
                {{ user.is_admin ? '是' : '否' }}
              </span>
            </td>
            <td>
              <span :class="['badge', user.email_verified ? 'badge-success' : 'badge-warning']">
                {{ user.email_verified ? '已验证' : '未验证' }}
              </span>
            </td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td>
              <button @click="editUser(user)" class="btn-sm btn-edit">编辑</button>
              <button @click="toggleAdmin(user)" class="btn-sm btn-admin">
                {{ user.is_admin ? '取消管理员' : '设为管理员' }}
              </button>
              <button @click="deleteUser(user)" class="btn-sm btn-delete">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑用户模态框 -->
    <div v-if="showEditModal" class="modal-overlay" @click="closeEditModal">
      <div class="modal-content" @click.stop>
        <h2>编辑用户</h2>
        <form @submit.prevent="saveUser">
          <div class="form-group">
            <label>用户名:</label>
            <input v-model="editingUser.username" type="text" required />
          </div>
          <div class="form-group">
            <label>邮箱:</label>
            <input v-model="editingUser.email" type="email" required />
          </div>
          <div class="form-group">
            <label>电话:</label>
            <input v-model="editingUser.phone" type="text" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="editingUser.is_admin" type="checkbox" />
              管理员
            </label>
          </div>
          <div class="form-group">
            <label>
              <input v-model="editingUser.email_verified" type="checkbox" />
              邮箱已验证
            </label>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeEditModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api/client'
import { useRouter } from 'vue-router'

interface User {
  id: number
  username: string
  email: string
  phone: string | null
  is_admin: boolean
  email_verified: boolean
  created_at: string
}

const router = useRouter()
const users = ref<User[]>([])
const loading = ref(false)
const searchTerm = ref('')
const showEditModal = ref(false)
const editingUser = ref<User | null>(null)

onMounted(async () => {
  await loadUsers()
})

async function loadUsers() {
  loading.value = true
  try {
    const response = await api.get<User[]>('/auth/users')
    users.value = response || []
  } catch (error) {
    console.error('Failed to load users:', error)
    alert('加载用户数据失败')
  } finally {
    loading.value = false
  }
}

const filteredUsers = ref<User[]>([])

function filterUsers() {
  if (!searchTerm.value) {
    filteredUsers.value = users.value
  } else {
    const term = searchTerm.value.toLowerCase()
    filteredUsers.value = users.value.filter(user =>
      user.username.toLowerCase().includes(term) ||
      user.email.toLowerCase().includes(term)
    )
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

function editUser(user: User) {
  editingUser.value = { ...user }
  showEditModal.value = true
}

function closeEditModal() {
  showEditModal.value = false
  editingUser.value = null
}

async function saveUser() {
  if (!editingUser.value) return

  try {
    await api.put(`/auth/users/${editingUser.value.id}`, editingUser.value)
    closeEditModal()
    await loadUsers() // 重新加载用户列表
    alert('用户信息已更新')
  } catch (error) {
    console.error('Failed to save user:', error)
    alert('更新用户信息失败')
  }
}

async function toggleAdmin(user: User) {
  if (confirm(`确定要${user.is_admin ? '取消' : '设置'}用户 "${user.username}" 为管理员吗？`)) {
    try {
      await api.put(`/auth/users/${user.id}/admin`, {
        is_admin: !user.is_admin
      })
      await loadUsers() // 重新加载用户列表
      alert(`用户 "${user.username}" 的管理员权限已${user.is_admin ? '取消' : '设置'}`)
    } catch (error) {
      console.error('Failed to toggle admin:', error)
      alert('更新管理员权限失败')
    }
  }
}

async function deleteUser(user: User) {
  if (confirm(`确定要删除用户 "${user.username}" 吗？此操作不可撤销。`)) {
    try {
      await api.delete(`/auth/users/${user.id}`)
      await loadUsers() // 重新加载用户列表
      alert(`用户 "${user.username}" 已被删除`)
    } catch (error) {
      console.error('Failed to delete user:', error)
      alert('删除用户失败')
    }
  }
}
</script>

<style scoped>
.user-management {
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

.user-controls {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  align-items: center;
}

.search-box {
  flex: 1;
  max-width: 300px;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.btn-refresh {
  padding: 0.75rem 1.5rem;
  background: #667eea;
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

.users-table-container {
  overflow-x: auto;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.users-table th,
.users-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.users-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.users-table tr:last-child td {
  border-bottom: none;
}

.badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.badge-success {
  background: #e6f4ea;
  color: #137333;
}

.badge-warning {
  background: #fef7e0;
  color: #f5a623;
}

.badge-default {
  background: #f0f0f0;
  color: #666;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
  margin-right: 0.25rem;
}

.btn-edit {
  background: #667eea;
  color: white;
}

.btn-edit:hover {
  background: #5a6fd8;
}

.btn-admin {
  background: #f5a623;
  color: white;
}

.btn-admin:hover {
  background: #e0951d;
}

.btn-delete {
  background: #de350b;
  color: white;
}

.btn-delete:hover {
  background: #bc2e0b;
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
  max-width: 600px;
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

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 0.5rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
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
</style>