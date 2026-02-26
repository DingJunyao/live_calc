<template>
  <div class="invite-codes-manager">
    <header class="page-header">
      <div class="nav-buttons">
        <button @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
          <i class="mdi mdi-arrow-left"></i>
        </button>
        <button @click="$router.push('/')" class="btn-square nav-btn" title="主页">
          <i class="mdi mdi-home"></i>
        </button>
      </div>
      <h1>邀请码管理</h1>
    </header>

    <div class="manager-content">
      <!-- 创建邀请码表单 -->
      <div class="card">
        <h2>创建新邀请码</h2>
        <div class="form-group">
          <label>过期时间 (可选):</label>
          <input
            v-model="expiresAt"
            type="datetime-local"
            class="form-control"
          />
        </div>
        <button @click="createInviteCode" :disabled="creating" class="btn-primary">
          {{ creating ? '创建中...' : '创建邀请码' }}
        </button>
      </div>

      <!-- 邀请码列表 -->
      <div class="card">
        <h2>邀请码列表</h2>
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>邀请码</th>
                <th>创建者</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>过期时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="code in inviteCodes" :key="code.id">
                <td><code>{{ code.code }}</code></td>
                <td>{{ code.createdBy || '系统' }}</td>
                <td>
                  <span :class="['status-badge', code.used ? 'status-used' : 'status-active']">
                    {{ code.used ? '已使用' : '未使用' }}
                  </span>
                </td>
                <td>{{ formatDate(code.createdAt) }}</td>
                <td>{{ code.expiresAt ? formatDate(code.expiresAt) : '-' }}</td>
                <td>
                  <button
                    @click="deleteInviteCode(code.id)"
                    :disabled="deleting[code.id]"
                    class="btn-danger btn-sm"
                  >
                    {{ deleting[code.id] ? '删除中...' : '删除' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 结果提示 -->
    <div v-if="resultMessage" :class="['alert', resultType]">
      {{ resultMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

interface InviteCode {
  id: number
  code: string
  createdBy: number | null
  used: boolean
  createdAt: string
  expiresAt: string | null
}

const inviteCodes = ref<InviteCode[]>([])
const expiresAt = ref<string>('')
const creating = ref(false)
const deleting = ref<Record<number, boolean>>({})
const resultMessage = ref('')
const resultType = ref<'success' | 'error'>('success')

async function loadInviteCodes() {
  try {
    const response = await api.get<InviteCode[]>('/invite-codes')
    inviteCodes.value = response.map(code => ({
      ...code,
      createdAt: code.createdAt.replace(' ', 'T'),
      expiresAt: code.expiresAt ? code.expiresAt.replace(' ', 'T') : null
    }))
  } catch (error) {
    console.error('加载邀请码失败:', error)
    showResult('加载邀请码失败', 'error')
  }
}

async function createInviteCode() {
  if (creating.value) return

  creating.value = true
  try {
    const payload: { expiresAt?: string } = {}
    if (expiresAt.value) {
      payload.expiresAt = expiresAt.value
    }

    await api.post('/invite-codes', payload)
    showResult('邀请码创建成功', 'success')
    await loadInviteCodes()
    expiresAt.value = ''
  } catch (error) {
    console.error('创建邀请码失败:', error)
    showResult('创建邀请码失败: ' + (error as any).message, 'error')
  } finally {
    creating.value = false
  }
}

async function deleteInviteCode(id: number) {
  if (deleting.value[id]) return

  if (!confirm('确定要删除这个邀请码吗？此操作不可撤销。')) {
    return
  }

  deleting.value[id] = true
  try {
    await api.delete(`/invite-codes/${id}`)
    showResult('邀请码删除成功', 'success')
    await loadInviteCodes()
  } catch (error) {
    console.error('删除邀请码失败:', error)
    showResult('删除邀请码失败: ' + (error as any).message, 'error')
  } finally {
    deleting.value[id] = false
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

function showResult(message: string, type: 'success' | 'error') {
  resultMessage.value = message
  resultType.value = type
  setTimeout(() => {
    resultMessage.value = ''
  }, 5000)
}

onMounted(() => {
  loadInviteCodes()
})
</script>

<style scoped>
.invite-codes-manager {
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

.manager-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.card {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
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

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-danger {
  padding: 0.5rem 1rem;
  background: #e53e3e;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-danger:hover:not(:disabled) {
  background: #c53030;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.table-container {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.table th {
  background-color: #f7fafc;
  font-weight: 600;
  color: #4a5568;
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-active {
  background-color: #e6fffa;
  color: #234e52;
}

.status-used {
  background-color: #fed7d7;
  color: #721c24;
}

.alert {
  padding: 1rem;
  border-radius: 0.5rem;
  margin: 1rem 0;
}

.alert.success {
  background: #e6f4ea;
  border: 1px solid #a3d9b1;
  color: #137333;
}

.alert.error {
  background: #fce8e6;
  border: 1px solid #f5a6a0;
  color: #d93025;
}
</style>