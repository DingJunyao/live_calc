/**
 * 百度地图 SDK 引擎
 * 支持百度地图原生 JavaScript API v3.0 (Legacy) 和 GL 版本
 */

import type { MapEngine, MarkerOptions, MapConfig } from '../../map/mapTypes';
import { convertCoordinate } from '../../coordinateTransform';
import { sdkLoader } from '../../SDKLoader';

declare global {
  interface Window {
    BMap?: any;
    BMapGL?: any;
  }
}

export class BaiduSDKEngine implements MapEngine {
  name = 'baidu-sdk' as const;
  displayName = '百度地图 (SDK)';

  private map: any = null;
  private markers: Map<any, any> = new Map();
  private config: MapConfig;
  private eventHandlers: Map<string, Set<Function>> = new Map();
  private useGL: boolean = true; // 默认使用 GL 版本

  constructor(config: MapConfig) {
    this.config = config;
    // 可以通过配置选择版本
    this.useGL = config.mapApiKeys.baiduUseGL !== false;
  }

  async init(container: HTMLElement, options: any): Promise<void> {
    const center = options.center || [39.9042, 116.4074];
    const zoom = options.zoom || 13;

    // 加载 SDK
    const apiKey = this.config.mapApiKeys.baidu;
    if (!apiKey) {
      throw new Error('[BaiduSDKEngine] API Key is required');
    }

    try {
      await sdkLoader.loadBMap(apiKey, this.useGL);
    } catch (error) {
      console.error('[BaiduSDKEngine] Failed to load SDK:', error);
      throw error;
    }

    // 等待 BMap 全局对象就绪
    await this.waitForBMap();

    // 获取 BMap 类（GL 版本或 Legacy 版本）
    const BMap = this.useGL ? window.BMapGL : window.BMap;
    if (!BMap) {
      throw new Error(`[BaiduSDKEngine] BMap${this.useGL ? 'GL' : ''} is not available`);
    }

    // 创建地图实例（百度使用 [lng, lat] 格式）
    // WGS84 转 BD-09
    const bd09Coord = convertCoordinate(center[0], center[1], 'wgs84', 'bd09');

    this.map = new BMap.Map(container, {
      enableMapClick: options.enableClick !== false
    });

    const point = new BMap.Point(bd09Coord.lng, bd09Coord.lat);
    this.map.centerAndZoom(point, zoom);

    // 添加点击事件
    if (options.enableClick !== false) {
      this.map.addEventListener('click', (e: any) => {
        // BD-09 转 WGS84
        const wgs84Coord = convertCoordinate(e.latlng.lat, e.latlng.lng, 'bd09', 'wgs84');
        this.emit('click', {
          lat: wgs84Coord.lat,
          lng: wgs84Coord.lng
        });
      });
    }

    // 启用滚轮缩放
    this.map.enableScrollWheelZoom(true);

    // 延迟调用 invalidateSize
    setTimeout(() => {
      if (this.map) {
        const size = this.map.getContainer()?.getBoundingClientRect();
        if (size) {
          this.map.reset();
        }
      }
    }, 100);
  }

  setCenter(lat: number, lng: number): void {
    if (this.map) {
      const BMap = this.useGL ? window.BMapGL : window.BMap;
      if (!BMap) return;

      // 注意：坐标已经由调用方转换为 BD-09，直接使用
      // 百度地图使用 [lng, lat] 格式
      const point = new BMap.Point(lng, lat);
      this.map.setCenter(point);
    }
  }

  setZoom(zoom: number): void {
    if (this.map) {
      this.map.setZoom(zoom);
    }
  }

  addMarker(lat: number, lng: number, options?: MarkerOptions): any {
    if (!this.map) {
      throw new Error('[BaiduSDKEngine] Map not initialized');
    }

    const BMap = this.useGL ? window.BMapGL : window.BMap;
    if (!BMap) {
      throw new Error('[BaiduSDKEngine] BMap is not available');
    }

    // 注意：坐标已经由调用方转换为 BD-09，直接使用
    // 百度地图使用 [lng, lat] 格式
    const point = new BMap.Point(lng, lat);

    const marker = new BMap.Marker(point, {
      enableDragging: options?.draggable ?? true
    });

    this.map.addOverlay(marker);

    // 拖拽事件
    if (options?.draggable !== false) {
      marker.addEventListener('dragend', (e: any) => {
        const position = marker.getPosition();
        // BD-09 转 WGS84（返回给调用方）
        const wgs84Coord = convertCoordinate(position.lat, position.lng, 'bd09', 'wgs84');
        this.emit('markerDragend', {
          lat: wgs84Coord.lat,
          lng: wgs84Coord.lng
        });
      });
    }

    const markerId = Symbol('marker');
    this.markers.set(markerId, marker);
    return markerId;
  }

  removeMarker(markerId: any): void {
    const marker = this.markers.get(markerId);
    if (marker && this.map) {
      this.map.removeOverlay(marker);
      this.markers.delete(markerId);
    }
  }

  updateMarkerPosition(markerId: any, lat: number, lng: number): void {
    const marker = this.markers.get(markerId);
    if (marker) {
      const BMap = this.useGL ? window.BMapGL : window.BMap;
      if (!BMap) return;

      // 注意：坐标已经由调用方转换为 BD-09，直接使用
      // 百度地图使用 [lng, lat] 格式
      const point = new BMap.Point(lng, lat);
      marker.setPosition(point);
    }
  }

  destroy(): void {
    // 移除所有标记
    this.markers.forEach(marker => {
      if (this.map) {
        this.map.removeOverlay(marker);
      }
    });
    this.markers.clear();

    // 销毁地图实例
    if (this.map) {
      try {
        // 百度地图有 destroy 方法
        if (typeof this.map.destroy === 'function') {
          this.map.destroy();
        }
      } catch (error) {
        console.warn('[BaiduSDKEngine] Error destroying map:', error);
      }
      this.map = null;
    }

    this.eventHandlers.clear();
  }

  getMap(): any {
    return this.map;
  }

  on(event: string, handler: Function): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    // 绑定到地图
    if (this.map && event === 'click') {
      this.map.addEventListener('click', (e: any) => {
        const wgs84Coord = convertCoordinate(e.latlng.lat, e.latlng.lng, 'bd09', 'wgs84');
        handler({ lat: wgs84Coord.lat, lng: wgs84Coord.lng });
      });
    }
  }

  off(event: string, handler: Function): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  private emit(event: string, data: any): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }

  // 等待 BMap 全局对象就绪
  private waitForBMap(): Promise<void> {
    return new Promise((resolve) => {
      const check = () => {
        const BMap = this.useGL ? window.BMapGL : window.BMap;
        if (BMap) {
          resolve();
        } else {
          setTimeout(check, 50);
        }
      };
      check();
    });
  }
}
