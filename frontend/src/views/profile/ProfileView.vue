<template>
  <v-container fluid>
    <!-- 顶部 -->
    <v-app-bar elevation="0" color="background">
      <v-app-bar-title class="text-h6">我的</v-app-bar-title>
      <v-spacer />
      <v-btn icon="mdi-cog" variant="text" @click="showSettings" />
    </v-app-bar>

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
      <v-col cols="4">
        <v-card elevation="0">
          <v-card-text class="text-center pa-4">
            <div class="text-h4 font-weight-bold text-primary">¥256.80</div>
            <div class="text-caption text-medium-emphasis">本月支出</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card elevation="0">
          <v-card-text class="text-center pa-4">
            <div class="text-h4 font-weight-bold">42</div>
            <div class="text-caption text-medium-emphasis">记录数</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card elevation="0">
          <v-card-text class="text-center pa-4">
            <div class="text-h4 font-weight-bold">15</div>
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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const theme = useTheme()
const userStore = useUserStore()

const search = ref('')

const isDark = computed(() => theme.global.current.value.dark)

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

const showSettings = () => {
  alert('该功能即将推出')
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}
</script>
