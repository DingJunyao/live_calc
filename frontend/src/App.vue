<template>
  <v-app>
    <router-view />
    <PWAUpdatePrompt />
    <GlobalConfirmDialog />
    <GlobalSnackbar />
  </v-app>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import GlobalConfirmDialog from '@/components/common/GlobalConfirmDialog.vue'
import GlobalSnackbar from '@/components/common/GlobalSnackbar.vue'
import PWAUpdatePrompt from '@/components/common/PWAUpdatePrompt.vue'

const userStore = useUserStore()
const router = useRouter()

// 解析 web+livecalc 协议唤起：浏览器以 /?protocol-uri=web+livecalc://recipe/123 打开应用，
// 命中则跳转到对应详情页（router.replace 顺带清掉 query，避免刷新重复触发）
const handleProtocolUri = () => {
  const uri = new URLSearchParams(window.location.search).get('protocol-uri')
  if (!uri) return
  const m = uri.match(/^web\+livecalc:\/\/(recipe|product|ingredient|merchant)\/(\w+)/)
  if (!m) return
  const [, type, id] = m
  const pathMap: Record<string, string> = {
    recipe: `/recipes/${id}`,
    product: `/data/products/${id}`,
    ingredient: `/data/ingredients/${id}`,
    merchant: `/data/merchants/${id}`,
  }
  const target = pathMap[type]
  if (target) router.replace(target)
}

onMounted(async () => {
  // 本地模式启动检测：检查基础数据是否已初始化，未初始化则重定向到向导页
  if (import.meta.env.VITE_STORAGE_MODE === 'local' && window.location.pathname !== '/setup') {
    const { isInitialized } = await import('@/api/local/seed')
    const ready = await isInitialized()
    if (!ready) {
      router.replace('/setup')
      return
    }
  }

  if (userStore.isLoggedIn) {
    await userStore.fetchUser()
  }

  // 解析 web+livecalc 协议唤起（登录态已就绪，跳详情页守卫可放行）
  handleProtocolUri()

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

/* 窗口控件覆盖模式（桌面 PWA 安装版）：顶部 app-bar 铺入标题栏区域，
   整条可拖拽移动窗口，右侧留出系统控件区（关闭/最小化/最大化）不被遮挡，
   内部按钮/输入框保持可点击。仅 display_override 含 window-controls-overlay 时生效。 */
@media (display-mode: window-controls-overlay) {
  header.v-app-bar {
    -webkit-app-region: drag;
  }
  header.v-app-bar .v-toolbar__content {
    /* 右侧留出系统控件区宽度（env 安全区之外即控件区），append 按钮左移避让；
       用 padding-inline-end 对齐 Vuetify 3 逻辑属性，!important 压过 toolbar 默认内边距 */
    padding-inline-end: calc(100vw - env(titlebar-area-x) - env(titlebar-area-width)) !important;
  }
  header.v-app-bar :is(button, a, input, .v-btn, .v-field, [role='button']) {
    -webkit-app-region: no-drag;
  }
}
</style>
