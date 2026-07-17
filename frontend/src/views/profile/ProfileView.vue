<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">个人中心</v-app-bar-title>
  </v-app-bar>

  <v-container fluid>
    <!-- 搜索栏 -->
    <!-- <v-text-field
      v-model="search"
      label="搜索..."
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      hide-details
      clearable
      class="mb-4"
    /> -->

    <!-- 统计卡片 -->
    <v-row class="ma-2">
      <v-col cols="12" sm="4">
        <v-card elevation="0">
          <v-card-text class="text-center pa-2 pa-sm-4">
            <div v-if="loadingStats" class="text-h5 text-sm-h4 font-weight-bold text-primary text-truncate">--</div>
            <div v-else class="text-h5 text-sm-h4 font-weight-bold text-primary text-truncate">
              ¥{{ monthlyExpense !== null ? monthlyExpense.toFixed(2) : '0.00' }}
            </div>
            <div class="text-caption text-medium-emphasis">本月支出</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="4">
        <v-card elevation="0">
          <v-card-text class="text-center pa-2 pa-sm-4">
            <div v-if="loadingStats" class="text-h5 text-sm-h4 font-weight-bold text-truncate">--</div>
            <div v-else class="text-h5 text-sm-h4 font-weight-bold text-truncate">{{ totalRecords }}</div>
            <div class="text-caption text-medium-emphasis">记录数</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="4">
        <v-card elevation="0">
          <v-card-text class="text-center pa-2 pa-sm-4">
            <div v-if="loadingStats" class="text-h5 text-sm-h4 font-weight-bold text-truncate">--</div>
            <div v-else class="text-h5 text-sm-h4 font-weight-bold text-truncate">{{ totalRecipes }}</div>
            <div class="text-caption text-medium-emphasis">菜谱数</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 设置列表 -->
    <v-card class="ma-4" elevation="0">
      <v-list>
        <v-list-item @click="openAccountDialog">
          <template #prepend>
            <v-icon>mdi-account-edit</v-icon>
          </template>
          <v-list-item-title>用户信息编辑</v-list-item-title>
          <v-list-item-subtitle>用户名、邮箱、密码</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item class="theme-mode-item">
          <template #prepend>
            <v-icon>mdi-theme-light-dark</v-icon>
          </template>
          <div class="theme-mode-content w-100">
            <div class="d-flex align-center justify-space-between">
              <span class="text-body-2">外观主题</span>
              <span class="text-caption text-medium-emphasis">{{ themeModeLabel }}</span>
            </div>
            <v-btn-toggle
              v-model="themeMode"
              mandatory
              color="primary"
              density="comfortable"
              divided
              class="mt-2 w-100"
            >
              <v-btn value="light" size="small" class="flex-grow-1">
                <v-icon start>mdi-weather-sunny</v-icon>浅色
              </v-btn>
              <v-btn value="dark" size="small" class="flex-grow-1">
                <v-icon start>mdi-weather-night</v-icon>深色
              </v-btn>
              <v-btn value="system" size="small" class="flex-grow-1">
                <v-icon start>mdi-monitor</v-icon>自动
              </v-btn>
            </v-btn-toggle>
          </div>
        </v-list-item>

        <v-list-item @click="router.push('/profile/places')">
          <template #prepend>
            <v-icon>mdi-map-marker-multiple</v-icon>
          </template>
          <v-list-item-title>我的常用地点</v-list-item-title>
          <v-list-item-subtitle>家、公司等，地图默认聚焦</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item @click="router.push('/profile/proposals')">
          <template #prepend>
            <v-icon>mdi-clipboard-text-clock</v-icon>
          </template>
          <v-list-item-title>我的提议</v-list-item-title>
          <v-list-item-subtitle>查看提交的变更提议及审核状态</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item @click="openNutritionDialog">
          <template #prepend>
            <v-icon>mdi-food-apple-outline</v-icon>
          </template>
          <v-list-item-title>饮食偏好</v-list-item-title>
          <v-list-item-subtitle>每日营养目标与预算</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item @click="openUnitPrefsDialog">
          <template #prepend>
            <v-icon>mdi-ruler</v-icon>
          </template>
          <v-list-item-title>单位偏好</v-list-item-title>
          <v-list-item-subtitle>能量 / 质量 / 容积 / 记价默认单位</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item @click="blacklistDialog = true">
          <template #prepend>
            <v-icon>mdi-cancel</v-icon>
          </template>
          <v-list-item-title>原料黑名单</v-list-item-title>
          <v-list-item-subtitle>已屏蔽 {{ blacklistCount }} 种原料</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item @click="exportDialog = true">
          <template #prepend>
            <v-icon>mdi-export</v-icon>
          </template>
          <v-list-item-title>数据导出</v-list-item-title>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item @click="importDialog = true">
          <template #prepend>
            <v-icon>mdi-upload</v-icon>
          </template>
          <v-list-item-title>数据导入</v-list-item-title>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item>
          <template #prepend>
            <v-icon>mdi-information</v-icon>
          </template>
          <v-list-item-title>关于</v-list-item-title>
          <v-list-item-subtitle>版本 0.2.0</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- 退出登录按钮 -->
    <v-card class="ma-4" elevation="0">
      <v-btn block color="error" variant="text" @click="logout">
        <v-icon start>mdi-logout</v-icon>
        退出登录
      </v-btn>
    </v-card>

    <!-- 用户信息编辑对话框 -->
    <v-dialog v-model="accountDialog" max-width="520">
      <v-card>
        <v-card-title class="d-flex align-center">
          用户信息编辑
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="accountDialog = false" />
        </v-card-title>
        <v-card-text>
          <div class="text-caption text-medium-emphasis mb-2">基本信息</div>
          <v-text-field
            v-model="accountForm.username"
            label="用户名"
            variant="outlined"
            density="compact"
            :error-messages="accountErrors.username"
            class="mb-2"
          />
          <v-text-field
            v-model="accountForm.email"
            label="邮箱"
            type="email"
            variant="outlined"
            density="compact"
            :error-messages="accountErrors.email"
            class="mb-2"
          />
          <v-text-field
            v-model="accountForm.phone"
            label="手机号（可清空）"
            variant="outlined"
            density="compact"
            :error-messages="accountErrors.phone"
            class="mb-4"
          />

          <v-btn
            variant="outlined"
            block
            prepend-icon="mdi-lock-reset"
            class="mt-2"
            @click="openChangePasswordDialog"
          >
            修改密码
          </v-btn>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="savingAccount" @click="accountDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingAccount" @click="saveAccount">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 修改密码对话框 -->
    <v-dialog v-model="changePasswordDialog" max-width="460">
      <v-card>
        <v-card-title class="d-flex align-center">
          修改密码
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="changePasswordDialog = false" />
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="changePasswordForm.currentPassword"
            label="当前密码"
            type="password"
            variant="outlined"
            density="compact"
            :error-messages="changePasswordErrors.currentPassword"
            class="mb-2"
          />
          <v-text-field
            v-model="changePasswordForm.newPassword"
            label="新密码"
            type="password"
            variant="outlined"
            density="compact"
            :error-messages="changePasswordErrors.newPassword"
            class="mb-2"
          />
          <v-text-field
            v-model="changePasswordForm.confirmPassword"
            label="确认新密码"
            type="password"
            variant="outlined"
            density="compact"
            :error-messages="changePasswordErrors.confirmPassword"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="savingPassword" @click="changePasswordDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingPassword" @click="saveChangePassword">修改</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 数据导入对话框 -->
    <ImportUploadDialog v-model="importDialog" />

    <!-- 黑名单对话框 -->
    <BlacklistDialog v-model="blacklistDialog" />

    <!-- 饮食偏好对话框 -->
    <v-dialog v-model="nutritionDialog" max-width="480">
      <v-card>
        <v-card-title class="d-flex align-center">
          饮食偏好
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="nutritionDialog = false" />
        </v-card-title>
        <v-card-text>
          <p class="text-caption text-medium-emphasis mb-4">
            设置每日营养目标和预算上限，用于饮食推荐。
          </p>

          <v-row dense>
            <v-col cols="6">
              <v-text-field
                v-model.number="nutritionForm.daily_calorie_target"
                :label="`每日热量 (${energyUnit})`"
                type="number"
                variant="outlined"
                density="compact"
                hide-details="auto"
                :min="energyUnit === 'kJ' ? 2000 : 500"
                :max="energyUnit === 'kJ' ? 21000 : 5000"
                step="50"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="nutritionForm.daily_protein_target"
                label="蛋白质 (g)"
                type="number"
                variant="outlined"
                density="compact"
                hide-details="auto"
                min="10"
                max="300"
                step="5"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="nutritionForm.daily_carb_target"
                label="碳水 (g)"
                type="number"
                variant="outlined"
                density="compact"
                hide-details="auto"
                min="50"
                max="600"
                step="10"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="nutritionForm.daily_fat_target"
                label="脂肪 (g)"
                type="number"
                variant="outlined"
                density="compact"
                hide-details="auto"
                min="10"
                max="200"
                step="5"
              />
            </v-col>
            <v-col cols="12">
              <v-text-field
                v-model.number="nutritionForm.daily_budget"
                label="每日预算 (元，留空不限)"
                type="number"
                variant="outlined"
                density="compact"
                hide-details="auto"
                min="0"
                step="5"
                clearable
                placeholder="不限"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="nutritionDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingNutrition" @click="saveNutrition">
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 单位偏好对话框 -->
    <v-dialog v-model="unitPrefsDialog" max-width="480">
      <v-card>
        <v-card-title class="d-flex align-center">
          单位偏好
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="unitPrefsDialog = false" />
        </v-card-title>
        <v-card-text>
          <p class="text-caption text-medium-emphasis mb-4">
            设置你的默认单位，所有页面将按此显示与填写。
          </p>
          <v-select
            v-model="unitPrefsForm.default_energy_unit"
            :items="[{ title: '千卡 (kcal)', value: 'kcal' }, { title: '千焦 (kJ)', value: 'kJ' }]"
            item-title="title"
            item-value="value"
            label="能量单位"
            variant="outlined"
            density="compact"
            class="mb-3"
          />
          <v-autocomplete
            v-model="unitPrefsForm.default_mass_unit_id"
            :items="massUnitOptions"
            item-title="name"
            item-value="id"
            label="默认质量单位"
            variant="outlined"
            density="compact"
            class="mb-3"
            clearable
          />
          <v-autocomplete
            v-model="unitPrefsForm.default_volume_unit_id"
            :items="volumeUnitOptions"
            item-title="name"
            item-value="id"
            label="默认容积单位"
            variant="outlined"
            density="compact"
            class="mb-3"
            clearable
          />
          <v-autocomplete
            v-model="unitPrefsForm.default_price_unit_id"
            :items="priceUnitOptions"
            item-title="name"
            item-value="id"
            label="默认记价单位（含个/包/瓶）"
            variant="outlined"
            density="compact"
            clearable
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="unitPrefsDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingUnitPrefs" @click="saveUnitPrefs">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 数据导出对话框 -->
    <v-dialog v-model="exportDialog" max-width="420">
      <v-card>
        <v-card-title>数据导出</v-card-title>
        <v-card-text>
          <p class="text-body-2 text-medium-emphasis mb-3">
            选择导出范围，导出文件将打包为 zip 下载。
          </p>
          <v-radio-group v-model="exportScope">
            <v-radio value="full">
              <template #label>
                <div>
                  <strong>全量数据</strong>
                  <div class="text-caption text-medium-emphasis">
                    包括我创建的和系统/管理员创建的所有数据
                  </div>
                </div>
              </template>
            </v-radio>
            <v-radio value="mine">
              <template #label>
                <div>
                  <strong>仅我的数据</strong>
                  <div class="text-caption text-medium-emphasis">
                    只导出我创建的数据；我引用到的系统数据会一并带上
                  </div>
                </div>
              </template>
            </v-radio>
          </v-radio-group>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="exporting" @click="exportDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="exporting" @click="doExport">导出</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 导出进度遮罩 -->
    <v-overlay v-model="exporting" class="align-center justify-center" persistent>
      <div class="text-center">
        <v-progress-circular indeterminate size="48" />
        <div class="mt-3">正在打包数据，请稍候…</div>
      </div>
    </v-overlay>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { api } from '@/api/client'
