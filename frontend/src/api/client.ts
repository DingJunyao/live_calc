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
    data?: any
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json'
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const options: RequestInit = {
      method,
      headers
    }

    // 只在请求方法需要 body 时才添加
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(data)
    }

    try {
      const response = await fetch(`${this.baseURL}${path}`, options)

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '请求失败')
      }

      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  async get<T>(path: string): Promise {
    return this.request<T>('GET', path)
  }

  async post<T>(path: string, data?: any): Promise {
    return this.request<T>('POST', path, data)
  }

  async put<T>(path: string, data?: any): Promise {
    return this.request<T>('PUT', path, data)
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path)
  }
}

export const api = new ApiClient()
