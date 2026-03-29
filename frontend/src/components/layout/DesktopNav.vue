<template>
  <v-navigation-drawer permanent :rail="rail" elevation="2">
    <!-- 头部 -->
    <v-list-item
      prepend-avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
      :title="userStore.user?.username || '用户'"
      :subtitle="userStore.user?.email || ''"
      nav
    >
      <template #append>
        <v-btn
          :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          variant="text"
          @click.stop="rail = !rail"
        />
      </template>
    </v-list-item>

    <v-divider />

    <!-- 导航菜单 -->
    <v-list density="compact" nav>
      <v-list-item
        v-for="item in menuItems"
        :key="item.value"
        :prepend-icon="item.icon"
        :title="item.title"
        :value="item.value"
        :to="item.to"
        color="primary"
      />
    </v-list>

    <template #append>
      <div class="pa-2">
        <v-btn block variant="text" @click="toggleTheme">
          <v-icon start>
            {{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}
          </v-icon>
          {{ isDark ? '浅色' : '深色' }}
        </v-btn>
        <v-btn block variant="text" color="error" class="mt-2" @click="logout">
          <v-icon start>mdi-logout</v-icon>
          退出登录
        </v-btn>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const theme = useTheme()

const rail = ref(false)

const isDark = computed(() => theme.global.current.value.dark)

const menuItems = [
  { title: '价格记录', icon: 'mdi-currency-cny', value: 'prices', to: '/' },
  { title: '菜谱管理', icon: 'mdi-book-open-variant', value: 'recipes', to: '/recipes' },
  { title: '商品管理', icon: 'mdi-package-variant', value: 'products', to: '/data/products' },
  { title: '原料管理', icon: 'mdi-leaf', value: 'ingredients', to: '/data/ingredients' },
  { title: '商家管理', icon: 'mdi-store', value: 'merchants', to: '/data/merchants' },
  { title: '个人中心', icon: 'mdi-account', value: 'profile', to: '/profile' },
]

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}
</script>
