// composables/useTheme.ts
import { ref, computed, watch } from 'vue'
import { useTheme } from 'vuetify'

export function useThemeToggle() {
  const vuetifyTheme = useTheme()

  // 主题模式：light, dark, system
  const storedMode = localStorage.getItem('theme-mode') as 'light' | 'dark' | 'system' | null
  const themeMode = ref<'light' | 'dark' | 'system'>(storedMode || 'system')

  // 监听主题模式变化，保存到 localStorage
  watch(themeMode, (newMode) => {
    localStorage.setItem('theme-mode', newMode)
  })

  // 系统主题偏好
  const prefersDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)

  // 监听系统主题变化
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    prefersDark.value = e.matches
  })

  // 计算实际主题
  const actualTheme = computed(() => {
    if (themeMode.value === 'system') {
      return prefersDark.value ? 'dark' : 'light'
    }
    return themeMode.value
  })

  // 应用主题
  watch(actualTheme, (newTheme) => {
    vuetifyTheme.global.name.value = newTheme
  }, { immediate: true })

  // 切换主题
  const toggleTheme = () => {
    if (themeMode.value === 'system') {
      themeMode.value = prefersDark.value ? 'light' : 'dark'
    } else {
      themeMode.value = themeMode.value === 'light' ? 'dark' : 'light'
    }
  }

  // 设置主题模式
  const setThemeMode = (mode: 'light' | 'dark' | 'system') => {
    themeMode.value = mode
  }

  return {
    themeMode,
    actualTheme,
    toggleTheme,
    setThemeMode,
  }
}
