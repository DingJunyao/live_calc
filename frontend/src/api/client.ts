class ApiClient {
  private baseURL: string
  private token: string | null = null

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || '/api/v1'
    this.token = localStorage.getItem('token')
  }

  setToken(token: string): void {
    this.token = token
    localStorage.setItem('token', token)
  }

  clearToken(): void {
    this.token = null
    localStorage.removeItem('token')
  }

  private async request<T>(
    method: string,
    path: string,
    data?: any,
    options: { isFormData?: boolean } = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': options.isFormData ? 'multipart/form-data' : 'application/json'
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
      const response = await fetch(`${this.baseURL}${path}`, reqOptions)

      if (!response.ok) {
        if (response.status === 401) {
          // 未授权，令牌可能已过期，清理用户信息并跳转到登录页
          localStorage.removeItem('token');
          window.location.href = '/login';
          return Promise.reject(new Error('未授权，请重新登录'));
        }

        const error = await response.json()
        throw new Error(error.detail || '请求失败')
      }

      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)

      // 检查是否是认证相关的错误
      if (error instanceof TypeError || (error instanceof Error && error.message.includes('未授权'))) {
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
