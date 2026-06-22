<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">用户管理</v-app-bar-title>
    <template #append>
      <v-btn color="primary" variant="tonal" @click="openCreateDialog">
        <v-icon start>mdi-plus</v-icon>
        新增用户
      </v-btn>
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 搜索栏 -->
    <v-card class="rounded-lg mb-4">
      <v-card-text class="pb-0">
        <v-text-field
          v-model="search"
          label="搜索用户名或邮箱"
          prepend-inner-icon="mdi-magnify"
          clearable
          hide-details
          single-line
          variant="plain"
          @update:model-value="onSearch"
        />
      </v-card-text>
    </v-card>

    <!-- 用户列表 -->
    <v-card class="rounded-lg">
      <v-data-table-server
        v-model:items-per-page="itemsPerPage"
        :headers="headers"
        :items="users"
        :items-length="totalItems"
        :loading="loading"
        item-value="id"
        class="rounded-lg"
        @update:options="fetchUsers"
      >
        <!-- 管理员列 -->
        <template #item.is_admin="{ item }">
          <v-chip
            v-if="item.is_admin"
            color="warning"
            size="small"
            variant="tonal"
          >
            <v-icon start size="16">mdi-shield-account</v-icon>
            管理员
          </v-chip>
          <span v-else class="text-medium-emphasis">普通用户</span>
        </template>

        <!-- 状态列 -->
        <template #item.is_active="{ item }">
          <v-chip
            :color="item.is_active ? 'success' : 'error'"
            size="small"
            variant="tonal"
          >
            {{ item.is_active ? '活跃' : '已失效' }}
          </v-chip>
        </template>

        <!-- 注册时间列 -->
        <template #item.created_at="{ item }">
          {{ item.created_at ? formatToLocalDateTimeShort(item.created_at) : '-' }}
        </template>

        <!-- 操作列 -->
        <template #item.actions="{ item }">
          <div class="d-flex ga-1 justify-end">
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              color="primary"
              @click="openEditDialog(item)"
            >
              <v-icon>mdi-pencil</v-icon>
              <v-tooltip activator="parent" location="top">编辑</v-tooltip>
            </v-btn>
            <v-btn
              icon="mdi-shield-account"
              size="small"
              variant="text"
              :color="item.is_admin ? 'warning' : 'default'"
              :disabled="!canToggleAdmin(item)"
              @click="confirmToggleAdmin(item)"
            >
              <v-icon>{{ item.is_admin ? 'mdi-shield-account' : 'mdi-shield-account-outline' }}</v-icon>
              <v-tooltip activator="parent" location="top">
                {{ adminTooltip(item) }}
              </v-tooltip>
            </v-btn>
            <v-btn
              icon="mdi-power"
              size="small"
              variant="text"
              :color="item.is_active ? 'error' : 'success'"
              :disabled="!canToggleActive(item)"
              @click="confirmToggleActive(item)"
            >
              <v-icon>mdi-power</v-icon>
              <v-tooltip activator="parent" location="top">
                {{ activeTooltip(item) }}
              </v-tooltip>
            </v-btn>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- 新增/编辑对话框 -->
    <v-dialog v-model="formDialog" max-width="500px" persistent>
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center py-4">
          <v-icon class="mr-2">{{ isEditing ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
          <span>{{ isEditing ? '修改用户' : '新增用户' }}</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-6">
          <v-form ref="form" @submit.prevent="saveUser">
            <v-text-field
              v-model="formData.username"
              label="用户名"
              prepend-icon="mdi-account"
              required
              :rules="[rules.required]"
              variant="outlined"
              density="comfortable"
            />
            <v-text-field
              v-model="formData.email"
              label="邮箱"
              prepend-icon="mdi-email"
              required
              :rules="[rules.required, rules.email]"
              variant="outlined"
              density="comfortable"
            />
            <v-text-field
              v-model="formData.phone"
              label="手机号"
              prepend-icon="mdi-phone"
              variant="outlined"
              density="comfortable"
            />
            <v-text-field
              v-model="formData.password"
              label="密码"
              prepend-icon="mdi-lock"
              variant="outlined"
              density="comfortable"
              :required="!isEditing"
              :rules="isEditing ? [] : [rules.required, rules.minPassword]"
              type="password"
              :hint="isEditing ? '留空则不修改密码' : ''"
              persistent-hint
            />
            <v-checkbox
              v-model="formData.is_admin"
              label="设为管理员"
              color="primary"
              density="comfortable"
            />
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="tonal" @click="formDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveUser">
            {{ isEditing ? '保存' : '创建' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 管理员切换确认 -->
    <v-dialog v-model="adminDialog" max-width="400px">
      <v-card class="rounded-lg">
        <v-card-title class="text-h6">
          {{ adminTarget?.is_admin ? '取消管理员' : '设为管理员' }}
        </v-card-title>
        <v-card-text>
          确定要{{ adminTarget?.is_admin ? '取消' : '授予' }}
          <strong>{{ adminTarget?.username }}</strong> 的管理员权限吗？
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="adminDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="toggling" @click="toggleAdmin">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 激活切换确认 -->
    <v-dialog v-model="activeDialog" max-width="400px">
      <v-card class="rounded-lg">
        <v-card-title class="text-h6">
          {{ activeTarget?.is_active ? '失效用户' : '激活用户' }}
        </v-card-title>
        <v-card-text>
          确定要{{ activeTarget?.is_active ? '失效' : '激活' }}
          <strong>{{ activeTarget?.username }}</strong> 吗？
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="activeDialog = false">取消</v-btn>
          <v-btn :color="activeTarget?.is_active ? 'error' : 'success'" :loading="toggling" @click="toggleActive">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 操作提示 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      <v-icon start>{{ snackbar.icon }}</v-icon>
      {{ snackbar.message }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useUserStore } from '@/stores/user'
import api from '@/api/client'
import { formatToLocalDateTimeShort } from '@/utils/timezone'
import { hashPassword } from '@/utils/crypto'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()
const userStore = useUserStore()

const currentUserId = computed(() => userStore.user?.id)

const goBack = () => {
  router.back()
}

interface User {
  id: number
  username: string
  email: string
  phone: string | null
  is_admin: boolean
  is_active?: boolean
  email_verified: boolean
  created_at: string | null
}

const headers = [
  { title: 'ID', key: 'id', width: 60, sortable: false },
  { title: '用户名', key: 'username', sortable: false },
  { title: '邮箱', key: 'email', sortable: false },
  { title: '手机号', key: 'phone', sortable: false },
  { title: '角色', key: 'is_admin', sortable: false, width: 100 },
  { title: '状态', key: 'is_active', sortable: false, width: 90 },
  { title: '注册时间', key: 'created_at', sortable: false },
  { title: '操作', key: 'actions', sortable: false, align: 'end', width: 140 },
]

const users = ref<User[]>([])
const loading = ref(false)
const totalItems = ref(0)
const itemsPerPage = ref(20)
const search = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const rules = {
  required: (v: string) => !!v || '必填',
  email: (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || '邮箱格式不正确',
  minPassword: (v: string) => (v && v.length >= 6) || '密码至少6位',
}

// 表单
const formDialog = ref(false)
const saving = ref(false)
const isEditing = ref(false)
const editingUserId = ref<number | null>(null)
const formData = reactive({
  username: '',
  email: '',
  phone: '',
  password: '',
  is_admin: false,
})

// 管理员切换
const adminDialog = ref(false)
const adminTarget = ref<User | null>(null)
const toggling = ref(false)

// 激活切换
const activeDialog = ref(false)
const activeTarget = ref<User | null>(null)

// 提示
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

// 安全规则
const canToggleAdmin = (user: User): boolean => {
  if (user.id === currentUserId.value) return false
  if (user.id === 1) return false
  return true
}

const canToggleActive = (user: User): boolean => {
  if (user.id === currentUserId.value) return false
  if (user.id === 1) return false
  return true
}

const adminTooltip = (user: User): string => {
  if (user.id === currentUserId.value) return '不能修改自己的管理员权限'
  if (user.id === 1) return '不能修改系统初始管理员'
  return user.is_admin ? '取消管理员' : '设为管理员'
}

const activeTooltip = (user: User): string => {
  if (user.id === currentUserId.value) return '不能失效自己的账户'
  if (user.id === 1) return '不能失效系统初始管理员'
  return user.is_active ? '失效用户' : '激活用户'
}

// 获取用户列表
const fetchUsers = async ({ page, itemsPerPage: limit }: { page: number; itemsPerPage: number }) => {
  loading.value = true
  try {
    const skip = (page - 1) * limit
    const params: Record<string, any> = { skip, limit }
    if (search.value) params.search = search.value
    const response = await api.get('/auth/users', { params })
    users.value = response.items.map((u: any) => ({
      ...u,
      is_active: u.is_active !== false,
    }))
    totalItems.value = response.total
  } catch (error) {
    console.error('获取用户列表失败:', error)
    showSnackbar('获取用户列表失败', 'error', 'mdi-alert-circle')
  } finally {
    loading.value = false
  }
}

const onSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchUsers({ page: 1, itemsPerPage: itemsPerPage.value })
  }, 300)
}

// 新增/编辑
const openCreateDialog = () => {
  isEditing.value = false
  editingUserId.value = null
  formData.username = ''
  formData.email = ''
  formData.phone = ''
  formData.password = ''
  formData.is_admin = false
  formDialog.value = true
}

const openEditDialog = (user: User) => {
  isEditing.value = true
  editingUserId.value = user.id
  formData.username = user.username
  formData.email = user.email
  formData.phone = user.phone || ''
  formData.password = ''
  formData.is_admin = user.is_admin
  formDialog.value = true
}

const saveUser = async () => {
  saving.value = true
  try {
    const payload: Record<string, any> = {}
    if (isEditing.value) {
      payload.username = formData.username
      payload.email = formData.email
      payload.phone = formData.phone || null
      if (formData.password) {
        payload.password_hash = hashPassword(formData.password)
      }
    } else {
      payload.username = formData.username
      payload.email = formData.email
      payload.phone = formData.phone || null
      payload.password_hash = hashPassword(formData.password)
      payload.is_admin = formData.is_admin
    }

    if (isEditing.value) {
      await api.put(`/auth/users/${editingUserId.value}`, payload)
      showSnackbar('用户信息已更新')
    } else {
      await api.post('/auth/users', payload)
      showSnackbar('用户创建成功')
    }
    formDialog.value = false
    fetchUsers({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error: any) {
    const msg = error?.response?.data?.detail || error?.message || '操作失败'
    showSnackbar(msg, 'error', 'mdi-alert-circle')
  } finally {
    saving.value = false
  }
}

// 管理员切换
const confirmToggleAdmin = (user: User) => {
  adminTarget.value = user
  adminDialog.value = true
}

const toggleAdmin = async () => {
  if (!adminTarget.value) return
  toggling.value = true
  try {
    await api.put(`/auth/users/${adminTarget.value.id}/admin`, {
      is_admin: !adminTarget.value.is_admin,
    })
    showSnackbar(
      `${adminTarget.value.username} ${adminTarget.value.is_admin ? '已取消管理员' : '已设为管理员'}`
    )
    adminDialog.value = false
    fetchUsers({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error: any) {
    const msg = error?.response?.data?.detail || error?.message || '操作失败'
    showSnackbar(msg, 'error', 'mdi-alert-circle')
  } finally {
    toggling.value = false
  }
}

// 激活切换
const confirmToggleActive = (user: User) => {
  activeTarget.value = user
  activeDialog.value = true
}

const toggleActive = async () => {
  if (!activeTarget.value) return
  toggling.value = true
  try {
    await api.put(`/auth/users/${activeTarget.value.id}/active`, {
      is_active: !activeTarget.value.is_active,
    })
    showSnackbar(
      `${activeTarget.value.username} ${activeTarget.value.is_active ? '已失效' : '已激活'}`
    )
    activeDialog.value = false
    fetchUsers({ page: 1, itemsPerPage: itemsPerPage.value })
  } catch (error: any) {
    const msg = error?.response?.data?.detail || error?.message || '操作失败'
    showSnackbar(msg, 'error', 'mdi-alert-circle')
  } finally {
    toggling.value = false
  }
}
</script>
