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

  async function login(username: string, passwordHash: string) {
    const data = await api.post('/auth/login', { username, password_hash: passwordHash })
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await fetchUser()
  }

  async function register(username: string, email: string, passwordHash: string, inviteCode?: string) {
    const data = await api.post('/auth/register', {
      username,
      email,
      password_hash: passwordHash,
      invite_code: inviteCode,
    })
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
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
    login,
    register,
    logout,
  }
})
