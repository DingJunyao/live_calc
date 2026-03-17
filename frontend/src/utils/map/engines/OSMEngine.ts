/**
 * OpenStreetMap 地图引擎
 * 使用 Leaflet 原生 OSM 瓦片，无需 API Key
 */

import type { MapEngine, MapEngineType, MapOptions, MarkerOptions, SearchResult, MapConfig } from '../mapTypes';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export class OSMEngine implements MapEngine {
  name: MapEngineType = 'osm';
  displayName: string = 'OpenStreetMap';

  private map: L.Map | null = null;
  private markers: Map<any, L.Marker> = new Map();
  private config: MapConfig;
  private eventHandlers: Map<string, Set<Function>> = new Map();

  constructor(config: MapConfig) {
    this.config = config;
  }

  init(container: HTMLElement, options: MapOptions): void {
    // 如果已经初始化，先销毁
    if (this.map) {
      this.destroy();
    }

    // 设置视图中心
    const center = options.center || [39.9042, 116.4074]; // 默认北京
    const zoom = options.zoom || 13;

    // 创建地图
    this.map = L.map(container, {
      center: center,
      zoom: zoom,
      zoomControl: true
    });

    // 添加 OpenStreetMap 瓦片
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(this.map);

    // 绑定点击事件
    if (options.enableClick !== false) {
      this.map.on('click', (e: L.LeafletMouseEvent) => {
        this.emit('click', {
          lat: e.latlng.lat,
          lng: e.latlng.lng
        });
      });
    }
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

  addMarker(lat: number, lng: number, options?: MarkerOptions): L.Marker {
    if (!this.map) {
      throw new Error('Map not initialized');
    }

    const marker = L.marker([lat, lng], {
      draggable: options?.draggable ?? true
    }).addTo(this.map);

    // 绑定拖拽事件
    if (options?.draggable !== false) {
      marker.on('dragend', (e: L.LeafletEvent) => {
        const position = marker.getLatLng();
        this.emit('markerDragend', {
          lat: position.lat,
          lng: position.lng
        });
      });
    }

    const markerId = Symbol('marker');
    this.markers.set(markerId, marker);
    return markerId as any;
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
    // OpenStreetMap 没有官方的反向地理编码服务
    // 使用 Nominatim 进行地址搜索
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5`;
      const response = await fetch(url);
      const data = await response.json();

      return data.map((item: any) => ({
        address: item.display_name,
        lat: parseFloat(item.lat),
        lng: parseFloat(item.lon),
        name: item.name
      }));
    } catch (error) {
      console.error('OSM search error:', error);
      return [];
    }
  }

  async geocode(address: string): Promise<SearchResult> {
    const results = await this.searchAddress(address);
    if (results.length > 0) {
      return results[0];
    }
    throw new Error('Address not found');
  }

  destroy(): void {
    // 移除所有标记
    this.markers.forEach(marker => marker.remove());
    this.markers.clear();

    // 销毁地图
    if (this.map) {
      this.map.remove();
      this.map = null;
    }

    // 清除事件处理器
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

    // 绑定到地图事件
    if (this.map) {
      if (event === 'click') {
        this.map.on('click', (e: L.LeafletMouseEvent) => {
          handler({ lat: e.latlng.lat, lng: e.latlng.lng });
        });
      } else if (event === 'markerDragend') {
        // 标记拖拽事件由 addMarker 单独处理
      }
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