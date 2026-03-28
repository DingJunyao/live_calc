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

  // 检测桌面端并设置初始 class
  updateDesktopClass()

  // 监听窗口大小变化
  window.addEventListener('resize', updateDesktopClass)

  // 使用轮询来检测侧边栏状态（更可靠）
  setInterval(() => {
    if (document.body.classList.contains('is-desktop')) {
      updateDrawerClass()
    }
  }, 500)
})

// 更新桌面端 class
const updateDesktopClass = () => {
  const isDesktop = window.innerWidth >= 960
  if (isDesktop) {
    document.body.classList.add('is-desktop')
    // 立即更新侧边栏状态
    setTimeout(() => updateDrawerClass(), 0)
  } else {
    document.body.classList.remove('is-desktop', 'is-rail', 'is-expanded')
  }
}

// 更新侧边栏状态 class
const updateDrawerClass = () => {
  const drawer = document.querySelector('.v-navigation-drawer')
  if (drawer) {
    const isRail = drawer.classList.contains('v-navigation-drawer--rail')
    if (isRail) {
      document.body.classList.add('is-rail')
      document.body.classList.remove('is-expanded')
    } else {
      document.body.classList.add('is-expanded')
      document.body.classList.remove('is-rail')
    }
  }
}
</script>

<style>
/* 强制固定所有 header.v-app-bar 元素 */
header.v-app-bar {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 900 !important;
  transition: left 0.2s ease !important;
}

/* 桌面端：侧边栏展开模式（宽度 256px），header 从 256px 开始 */
body.is-desktop.is-expanded header.v-app-bar {
  left: 256px !important;
}

/* 桌面端：侧边栏 rail 模式（宽度 56px），header 从 56px 开始 */
body.is-desktop.is-rail header.v-app-bar {
  left: 56px !important;
}

/* 移动端：header 保持从左边 0 开始 */
@media (max-width: 959px) {
  header.v-app-bar {
    left: 0 !important;
  }
}
</style>
