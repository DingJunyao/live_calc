/**
 * 腾讯地图 SDK 引擎
 * 使用腾讯地图原生 JavaScript API v4.0 (GL)
 */

import type { MapEngine, MarkerOptions, MapConfig } from '../../map/mapTypes';
import { convertCoordinate } from '../../coordinateTransform';
import { sdkLoader } from '../../SDKLoader';

declare global {
  interface Window {
    TMap?: any;
  }
}

export class TencentSDKEngine implements MapEngine {
  name = 'tencent-sdk' as const;
  displayName = '腾讯地图 (SDK)';

  private map: any = null;
  private markers: Map<any, any> = new Map();
  private geometries: any[] = []; // 腾讯地图标记的几何对象
  private config: MapConfig;
  private eventHandlers: Map<string, Set<Function>> = new Map();

  constructor(config: MapConfig) {
    this.config = config;
  }

  async init(container: HTMLElement, options: any): Promise<void> {
    const center = options.center || [39.9042, 116.4074];
    const zoom = options.zoom || 13;

    // 加载 SDK
    const apiKey = this.config.mapApiKeys.tencent;
    if (!apiKey) {
      throw new Error('[TencentSDKEngine] API Key is required');
    }

    try {
      // 使用腾讯地图推荐版本：1.exp（最新版）或 1.3（稳定版）
      await sdkLoader.loadTencentMap(apiKey, '1.exp');
    } catch (error) {
      console.error('[TencentSDKEngine] Failed to load SDK:', error);
      throw error;
    }

    // 等待 TMap 全局对象就绪
    await this.waitForTMap();

    const TMap = window.TMap;
    if (!TMap) {
      throw new Error('[TencentSDKEngine] TMap is not available');
    }

    // 调试：检查容器状态
    console.log('[TencentSDKEngine] Container info:', {
      element: container,
      className: container.className,
      display: window.getComputedStyle(container).display,
      visibility: window.getComputedStyle(container).visibility,
      width: container.offsetWidth,
      height: container.offsetHeight,
      clientWidth: container.clientWidth,
      clientHeight: container.clientHeight,
      parentElement: container.parentElement
    });

    // 如果容器不可见，先让它可见
    const computedStyle = window.getComputedStyle(container);
    if (computedStyle.display === 'none' || computedStyle.visibility === 'hidden') {
      console.log('[TencentSDKEngine] Container is hidden, making it visible');
      container.style.display = 'block';
      container.style.visibility = 'visible';
    }

    // 确保容器有最小尺寸（腾讯地图必需）
    if (container.offsetWidth === 0 || container.offsetHeight === 0) {
      console.log('[TencentSDKEngine] Container has no size, setting minimum dimensions');
      // 直接设置具体的像素值，而不是百分比
      const parentRect = container.parentElement?.getBoundingClientRect();
      const width = parentRect?.width || container.parentElement?.clientWidth || 800;
      const height = parentRect?.height || container.parentElement?.clientHeight || 600;

      container.style.width = `${width}px`;
      container.style.height = `${height}px`;
      container.style.minWidth = `${width}px`;
      container.style.minHeight = `${height}px`;
      container.style.position = 'relative';
      container.style.zIndex = '1';

      console.log('[TencentSDKEngine] Container size set to:', { width, height });
    }

    // WGS84 转 GCJ-02（腾讯使用 GCJ-02）
    // 注意：center 格式为 [lat, lng]
    const gcj02Coord = convertCoordinate(center[0], center[1], 'wgs84', 'gcj02');

    console.log('[TencentSDKEngine] Coordinate conversion:', {
      original: center,
      gcj02: gcj02Coord
    });

    // 验证坐标值的有效性
    if (!gcj02Coord ||
        !Number.isFinite(gcj02Coord.lat) ||
        !Number.isFinite(gcj02Coord.lng)) {
      throw new Error(`[TencentSDKEngine] Invalid coordinates after conversion: ${JSON.stringify(gcj02Coord)}`);
    }

    // 确保坐标在有效范围内
    const lat = Math.max(-90, Math.min(90, gcj02Coord.lat));
    const lng = Math.max(-180, Math.min(180, gcj02Coord.lng));

    console.log('[TencentSDKEngine] Validated coordinates:', { lat, lng });

    // 创建地图实例
    try {
      // 腾讯地图必需参数：
      // - center: 地图中心点（TMap.LatLng 对象）
      // - zoom: 地图缩放级别（3-20）
      // - viewMode: 地图展示模式（'2D' 或 '3D'）
      const mapOptions = {
        center: new TMap.LatLng(lat, lng),
        zoom: Math.min(Math.max(zoom, 3), 20), // 确保缩放级别在有效范围内
        viewMode: '2D' as const
        // 注意：不需要设置 mapTypeId，默认就是标准道路地图
      };

      console.log('[TencentSDKEngine] Map options:', mapOptions);
      console.log('[TencentSDKEngine] TMap.LatLng:', mapOptions.center);

      this.map = new TMap.Map(container, mapOptions);

      console.log('[TencentSDKEngine] Map created successfully');
    } catch (error) {
      console.error('[TencentSDKEngine] Failed to create map:', error);
      throw error;
    }

    // 添加点击事件
    if (options.enableClick !== false) {
      this.map.on('click', (e: any) => {
        // 腾讯地图点击事件返回的坐标格式为 e.latLng
        const latLng = e.latLng;
        if (latLng && typeof latLng.lat === 'function' && typeof latLng.lng === 'function') {
          // GCJ-02 转 WGS84
          const wgs84Coord = convertCoordinate(latLng.lat(), latLng.lng(), 'gcj02', 'wgs84');
          this.emit('click', {
            lat: wgs84Coord.lat,
            lng: wgs84Coord.lng
          });
        }
      });
    }

    // 延迟更新地图尺寸（确保容器已渲染）
    setTimeout(() => {
      if (this.map && this.map.refresh) {
        try {
          this.map.refresh();
        } catch (e) {
          // 忽略错误
        }
      }
    }, 300);
  }

