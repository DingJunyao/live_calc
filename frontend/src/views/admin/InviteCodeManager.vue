<template>
  <PageHeader title="邀请码管理" :show-back="true" />

  <div class="invite-codes-manager">

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

        <!-- 分页 -->
        <Pagination
          v-if="total > 0"
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          @change-page="handlePageChange"
          @change-page-size="handlePageSizeChange"
        />
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
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

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

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

async function loadInviteCodes() {
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const url = `/invite-codes?skip=${skip}&limit=${pageSize.value}`
    const response = await api.get<any>(url)

    // 解析分页响应
    let items: InviteCode[]
    let totalCount = 0  // 使用不同的变量名避免与 ref 冲突

    if (response.items && response.total !== undefined) {
      // 新的 PaginatedResponse 格式
      items = response.items
      totalCount = response.total
    } else if (Array.isArray(response)) {
      // 旧的 List 格式
      items = response.map((code: any) => ({
        id: code.id,
        code: code.code,
        createdBy: code.createdBy,
        used: code.used,
        createdAt: code.createdAt.replace(' ', 'T'),
        expiresAt: code.expiresAt ? code.expiresAt.replace(' ', 'T') : null
      }))
      // 如果是第一页，用当前数据量作为 totalCount
      if (currentPage.value === 1) {
        totalCount = items.length
      }
    }

    inviteCodes.value = items
    total.value = totalCount
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

// 分页处理函数
function handlePageChange(page: number) {
  currentPage.value = page
  loadInviteCodes()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadInviteCodes()
}

onMounted(() => {
  loadInviteCodes()
})
</script>

<style scoped>
.invite-codes-manager {
  padding-left: 1rem;
  padding-right: 1rem;
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

/* 移动端优化 */
@media (max-width: 768px) {
  .invite-codes-manager {
    padding: 0.75rem;
  }

  .manager-content {
    gap: 1.5rem;
  }

  .card {
    padding: 1rem;
  }

  .card h2 {
    font-size: 1.125rem;
  }

  .form-group {
    margin-bottom: 0.75rem;
  }

  .form-group label {
    font-size: 0.8125rem;
  }

  .form-control {
    font-size: 0.875rem;
    padding: 0.625rem;
  }

  .btn-primary,
  .btn-secondary {
    padding: 0.625rem 1.25rem;
    font-size: 0.8125rem;
  }

  .table-container {
    overflow-x: auto;
  }

  .table th,
  .table td {
    padding: 0.5rem;
    font-size: 0.8125rem;
  }

  .table th {
    font-size: 0.75rem;
  }

  .status-badge {
    font-size: 0.6875rem;
    padding: 0.125rem 0.375rem;
  }

  .alert {
    padding: 0.75rem;
    font-size: 0.8125rem;
  }

  .btn-danger {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }

  .btn-sm {
    padding: 0.125rem 0.375rem;
    font-size: 0.6875rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .invite-codes-manager {
    padding: 0.5rem;
  }

  .card {
    padding: 0.75rem;
  }

  .card h2 {
    font-size: 1rem;
  }

  .table th,
  .table td {
    padding: 0.375rem;
    font-size: 0.75rem;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }

  .alert {
    font-size: 0.75rem;
  }
}
</style>