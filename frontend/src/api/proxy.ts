import { localGet, localPost, localPut, localDelete } from './local/proxy'

export function createLocalProxy() {
  return {
    get: (url: string, config?: any) => localGet(url, config?.params),
    post: (url: string, data?: any) => localPost(url, data),
    put: (url: string, data?: any) => localPut(url, data),
    delete: (url: string) => localDelete(url),
  }
}
