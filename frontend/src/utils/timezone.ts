/**
 * 时区处理工具
 *
 * 统一处理前端时区相关的计算和转换。
 * 注：用户时区由 api/client.ts 的请求拦截器统一以 X-Timezone 头注入，
 * 这里只保留客户端显示/输入用的转换工具。
 */

/**
 * 将UTC时间转换为本地日期字符串（YYYY-MM-DD格式）
 * @param utcString UTC时间字符串（ISO格式）
 * @returns 本地日期字符串
 *
 * @example
 * utcToLocalDate('2026-03-28T17:00:00.000Z') // '2026-03-29' (东八区)
 */
export function utcToLocalDate(utcString: string): string {
  const date = new Date(utcString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * 格式化日期时间为本地字符串
 * @param utcString UTC时间字符串（ISO格式）
 * @returns 格式化的本地日期时间字符串
 *
 * @example
 * formatToLocalDateTime('2026-03-28T09:46:00.000Z') // '2026-03-28 17:46:00'
 */
export function formatToLocalDateTime(utcString: string): string {
  const date = new Date(utcString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

/**
 * 获取当前本地日期字符串（YYYY-MM-DD）
 * 使用本地时间而非 UTC，避免时区偏移导致的日期错误
 *
 * @example
 * // 在北京时间 2026-06-13 01:00 调用
 * getLocalDateString() // '2026-06-13'（而非 '2026-06-12'）
 */
export function getLocalDateString(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * 获取当前本地日期时间字符串（YYYY-MM-DDTHH:mm）
 * 用于 datetime-local input 的默认值
 *
 * @example
 * getLocalDateTimeString() // '2026-06-13T10:25'
 */
export function getLocalDateTimeString(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

/**
 * 格式化 UTC 时间为本地日期时间字符串（YYYY-MM-DD HH:mm，不含秒）
 * @param utcString UTC时间字符串（ISO格式，需带时区信息）
 * @returns 格式化的本地日期时间字符串，空值返回 '-'
 *
 * @example
 * formatToLocalDateTimeShort('2026-03-28T09:46:00+00:00') // '2026-03-28 17:46'
 */
export function formatToLocalDateTimeShort(utcString: string | null | undefined): string {
  if (!utcString) return '-'
  const date = new Date(utcString)
  if (isNaN(date.getTime())) return '-'
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

/**
 * 格式化 UTC 时间为本地日期字符串（YYYY-MM-DD）
 * @param utcString UTC时间字符串（ISO格式，需带时区信息）
 * @returns 本地日期字符串，空值返回 '-'
 *
 * @example
 * formatToLocalDate('2026-03-28T17:00:00+00:00') // '2026-03-29' (东八区)
 */
export function formatToLocalDate(utcString: string | null | undefined): string {
  if (!utcString) return '-'
  const date = new Date(utcString)
  if (isNaN(date.getTime())) return '-'
  return utcToLocalDate(utcString)
}

/**
 * 判断两个UTC时间是否在同一天（本地时区）
 * @param utcString1 第一个UTC时间
 * @param utcString2 第二个UTC时间
 * @returns 是否在同一天
 */
export function isSameLocalDay(utcString1: string, utcString2: string): boolean {
  return utcToLocalDate(utcString1) === utcToLocalDate(utcString2)
}
