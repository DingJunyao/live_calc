<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">个人中心</v-app-bar-title>
  </v-app-bar>

  <v-container fluid>
    <!-- 搜索栏 -->
    <v-text-field
      v-model="search"
      label="搜索..."
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      hide-details
      clearable
      class="mb-4"
    />

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

        <v-list-item>
          <template #prepend>
            <v-icon>mdi-export</v-icon>
          </template>
          <v-list-item-title>数据导出</v-list-item-title>
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
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useUserStore } from '@/stores/user'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { api } from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

const router = useRouter()
const theme = useTheme()
const userStore = useUserStore()

const search = ref('')

// 统计数据
const monthlyExpense = ref<number | null>(null)
const totalRecords = ref(0)
const totalRecipes = ref(0)
const loadingStats = ref(false)

const isDark = computed(() => theme.global.current.value.dark)

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

onMounted(() => {
  loadStats()
})
</script>
