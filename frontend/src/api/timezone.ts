/**
 * API 时区处理工具
 *
 * 自动为 API 请求添加时区偏移参数
 */
import { getTimezoneOffsetSeconds } from '@/utils/timezone'

/**
 * 为 API 参数添加时区偏移
 * @param params 原始参数对象
 * @returns 包含时区偏移的参数对象
 *
 * @example
 * const params = addTimezoneOffset({ start_date: '2026-03-29', end_date: '2026-03-29' })
 * // { start_date: '2026-03-29', end_date: '2026-03-29', timezone_offset: 28800 }
 */
export function addTimezoneOffset<T extends Record<string, any>>(params: T): T & { timezone_offset: number } {
  return {
    ...params,
    timezone_offset: getTimezoneOffsetSeconds()
  }
}

/**
 * 为 Axios 请求配置添加时区偏移参数
 * @param config Axios 请求配置
 * @returns 更新后的请求配置
 *
 * @example
 * api.get('/reports/expense', addTimezoneToConfig({
 *   params: { start_date: '2026-03-29', end_date: '2026-03-29' }
 * }))
 */
export function addTimezoneToConfig(config: Record<string, any>): Record<string, any> {
  const params = config.params || {}
  return {
    ...config,
    params: {
      ...params,
      timezone_offset: getTimezoneOffsetSeconds()
    }
  }
}
