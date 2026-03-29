/**
 * 地图相关类型定义
 */

// 地图引擎类型
export type MapEngineType = 'amap' | 'baidu' | 'tencent' | 'tianditu' | 'osm';

// 地图配置
export interface MapConfig {
  // 可显示的地图列表
  availableMaps: MapEngineType[];
  // 默认地图
  defaultMap: MapEngineType;
  // 地图 API Keys
  mapApiKeys: {
    amap?: string;
    baidu?: string;
    tencent?: string;
    tianditu?: {
      token: string;
      type: 'vec' | 'img';
    };
  };
  // 反向地理编码配置
  geocoding: {
    enabledService: 'amap' | 'baidu' | 'tencent' | 'nominatim';
    apiKeys: {
      amap?: string;
      baidu?: string;
      tencent?: string;
    };
    nominatimUrl: string;
  };
}

// 用户地图偏好
export interface UserMapPreference {
  currentMap: MapEngineType;
  configs: {
    [key: string]: {
      zoom?: number;
      center?: [number, number];
    };
  };
  lastUpdated: string;
}

// 坐标
export interface Coordinate {
  lat: number;
  lng: number;
}

// 搜索结果
export interface SearchResult {
  address: string;
  lat: number;
  lng: number;
  name?: string;
}

// 地图引擎选项
export interface MapOptions {
  center?: [number, number];
  zoom?: number;
  enableDrag?: boolean;
  enableClick?: boolean;
}

// 标记选项
export interface MarkerOptions {
  draggable?: boolean;
  icon?: any;
}

// 地图引擎接口
export interface MapEngine {
  name: string;
  displayName: string;

  // 初始化地图
  init(container: HTMLElement, options: MapOptions): void;

  // 设置中心点
  setCenter(lat: number, lng: number): void;

  // 设置缩放级别
  setZoom(zoom: number): void;

  // 添加标记
  addMarker(lat: number, lng: number, options?: MarkerOptions): any;

  // 移除标记
  removeMarker(marker: any): void;

  // 更新标记位置
  updateMarkerPosition(marker: any, lat: number, lng: number): void;

  // 地址搜索（反向地理编码）
  searchAddress(query: string): Promise<SearchResult[]>;

  // 地址解析（地理编码）
  geocode(address: string): Promise<SearchResult>;

  // 销毁
  destroy(): void;

  // 获取地图实例
  getMap(): any;

  // 绑定事件
  on(event: string, handler: any): void;

  // 解绑事件
  off(event: string, handler: any): void;
}

// 默认配置
export const defaultMapConfig: MapConfig = {
  availableMaps: ['amap', 'baidu', 'tencent', 'tianditu', 'osm'],
  defaultMap: 'amap',
  mapApiKeys: {},
  geocoding: {
    enabledService: 'amap',
    apiKeys: {},
    nominatimUrl: ''
  }
};

// 地图显示名称
export const mapEngineNames: Record<MapEngineType, string> = {
  amap: '高德地图',
  baidu: '百度地图',
  tencent: '腾讯地图',
  tianditu: '天地图',
  osm: 'OpenStreetMap'
};