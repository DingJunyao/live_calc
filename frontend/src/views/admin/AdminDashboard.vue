<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">后台管理</v-app-bar-title>
    <template #append>
      <v-chip color="primary" variant="tonal" size="small">
        <v-icon start size="small">mdi-shield-account</v-icon>
        管理员
      </v-chip>
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 统计卡片 -->
    <v-row class="ma-2 mb-4">
      <v-col cols="12" sm="6" lg="3">
        <v-card
          elevation="0"
          class="user-stats-card"
          hover
          :to="'/admin/users'"
        >
          <v-card-text class="text-center pa-4">
            <v-avatar color="primary" variant="tonal" size="48" class="mb-2">
              <v-icon size="28">mdi-account-group</v-icon>
            </v-avatar>
            <div v-if="loading" class="text-h5 font-weight-bold text-primary">--</div>
            <div v-else class="text-h5 font-weight-bold text-primary">{{ stats?.users || 0 }}</div>
            <div class="text-caption text-medium-emphasis mt-1">
              用户总数
              <v-icon size="14" class="ms-1">mdi-arrow-right-thin</v-icon>
            </div>
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
          prepend-icon="mdi-account-cog"
          title="用户管理"
          subtitle="管理用户账户、权限和状态"
          to="/admin/users"
        >
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

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
          prepend-icon="mdi-robot"
          title="AI 与机翻配置"
          subtitle="AI 服务与机器翻译密钥设置"
          to="/admin/ai-config"
        >
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          prepend-icon="mdi-database-cog"
          title="数据维护中心"
          subtitle="菜谱导入、AI 维护、USDA 数据管理"
          to="/admin/data-maintenance"
        >
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>

        <v-list-item
          prepend-icon="mdi-robot-outline"
          title="Agent 任务台"
          subtitle="发起 Agent 维护任务、审批 SQL、对话流"
          to="/admin/agent-console"
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

<style scoped>
.user-stats-card {
  cursor: pointer;
  transition: transform 0.15s ease;
}
.user-stats-card:hover {
  transform: translateY(-2px);
}
</style>
