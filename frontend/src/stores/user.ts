import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User as UserType } from '../types/user'
import { api } from '../api/client'

interface UserState {
  user: User | null
  token: string | null
  isLoggedIn: computed(() => !!state.user.value)
}

export const useUserStore = defineStore('user', {
  state: (): UserState {
    user: null,
    token: localStorage.getItem('token')
  },

  getters: {
    isLoggedIn: (state): boolean => !!state.user
  },

  actions: {
    setUser(user: User): void {
      state.user = user
      state.token = user.token || ''
    },

    setToken(token: string): void {
      state.token = token
      localStorage.setItem('token', token)
      api.setToken(token)
    },

    clearUser(): void {
      state.user = null
      state.token = null
      localStorage.removeItem('token')
      api.clearToken()
    },

    async login(username: string, password_hash: string): Promise<void> {
      try {
        const response = await api.post<{ access_token: string, refresh_token: string }>(
          '/auth/login',
          { username, password_hash }
        )

        this.setUser({
          id: 1, // Mock user ID from backend
          username,
          email: 'test@example.com',
          phone: null,
          is_admin: false,
          email_verified: false
        })

        this.setToken(response.access_token)
        api.setToken(response.access_token)
      } catch (error) {
        console.error('Login failed:', error)
        throw error
      }
    },

    async register(userData: any): Promise<void> {
      try {
        const response = await api.post<{ access_token: string, refresh_token: string }>('/auth/register', userData)

        const user: {
          id: 1,
          username: userData.username,
          email: userData.email,
          phone: userData.phone || null,
          is_admin: false,
          email_verified: false
        }

        this.setUser(user)
        this.setToken(response.access_token)
        api.setToken(response.access_token)
      } catch (error) {
        console.error('Register failed:', error)
        throw error
      }
    },

    logout(): void {
      this.clearUser()
      router.push('/login')
    }
  }
})
