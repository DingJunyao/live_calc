// composables/useTheme.ts
// 全局主题（浅色/深色/自动）单例管理：
// - themeMode：用户选择的三态（light / dark / system），持久化到 localStorage
// - actualTheme：实际生效主题（system 模式按系统偏好解析为 light / dark）
// - 监听系统 prefers-color-scheme 变化，system 模式下实时跟随
// 响应式状态与 matchMedia 监听器都在模块层级，只初始化一次；
// useThemeToggle() 仅负责把 actualTheme 绑定到 Vuetify（同样只绑定一次）。
import { ref, computed, watch } from 'vue'
import { useTheme } from 'vuetify'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme-mode'

// 用户选择的主题模式（持久化）
const themeMode = ref<ThemeMode>(
  (localStorage.getItem(STORAGE_KEY) as ThemeMode | null) || 'system'
)

// 系统主题偏好
const prefersDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)

// 监听系统主题变化（只注册一次）
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  prefersDark.value = e.matches
})

// 计算实际生效主题
const actualTheme = computed<'light' | 'dark'>(() => {
  if (themeMode.value === 'system') {
    return prefersDark.value ? 'dark' : 'light'
  }
  return themeMode.value
})

// 当前是否深色（供 UI 判断图标/文案）
const isDark = computed(() => actualTheme.value === 'dark')

// 持久化模式选择
watch(themeMode, (newMode) => {
  localStorage.setItem(STORAGE_KEY, newMode)
})

// 快切：三态循环 浅色 → 深色 → 自动 → 浅色（侧边栏单击在三种模式间循环）
const toggleTheme = () => {
  const order: ThemeMode[] = ['light', 'dark', 'system']
  const idx = order.indexOf(themeMode.value)
  themeMode.value = order[(idx + 1) % order.length]
}

// 直接设置三态之一
const setThemeMode = (mode: ThemeMode) => {
  themeMode.value = mode
}

// Vuetify 绑定标志（只绑定一次）
let vuetifyBound = false

// 在 setup 内调用，返回单例状态与方法
export function useThemeToggle() {
  const vuetifyTheme = useTheme()
  if (!vuetifyBound) {
    vuetifyBound = true
    // 把实际主题应用到 Vuetify（immediate 确保首次调用即同步）
    watch(actualTheme, (newTheme) => {
      vuetifyTheme.global.name.value = newTheme
      // 同步 html data-theme，驱动 index.html 里 body 防闪背景跟随主题
      document.documentElement.setAttribute('data-theme', newTheme)
    }, { immediate: true })
  }
  return {
    themeMode,
    actualTheme,
    isDark,
    prefersDark,
    toggleTheme,
    setThemeMode,
  }
}
