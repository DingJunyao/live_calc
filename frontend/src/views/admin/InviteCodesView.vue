<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">邀请码管理</v-app-bar-title>
    <template #append>
      <v-btn color="primary" variant="tonal" @click="openCreateDialog">
        <v-icon start>mdi-plus</v-icon>
        创建邀请码
      </v-btn>
    </template>
  </v-app-bar>

  <v-container class="pa-4">

    <!-- 邀请码列表 -->
    <v-card class="rounded-lg">
      <v-data-table-server
        v-model:items-per-page="itemsPerPage"
        :headers="headers"
        :items="inviteCodes"
        :items-length="totalItems"
        :loading="loading"
        item-value="id"
        class="rounded-lg"
        @update:options="fetchInviteCodes"
      >
        <!-- 邀请码列 -->
        <template #item.code="{ item }">
          <div class="d-flex align-center">
            <code class="text-subtitle-2 font-weight-bold">{{ item.code }}</code>
            <v-chip
              v-if="item.used"
              color="success"
              size="x-small"
              class="ml-2"
              variant="tonal"
            >
              已使用
            </v-chip>
            <v-chip
              v-else-if="isExpired(item.expiresAt)"
              color="error"
              size="x-small"
              class="ml-2"
              variant="tonal"
            >
              已过期
            </v-chip>
            <v-chip
              v-else
              color="success"
              size="x-small"
              class="ml-2"
              variant="outlined"
            >
              有效
            </v-chip>
          </div>
        </template>

        <!-- 创建时间列 -->
        <template #item.createdAt="{ item }">
          {{ formatDate(item.createdAt) }}
        </template>

        <!-- 过期时间列 -->
        <template #item.expiresAt="{ item }">
          <span v-if="item.expiresAt">{{ formatDate(item.expiresAt) }}</span>
          <span v-else class="text-medium-emphasis">永不过期</span>
        </template>

        <!-- 操作列 -->
        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-content-copy"
            size="small"
            variant="text"
            color="primary"
            @click="copyToClipboard(item.code)"
          >
            <v-icon>mdi-content-copy</v-icon>
            <v-tooltip activator="parent" location="top">复制邀请码</v-tooltip>
          </v-btn>
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            :disabled="item.used"
            @click="confirmDelete(item)"
          >
            <v-icon>mdi-delete</v-icon>
            <v-tooltip activator="parent" location="top">删除</v-tooltip>
          </v-btn>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- 创建邀请码对话框 -->
    <v-dialog v-model="createDialog" max-width="500px" persistent>
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center py-4">
          <v-icon class="mr-2">mdi-ticket-outline</v-icon>
          <span>创建邀请码</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-6">
          <v-form ref="form" @submit.prevent="createInviteCode">
            <v-date-input
              v-model="newInviteCode.expiresAt"
              label="过期时间"
              placeholder="留空表示永不过期"
              prepend-icon="mdi-calendar"
              clearable
              :min="new Date().toISOString()"
            />
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="tonal" @click="createDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="creating" @click="createInviteCode">创建</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card class="rounded-lg">
        <v-card-title class="text-h6">确认删除</v-card-title>
        <v-card-text>
          确定要删除邀请码 <code>{{ deleteTarget?.code }}</code> 吗？此操作不可撤销。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteInviteCode">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 复制成功提示 -->
    <v-snackbar v-model="copied" color="success" timeout="2000">
      <v-icon start>mdi-check-circle</v-icon>
      邀请码已复制到剪贴板
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import api from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => {
  router.back()
}

interface InviteCode {
  id: number
  code: string
  createdBy: number
  used: boolean
  createdAt: string
  expiresAt: string | null
}

const headers = [
  { title: '邀请码', key: 'code', sortable: false },
  { title: '创建时间', key: 'createdAt', sortable: false },
  { title: '过期时间', key: 'expiresAt', sortable: false },
  { title: '状态', key: 'used', sortable: false },
  { title: '操作', key: 'actions', sortable: false, align: 'end' },
]

const inviteCodes = ref<InviteCode[]>([])
const loading = ref(false)
const totalItems = ref(0)
const itemsPerPage = ref(20)

const createDialog = ref(false)
const creating = ref(false)
const newInviteCode = reactive({
  expiresAt: null as Date | null,
})

const deleteDialog = ref(false)
const deleting = ref(false)
const deleteTarget = ref<InviteCode | null>(null)

const copied = ref(false)

const fetchInviteCodes = async ({ page, itemsPerPage }: { page: number; itemsPerPage: number }) => {
  loading.value = true
  try {
    const skip = (page - 1) * itemsPerPage
    const response = await api.get('/invite-codes', {
      params: { skip, limit: itemsPerPage },
    })
    inviteCodes.value = response.items
    totalItems.value = response.total
  } catch (error) {
    console.error('获取邀请码列表失败:', error)
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  newInviteCode.expiresAt = null
  createDialog.value = true
}

const createInviteCode = async () => {
  creating.value = true
  try {
    const data = {
      expires_at: newInviteCode.expiresAt?.toISOString() || null,
    }
    await api.post('/invite-codes', data)
    createDialog.value = false
    // 刷新列表
    fetchInviteCodes({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error) {
    console.error('创建邀请码失败:', error)
  } finally {
    creating.value = false
  }
}

const confirmDelete = (code: InviteCode) => {
  deleteTarget.value = code
  deleteDialog.value = true
}

const deleteInviteCode = async () => {
  if (!deleteTarget.value) return

  deleting.value = true
  try {
    await api.delete(`/invite-codes/${deleteTarget.value.id}`)
    deleteDialog.value = false
    // 刷新列表
    fetchInviteCodes({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error) {
    console.error('删除邀请码失败:', error)
  } finally {
    deleting.value = false
  }
}

const copyToClipboard = async (code: string) => {
  try {
    await navigator.clipboard.writeText(code)
    copied.value = true
  } catch (error) {
    console.error('复制失败:', error)
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const isExpired = (dateString: string | null) => {
  if (!dateString) return false
  return new Date(dateString) < new Date()
}
</script>

<style scoped>
code {
  font-family: 'Courier New', monospace;
  padding: 2px 6px;
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 4px;
}
</style>
