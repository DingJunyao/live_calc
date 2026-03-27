<template>
  <v-layout>
    <!-- 桌面端侧边导航 -->
    <v-navigation-drawer v-if="isDesktop" permanent>
      <v-list density="compact" nav>
        <v-list-item prepend-avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" :title="userStore.user?.username || '用户'" :subtitle="userStore.user?.email || ''" />
      </v-list>

      <v-divider />

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-currency-cny" title="价格记录" to="/" />
        <v-list-item prepend-icon="mdi-book-open-variant" title="菜谱管理" to="/recipes" />
        <v-list-item prepend-icon="mdi-package-variant" title="商品管理" to="/data/products" />
        <v-list-item prepend-icon="mdi-leaf" title="原料管理" to="/data/ingredients" />
        <v-list-item prepend-icon="mdi-store" title="商家管理" to="/data/merchants" />
        <v-list-item prepend-icon="mdi-account" title="个人中心" to="/profile" />
      </v-list>

      <template #append>
        <div class="pa-2">
          <v-btn block variant="text" @click="toggleTheme">
            <v-icon start>{{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
            {{ isDark ? '浅色' : '深色' }}
          </v-btn>
          <v-btn block variant="text" color="error" class="mt-2" @click="logout">
            <v-icon start>mdi-logout</v-icon>
            退出登录
          </v-btn>
        </div>
      </template>
    </v-navigation-drawer>

    <!-- 移动端底部导航 -->
    <v-bottom-navigation
      v-if="!isDesktop"
      color="primary"
      grow
    >
      <v-btn to="/">
        <v-icon>mdi-currency-cny</v-icon>
        <span>记录</span>
      </v-btn>
      <v-btn to="/recipes">
        <v-icon>mdi-book-open-variant</v-icon>
        <span>菜谱</span>
      </v-btn>
      <v-btn to="/data">
        <v-icon>mdi-database</v-icon>
        <span>数据</span>
      </v-btn>
      <v-btn to="/profile">
        <v-icon>mdi-account</v-icon>
        <span>我的</span>
      </v-btn>
    </v-bottom-navigation>

    <!-- 主内容区 -->
    <v-main>
      <router-view />
    </v-main>
  </v-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const theme = useTheme()

const isDesktop = ref(true)
let mediaQuery: MediaQueryList | null = null

const isDark = computed(() => theme.global.current.value.dark)

const updateIsDesktop = (e: MediaQueryListEvent | MediaQueryList) => {
  isDesktop.value = e.matches
}

onMounted(() => {
  mediaQuery = window.matchMedia('(min-width: 960px)')
  isDesktop.value = mediaQuery.matches
  mediaQuery.addEventListener('change', updateIsDesktop)
})

onUnmounted(() => {
  if (mediaQuery) {
    mediaQuery.removeEventListener('change', updateIsDesktop)
  }
})

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}
</script>
