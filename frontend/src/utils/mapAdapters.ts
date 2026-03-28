/**
 * 地图引擎适配器
 *
 * 使用适配器模式统一不同地图引擎的接口
 */

import L from 'leaflet'
import 'leaflet.chinatmsproviders'
import type {
  MapAdapter,
  MapEngine,
  MapInstance,
  MapOptions,
  Marker,
  MarkerOptions,
  LatLng
} from '@/types/map'
import { fromWGS84, toWGS84 } from './coordTransform'

/**
 * Leaflet 适配器
 *
 * 支持通过 leaflet.chinatmsproviders 插件使用各种中国地图服务
 */
export class LeafletAdapter implements MapAdapter {
  private engine: MapEngine
  private apiKey?: string
  private markers: Map<any, L.Marker> = new Map()

  constructor(engine: MapEngine, apiKey?: string) {
    this.engine = engine
    this.apiKey = apiKey
  }

  /**
   * 初始化地图
   */
  async init(container: HTMLElement, options: MapOptions): Promise<MapInstance> {
    // 默认中心点：北京
    const center = options.center || { lat: 39.9042, lng: 116.4074 }
    const zoom = options.zoom || 12

    // 创建地图实例
    const map = L.map(container, {
      zoomControl: true,
      attributionControl: true
    }).setView([center.lat, center.lng], zoom)

    // 添加地图图层
    const layer = this.getTileLayer()
    layer.addTo(map)

    // 绑定点击事件
    if (options.onClick) {
      map.on('click', (e: L.LeafletMouseEvent) => {
        const latlng = e.latlng
        options.onClick!({ lat: latlng.lat, lng: latlng.lng })
      })
    }

    // 返回统一接口的包装对象
    return this.wrapMapInstance(map)
  }

