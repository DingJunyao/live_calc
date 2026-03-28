/**
 * 地图引擎管理器
 * 负责加载和管理各种地图引擎
 * 支持创建多个独立的地图引擎实例
 */

import type { MapEngine, MapEngineType, MapOptions, MapConfig } from './map/mapTypes';
import { defaultMapConfig } from './map/mapTypes';

class MapEngineManager {
  private engineLoaders: Map<MapEngineType, (config: MapConfig) => Promise<MapEngine>> = new Map();
  private config: MapConfig = defaultMapConfig;

  constructor() {
    this.registerEngineLoaders();
  }

  // 注册地图引擎加载器（工厂函数）
  private registerEngineLoaders() {
    // Leaflet 版本引擎
    this.engineLoaders.set('osm', async (config: MapConfig) => {
      const { OSMEngine } = await import('./map/engines/OSMEngine');
      return new OSMEngine(config);
    });

    this.engineLoaders.set('amap', async (config: MapConfig) => {
      const { AMapEngine } = await import('./map/engines/AMapEngine');
      return new AMapEngine(config);
    });

    this.engineLoaders.set('baidu', async (config: MapConfig) => {
      const { BaiduMapEngine } = await import('./map/engines/BaiduMapEngine');
      return new BaiduMapEngine(config);
    });

    this.engineLoaders.set('tencent', async (config: MapConfig) => {
      const { TencentMapEngine } = await import('./map/engines/TencentMapEngine');
      return new TencentMapEngine(config);
    });

    this.engineLoaders.set('tianditu', async (config: MapConfig) => {
      const { TiandituEngine } = await import('./map/engines/TiandituEngine');
      return new TiandituEngine(config);
    });

    // SDK 版本引擎
    this.engineLoaders.set('amap-sdk', async (config: MapConfig) => {
      const { AMapSDKEngine } = await import('./map/engines/AMapSDKEngine');
      return new AMapSDKEngine(config);
    });

    this.engineLoaders.set('baidu-sdk', async (config: MapConfig) => {
      const { BaiduSDKEngine } = await import('./map/engines/BaiduSDKEngine');
      return new BaiduSDKEngine(config);
    });

    this.engineLoaders.set('tencent-sdk', async (config: MapConfig) => {
      const { TencentSDKEngine } = await import('./map/engines/TencentSDKEngine');
      return new TencentSDKEngine(config);
    });
  }

  // 设置全局配置
  setConfig(config: MapConfig) {
    this.config = config;
  }

  // 获取当前配置
  getConfig(): MapConfig {
    return this.config;
  }

  // 创建新的地图引擎实例（每个组件可以创建自己的实例）
  async createEngine(type: MapEngineType, container: HTMLElement, options: MapOptions): Promise<MapEngine> {
    // 智能选择：如果配置了 API Key 且支持 SDK，则使用 SDK 版本
    const engineType = this.shouldUseSDK(type) ? `${type}-sdk` as MapEngineType : type;

    const loader = this.engineLoaders.get(engineType);
    if (!loader) {
      throw new Error(`Map engine ${engineType} not found`);
    }

    try {
      // 创建新的引擎实例
      const engine = await loader(this.config);

      // 初始化地图
      await engine.init(container, options);

      return engine;
    } catch (error) {
      // SDK 加载失败时，自动降级到 Leaflet 版本
      if (engineType.endsWith('-sdk')) {
        console.warn(`[MapEngineManager] SDK engine ${engineType} failed, fallback to Leaflet version:`, error);
        return this.createEngine(type, container, options);
      }
      throw error;
    }
  }

  // 判断是否应该使用 SDK
  private shouldUseSDK(type: MapEngineType): boolean {
    const keys = this.config.mapApiKeys;
    switch (type) {
      case 'amap':
        // 高德地图：只要有 API Key 就使用 SDK
        return !!keys.amap;
      case 'baidu':
        return !!keys.baidu;
      case 'tencent':
        return !!keys.tencent;
      case 'tianditu':
        // 天地图没有 SDK 版本，始终返回 false
        return false;
      case 'osm':
        return false;
      default:
        return false;
    }
  }

  // 检查是否有可用的引擎
  hasEngine(type: MapEngineType): boolean {
    return this.engineLoaders.has(type);
  }

  // 获取所有可用的引擎
  getAvailableEngines(): MapEngineType[] {
    return Array.from(this.engineLoaders.keys());
  }
}

// 导出单例（用于配置管理和引擎创建）
export const mapEngineManager = new MapEngineManager();