import { ImportUploadDialog } from '@/components/import'
import BlacklistDialog from '@/components/blacklist/BlacklistDialog.vue'
import { useGlobalSnackbar } from '@/composables/useGlobalSnackbar'
import { useUserUnits } from '@/composables/useUserUnits'
import { useThemeToggle } from '@/composables/useTheme'
import { hashPassword } from '@/utils/crypto'

const { notify } = useGlobalSnackbar()
const { energyUnit, toDisplayCalorie, fromDisplayCalorie } = useUserUnits()

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

const router = useRouter()
const userStore = useUserStore()
const { themeMode } = useThemeToggle()
// 当前主题模式的中文标签
const themeModeLabel = computed(() => {
  switch (themeMode.value) {
    case 'light':
      return '浅色模式'
    case 'dark':
      return '深色模式'
    case 'system':
      return '自动跟随系统'
    default:
      return ''
  }
})

const search = ref('')

// 数据导入与导出
const importDialog = ref(false)
const exportDialog = ref(false)
const exportScope = ref<'full' | 'mine'>('full')
const exporting = ref(false)

// 用户信息编辑
const accountDialog = ref(false)
const savingAccount = ref(false)
const accountForm = ref({
  username: '',
  email: '',
  phone: '',
})
const accountErrors = reactive({
  username: '',
  email: '',
  phone: '',
})

