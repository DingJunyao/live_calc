// stores/user.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import { api } from '@/api'

export const useUserStore = defineStore('user', () => {
  // ---- Local mode: return a fixed admin user without API calls ----
  if (import.meta.env.VITE_STORAGE_MODE === 'local') {
    const localUserData: User = {
      id: 1,
      username: 'local',
      email: 'local@local.dev',
      phone: null,
      is_admin: true,
      is_active: true,
      email_verified: true,
      avatar: null,
      nickname: '本地用户',
      created_at: new Date().toISOString(),
      nutrition_goals: null,
      daily_budget: null,
      unit_preferences: {
        energy_unit: 'kcal',
        mass_unit: { id: 3, name: '斤', abbreviation: '斤' },
        volume_unit: null,
        price_unit: { id: 3, name: '斤', abbreviation: '斤' },
      },
      region_id: null,
    }

    const user = ref<User | null>(localUserData)
    const token = ref<string | null>('local-mode')

    return {
      user,
      token,
      isLoggedIn: computed(() => true),
      fetchUser: async () => {},
      setTokens: () => {},
      login: async () => { user.value = localUserData; token.value = 'local-mode' },
      register: async () => { user.value = localUserData; token.value = 'local-mode' },
      logout: () => { user.value = null; token.value = null },
    }
  }

  // ---- Cloud/normal mode ----
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))

  const isLoggedIn = computed(() => !!token.value)

  async function fetchUser() {
    if (!token.value) return
    try {
      const data = await api.get('/auth/me')
      user.value = data
    } catch (error) {
      console.error('Failed to fetch user:', error)
    }
  }

  function setTokens(access: string, refresh: string) {
    token.value = access
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  async function login(username: string, passwordHash: string) {
    const data = await api.post('/auth/login', { username, password_hash: passwordHash })
    setTokens(data.access_token, data.refresh_token)
    await fetchUser()
  }

  async function register(username: string, email: string, passwordHash: string, inviteCode?: string) {
    const data = await api.post('/auth/register', {
      username,
      email,
      password_hash: passwordHash,
      invite_code: inviteCode,
    })
    setTokens(data.access_token, data.refresh_token)
    await fetchUser()
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return {
    user,
    token,
    isLoggedIn,
    fetchUser,
    setTokens,
    login,
    register,
    logout,
  }
})
