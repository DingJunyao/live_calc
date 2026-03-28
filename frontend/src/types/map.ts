/**
 * 地图相关类型定义
 */

/**
 * 经纬度坐标
 */
export interface LatLng {
  lat: number
  lng: number
}

/**
 * 地图初始化选项
 */
export interface MapOptions {
  center?: LatLng
  zoom?: number
  engine: MapEngine
  apiKey?: string
  onClick?: (latlng: LatLng) => void
}

/**
 * 地图引擎类型
 */
export type MapEngine = 'amap' | 'baidu' | 'tencent' | 'tianditu' | 'osm'

/**
 * 标记选项
 */
export interface MarkerOptions {
  title?: string
  draggable?: boolean
  merchantId?: number
  color?: string
  highlighted?: boolean
}

/**
 * 地图实例接口（所有地图引擎的统一接口）
 */
export interface MapInstance {
  setView(center: LatLng, zoom?: number): void
  getCenter(): LatLng
  getZoom(): number
  on(event: string, handler: Function): void
  off(event: string, handler: Function): void
  remove(): void
}

/**
 * 标记实例接口
 */
export interface Marker {
  setLatLng(latlng: LatLng): Marker
  addTo(map: MapInstance): Marker
  remove(): void
}

/**
 * 地图适配器接口
 */
export interface MapAdapter {
  /**
   * 初始化地图
   */
  init(container: HTMLElement, options: MapOptions): Promise<MapInstance>

  /**
   * 添加标记
   */
  addMarker(map: MapInstance, position: LatLng, options?: MarkerOptions): Marker

  /**
   * 移除标记
   */
  removeMarker(marker: Marker): void

  /**
   * 设置地图中心
   */
  setCenter(map: MapInstance, position: LatLng): void

  /**
   * 设置缩放级别
   */
  setZoom(map: MapInstance, level: number): void

  /**
   * 高亮标记
   */
  highlightMarker(marker: Marker, highlighted: boolean): void

  /**
   * 销毁地图
   */
  destroy(map: MapInstance): void
}

/**
 * 商家信息（用于地图标记）
 */
export interface MerchantMarker {
  id: number
  name: string
  address?: string
  latitude: number
  longitude: number
}

/**
 * 地图配置
 */
export interface MapConfig {
  available_maps: string[]
  default_map: string
  map_api_keys: {
    amap: string | null
    amap_security: string | null
    baidu: string | null
    tencent: string | null
    tianditu: {
      token: string
      type: string
    }
  }
}

/**
 * 坐标系类型
 */
export type CoordSystem = 'WGS84' | 'GCJ02' | 'BD09'

/**
 * 坐标转换结果
 */
export interface CoordTransformResult {
  lat: number
  lng: number
  system: CoordSystem
}
