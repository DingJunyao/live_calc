/**
 * 时区处理工具
 *
 * 统一处理前端时区相关的计算和转换
 */

/**
 * 获取当前时区偏移（秒）
 * @returns 时区偏移（秒），东八区返回 28800
 */
export function getTimezoneOffsetSeconds(): number {
  return -new Date().getTimezoneOffset() * 60
}

/**
 * 获取当前时区偏移（小时）
 * @returns 时区偏移（小时），东八区返回 8
 */
export function getTimezoneOffsetHours(): number {
  return -new Date().getTimezoneOffset() / 60
}

/**
 * 将本地日期转换为UTC时间范围（用于API查询）
 * @param localDate 本地日期（如 '2026-03-29'）
 * @returns [utcStart, utcEnd] ISO格式的UTC时间范围
 *
 * @example
 * const [start, end] = localDateToUTCRange('2026-03-29')
 * // start: '2026-03-28T16:00:00.000Z'
 * // end: '2026-03-29T15:59:59.999Z'
 * // 对应北京时间的 2026-03-29 00:00:00 到 23:59:59
 */
export function localDateToUTCRange(localDate: string): [string, string] {
  const date = new Date(localDate)

  // 本地日期的开始时间（00:00:00）
  const localStart = new Date(date)
  localStart.setHours(0, 0, 0, 0)

  // 本地日期的结束时间（23:59:59.999）
  const localEnd = new Date(date)
  localEnd.setHours(23, 59, 59, 999)

  // 转换为UTC时间
  const utcStart = new Date(localStart.getTime() - localStart.getTimezoneOffset() * 60 * 1000)
  const utcEnd = new Date(localEnd.getTime() - localEnd.getTimezoneOffset() * 60 * 1000)

  return [
    utcStart.toISOString(),
    utcEnd.toISOString()
  ]
}

/**
 * 将本地日期范围转换为UTC时间范围（用于API查询）
 * @param startDate 开始日期（如 '2026-03-01'）
 * @param endDate 结束日期（如 '2026-03-31'）
 * @returns [utcStart, utcEnd] ISO格式的UTC时间范围
 */
export function localDateRangeToUTCRange(startDate: string, endDate: string): [string, string] {
  const [start] = localDateToUTCRange(startDate)
  const [, end] = localDateToUTCRange(endDate)
  return [start, end]
}

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
 * 判断两个UTC时间是否在同一天（本地时区）
 * @param utcString1 第一个UTC时间
 * @param utcString2 第二个UTC时间
 * @returns 是否在同一天
 */
export function isSameLocalDay(utcString1: string, utcString2: string): boolean {
  return utcToLocalDate(utcString1) === utcToLocalDate(utcString2)
}