  setCenter(lat: number, lng: number): void {
    if (this.map) {
      const TMap = window.TMap;
      if (!TMap) return;

      // 注意：坐标已经由调用方转换为 GCJ-02，直接使用
      const latLng = new TMap.LatLng(lat, lng);
      this.map.setCenter(latLng);
    }
  }

  setZoom(zoom: number): void {
    if (this.map) {
      this.map.setZoom(zoom);
    }
  }

  addMarker(lat: number, lng: number, options?: MarkerOptions): any {
    if (!this.map) {
      throw new Error('[TencentSDKEngine] Map not initialized');
    }

    const TMap = window.TMap;
    if (!TMap) {
      throw new Error('[TencentSDKEngine] TMap is not available');
    }

    // 注意：坐标已经由调用方转换为 GCJ-02，直接使用
    console.log('[TencentSDKEngine] Adding marker at:', { lat, lng });
    console.log('[TencentSDKEngine] TMap.Marker:', TMap.Marker);
    console.log('[TencentSDKEngine] TMap.MultiMarker:', TMap.MultiMarker);

    // 腾讯地图可能使用 MultiMarker
    let marker: any;

    if (TMap.MultiMarker) {
      // 使用 MultiMarker API
      marker = new TMap.MultiMarker({
        map: this.map,
        geometries: [
          {
            id: 'marker-' + Date.now(),
            position: new TMap.LatLng(lat, lng)
          }
        ]
      });
    } else if (TMap.Marker) {
      // 使用 Marker API
      marker = new TMap.Marker({
        map: this.map,
        position: new TMap.LatLng(lat, lng),
        draggable: options?.draggable ?? true
      });
    } else {
      throw new Error('[TencentSDKEngine] No marker API available');
    }

    // 拖拽支持
    if (options?.draggable !== false && marker.on) {
      marker.on('dragend', (e: any) => {
        const position = marker.getPosition();
        // 腾讯地图的 position 可能是 TMap.LatLng 对象或普通对象
        const lat = typeof position.lat === 'function' ? position.lat() : position.lat;
        const lng = typeof position.lng === 'function' ? position.lng() : position.lng;
        // GCJ-02 转 WGS84（返回给调用方）
        const wgs84Coord = convertCoordinate(lat, lng, 'gcj02', 'wgs84');
        this.emit('markerDragend', {
          lat: wgs84Coord.lat,
          lng: wgs84Coord.lng
        });
      });
    }

    // 存储标记
    const markerId = Symbol('marker');
    this.markers.set(markerId, marker);

    console.log('[TencentSDKEngine] Marker added successfully');

    return markerId;
  }