  /**
   * 获取地图图层
   */
  private getTileLayer(): L.TileLayer {
    // 注意：leaflet.chinatmsproviders 的类型定义可能不完整
    // 使用 any 来绕过类型检查
    const provider = this.getChinaProvider()

    // @ts-ignore - leaflet.chinatmsproviders 扩展了 L.tileLayer
    if (L.tileLayer.chinaProvider) {
      // @ts-ignore
      return L.tileLayer.chinaProvider(provider, {
        key: this.apiKey,
        maxZoom: 18
      })
    }

    // 降级到 OSM
    return L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    })
  }

  /**
   * 获取中国地图提供商
   */
  private getChinaProvider(): string {
    switch (this.engine) {
      case 'amap':
        return 'GaoDe.Normal.Map'
      case 'baidu':
        return 'Baidu.Normal.Map'
      case 'tencent':
        return 'Tencent.Normal.Map'
      case 'tianditu':
        return 'Tianditu.Normal.Map'
      case 'osm':
      default:
        return 'Normal.Map'
    }
  }

  /**
   * 添加标记
   */
  addMarker(map: MapInstance, position: LatLng, options?: MarkerOptions): Marker {
    const leafletMap = this.unwrapMapInstance(map)

    // 如果不是 WGS84 坐标系，需要转换
    let pos = position
    if (this.engine !== 'osm' && this.engine !== 'tianditu') {
      try {
        const converted = fromWGS84(position.lat, position.lng, this.engine)
        pos = { lat: converted.lat, lng: converted.lng }
      } catch (err) {
        console.warn('坐标转换失败，使用原始坐标:', err)
      }
    }

    // 验证坐标有效性
    if (!pos.lat || !pos.lng || isNaN(pos.lat) || isNaN(pos.lng)) {
      console.error('无效的坐标:', position, pos)
      throw new Error(`无效的坐标: (${pos.lat}, ${pos.lng})`)
    }

    // 创建标记图标
    const icon = this.createMarkerIcon(options)

    // 创建标记
    const marker = L.marker([pos.lat, pos.lng], {
      icon,
      draggable: options?.draggable || false,
      title: options?.title
    })

    marker.addTo(leafletMap)

    // 保存标记引用
    this.markers.set(marker, marker)

    return this.wrapMarkerInstance(marker)
  }

  /**
   * 创建标记图标
   */
  private createMarkerIcon(options?: MarkerOptions): L.DivIcon {
    const color = options?.highlighted ? '#ff5252' : '#4285f4'
    const size = options?.highlighted ? 36 : 30

    return L.divIcon({
      className: 'custom-map-marker',
      html: `
        <div style="
          width: ${size}px;
          height: ${size}px;
          background: ${color};
          border: 3px solid white;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        "></div>
        <div style="
          width: 8px;
          height: 8px;
          background: white;
          border-radius: 50%;
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
        "></div>
      `,
      iconSize: [size, size],
      iconAnchor: [size / 2, size],
      popupAnchor: [0, -size]
    })
  }

  /**
   * 移除标记
   */
  removeMarker(marker: Marker): void {
    const leafletMarker = this.unwrapMarkerInstance(marker)
    leafletMarker.remove()
    this.markers.delete(leafletMarker)
  }

  /**
   * 设置地图中心
   */
  setCenter(map: MapInstance, position: LatLng): void {
    const leafletMap = this.unwrapMapInstance(map)

    // 如果不是 WGS84 坐标系，需要转换
    let pos = position
    if (this.engine !== 'osm' && this.engine !== 'tianditu') {
      try {
        const converted = fromWGS84(position.lat, position.lng, this.engine)
        pos = { lat: converted.lat, lng: converted.lng }
      } catch (err) {
        console.warn('坐标转换失败，使用原始坐标:', err)
      }
    }

    // 验证坐标有效性
    if (!pos.lat || !pos.lng || isNaN(pos.lat) || isNaN(pos.lng)) {
      console.error('设置中心失败：无效的坐标', position, pos)
      return
    }

    leafletMap.setView([pos.lat, pos.lng])
  }

  /**
   * 设置缩放级别
   */
  setZoom(map: MapInstance, level: number): void {
    const leafletMap = this.unwrapMapInstance(map)

    // 验证缩放级别
    if (level < 1 || level > 20 || isNaN(level)) {
      console.warn('无效的缩放级别:', level)
      return
    }

    leafletMap.setZoom(level)
  }

  /**
   * 高亮标记
   */
  highlightMarker(marker: Marker, highlighted: boolean): void {
    const leafletMarker = this.unwrapMarkerInstance(marker)
    const icon = this.createMarkerIcon({ highlighted })
    leafletMarker.setIcon(icon)
  }

  /**
   * 销毁地图
   */
  destroy(map: MapInstance): void {
    const leafletMap = this.unwrapMapInstance(map)
    leafletMap.remove()
  }

  /**
   * 包装 Leaflet 地图实例为统一接口
   */
  private wrapMapInstance(leafletMap: L.Map): MapInstance {
    // 保存原始实例引用
    const wrapped = leafletMap as any
    wrapped._leafletInstance = leafletMap

    // 直接返回原生实例，因为它已经包含了所有需要的方法
    return leafletMap as any
  }

  /**
   * 解包装获取 Leaflet 地图实例
   */
  private unwrapMapInstance(map: MapInstance): L.Map {
    // 如果是包装过的，返回原始实例
    if ((map as any)._leafletInstance) {
      return (map as any)._leafletInstance
    }
    // 否则直接返回（可能就是原生实例）
    return map as any
  }

  /**
   * 包装 Leaflet 标记实例为统一接口
   */
  private wrapMarkerInstance(leafletMarker: L.Marker): Marker {
    // 保存原始实例引用
    const wrapped = leafletMarker as any
    wrapped._leafletInstance = leafletMarker

    // 直接返回原生实例
    return leafletMarker as any
  }

  /**
   * 解包装获取 Leaflet 标记实例
   */
  private unwrapMarkerInstance(marker: Marker): L.Marker {
    // 如果是包装过的，返回原始实例
    if ((marker as any)._leafletInstance) {
      return (marker as any)._leafletInstance
    }
    // 否则直接返回
    return marker as any
  }
}

/**
 * 地图适配器工厂
 */
export class MapAdapterFactory {
  /**
   * 创建地图适配器
   */
  static create(engine: MapEngine, apiKey?: string): MapAdapter {
    // 目前只实现 Leaflet 适配器
    // SDK 适配器在后续阶段实现
    return new LeafletAdapter(engine, apiKey)
  }

  /**
   * 判断是否应该使用 SDK（而不是 Leaflet）
   */
  static shouldUseSDK(engine: MapEngine, hasApiKey: boolean): boolean {
    // 高德、百度、腾讯有 API Key 时使用自有 SDK
    return ['amap', 'baidu', 'tencent'].includes(engine) && hasApiKey
  }
}