// 修改密码（独立对话框）
const changePasswordDialog = ref(false)
const savingPassword = ref(false)
const changePasswordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const changePasswordErrors = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const doExport = async () => {
  exporting.value = true
  try {
    // 注意：api 客户端的响应拦截器对所有响应统一返回 response.data（见 frontend/src/api/client.ts），
    // 这会剥离外层 AxiosResponse，导致 blob 请求无法拿到 response.headers/content-disposition。
    // 因此此处直接使用原生 axios，手动附加 Authorization，以保留完整 AxiosResponse。
    const token = localStorage.getItem('access_token')
    const baseURL = import.meta.env.VITE_API_URL || '/api/v1'
    const response = await axios.get(`${baseURL}/export/data`, {
      params: { scope: exportScope.value },
      responseType: 'blob',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    // 从响应头取文件名
    const disposition = response.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    const filename = match?.[1] || `export_${Date.now()}.zip`
    // 触发下载
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    exportDialog.value = false
  } catch (e: any) {
    console.error('数据导出失败', e)
    notify('数据导出失败：' + (e?.userMessage || e?.message || '未知错误'), 'error')
  } finally {
    exporting.value = false
  }
}

// 统计数据
const monthlyExpense = ref<number | null>(null)
const totalRecords = ref(0)
const totalRecipes = ref(0)
const loadingStats = ref(false)

// 饮食偏好
const nutritionDialog = ref(false)
const savingNutrition = ref(false)
const nutritionForm = ref({
  daily_calorie_target: 2000,
  daily_protein_target: 60,
  daily_carb_target: 300,
  daily_fat_target: 65,
  daily_budget: null as number | null,
})

function openNutritionDialog() {
  // 从 userStore 读取当前值（热量按用户能量单位换算显示，库存仍 kcal）
  const u = userStore.user as any
  const storedKcal = u?.nutrition_goals?.daily_calorie_target ?? 2000
  nutritionForm.value = {
    daily_calorie_target: toDisplayCalorie(storedKcal) as number,
    daily_protein_target: u?.nutrition_goals?.daily_protein_target ?? 60,
    daily_carb_target: u?.nutrition_goals?.daily_carb_target ?? 300,
    daily_fat_target: u?.nutrition_goals?.daily_fat_target ?? 65,
    daily_budget: u?.daily_budget ?? null,
  }
  nutritionDialog.value = true
}

async function saveNutrition() {
  savingNutrition.value = true
  try {
    await api.patch('/auth/me', {
      daily_calorie_target: fromDisplayCalorie(nutritionForm.value.daily_calorie_target),
      daily_protein_target: nutritionForm.value.daily_protein_target || null,
      daily_carb_target: nutritionForm.value.daily_carb_target || null,
      daily_fat_target: nutritionForm.value.daily_fat_target || null,
      daily_budget: nutritionForm.value.daily_budget || null,
    })
    // 刷新 userStore 以同步最新值
    await userStore.fetchUser()
    nutritionDialog.value = false
  } catch (e: any) {
    notify('保存失败：' + (e?.userMessage || e?.message || '未知错误'), 'error')
  } finally {
    savingNutrition.value = false
  }
}

// 单位偏好
const unitPrefsDialog = ref(false)
const savingUnitPrefs = ref(false)
const unitOptionsAll = ref<any[]>([])
const unitPrefsForm = ref({
  default_energy_unit: 'kcal' as 'kcal' | 'kJ',
  default_mass_unit_id: null as number | null,
  default_volume_unit_id: null as number | null,
  default_price_unit_id: null as number | null,
})

const massUnitOptions = computed(() => unitOptionsAll.value.filter(u => u.unit_type === 'mass'))
const volumeUnitOptions = computed(() => unitOptionsAll.value.filter(u => u.unit_type === 'volume'))
const priceUnitOptions = computed(() => unitOptionsAll.value.filter(u => ['mass', 'volume', 'count'].includes(u.unit_type)))

async function openUnitPrefsDialog() {
  const u = userStore.user as any
  unitPrefsForm.value = {
    default_energy_unit: u?.unit_preferences?.energy_unit ?? 'kcal',
    default_mass_unit_id: u?.unit_preferences?.mass_unit?.id ?? null,
    default_volume_unit_id: u?.unit_preferences?.volume_unit?.id ?? null,
    default_price_unit_id: u?.unit_preferences?.price_unit?.id ?? null,
  }
  if (!unitOptionsAll.value.length) {
    try {
      const res = await api.get('/units/', { params: { limit: 500 } })
      unitOptionsAll.value = (res?.items || res || []) as any[]
    } catch { /* ignore */ }
  }
  unitPrefsDialog.value = true
}

async function saveUnitPrefs() {
  savingUnitPrefs.value = true
  try {
    await api.patch('/auth/me', {
      default_energy_unit: unitPrefsForm.value.default_energy_unit || null,
      default_mass_unit_id: unitPrefsForm.value.default_mass_unit_id || null,
      default_volume_unit_id: unitPrefsForm.value.default_volume_unit_id || null,
      default_price_unit_id: unitPrefsForm.value.default_price_unit_id || null,
    })
    await userStore.fetchUser()
    unitPrefsDialog.value = false
  } catch (e: any) {
    notify('保存失败：' + (e?.userMessage || e?.message || '未知错误'), 'error')
  } finally {
    savingUnitPrefs.value = false
  }
}

function openAccountDialog() {
  const u = userStore.user as any
  accountForm.value = {
    username: u?.username ?? '',
    email: u?.email ?? '',
    phone: u?.phone ?? '',
  }
  Object.keys(accountErrors).forEach(k => (accountErrors[k as keyof typeof accountErrors] = ''))
  accountDialog.value = true
}

function openChangePasswordDialog() {
  changePasswordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
  Object.keys(changePasswordErrors).forEach(k => (changePasswordErrors[k as keyof typeof changePasswordErrors] = ''))
  changePasswordDialog.value = true
}

async function saveAccount() {
  Object.keys(accountErrors).forEach(k => (accountErrors[k as keyof typeof accountErrors] = ''))
  const f = accountForm.value
  let hasError = false
  if (!f.username || f.username.length < 3 || f.username.length > 50) {
    accountErrors.username = '用户名需 3-50 个字符'; hasError = true
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) {
    accountErrors.email = '邮箱格式不正确'; hasError = true
  }
  if (f.phone && !/^1[3-9]\d{9}$/.test(f.phone)) {
    accountErrors.phone = '手机号格式不正确'; hasError = true
  }
  if (hasError) return

  savingAccount.value = true
  try {
    const u = userStore.user as any
    const payload: Record<string, any> = {}
    if (f.username !== u?.username) payload.username = f.username
    if (f.email !== u?.email) payload.email = f.email
    if ((f.phone || null) !== (u?.phone || null)) payload.phone = f.phone || null
    if (Object.keys(payload).length === 0) {
      accountDialog.value = false
      return
    }
    await api.put('/auth/me/account', payload)
    await userStore.fetchUser()
    accountDialog.value = false
    notify('已更新', 'success')
  } catch (e: any) {
    notify('保存失败：' + (e?.userMessage || e?.message || '未知错误'), 'error')
  } finally {
    savingAccount.value = false
  }
}

async function saveChangePassword() {
  Object.keys(changePasswordErrors).forEach(k => (changePasswordErrors[k as keyof typeof changePasswordErrors] = ''))
  const f = changePasswordForm.value
  let hasError = false
  if (!f.currentPassword) { changePasswordErrors.currentPassword = '请输入当前密码'; hasError = true }
  if (!f.newPassword || f.newPassword.length < 6) {
    changePasswordErrors.newPassword = '新密码至少 6 个字符'; hasError = true
  }
  if (f.newPassword !== f.confirmPassword) {
    changePasswordErrors.confirmPassword = '两次输入的新密码不一致'; hasError = true
  }
  if (hasError) return

  savingPassword.value = true
  try {
    const data: any = await api.put('/auth/me/account', {
      current_password: hashPassword(f.currentPassword),
      new_password: hashPassword(f.newPassword),
    })
    if (data.access_token && data.refresh_token) {
      userStore.setTokens(data.access_token, data.refresh_token)
    }
    await userStore.fetchUser()
    changePasswordDialog.value = false
    notify('密码已修改，登录态已刷新', 'success')
  } catch (e: any) {
    notify('修改失败：' + (e?.userMessage || e?.message || '未知错误'), 'error')
  } finally {
    savingPassword.value = false
  }
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}

// 加载统计数据
const loadStats = async () => {
  loadingStats.value = true
  try {
    // 获取价格记录总数
    const productsResponse = await api.get('/products', { params: { limit: 1 } })
    totalRecords.value = productsResponse.total || 0

    // 获取菜谱总数
    const recipesResponse = await api.get('/recipes', { params: { limit: 1 } })
    totalRecipes.value = recipesResponse.total || 0

    // 获取本月支出（从价格记录中计算）
    const now = new Date()
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59)

    try {
      const purchaseRecordsResponse = await api.get('/products', {
        params: {
          start_date: firstDay.toISOString(),
          end_date: lastDay.toISOString(),
          limit: 1000  // 获取足够多的记录以计算总支出
        }
      })

      // 筛选出 record_type='purchase' 的记录，并计算总支出
      if (purchaseRecordsResponse.items && Array.isArray(purchaseRecordsResponse.items)) {
        const purchaseRecords = purchaseRecordsResponse.items.filter(
          (item: any) => item.record_type === 'purchase'
        )

        // price 字段已经是该条记录的总价格，直接累加即可
        monthlyExpense.value = purchaseRecords.reduce((sum: number, record: any) => {
          const price = parseFloat(record.price) || 0
          return sum + price
        }, 0)
      } else {
        monthlyExpense.value = 0
      }
    } catch (e) {
      // 如果获取支出失败，设为0
      monthlyExpense.value = 0
    }
  } catch (e: any) {
    console.error('加载统计数据失败', e)
  } finally {
    loadingStats.value = false
  }
}

// 黑名单
const blacklistDialog = ref(false)
const blacklistCount = ref(0)

async function loadBlacklistCount() {
  try {
    const data = await api.get('/blacklist/ingredient-ids')
    blacklistCount.value = data?.ingredient_ids?.length || 0
  } catch {
    // 忽略
  }
}

// 黑名单对话框关闭后刷新计数
watch(blacklistDialog, (val) => {
  if (!val) loadBlacklistCount()
})

onMounted(() => {
  loadStats()
  loadBlacklistCount()
})
</script>
