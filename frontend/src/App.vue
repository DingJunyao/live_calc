<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(async () => {
  if (userStore.isLoggedIn) {
    await userStore.fetchUser()
  }
})
</script>

<style>
/* 强制固定所有 header.v-app-bar 元素 */
/* 但 z-index 要低于侧边栏，让侧边栏及其阴影能在上方 */
header.v-app-bar {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 900 !important;
}
</style>
