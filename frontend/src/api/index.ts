// API 模块入口 — 根据 VITE_STORAGE_MODE 环境变量切换云端 / 本地存储模式。
//  cloud（默认）→ 使用 Axios HTTP 客户端
//  local → 使用 IndexedDB 本地存储（路由到 local/proxy）

import { api as cloudApi, REQUEST_TIMEOUT, LONG_REQUEST_TIMEOUT } from './client'

const storageMode = import.meta.env.VITE_STORAGE_MODE || 'cloud'

type ApiFn = (url: string, data?: any, config?: any) => Promise<any>

interface ApiLike {
  get: ApiFn
  post: ApiFn
  put: ApiFn
  delete: ApiFn
}

function createLocalApi(): ApiLike {
  return {
    get: async (url, config) => {
      const m = await import('./local/proxy')
      return m.localGet(url, config?.params)
    },
    post: async (url, data) => {
      const m = await import('./local/proxy')
      return m.localPost(url, data)
    },
    put: async (url, data) => {
      const m = await import('./local/proxy')
      return m.localPut(url, data)
    },
    delete: async (url) => {
      const m = await import('./local/proxy')
      return m.localDelete(url)
    },
  }
}

function createCloudApi(): ApiLike {
  return {
    get: (url, config) => cloudApi.get(url, config) as Promise<any>,
    post: (url, data, config) => cloudApi.post(url, data, config) as Promise<any>,
    put: (url, data, config) => cloudApi.put(url, data, config) as Promise<any>,
    delete: (url, config) => cloudApi.delete(url, config) as Promise<any>,
  }
}

export const api: ApiLike = storageMode === 'local' ? createLocalApi() : createCloudApi()

export { REQUEST_TIMEOUT, LONG_REQUEST_TIMEOUT }
