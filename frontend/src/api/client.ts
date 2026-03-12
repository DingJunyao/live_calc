class ApiClient {
  private baseURL: string
  private token: string | null = null
  private refreshToken: string | null = localStorage.getItem('refresh_token')

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || '/api/v1'
    this.token = localStorage.getItem('token')
  }

  setToken(token: string, refreshToken?: string): void {
    this.token = token
    localStorage.setItem('token', token)
    if (refreshToken) {
      this.refreshToken = refreshToken
      localStorage.setItem('refresh_token', refreshToken)
    }
  }

  clearToken(): void {
    this.token = null
    this.refreshToken = null
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  }

  // 尝试刷新 token
  private async tryRefreshToken(): Promise<boolean> {
    if (!this.refreshToken) {
      console.warn('No refresh token available');
      return false;
    }

    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken })
      });

      if (response.ok) {
        const data = await response.json();
        this.token = data.access_token;

        // 更新 localStorage 中的 tokens
        localStorage.setItem('token', data.access_token);

        // 如果后端返回了新的 refresh token，也需要更新
        if (data.refresh_token) {
          this.refreshToken = data.refresh_token;
          localStorage.setItem('refresh_token', data.refresh_token);
        }

        return true;
      } else {
        console.error('Token refresh failed with status:', response.status);
        const errorData = await response.json();
        console.error('Refresh error details:', errorData);
        return false;
      }
    } catch (e) {
      console.error('Token refresh failed with exception:', e);
      return false;
    }
  }

  private async request<T>(
    method: string,
    path: string,
    data?: any,
    options: { isFormData?: boolean } = {}
  ): Promise<T> {
    const headers: HeadersInit = {}

    // 仅当不是 FormData 请求时设置 Content-Type
    if (!options.isFormData) {
      headers['Content-Type'] = 'application/json'
    }

    // 添加认证头，除非是form data的GET请求（GET请求不应该有body）
    if (this.token && !(options.isFormData && method === 'GET')) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const reqOptions: RequestInit = {
      method,
      headers: options.isFormData ? {} : headers // multipart/form-data的headers由浏览器自动设置
    }

    // 只在请求方法需要 body 时才添加
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH') && !options.isFormData) {
      reqOptions.body = JSON.stringify(data)
    } else if (options.isFormData && data instanceof FormData) {
      reqOptions.body = data
      // 当使用FormData时，不要设置Content-Type头部，让浏览器自动设置
      // 但仍需要添加 Authorization 头
      if (this.token) {
        reqOptions.headers = {
          'Authorization': `Bearer ${this.token}`
        }
      }
    }

    try {
      let response = await fetch(`${this.baseURL}${path}`, reqOptions)

      if (!response.ok) {
        if (response.status === 401) {
          // 尝试刷新 token
          const refreshed = await this.tryRefreshToken()
          if (refreshed) {
            // 使用新 token 重试请求
            if (this.token) {
              reqOptions.headers = {
                ...reqOptions.headers,
                'Authorization': `Bearer ${this.token}`
              }
            }
            response = await fetch(`${this.baseURL}${path}`, reqOptions)

            // 如果重试成功，返回结果
            if (response.ok) {
              return await response.json()
            } else {
              // 重试失败，可能是其他错误，继续抛出错误
              const error = await response.json().catch(() => ({ detail: 'Request failed after token refresh' }))
              throw new Error(error.detail || 'Request failed after token refresh')
            }
          } else {
            // 刷新失败，清理用户信息并跳转登录页
            this.clearToken()
            window.location.href = '/login'
            return Promise.reject(new Error('登录已过期，请重新登录'))
          }
        }

        const error = await response.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(error.detail || '请求失败')
      }

      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)

      // 检查是否是网络错误或其他连接问题
      if (error instanceof TypeError) {
        // 网络错误，不一定是认证问题
        throw error
      }

      // 检查是否是认证相关的错误
      if (error instanceof Error && error.message.includes('未授权')) {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }

      throw error
    }
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path)
  }

  async post<T>(path: string, data?: any): Promise<T> {
    return this.request<T>('POST', path, data)
  }

  async put<T>(path: string, data?: any): Promise<T> {
    return this.request<T>('PUT', path, data)
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path)
  }

  async upload<T>(path: string, formData: FormData): Promise<T> {
    return this.request<T>('POST', path, formData, { isFormData: true })
  }
}

export const api = new ApiClient()

// Product Entity APIs
export const productAPI = {
  create: async (data: any) => {
    return api.post('/products/entity', data)
  },

  list: async (params?: {
    skip?: number
    limit?: number
    ingredient_id?: number
    search?: string
  }) => {
    const query = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          query.append(key, String(value))
        }
      })
    }
    const queryString = query.toString()
    return api.get(`/products/entity${queryString ? `?${queryString}` : ''}`)
  },

  get: async (id: number) => {
    return api.get(`/products/entity/${id}`)
  },

  update: async (id: number, data: any) => {
    return api.put(`/products/entity/${id}`, data)
  },

  delete: async (id: number) => {
    return api.delete(`/products/entity/${id}`)
  }
}

// User Preference APIs
export const preferenceAPI = {
  set: async (data: any) => {
    return api.post('/preferences', data)
  },

  list: async (params?: { skip?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          query.append(key, String(value))
        }
      })
    }
    const queryString = query.toString()
    return api.get(`/preferences${queryString ? `?${queryString}` : ''}`)
  },

  get: async (ingredient_id: number) => {
    return api.get(`/preferences/${ingredient_id}`)
  },

  update: async (ingredient_id: number, data: any) => {
    return api.put(`/preferences/${ingredient_id}`, data)
  },

  delete: async (ingredient_id: number) => {
    return api.delete(`/preferences/${ingredient_id}`)
  }
}
