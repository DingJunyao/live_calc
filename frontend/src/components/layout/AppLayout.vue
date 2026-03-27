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
      <v-list density="compact" nav>
        <v-list-item prepend-avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" :title="userStore.user?.username || '用户'" :subtitle="userStore.user?.email || ''" />
      </v-list>

      <v-divider />

      <v-list density="compact" nav>
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
          <v-list-item
            :prepend-icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
            :title="isDark ? '浅色' : '深色'"
            @click="toggleTheme"
          />
          <v-list-item
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
      <v-list density="compact" nav class="pt-4">
        <v-list-item
          prepend-avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
          :title="userStore.user?.username || '用户'"
          :subtitle="userStore.user?.email || ''"
        />
      </v-list>

      <v-divider />

      <v-list density="compact" nav>
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
          <v-list-item
            :prepend-icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
            :title="isDark ? '浅色' : '深色'"
            @click="toggleTheme"
          />
          <v-list-item
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
import { useTheme } from 'vuetify'
import { useUserStore } from '@/stores/user'
import { useMobileDrawer } from '@/composables/useMobileDrawer'

const userStore = useUserStore()
const router = useRouter()
const theme = useTheme()
const { mobileDrawer, desktopSidebar, isDesktop, closeDrawer } = useMobileDrawer()

const isDark = computed(() => theme.global.current.value.dark)

// 监听桌面端状态变化，切换到桌面端时关闭移动端抽屉
watch(isDesktop, (value) => {
  if (value) {
    closeDrawer()
  }
})

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

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
