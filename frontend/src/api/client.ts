// api/client.ts
import axios from 'axios'

// 请求超时（毫秒），可从 .env 配置
export const REQUEST_TIMEOUT = parseInt(import.meta.env.VITE_REQUEST_TIMEOUT || '10000', 10)
export const LONG_REQUEST_TIMEOUT = parseInt(import.meta.env.VITE_LONG_REQUEST_TIMEOUT || '30000', 10)

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 统一注入用户时区（IANA 名），后端用于按用户本地日聚合
    config.headers['X-Timezone'] = Intl.DateTimeFormat().resolvedOptions().timeZone
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 从 Axios 错误响应中提取后端错误详情。
 * 后端返回格式: { detail: "错误信息" } 或 { detail: "...", errors: [...] }
 */
function extractErrorDetail(error: any): string | null {
  // 后端结构化错误详情
  if (error.response?.data?.detail && typeof error.response.data.detail === 'string') {
    // 如果有多个验证错误，拼接展示
    if (error.response.data.errors && Array.isArray(error.response.data.errors)) {
      const fieldErrors = error.response.data.errors
        .map((e: any) => `${e.field}: ${e.message}`)
        .join('; ')
      if (fieldErrors) {
        return `${error.response.data.detail}: ${fieldErrors}`
      }
    }
    return error.response.data.detail
  }
  // 备用消息字段
  if (error.response?.data?.message && typeof error.response.data.message === 'string') {
    return error.response.data.message
  }
  return null
}

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    // 401 处理: Token 过期，尝试刷新
    if (error.response?.status === 401) {
      // 登录请求的 401 = 凭证错误，不刷新 token、不跳登录页（用户本就在登录页），
      // 交给调用方 Login.vue 的 catch 显示错误；否则整页刷新会冲掉刚设的错误提示
      const isLoginRequest = error.config?.url?.includes('/auth/login')
      // _retry 标志位：同一次请求最多 refresh 重试一次。
      // 业务校验型 401（如改密码时「当前密码错误」）refresh 救不了——重放照样 401，
      // 不拦就会无限 refresh→重放→401 死循环，前端一直转圈、调用方 catch 也收不到错误。
      // 已重试仍 401 说明不是 token 过期，直接透传给下面 extractErrorDetail + reject 显示。
      if (!isLoginRequest && !(error.config as any)?._retry) {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          try {
            const response = await axios.post('/api/v1/auth/refresh', {
              refresh_token: refreshToken,
            })
            localStorage.setItem('access_token', response.data.access_token)
            // 重试原请求（仅此一次，_retry 防二次 401 再入 refresh 死循环）
            ;(error.config as any)._retry = true
            error.config.headers.Authorization = `Bearer ${response.data.access_token}`
            return api.request(error.config)
          } catch {
            // 刷新失败，清除 token
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            window.location.href = '/login'
          }
        } else {
          window.location.href = '/login'
        }
      }
    }

    // 为所有错误附加用户可读的消息
    const detail = extractErrorDetail(error)
    if (detail) {
      error.userMessage = detail
    } else if (error.message === 'Network Error') {
      error.userMessage = '网络连接失败，请检查网络后重试'
    } else if (error.code === 'ECONNABORTED') {
      error.userMessage = '请求超时，请稍后重试'
    }

    return Promise.reject(error)
  }
)

export default api
