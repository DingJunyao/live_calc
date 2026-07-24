<template>
  <v-layout>
    <!-- 桌面端侧边导航 -->
    <v-navigation-drawer
      v-if="isDesktop"
      :model-value="true"
      :rail="!desktopSidebar"
      permanent
      touchless
    >
      <!-- 用户卡片 / 本地模式品牌展示 -->
      <v-list v-if="userStore.user" density="compact" nav>
        <!-- 本地模式：图标 + 名称 + slogan -->
        <v-list-item v-if="isLocalMode" class="pa-2">
          <template #prepend>
            <v-avatar size="36" color="primary" class="mr-2">
              <v-img src="/logo.svg" alt="生计" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            生计
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            生活成本计算器
          </v-list-item-subtitle>
        </v-list-item>
        <!-- 云模式：用户信息 -->
        <v-list-item v-else class="pa-2">
          <template #prepend>
            <v-avatar size="36" color="primary" class="mr-2">
              <v-img v-if="userStore.user.avatar" :src="resolveImageUrl(userStore.user.avatar)" alt="avatar" />
              <v-icon v-else>mdi-account</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ userStore.user.nickname || userStore.user.username }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ userStore.user.email }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-divider />

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-silverware-fork-knife" title="今日推荐" to="/" exact />
        <v-list-item prepend-icon="mdi-currency-cny" title="价格记录" to="/prices" />
        <v-list-item prepend-icon="mdi-book-open-variant" title="菜谱管理" to="/recipes" />
        <v-list-item prepend-icon="mdi-package-variant" title="商品管理" to="/data/products" />
        <v-list-item prepend-icon="mdi-leaf" title="原料管理" to="/data/ingredients" />
        <v-list-item prepend-icon="mdi-store" title="商家管理" to="/data/merchants" />
        <v-list-item prepend-icon="mdi-account" title="个人中心" to="/profile" />
        <v-divider v-if="userStore.user?.is_admin" class="my-2" />
        <v-list-item
          v-if="userStore.user?.is_admin"
          prepend-icon="mdi-shield-account"
          title="后台管理"
          to="/admin"
          base-color="primary"
        />
      </v-list>

      <template #append>
        <v-list density="compact" nav>
          <!-- 展开模式：三态图标按钮组 -->
          <div v-if="desktopSidebar" class="theme-switch pa-2">
            <div class="text-caption text-medium-emphasis px-1 pb-1">外观主题</div>
            <v-btn-toggle
              v-model="themeMode"
              mandatory
              color="primary"
              density="compact"
              divided
              class="w-100"
            >
              <v-btn value="light" size="small" class="flex-grow-1"><v-icon>mdi-weather-sunny</v-icon></v-btn>
              <v-btn value="dark" size="small" class="flex-grow-1"><v-icon>mdi-weather-night</v-icon></v-btn>
              <v-btn value="system" size="small" class="flex-grow-1"><v-icon>mdi-monitor</v-icon></v-btn>
            </v-btn-toggle>
          </div>
          <!-- 收起（rail）模式：退化为单图标，单击三态循环 -->
          <v-list-item
            v-else
            :prepend-icon="themeIcon"
            @click="toggleTheme"
          />
          <v-list-item
            v-if="!isLocalMode"
            prepend-icon="mdi-logout"
            title="退出登录"
            base-color="error"
            @click="logout"
          />
        </v-list>
      </template>
    </v-navigation-drawer>

    <!-- 移动端侧边导航抽屉 -->
    <v-navigation-drawer
      v-if="!isDesktop"
      :model-value="mobileDrawer"
      temporary
      fixed
      location="left"
      width="280"
      scrim
      :z-index="1000"
      @update:model-value="handleMobileDrawerUpdate"
    >
      <!-- 用户卡片 / 本地模式品牌展示 -->
      <v-list v-if="userStore.user" density="compact" nav class="pt-4">
        <!-- 本地模式：图标 + 名称 + slogan -->
        <v-list-item v-if="isLocalMode" class="pa-2">
          <template #prepend>
            <v-avatar size="40" color="primary" class="mr-2">
              <v-img src="/logo.svg" alt="生计" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            生计
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            生活成本计算器
          </v-list-item-subtitle>
        </v-list-item>
        <!-- 云模式：用户信息 -->
        <v-list-item v-else class="pa-2">
          <template #prepend>
            <v-avatar size="40" color="primary" class="mr-2">
              <v-img v-if="userStore.user.avatar" :src="resolveImageUrl(userStore.user.avatar)" alt="avatar" />
              <v-icon v-else>mdi-account</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ userStore.user.nickname || userStore.user.username }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ userStore.user.email }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-divider />

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-silverware-fork-knife" title="今日推荐" to="/" exact @click="closeDrawer" />
        <v-list-item prepend-icon="mdi-currency-cny" title="价格记录" to="/prices" @click="closeDrawer" />
        <v-list-item prepend-icon="mdi-book-open-variant" title="菜谱管理" to="/recipes" @click="closeDrawer" />
        <v-list-item prepend-icon="mdi-package-variant" title="商品管理" to="/data/products" @click="closeDrawer" />
        <v-list-item prepend-icon="mdi-leaf" title="原料管理" to="/data/ingredients" @click="closeDrawer" />
        <v-list-item prepend-icon="mdi-store" title="商家管理" to="/data/merchants" @click="closeDrawer" />
        <v-list-item prepend-icon="mdi-account" title="个人中心" to="/profile" @click="closeDrawer" />
        <v-divider v-if="userStore.user?.is_admin" class="my-2" />
        <v-list-item
          v-if="userStore.user?.is_admin"
          prepend-icon="mdi-shield-account"
          title="后台管理"
          to="/admin"
          base-color="primary"
          @click="closeDrawer"
        />
      </v-list>

      <template #append>
        <v-list density="compact" nav>
          <div class="theme-switch pa-2">
            <div class="text-caption text-medium-emphasis px-1 pb-1">外观主题</div>
            <v-btn-toggle
              v-model="themeMode"
              mandatory
              color="primary"
              density="compact"
              divided
              class="w-100"
            >
              <v-btn value="light" size="small" class="flex-grow-1"><v-icon>mdi-weather-sunny</v-icon></v-btn>
              <v-btn value="dark" size="small" class="flex-grow-1"><v-icon>mdi-weather-night</v-icon></v-btn>
              <v-btn value="system" size="small" class="flex-grow-1"><v-icon>mdi-monitor</v-icon></v-btn>
            </v-btn-toggle>
          </div>
          <v-list-item
            v-if="!isLocalMode"
            prepend-icon="mdi-logout"
            title="退出登录"
            base-color="error"
            @click="logout"
          />
        </v-list>
      </template>
    </v-navigation-drawer>

    <!-- 主内容区 -->
    <v-main>
      <router-view />
    </v-main>
  </v-layout>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useMobileDrawer } from '@/composables/useMobileDrawer'
