<template>
  <v-container class="pa-4">
    <!-- 顶部标题栏 -->
    <v-app-bar elevation="0" color="background" density="comfortable" class="mb-4">
      <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
      <v-app-bar-title class="text-h6">后台管理</v-app-bar-title>
      <template #append>
        <v-chip color="primary" variant="tonal" size="small">
          <v-icon start size="small">mdi-shield-account</v-icon>
          管理员
        </v-chip>
      </template>
    </v-app-bar>

    <!-- 统计卡片 -->
    <v-row class="ma-2 mb-4">
      <v-col cols="12" sm="6" lg="3">
        <v-card elevation="0">
          <v-card-text class="text-center pa-4">
            <v-avatar color="primary" variant="tonal" size="48" class="mb-2">
              <v-icon size="28">mdi-account-group</v-icon>
            </v-avatar>
            <div v-if="loading" class="text-h5 font-weight-bold text-primary">--</div>
            <div v-else class="text-h5 font-weight-bold text-primary">{{ stats?.users || 0 }}</div>
            <div class="text-caption text-medium-emphasis mt-1">用户总数</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" lg="3">
        <v-card elevation="0">
          <v-card-text class="text-center pa-4">
            <v-avatar color="success" variant="tonal" size="48" class="mb-2">
              <v-icon size="28">mdi-package-variant-closed</v-icon>
            </v-avatar>
            <div v-if="loading" class="text-h5 font-weight-bold text-success">--</div>
            <div v-else class="text-h5 font-weight-bold text-success">{{ stats?.products || 0 }}</div>
            <div class="text-caption text-medium-emphasis mt-1">商品记录</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" lg="3">
        <v-card elevation="0">
          <v-card-text class="text-center pa-4">
            <v-avatar color="warning" variant="tonal" size="48" class="mb-2">
              <v-icon size="28">mdi-book-open-variant</v-icon>
            </v-avatar>
            <div v-if="loading" class="text-h5 font-weight-bold text-warning">--</div>
            <div v-else class="text-h5 font-weight-bold text-warning">{{ stats?.recipes || 0 }}</div>
            <div class="text-caption text-medium-emphasis mt-1">菜谱数量</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" lg="3">
        <v-card elevation="0">
          <v-card-text class="text-center pa-4">
            <v-avatar color="info" variant="tonal" size="48" class="mb-2">
              <v-icon size="28">mdi-store</v-icon>
            </v-avatar>
            <div v-if="loading" class="text-h5 font-weight-bold text-info">--</div>
            <div v-else class="text-h5 font-weight-bold text-info">{{ stats?.merchants || 0 }}</div>
            <div class="text-caption text-medium-emphasis mt-1">商家数量</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 管理功能 -->
    <v-card class="ma-4" elevation="0">
      <v-list>
        <v-list-item
          prepend-icon="mdi-ticket-outline"
          title="邀请码管理"
          subtitle="管理用户注册邀请码"
          to="/admin/invite-codes"
        >
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          prepend-icon="mdi-ruler"
          title="单位管理"
          subtitle="管理计量单位和换算关系"
          to="/admin/units"
        >
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          prepend-icon="mdi-map-marker-path"
          title="地图设置"
          subtitle="配置地图服务 API 密钥"
          to="/admin/map-settings"
        >
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          prepend-icon="mdi-import"
          title="菜谱导入"
          subtitle="从外部来源导入菜谱数据"
          to="/admin/recipe-import"
        >
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>
      </v-list>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import api from '@/api/client'

interface AdminStats {
  users: number
  products: number
  recipes: number
  merchants: number
}

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

const stats = ref<AdminStats | null>(null)
const loading = ref(false)

const fetchStats = async () => {
  loading.value = true
  try {
    stats.value = await api.get('/admin/stats')
  } catch (error) {
    console.error('获取统计信息失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>
