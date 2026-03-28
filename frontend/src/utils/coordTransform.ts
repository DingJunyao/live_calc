/**
 * 坐标系转换工具
 *
 * 支持的坐标系：
 * - WGS84: 国际标准坐标系（GPS、OSM、天地图）
 * - GCJ02: 火星坐标系（高德、腾讯）
 * - BD09: 百度坐标系
 */

import type { CoordSystem, CoordTransformResult } from '@/types/map'

/**
 * 圆周率
 */
const PI = Math.PI
/**
 * 半长轴
 */
const A = 6378245.0
/**
 * 扁率
 */
const EE = 0.00669342162296594323

/**
 * 判断是否在中国境内
 */
function isInChina(lat: number, lng: number): boolean {
  return lng >= 72.004 && lng <= 137.8347 && lat >= 0.8293 && lat <= 55.8271
}

/**
 * WGS84 转 GCJ02 (火星坐标系)
 */
export function wgs84_to_gcj02(lat: number, lng: number): CoordTransformResult {
  if (!isInChina(lat, lng)) {
    return { lat, lng, system: 'GCJ02' }
  }

  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = (lat / 180.0) * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)

  dLat = (dLat * 180.0) / ((A * (1 - EE)) / (magic * sqrtMagic) * PI)
  dLng = (dLng * 180.0) / (A / sqrtMagic * Math.cos(radLat) * PI)

  const mgLat = lat + dLat
  const mgLng = lng + dLng

  return { lat: mgLat, lng: mgLng, system: 'GCJ02' }
}

/**
 * GCJ02 转 WGS84
 */
export function gcj02_to_wgs84(lat: number, lng: number): CoordTransformResult {
  if (!isInChina(lat, lng)) {
    return { lat, lng, system: 'WGS84' }
  }

  const wgs = wgs84_to_gcj02(lat, lng)
  const dLat = wgs.lat - lat
  const dLng = wgs.lng - lng

  return { lat: lat - dLat, lng: lng - dLng, system: 'WGS84' }
}

/**
 * GCJ02 转 BD09 (百度坐标系)
 */
export function gcj02_to_bd09(lat: number, lng: number): CoordTransformResult {
  const x_pi = (PI * 3000.0) / 180.0
  const z = Math.sqrt(lng * lng + lat * lat) + 0.00002 * Math.sin(lat * x_pi)
  const theta = Math.atan2(lat, lng) + 0.000003 * Math.cos(lng * x_pi)

  const bdLng = z * Math.cos(theta) + 0.0065
  const bdLat = z * Math.sin(theta) + 0.006

  return { lat: bdLat, lng: bdLng, system: 'BD09' }
}

/**
 * BD09 转 GCJ02
 */
export function bd09_to_gcj02(lat: number, lng: number): CoordTransformResult {
  const x_pi = (PI * 3000.0) / 180.0
  const x = lng - 0.0065
  const y = lat - 0.006
  const z = Math.sqrt(x * x + y * y) - 0.00002 * Math.sin(y * x_pi)
  const theta = Math.atan2(y, x) - 0.000003 * Math.cos(x * x_pi)

  const gcjLng = z * Math.cos(theta)
  const gcjLat = z * Math.sin(theta)

  return { lat: gcjLat, lng: gcjLng, system: 'GCJ02' }
}

/**
 * WGS84 转 BD09
 */
export function wgs84_to_bd09(lat: number, lng: number): CoordTransformResult {
  const gcj = wgs84_to_gcj02(lat, lng)
  return gcj02_to_bd09(gcj.lat, gcj.lng)
}

/**
 * BD09 转 WGS84
 */
export function bd09_to_wgs84(lat: number, lng: number): CoordTransformResult {
  const gcj = bd09_to_gcj02(lat, lng)
  return gcj02_to_wgs84(gcj.lat, gcj.lng)
}

/**
 * 转换纬度
 */
function transformLat(lng: number, lat: number): number {
  let ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * Math.sqrt(Math.abs(lng))

  ret +=
    ((20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0) / 3.0
  ret +=
    ((20.0 * Math.sin(lat * PI) + 40.0 * Math.sin((lat / 3.0) * PI)) * 2.0) / 3.0
  ret +=
    ((160.0 * Math.sin((lat / 12.0) * PI) + 320 * Math.sin((lat * PI) / 30.0)) * 2.0) /
    3.0

  return ret
}

/**
 * 转换经度
 */
function transformLng(lng: number, lat: number): number {
  let ret =
    300.0 +
    lng +
    2.0 * lat +
    0.1 * lng * lng +
    0.1 * lng * lat +
    0.1 * Math.sqrt(Math.abs(lng))

  ret +=
    ((20.0 * Math.sin(6.0 * lng * PI) + 20.0 * Math.sin(2.0 * lng * PI)) * 2.0) / 3.0
  ret +=
    ((20.0 * Math.sin(lng * PI) + 40.0 * Math.sin((lng / 3.0) * PI)) * 2.0) / 3.0
  ret +=
    ((150.0 * Math.sin((lng / 12.0) * PI) + 300.0 * Math.sin((lng / 30.0) * PI)) * 2.0) /
    3.0

  return ret
}

/**
 * 根据地图引擎转换坐标到 WGS84
 */
export function toWGS84(lat: number, lng: number, fromEngine: string): CoordTransformResult {
  switch (fromEngine) {
    case 'amap':
    case 'tencent':
      return gcj02_to_wgs84(lat, lng)
    case 'baidu':
      return bd09_to_wgs84(lat, lng)
    case 'tianditu':
    case 'osm':
    default:
      return { lat, lng, system: 'WGS84' }
  }
}

/**
 * 根据地图引擎从 WGS84 转换坐标
 */
export function fromWGS84(lat: number, lng: number, toEngine: string): CoordTransformResult {
  switch (toEngine) {
    case 'amap':
    case 'tencent':
      return wgs84_to_gcj02(lat, lng)
    case 'baidu':
      return wgs84_to_bd09(lat, lng)
    case 'tianditu':
    case 'osm':
    default:
      return { lat, lng, system: 'WGS84' }
  }
}