import { useThemeToggle } from '@/composables/useTheme'
import { resolveImageUrl } from '@/utils/image'

const userStore = useUserStore()
const router = useRouter()
const { mobileDrawer, desktopSidebar, isDesktop, closeDrawer } = useMobileDrawer()
const { themeMode, toggleTheme } = useThemeToggle()

const isLocalMode = computed(() => import.meta.env.VITE_STORAGE_MODE === 'local')

// rail（侧边栏收起）模式下，主题切换退化为单图标，单击三态循环
const themeIcon = computed(() => {
  switch (themeMode.value) {
    case 'light':
      return 'mdi-weather-sunny'
    case 'dark':
      return 'mdi-weather-night'
    default:
      return 'mdi-monitor'
  }
})

// 监听桌面端状态变化，切换到桌面端时关闭移动端抽屉
watch(isDesktop, (value) => {
  if (value) {
    closeDrawer()
  }
})

const logout = () => {
  userStore.logout()
  router.push('/login')
}

// 处理移动端抽屉状态变化（点击外部关闭时）
const handleMobileDrawerUpdate = (value: boolean) => {
  if (!value) {
    closeDrawer()
  }
}
</script>

<style scoped>
/* 侧边栏固定视口高度，不随页面滚动 */
:deep(.v-navigation-drawer) {
  height: 100vh !important;
  max-height: 100vh !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
}

:deep(.v-navigation-drawer__content) {
  height: 100%;
  overflow-y: auto;
}

/* 移动端抽屉的遮罩层 */
:deep(.v-navigation-drawer--temporary) {
  z-index: 1000 !important;
}

:deep(.v-overlay__scrim) {
  z-index: 999 !important;
}
</style>
