/**
 * 坐标系转换工具
 * 中国常用的坐标系：
 * - WGS84: GPS 标准坐标（国际通用）
 * - GCJ02: 国测局坐标（高德、腾讯使用）
 * - BD09: 百度坐标（在 GCJ02 基础上加密）
 */

// π 常量
const PI = Math.PI;
// 转换系数
const x_pi = (Math.PI * 3000.0) / 180.0;

/**
 * GCJ02 转 BD09（高德/腾讯 -> 百度）
 */
export function gcj02ToBd09(lat: number, lng: number): { lat: number; lng: number } {
  const x = lng;
  const y = lat;
  const z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * x_pi);
  const theta = Math.atan2(y, x) + 0.000003 * Math.cos(x * x_pi);
  const bd_lng = z * Math.cos(theta) + 0.0065;
  const bd_lat = z * Math.sin(theta) + 0.006;
  return { lat: bd_lat, lng: bd_lng };
}

/**
 * BD09 转 GCJ02（百度 -> 高德/腾讯）
 */
export function bd09ToGcj02(lat: number, lng: number): { lat: number; lng: number } {
  const x = lng - 0.0065;
  const y = lat - 0.006;
  const z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * x_pi);
  const theta = Math.atan2(y, x) - 0.000003 * Math.cos(x * x_pi);
  const gcj_lng = z * Math.cos(theta);
  const gcj_lat = z * Math.sin(theta);
  return { lat: gcj_lat, lng: gcj_lng };
}

/**
 * WGS84 转 GCJ02（GPS -> 国测局）
 */
export function wgs84ToGcj02(lat: number, lng: number): { lat: number; lng: number } {
  // 转换阈值
  const dlat = transformLat(lng - 105.0, lat - 35.0);
  const dlng = transformLng(lng - 105.0, lat - 35.0);
  const radlat = (lat / 180.0) * PI;
  let magic = Math.sin(radlat);
  magic = 1 - 0.006693421622965943 * magic * magic;
  const sqrtmagic = Math.sqrt(magic);
  dlat = (dlat * 180.0) / ((6336242.6562 / magic) * sqrtmagic * PI);
  dlng = (dlng * 180.0) / (6378245.0 / sqrtmagic * Math.cos(radlat) * PI);
  return { lat: lat + dlat, lng: lng + dlng };
}

/**
 * GCJ02 转 WGS84（国测局 -> GPS）
 */
export function gcj02ToWgs84(lat: number, lng: number): { lat: number; lng: number } {
  const dlat = transformLat(lng - 105.0, lat - 35.0);
  const dlng = transformLng(lng - 105.0, lat - 35.0);
  const radlat = (lat / 180.0) * PI;
  let magic = Math.sin(radlat);
  magic = 1 - 0.006693421622965943 * magic * magic;
  const sqrtmagic = Math.sqrt(magic);
  dlat = (dlat * 180.0) / ((6336242.6562 / magic) * sqrtmagic * PI);
  dlng = (dlng * 180.0) / (6378245.0 / sqrtmagic * Math.cos(radlat) * PI);
  return { lat: lat - dlat, lng: lng - dlng };
}

/**
 * WGS84 转 BD09（GPS -> 百度）
 */
export function wgs84ToBd09(lat: number, lng: number): { lat: number; lng: number } {
  const gcj = wgs84ToGcj02(lat, lng);
  return gcj02ToBd09(gcj.lat, gcj.lng);
}

/**
 * BD09 转 WGS84（百度 -> GPS）
 */
export function bd09ToWgs84(lat: number, lng: number): { lat: number; lng: number } {
  const gcj = bd09ToGcj02(lat, lng);
  return gcj02ToWgs84(gcj.lat, gcj.lng);
}

// 辅助函数：转换纬度
function transformLat(lat: number, lng: number): number {
  let ret = -100.0 + 2.0 * lat + 3.0 * lng + 0.2 * lng * lng + 0.1 * lat * lng + 0.2 * Math.sqrt(Math.abs(lat));
  ret += (20.0 * Math.sin(6.0 * lat * PI) + 20.0 * Math.sin(2.0 * lat * PI)) * 2.0 / 3.0;
  ret += (20.0 * Math.sin(lng * PI) + 40.0 * Math.sin(lng / 3.0 * PI)) * 2.0 / 3.0;
  ret += (160.0 * Math.sin(lng / 12.0 * PI) + 320.0 * Math.sin(lng * PI / 30.0 * PI)) * 2.0 / 3.0;
  return ret;
}

// 辅助函数：转换经度
function transformLng(lat: number, lng: number): number {
  let ret = 300.0 + lat + 2.0 * lng + 0.1 * lat * lat + 0.1 * lat * lng + 0.1 * Math.sqrt(Math.abs(lat));
  ret += (20.0 * Math.sin(6.0 * lat * PI) + 20.0 * Math.sin(2.0 * lat * PI)) * 2.0 / 3.0;
  ret += (20.0 * Math.sin(lat * PI) + 40.0 * Math.sin(lat / 3.0 * PI)) * 2.0 / 3.0;
  ret += (150.0 * Math.sin(lat / 12.0 * PI) + 300.0 * Math.sin(lat / 30.0 * PI)) * 2.0 / 3.0;
  return ret;
}

// 坐标系类型
export type CoordinateSystem = 'wgs84' | 'gcj02' | 'bd09';

/**
 * 坐标转换函数
 * @param lat 纬度
 * @param lng 经度
 * @param from 源坐标系
 * @param to 目标坐标系
 */
export function convertCoordinate(
  lat: number,
  lng: number,
  from: CoordinateSystem,
  to: CoordinateSystem
): { lat: number; lng: number } {
  if (from === to) {
    return { lat, lng };
  }

  // WGS84 <-> GCJ02
  if ((from === 'wgs84' && to === 'gcj02') || (from === 'gcj02' && to === 'wgs84')) {
    if (from === 'wgs84') {
      return wgs84ToGcj02(lat, lng);
    } else {
      return gcj02ToWgs84(lat, lng);
    }
  }

  // GCJ02 <-> BD09
  if ((from === 'gcj02' && to === 'bd09') || (from === 'bd09' && to === 'gcj02')) {
    if (from === 'gcj02') {
      return gcj02ToBd09(lat, lng);
    } else {
      return bd09ToGcj02(lat, lng);
    }
  }

  // WGS84 <-> BD09
  if ((from === 'wgs84' && to === 'bd09') || (from === 'bd09' && to === 'wgs84')) {
    if (from === 'wgs84') {
      return wgs84ToBd09(lat, lng);
    } else {
      return bd09ToWgs84(lat, lng);
    }
  }

  return { lat, lng };
}

/**
 * 获取地图引擎对应的坐标系
 */
export function getCoordinateSystem(mapType: string): CoordinateSystem {
  switch (mapType) {
    case 'amap':  // 高德
    case 'tencent': // 腾讯
      return 'gcj02';
    case 'baidu': // 百度
      return 'bd09';
    case 'tianditu': // 天地图
    case 'osm': // OpenStreetMap
    default:
      return 'wgs84';
  }
}