/**
 * 百度地图引擎（基于 Leaflet）
 * TODO: 后续添加 SDK 支持
 */

import type { MapEngine, MarkerOptions, SearchResult, MapConfig } from '../../map/mapTypes';
import L from 'leaflet';
import 'leaflet.chinatmsproviders';

export class BaiduMapEngine implements MapEngine {
  name = 'baidu' as const;
  displayName = '百度地图';

  private map: L.Map | null = null;
  private markers: Map<any, L.Marker> = new Map();
  private config: MapConfig;
  private eventHandlers: Map<string, Set<Function>> = new Map();

  constructor(config: MapConfig) {
    this.config = config;
  }

  init(container: HTMLElement, options: any): void {
    const center = options.center || [39.9042, 116.4074];
    const zoom = options.zoom || 13;

    // 检查 Baidu CRS 是否可用
    const baiduCrs = (L as any).CRS.Baidu;
    if (!baiduCrs) {
      console.error('[BaiduMapEngine] Baidu CRS not available');
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: red;">百度地图加载失败，请刷新页面重试</div>';
      return;
    }

    // 百度地图需要使用 Baidu CRS
    this.map = L.map(container, {
      center: center,
      zoom: zoom,
      zoomControl: true,
      crs: baiduCrs
    });

    // 使用百度地图图层
    // @ts-ignore
    L.tileLayer.chinaProvider('Baidu.Normal.Map', {
      maxZoom: 18,
      minZoom: 5
    }).addTo(this.map);

    if (options.enableClick !== false) {
      this.map.on('click', (e: L.LeafletMouseEvent) => {
        this.emit('click', {
          lat: e.latlng.lat,
          lng: e.latlng.lng
        });
      });
    }

    // 延迟调用 invalidateSize 以确保容器尺寸正确
    setTimeout(() => {
      if (this.map) {
        this.map.invalidateSize();
      }
    }, 100);
  }

  setCenter(lat: number, lng: number): void {
    if (this.map) {
      this.map.setView([lat, lng], this.map.getZoom());
    }
  }

  setZoom(zoom: number): void {
    if (this.map) {
      this.map.setZoom(zoom);
    }
  }

  addMarker(lat: number, lng: number, options?: MarkerOptions): any {
    if (!this.map) {
      throw new Error('Map not initialized');
    }

    const marker = L.marker([lat, lng], {
      draggable: options?.draggable ?? true
    }).addTo(this.map);

    if (options?.draggable !== false) {
      marker.on('dragend', () => {
        const position = marker.getLatLng();
        this.emit('markerDragend', {
          lat: position.lat,
          lng: position.lng
        });
      });
    }

    const markerId = Symbol('marker');
    this.markers.set(markerId, marker);
    return markerId;
  }

  removeMarker(markerId: any): void {
    const marker = this.markers.get(markerId);
    if (marker) {
      marker.remove();
      this.markers.delete(markerId);
    }
  }

  updateMarkerPosition(markerId: any, lat: number, lng: number): void {
    const marker = this.markers.get(markerId);
    if (marker) {
      marker.setLatLng([lat, lng]);
    }
  }

  async searchAddress(query: string): Promise<SearchResult[]> {
    // TODO: 实现百度地图 API 搜索
    console.warn('BaiduMap searchAddress not implemented');
    return [];
  }

  destroy(): void {
    this.markers.forEach(marker => marker.remove());
    this.markers.clear();

    if (this.map) {
      this.map.remove();
      this.map = null;
    }

    this.eventHandlers.clear();
  }

  getMap(): L.Map | null {
    return this.map;
  }

  on(event: string, handler: Function): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    if (this.map && event === 'click') {
      this.map.on('click', (e: L.LeafletMouseEvent) => {
        handler({ lat: e.latlng.lat, lng: e.latlng.lng });
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
}