  removeMarker(markerId: any): void {
    const marker = this.markers.get(markerId);
    if (marker) {
      marker.setMap(null);
      this.markers.delete(markerId);
    }
  }

  updateMarkerPosition(markerId: any, lat: number, lng: number): void {
    const marker = this.markers.get(markerId);
    if (marker) {
      const TMap = window.TMap;
      if (!TMap) return;

      // 注意：坐标已经由调用方转换为 GCJ-02，直接使用
      marker.setPosition(new TMap.LatLng(lat, lng));
    }
  }

  destroy(): void {
    this.markers.forEach(marker => {
      if (marker) {
        marker.setMap(null);
      }
    });
    this.markers.clear();
    this.geometries = [];

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
        // 腾讯地图点击事件返回的坐标格式为 e.latLng
        const latLng = e.latLng;
        if (latLng && typeof latLng.lat === 'function' && typeof latLng.lng === 'function') {
          // GCJ-02 转 WGS84
          const wgs84Coord = convertCoordinate(latLng.lat(), latLng.lng(), 'gcj02', 'wgs84');
          handler({ lat: wgs84Coord.lat, lng: wgs84Coord.lng });
        }
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

  // 等待 TMap 全局对象就绪
  private waitForTMap(): Promise<void> {
    return new Promise((resolve) => {
      const check = () => {
        if (window.TMap) {
          resolve();
        } else {
          setTimeout(check, 50);
        }
      };
      check();
    });
  }

  // 等待容器有有效尺寸
  private waitForContainerSize(container: HTMLElement): Promise<void> {
    return new Promise((resolve, reject) => {
      const maxRetries = 20; // 最多等待 2 秒
      let retries = 0;

      const check = () => {
        const width = container.offsetWidth || container.clientWidth;
        const height = container.offsetHeight || container.clientHeight;

        if (width > 0 && height > 0) {
          console.log(`[TencentSDKEngine] Container size available after ${retries * 100}ms:`, { width, height });
          resolve();
        } else if (retries < maxRetries) {
          retries++;
          console.log(`[TencentSDKEngine] Container has no size, waiting... (${retries}/${maxRetries})`);
          setTimeout(check, 100);
        } else {
          // 超时后，强制设置容器尺寸
          console.warn('[TencentSDKEngine] Container still has no size after 2s, forcing minimum size');
          container.style.minWidth = '100%';
          container.style.minHeight = '400px';
          container.style.width = '100%';
          container.style.height = '400px';

          // 再检查一次
          const finalWidth = container.offsetWidth || container.clientWidth;
          const finalHeight = container.offsetHeight || container.clientHeight;

          if (finalWidth > 0 && finalHeight > 0) {
            console.log('[TencentSDKEngine] Container size forced successfully:', { width: finalWidth, height: finalHeight });
            resolve();
          } else {
            reject(new Error(`[TencentSDKEngine] Container has no valid size after forcing: ${finalWidth}x${finalHeight}`));
          }
        }
      };

      check();
    });
  }
}
