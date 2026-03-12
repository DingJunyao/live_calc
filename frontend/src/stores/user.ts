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
    token: localStorage.getItem('token') || null
  }),

  getters: {
    isLoggedIn: (state): boolean => !!state.user
  },

  actions: {
    async initializeUserFromStorage(): Promise<boolean> {
      const storedToken = localStorage.getItem('token')
      if (storedToken) {
        try {
          // 设置 API 客户端的令牌
          api.setToken(storedToken)

          // 尝试获取用户信息来验证令牌有效性
          const user = await api.get<User>('/auth/me')
          this.setUser(user)
          this.setToken(storedToken)
          return true
        } catch (error) {
          console.error('Failed to initialize user from stored token:', error)
          // 如果令牌无效，清除它
          this.clearUser()
          return false
        }
      }
      return false
    },

    setUser(user: User): void {
      this.user = user
      this.token = user.token || this.token || ''
    },

    setToken(token: string, refreshToken?: string): void {
      this.token = token
      localStorage.setItem('token', token)
      api.setToken(token, refreshToken)
    },

    clearUser(): void {
      this.user = null
      this.token = null
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      api.clearToken()
    },

    async login(username: string, password_hash: string): Promise<void> {
      try {
        const response = await api.post<{ access_token: string, refresh_token: string }>(
          '/auth/login',
          { username, password_hash }
        )

        // 设置 token 和 refresh_token
        this.setToken(response.access_token, response.refresh_token)

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

        // 设置 token 和 refresh_token
        this.setToken(response.access_token, response.refresh_token)

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
