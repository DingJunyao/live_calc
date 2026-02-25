import { defineStore } from 'pinia'
import { api } from '../api/client'
import router from '../router'

interface User {
  id: number
  username: string
  email: string
  phone: string | null
  is_admin: boolean
  email_verified: boolean
  token?: string
}

interface UserState {
  user: User | null
  token: string | null
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    user: null,
    token: localStorage.getItem('token')
  }),

  getters: {
    isLoggedIn: (state): boolean => !!state.user
  },

  actions: {
    setUser(user: User): void {
      this.user = user
      this.token = user.token || ''
    },

    setToken(token: string): void {
      this.token = token
      localStorage.setItem('token', token)
      api.setToken(token)
    },

    clearUser(): void {
      this.user = null
      this.token = null
      localStorage.removeItem('token')
      api.clearToken()
    },

    async login(username: string, password_hash: string): Promise<void> {
      try {
        const response = await api.post<{ access_token: string, refresh_token: string }>(
          '/auth/login',
          { username, password_hash }
        )

        // 设置 token
        this.setToken(response.access_token)

        // 获取用户信息
        const user = await api.get<User>('/auth/me')
        this.setUser(user)
      } catch (error) {
        console.error('Login failed:', error)
        throw error
      }
    },

    async register(userData: any): Promise<void> {
      try {
        const response = await api.post<{ access_token: string, refresh_token: string }>('/auth/register', userData)

        // 设置 token
        this.setToken(response.access_token)

        // 获取用户信息
        const user = await api.get<User>('/auth/me')
        this.setUser(user)
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
