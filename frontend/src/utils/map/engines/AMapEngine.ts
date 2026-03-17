/**
 * 高德地图引擎
 * 使用 leaflet.chinaProvider 加载瓦片
 */

import type { MapEngine, MapEngineType, MapOptions, MarkerOptions, SearchResult, MapConfig } from '../mapTypes';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.chinatmsproviders';

export class AMapEngine implements MapEngine {
  name: MapEngineType = 'amap';
  displayName: string = '高德地图';

  private map: L.Map | null = null;
  private markers: Map<any, L.Marker> = new Map();
  private config: MapConfig;
  private eventHandlers: Map<string, Set<Function>> = new Map();

  constructor(config: MapConfig) {
    this.config = config;
  }

  init(container: HTMLElement, options: MapOptions): void {
    if (this.map) {
      this.destroy();
    }

    const center = options.center || [39.9042, 116.4074];
    const zoom = options.zoom || 13;

    this.map = L.map(container, {
      center: center,
      zoom: zoom,
      zoomControl: true
    });

    // 使用 chinaProvider 加载高德瓦片
    const gaodeLayer = L.tileLayer.chinaProvider('GaoDe.Normal.Map', {
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
    const apiKey = this.config.mapApiKeys?.amap;
    const useApi = !!apiKey;

    if (useApi) {
      try {
        const url = `https://restapi.amap.com/v3/place/text?keywords=${encodeURIComponent(query)}&city=全国&output=json&key=${apiKey}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.pois && data.pois.length > 0) {
          return data.pois.slice(0, 5).map((poi: any) => ({
            address: poi.address || poi.name,
            lat: parseFloat(poi.location.split(',')[1]),
            lng: parseFloat(poi.location.split(',')[0]),
            name: poi.name
          }));
        }
      } catch (error) {
        console.error('AMap geocoding error:', error);
      }
    }

    return this.fallbackSearch(query);
  }

  private async fallbackSearch(query: string): Promise<SearchResult[]> {
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
      console.error('Fallback search error:', error);
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

    if (this.map) {
      if (event === 'click') {
        this.map.on('click', (e: L.LeafletMouseEvent) => {
          handler({ lat: e.latlng.lat, lng: e.latlng.lng });
        });
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
      handlers.forEach(h => h(data));
    }
  }
}