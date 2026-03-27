/**
 * 地图引擎管理器
 * 负责加载和管理各种地图引擎
 */

import type { MapEngine, MapEngineType, MapOptions, MapConfig } from './mapTypes';
import { defaultMapConfig } from './mapTypes';

class MapEngineManager {
  private engines: Map<MapEngineType, () => Promise<MapEngine>> = new Map();
  private currentEngine: MapEngine | null = null;
  private currentType: MapEngineType | null = null;
  private config: MapConfig = defaultMapConfig;

  constructor() {
    this.registerEngines();
  }

  // 注册地图引擎
  private registerEngines() {
    this.engines.set('osm', async () => {
      const { OSMEngine } = await import('./map/engines/OSMEngine');
      return new OSMEngine(this.config);
    });

    this.engines.set('amap', async () => {
      const { AMapEngine } = await import('./map/engines/AMapEngine');
      return new AMapEngine(this.config);
    });

    this.engines.set('baidu', async () => {
      const { BaiduMapEngine } = await import('./map/engines/BaiduMapEngine');
      return new BaiduMapEngine(this.config);
    });

    this.engines.set('tencent', async () => {
      const { TencentMapEngine } = await import('./map/engines/TencentMapEngine');
      return new TencentMapEngine(this.config);
    });

    this.engines.set('tianditu', async () => {
      const { TiandituEngine } = await import('./map/engines/TiandituEngine');
      return new TiandituEngine(this.config);
    });
  }

  // 设置配置
  setConfig(config: MapConfig) {
    this.config = config;
  }

  // 加载地图引擎
  async loadEngine(type: MapEngineType, container: HTMLElement, options: MapOptions): Promise<MapEngine> {
    // 如果已经加载了相同的引擎，直接返回
    if (this.currentType === type && this.currentEngine) {
      return this.currentEngine;
    }

    // 销毁之前的引擎
    if (this.currentEngine) {
      this.currentEngine.destroy();
      this.currentEngine = null;
    }

    // 加载新的引擎
    const loader = this.engines.get(type);
    if (!loader) {
      throw new Error(`Map engine ${type} not found`);
    }

    this.currentEngine = await loader();
    this.currentType = type;

    // 初始化地图
    this.currentEngine.init(container, options);

    return this.currentEngine;
  }

  // 获取当前引擎
  getCurrentEngine(): MapEngine | null {
    return this.currentEngine;
  }

  // 获取当前引擎类型
  getCurrentType(): MapEngineType | null {
    return this.currentType;
  }

  // 切换引擎
  async switchEngine(type: MapEngineType, container: HTMLElement, options: MapOptions): Promise<MapEngine> {
    return this.loadEngine(type, container, options);
  }

  // 销毁当前引擎
  destroy() {
    if (this.currentEngine) {
      this.currentEngine.destroy();
      this.currentEngine = null;
      this.currentType = null;
    }
  }

  // 检查是否有可用的引擎
  hasEngine(type: MapEngineType): boolean {
    return this.engines.has(type);
  }

  // 获取所有可用的引擎
  getAvailableEngines(): MapEngineType[] {
    return Array.from(this.engines.keys());
  }
}

// 导出单例
export const mapEngineManager = new MapEngineManager();