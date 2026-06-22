<template>
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
    <!-- 注册开关 -->
    <v-card class="rounded-lg mb-4">
      <v-card-text class="d-flex align-center">
        <v-switch
          v-model="registrationEnabled"
          color="primary"
          density="comfortable"
          hide-details
          :loading="togglingReg"
          @update:model-value="toggleRegistration"
        >
          <template #label>
            <span class="text-body-1">开启邀请码注册机制</span>
          </template>
        </v-switch>
      </v-card-text>
      <v-card-text v-if="!registrationEnabled" class="pt-0 text-caption text-medium-emphasis">
        当前注册不需要邀请码，任何人均可自由注册。
      </v-card-text>
      <v-card-text v-else class="pt-0 text-caption text-medium-emphasis">
        当前注册需要邀请码，新用户必须提供有效邀请码。
      </v-card-text>
    </v-card>

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
              v-if="isExhausted(item)"
              color="warning"
              size="x-small"
              class="ml-2"
              variant="tonal"
            >
              已用完
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

        <!-- 使用次数列 -->
        <template #item.usedCount="{ item }">
          {{ item.usedCount ?? 0 }}
        </template>

        <!-- 最大次数列 -->
        <template #item.maxUses="{ item }">
          <span v-if="item.maxUses">{{ item.maxUses }}</span>
          <span v-else class="text-medium-emphasis">∞</span>
        </template>

        <!-- 创建时间列 -->
        <template #item.createdAt="{ item }">
          {{ formatToLocalDateTimeShort(item.createdAt) }}
        </template>

        <!-- 过期时间列 -->
        <template #item.expiresAt="{ item }">
          <span v-if="item.expiresAt">{{ formatToLocalDateTimeShort(item.expiresAt) }}</span>
          <span v-else class="text-medium-emphasis">永不过期</span>
        </template>

        <!-- 操作列 -->
        <template #item.actions="{ item }">
          <div class="d-flex ga-1 justify-end">
            <v-tooltip location="top">
              <template #activator="{ props }">
                <v-btn v-bind="props" icon="mdi-content-copy" size="small" variant="text" color="primary" @click="copyToClipboard(item.code)" />
              </template>
              <span>复制邀请码</span>
            </v-tooltip>
            <v-tooltip location="top">
              <template #activator="{ props }">
                <v-btn v-bind="props" icon="mdi-pencil" size="small" variant="text" color="primary" @click="openEditDialog(item)" />
              </template>
              <span>编辑</span>
            </v-tooltip>
            <v-tooltip location="top">
              <template #activator="{ props }">
                <v-btn v-bind="props" icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDelete(item)" />
              </template>
              <span>删除</span>
            </v-tooltip>
          </div>
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
          <v-form ref="createForm" @submit.prevent="createInviteCode">
            <v-text-field
              v-model="newInviteCode.code"
              label="邀请码"
              prepend-icon="mdi-ticket"
              variant="outlined"
              density="comfortable"
              hint="留空将自动随机生成"
              persistent-hint
            >
              <template #append-inner>
                <v-btn
                  icon="mdi-dice-5"
                  size="small"
                  variant="text"
                  @click="generateRandomCode"
                >
                  <v-tooltip activator="parent" location="top">随机生成</v-tooltip>
                </v-btn>
              </template>
            </v-text-field>
            <v-text-field
              v-model.number="newInviteCode.maxUses"
              label="最大使用次数"
              prepend-icon="mdi-counter"
              variant="outlined"
              density="comfortable"
              type="number"
              min="1"
              max="9999"
              hint="留空表示不限次数"
              persistent-hint
            />
            <v-text-field
              v-model="newInviteCode.expiresAt"
              label="过期时间"
              prepend-icon="mdi-calendar-clock"
              variant="outlined"
              density="comfortable"
              type="datetime-local"
              hint="留空表示永不过期"
              persistent-hint
              :min="getLocalDateTimeString()"
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

    <!-- 编辑邀请码对话框 -->
    <v-dialog v-model="editDialog" max-width="500px" persistent>
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center py-4">
          <v-icon class="mr-2">mdi-pencil</v-icon>
          <span>编辑邀请码</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-6">
          <v-form ref="editForm" @submit.prevent="updateInviteCode">
            <v-text-field
              :model-value="editTarget?.code"
              label="邀请码"
              prepend-icon="mdi-ticket"
              variant="outlined"
              density="comfortable"
              readonly
            />
            <v-text-field
              v-model.number="editData.maxUses"
              label="最大使用次数"
              prepend-icon="mdi-counter"
              variant="outlined"
              density="comfortable"
              type="number"
              min="1"
              max="9999"
              hint="留空表示不限次数"
              persistent-hint
            />
            <v-text-field
              v-model="editData.expiresAt"
              label="过期时间"
              prepend-icon="mdi-calendar-clock"
              variant="outlined"
              density="comfortable"
              type="datetime-local"
              hint="留空表示永不过期"
              persistent-hint
            />
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="tonal" @click="editDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="updating" @click="updateInviteCode">保存</v-btn>
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

    <!-- 通知 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      <v-icon start>{{ snackbar.icon }}</v-icon>
      {{ snackbar.message }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import api from '@/api/client'
import { formatToLocalDateTimeShort, getLocalDateTimeString } from '@/utils/timezone'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => {
  router.back()
}

interface InviteCode {
  id: number
  code: string
  createdBy: number
  usedCount: number
  maxUses: number | null
  createdAt: string
  expiresAt: string | null
}

const headers = [
  { title: '邀请码', key: 'code', sortable: false },
  { title: '已用次数', key: 'usedCount', sortable: false, width: 100 },
  { title: '最大次数', key: 'maxUses', sortable: false, width: 100 },
  { title: '创建时间', key: 'createdAt', sortable: false },
  { title: '过期时间', key: 'expiresAt', sortable: false },
  { title: '操作', key: 'actions', sortable: false, align: 'end', width: 140 },
]

const inviteCodes = ref<InviteCode[]>([])
const loading = ref(false)
const totalItems = ref(0)
const itemsPerPage = ref(20)

// 注册开关
const registrationEnabled = ref(false)
const togglingReg = ref(false)

// 创建
const createDialog = ref(false)
const creating = ref(false)
const newInviteCode = reactive({
  code: '',
  maxUses: null as number | null,
  expiresAt: null as string | null,
})

// 编辑
const editDialog = ref(false)
const updating = ref(false)
const editTarget = ref<InviteCode | null>(null)
const editData = reactive({
  maxUses: null as number | null,
  expiresAt: null as string | null,
})

// 删除
const deleteDialog = ref(false)
const deleting = ref(false)
const deleteTarget = ref<InviteCode | null>(null)

// 通知
const snackbar = reactive({
  show: false,
  message: '',
  color: 'success',
  icon: 'mdi-check-circle',
})

const showSnackbar = (message: string, color = 'success', icon = 'mdi-check-circle') => {
  snackbar.message = message
  snackbar.color = color
  snackbar.icon = icon
  snackbar.show = true
}

// 获取邀请码列表
const fetchInviteCodes = async ({ page, itemsPerPage: limit }: { page: number; itemsPerPage: number }) => {
  loading.value = true
  try {
    const skip = (page - 1) * limit
    const response = await api.get('/invite-codes', {
      params: { skip, limit },
    })
    inviteCodes.value = response.items
    totalItems.value = response.total
  } catch (error) {
    console.error('获取邀请码列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 获取注册配置
const fetchRegistrationConfig = async () => {
  try {
    const config: any = await api.get('/auth/config')
    registrationEnabled.value = config.registration_require_invite_code || false
  } catch (error) {
    console.error('获取注册配置失败:', error)
  }
}

const toggleRegistration = async (val: boolean) => {
  togglingReg.value = true
  try {
    await api.post('/auth/config', { require_invite_code: val })
    showSnackbar(val ? '已开启邀请码注册' : '已关闭邀请码注册')
  } catch (error: any) {
    registrationEnabled.value = !val
    const msg = error?.response?.data?.detail || '操作失败'
    showSnackbar(msg, 'error', 'mdi-alert-circle')
  } finally {
    togglingReg.value = false
  }
}

// 随机生成
const generateRandomCode = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  let code = ''
  for (let i = 0; i < 8; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  newInviteCode.code = code
}

// 创建
const openCreateDialog = () => {
  newInviteCode.code = ''
  newInviteCode.maxUses = null
  newInviteCode.expiresAt = null
  createDialog.value = true
}

const createInviteCode = async () => {
  creating.value = true
  try {
    const data: Record<string, any> = {
      expires_at: newInviteCode.expiresAt ? new Date(newInviteCode.expiresAt).toISOString() : null,
      max_uses: newInviteCode.maxUses || null,
    }
    if (newInviteCode.code.trim()) {
      data.code = newInviteCode.code.trim()
    }
    await api.post('/invite-codes', data)
    createDialog.value = false
    showSnackbar('邀请码创建成功')
    fetchInviteCodes({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '创建失败'
    showSnackbar(msg, 'error', 'mdi-alert-circle')
  } finally {
    creating.value = false
  }
}

// 编辑
const openEditDialog = (item: InviteCode) => {
  editTarget.value = item
  editData.maxUses = item.maxUses
  editData.expiresAt = item.expiresAt ? toDatetimeLocalValue(item.expiresAt) : null
  editDialog.value = true
}

const updateInviteCode = async () => {
  if (!editTarget.value) return
  updating.value = true
  try {
    await api.put(`/invite-codes/${editTarget.value.id}`, {
      max_uses: editData.maxUses || null,
      expires_at: editData.expiresAt ? new Date(editData.expiresAt).toISOString() : null,
    })
    editDialog.value = false
    showSnackbar('邀请码已更新')
    fetchInviteCodes({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '更新失败'
    showSnackbar(msg, 'error', 'mdi-alert-circle')
  } finally {
    updating.value = false
  }
}

// 删除
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
    showSnackbar('邀请码已删除')
    fetchInviteCodes({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '删除失败'
    showSnackbar(msg, 'error', 'mdi-alert-circle')
  } finally {
    deleting.value = false
  }
}

const copyToClipboard = async (code: string) => {
  try {
    await navigator.clipboard.writeText(code)
    showSnackbar('邀请码已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
  }
}

const isExpired = (dateString: string | null) => {
  if (!dateString) return false
  return new Date(dateString) < new Date()
}

// UTC ISO → datetime-local 所需的本地时间字符串（YYYY-MM-DDTHH:mm）
const toDatetimeLocalValue = (isoStr: string) => {
  const d = new Date(isoStr)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const isExhausted = (item: InviteCode) => {
  return item.maxUses != null && (item.usedCount ?? 0) >= item.maxUses
}

onMounted(() => {
  fetchRegistrationConfig()
})
</script>

<style scoped>
code {
  font-family: 'Courier New', monospace;
  padding: 2px 6px;
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 4px;
}
</style>
