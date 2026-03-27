<template>
  <v-container fluid class="pa-4">
    <!-- 顶部导航 -->
    <v-app-bar elevation="0" color="background">
      <v-app-bar-title class="text-h6">后台管理</v-app-bar-title>
    </v-app-bar>

    <!-- 导航菜单 -->
    <v-list nav class="mb-4">
      <v-list-item
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
      >
        <template #prepend>
          <v-icon :icon="item.icon" />
        </template>

        <v-list-item-title>{{ item.title }}</v-list-item-title>
        <v-list-item-subtitle>{{ item.subtitle }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const isAdmin = computed(() => userStore.user?.is_superuser || false)

const menuItems = computed(() => [
  { path: '/admin/invite-codes', title: '邀请码管理', subtitle: '管理注册邀请码', icon: 'mdi-ticket-outline' },
  { path: '/admin/users', title: '用户管理', subtitle: '管理用户账户', icon: 'mdi-account-outline' },
  { path: '/admin/units', title: '单位管理', subtitle: '管理计量单位', icon: 'mdi-ruler' },
  { path: '/admin/map-settings', title: '地图设置', subtitle: '配置地图服务', icon: 'mdi-map-outline' },
  { path: '/admin/recipe-import', title: '菜谱导入', subtitle: '从其他来源导入菜谱', icon: 'mdi-import' },
])
</script>

<style scoped>
.v-list {
  background: transparent;
}

.v-list-item {
  margin-bottom: 4px;
}
</style>
