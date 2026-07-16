// stores/user.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import api from '@/api/client'

export const useUserStore = defineStore('user', () => {
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
