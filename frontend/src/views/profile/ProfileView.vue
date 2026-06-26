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
        <v-list-item @click="toggleTheme">
          <template #prepend>
            <v-icon>mdi-theme-light-dark</v-icon>
          </template>
          <v-list-item-title>主题切换</v-list-item-title>
          <v-list-item-subtitle>
            {{ isDark ? '深色' : '浅色' }}模式
          </v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
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
                label="每日热量 (kcal)"
                type="number"
                variant="outlined"
                density="compact"
                hide-details="auto"
                min="500"
                max="5000"
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { api } from '@/api/client'
import { ImportUploadDialog } from '@/components/import'
import BlacklistDialog from '@/components/blacklist/BlacklistDialog.vue'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

const router = useRouter()
const theme = useTheme()
const userStore = useUserStore()

const search = ref('')

// 数据导入与导出
const importDialog = ref(false)
const exportDialog = ref(false)
const exportScope = ref<'full' | 'mine'>('full')
const exporting = ref(false)

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
    alert('数据导出失败：' + (e?.userMessage || e?.message || '未知错误'))
  } finally {
    exporting.value = false
  }
}

// 统计数据
const monthlyExpense = ref<number | null>(null)
const totalRecords = ref(0)
const totalRecipes = ref(0)
const loadingStats = ref(false)

const isDark = computed(() => theme.global.current.value.dark)

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
  // 从 userStore 读取当前值
  const u = userStore.user as any
  nutritionForm.value = {
    daily_calorie_target: u?.nutrition_goals?.daily_calorie_target ?? 2000,
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
      daily_calorie_target: nutritionForm.value.daily_calorie_target || null,
      daily_protein_target: nutritionForm.value.daily_protein_target || null,
      daily_carb_target: nutritionForm.value.daily_carb_target || null,
      daily_fat_target: nutritionForm.value.daily_fat_target || null,
      daily_budget: nutritionForm.value.daily_budget || null,
    })
    // 刷新 userStore 以同步最新值
    await userStore.fetchUser()
    nutritionDialog.value = false
  } catch (e: any) {
    alert('保存失败：' + (e?.userMessage || e?.message || '未知错误'))
  } finally {
    savingNutrition.value = false
  }
}

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
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
