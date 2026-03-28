/**
 * 高德地图 SDK 引擎
 * 使用高德地图原生 JavaScript API v2.0
 */

import type { MapEngine, MarkerOptions, MapConfig } from '../../map/mapTypes';
import { convertCoordinate, getCoordinateSystem } from '../../coordinateTransform';
import { sdkLoader } from '../../SDKLoader';

declare global {
  interface Window {
    AMap?: any;
    _AMapSecurityConfig?: {
      securityJsCode: string;
    };
  }
}

export class AMapSDKEngine implements MapEngine {
  name = 'amap-sdk' as const;
  displayName = '高德地图 (SDK)';

  private map: any = null;
  private markers: Map<any, any> = new Map();
  private config: MapConfig;
  private eventHandlers: Map<string, Set<Function>> = new Map();
  private isSDKLoaded = false;

  constructor(config: MapConfig) {
    this.config = config;
  }

  async init(container: HTMLElement, options: any): Promise<void> {
    const center = options.center || [39.9042, 116.4074];
    const zoom = options.zoom || 13;

    // 设置安全密钥
    const securityCode = this.config.mapApiKeys.amapSecurity;
    if (securityCode) {
      window._AMapSecurityConfig = {
        securityJsCode: securityCode
      };
    }

    // 加载 SDK
    const apiKey = this.config.mapApiKeys.amap;
    if (!apiKey) {
      throw new Error('[AMapSDKEngine] API Key is required');
    }

    try {
      await sdkLoader.loadAMap(apiKey, '2.0');
      this.isSDKLoaded = true;
    } catch (error) {
      console.error('[AMapSDKEngine] Failed to load SDK:', error);
      throw error;
    }

    // 等待 AMap 全局对象就绪
    await this.waitForAMap();

    const AMap = window.AMap;
    if (!AMap) {
      throw new Error('[AMapSDKEngine] AMap is not available');
    }

    // 创建地图实例（高德使用 [lng, lat] 格式）
    this.map = new AMap.Map(container, {
      zoom: zoom,
      center: [center[1], center[0]], // WGS84 转 GCJ-02
      viewMode: '2D',
      rotateEnable: false,
      pitchEnable: false
    });

    // 添加点击事件
    if (options.enableClick !== false) {
      this.map.on('click', (e: any) => {
        // GCJ-02 转 WGS84
        const wgs84Coord = convertCoordinate(e.lnglat.lat, e.lnglat.lng, 'gcj02', 'wgs84');
        this.emit('click', {
          lat: wgs84Coord.lat,
          lng: wgs84Coord.lng
        });
      });
    }

    // 延迟调用 invalidateSize
    setTimeout(() => {
      if (this.map) {
        this.map.getSize();
      }
    }, 100);
  }

  setCenter(lat: number, lng: number): void {
    if (this.map) {
      // 注意：坐标已经由调用方转换为 GCJ-02，直接使用
      // 高德地图使用 [lng, lat] 格式
      this.map.setCenter([lng, lat]);
    }
  }

  setZoom(zoom: number): void {
    if (this.map) {
      this.map.setZoom(zoom);
    }
  }

  addMarker(lat: number, lng: number, options?: MarkerOptions): any {
    if (!this.map) {
      throw new Error('[AMapSDKEngine] Map not initialized');
    }

    const AMap = window.AMap;
    if (!AMap) {
      throw new Error('[AMapSDKEngine] AMap is not available');
    }

    // 注意：坐标已经由调用方转换为 GCJ-02，直接使用
    // 高德地图使用 [lng, lat] 格式
    const marker = new AMap.Marker({
      position: [lng, lat],
      draggable: options?.draggable ?? true,
      title: options?.title
    });

    this.map.add(marker);

    // 拖拽事件
    if (options?.draggable !== false) {
      marker.on('dragend', (e: any) => {
        const position = marker.getPosition();
        // GCJ-02 转 WGS84（返回给调用方）
        const wgs84Coord = convertCoordinate(position.lat, position.lng, 'gcj02', 'wgs84');
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
      this.map.remove(marker);
      this.markers.delete(markerId);
    }
  }

  updateMarkerPosition(markerId: any, lat: number, lng: number): void {
    const marker = this.markers.get(markerId);
    if (marker) {
      // 注意：坐标已经由调用方转换为 GCJ-02，直接使用
      // 高德地图使用 [lng, lat] 格式
      marker.setPosition([lng, lat]);
    }
  }

  destroy(): void {
    this.markers.forEach(marker => {
      if (this.map) {
        this.map.remove(marker);
      }
    });
    this.markers.clear();

    if (this.map) {
      this.map.destroy();
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
      this.map.on('click', (e: any) => {
        const wgs84Coord = convertCoordinate(e.lnglat.lat, e.lnglat.lng, 'gcj02', 'wgs84');
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

  // 等待 AMap 全局对象就绪
  private waitForAMap(): Promise<void> {
    return new Promise((resolve) => {
      const check = () => {
        if (window.AMap) {
          resolve();
        } else {
          setTimeout(check, 50);
        }
      };
      check();
    });
  }
}
