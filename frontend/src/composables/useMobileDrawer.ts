import { ref, readonly, computed } from 'vue'
import { useDisplay } from 'vuetify'

// 全局共享的移动端抽屉状态
const mobileDrawer = ref(false)

// 桌面端侧边栏状态（默认显示）
const desktopSidebar = ref(true)

// 用于 AppLayout - 可以读写状态
export function useMobileDrawer() {
  const { mdAndUp } = useDisplay()
  // 使用 mdAndUp (>= 960px) 作为桌面端判断标准
  // Vuetify 的 mobile 默认是 mdAndDown (< 1280px)，对于侧边栏来说太大了
  const isDesktop = mdAndUp

  const toggleDrawer = () => {
    mobileDrawer.value = !mobileDrawer.value
  }

  const openDrawer = () => {
    mobileDrawer.value = true
  }

  const closeDrawer = () => {
    mobileDrawer.value = false
  }

  // 桌面端侧边栏控制
  const toggleDesktopSidebar = () => {
    desktopSidebar.value = !desktopSidebar.value
  }

  const openDesktopSidebar = () => {
    desktopSidebar.value = true
  }

  const closeDesktopSidebar = () => {
    desktopSidebar.value = false
  }

  return {
    mobileDrawer: readonly(mobileDrawer),
    desktopSidebar: readonly(desktopSidebar),
    isDesktop,
    toggleDrawer,
    openDrawer,
    closeDrawer,
    toggleDesktopSidebar,
    openDesktopSidebar,
    closeDesktopSidebar
  }
}

// 用于子组件 - 可以控制抽屉，不能直接修改状态
export function useMobileDrawerControl() {
  const { mdAndUp } = useDisplay()
  // 使用 mdAndUp (>= 960px) 作为桌面端判断标准
  const isDesktop = mdAndUp

  const toggleDrawer = () => {
    mobileDrawer.value = !mobileDrawer.value
  }

  const openDrawer = () => {
    mobileDrawer.value = true
  }

  const closeDrawer = () => {
    mobileDrawer.value = false
  }

  // 桌面端侧边栏控制
  const toggleDesktopSidebar = () => {
    desktopSidebar.value = !desktopSidebar.value
  }

  const openDesktopSidebar = () => {
    desktopSidebar.value = true
  }

  const closeDesktopSidebar = () => {
    desktopSidebar.value = false
  }

  // 智能切换：根据当前设备类型切换对应的侧边栏
  const toggleSidebar = (desktop: boolean) => {
    if (desktop) {
      desktopSidebar.value = !desktopSidebar.value
    } else {
      mobileDrawer.value = !mobileDrawer.value
    }
  }

  return {
    isDesktop,
    toggleDrawer,
    openDrawer,
    closeDrawer,
    toggleDesktopSidebar,
    openDesktopSidebar,
    closeDesktopSidebar,
    toggleSidebar
  }
}
