// utils/errorHandler.ts
// 统一的错误处理工具，确保前端始终展示后端传来的有用错误信息，
// 而不是给用户看 HTTP 状态码。

/**
 * 从任意错误对象中提取用户可读的错误消息。
 *
 * 提取优先级：
 * 1. error.userMessage — 由 Axios 响应拦截器预处理的友好消息
 * 2. error.response.data.detail — 后端返回的结构化错误详情
 * 3. error.response.data.message — 后端返回的备用消息字段
 * 4. error.message — JavaScript 原生错误消息（排除 Axios 通用消息）
 * 5. fallback — 调用方指定的默认消息
 *
 * @param error - 捕获到的错误对象（通常来自 Axios catch）
 * @param fallback - 当所有提取方式都失败时的默认消息
 * @returns 用户可读的中文错误消息
 */
export function getErrorMessage(error: unknown, fallback: string = '操作失败'): string {
  if (!error) return fallback

  const e = error as any

  // 1. 由 Axios 拦截器预处理的消息
  if (e.userMessage && typeof e.userMessage === 'string') {
    return e.userMessage
  }

  // 2. 后端 structured error: { detail: "..." }
  if (e.response?.data?.detail && typeof e.response.data.detail === 'string') {
    return e.response.data.detail
  }

  // 3. 后端备用消息字段
  if (e.response?.data?.message && typeof e.response.data.message === 'string') {
    return e.response.data.message
  }

  // 4. JavaScript 原生错误消息，排除无用的 Axios 通用消息
  if (e.message && typeof e.message === 'string') {
    // 过滤掉 Axios 的通用 HTTP 状态码消息
    if (
      e.message.startsWith('Request failed with status code') ||
      e.message === 'Network Error'
    ) {
      // 对于网络错误，返回更友好的消息
      if (e.message === 'Network Error') {
        return '网络连接失败，请检查网络后重试'
      }
      // 对于 HTTP 状态码消息，走 fallback
      return fallback
    }
    return e.message
  }

  return fallback
}

/**
 * 判断错误是否为网络连接问题。
 */
export function isNetworkError(error: unknown): boolean {
  const e = error as any
  return (
    e?.message === 'Network Error' ||
    e?.userMessage === '网络连接失败' ||
    e?.code === 'ECONNABORTED' ||
    e?.code === 'ERR_NETWORK'
  )
}

/**
 * 判断错误是否为请求超时。
 */
export function isTimeoutError(error: unknown): boolean {
  const e = error as any
  return (
    e?.code === 'ECONNABORTED' ||
    e?.code === 'ETIMEDOUT' ||
    (e?.message && e.message.includes('timeout'))
  )
}

/**
 * 判断错误是否由 Token 过期导致（401）。
 */
export function isAuthError(error: unknown): boolean {
  const e = error as any
  return e?.response?.status === 401
}
