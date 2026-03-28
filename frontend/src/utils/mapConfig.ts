/**
 * 地图配置和用户偏好管理工具
 */

import type { MapConfig, UserMapPreference, MapEngineType } from './map/mapTypes';
import { defaultMapConfig } from './map/mapTypes';

const STORAGE_KEY = 'livecalc:mapPreference';

// 获取用户偏好
export function getUserMapPreference(): UserMapPreference | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Failed to get map preference:', error);
  }
  return null;
}

// 保存用户偏好
export function saveUserMapPreference(preference: UserMapPreference): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      ...preference,
      lastUpdated: new Date().toISOString()
    }));
  } catch (error) {
    console.error('Failed to save map preference:', error);
  }
}

// 更新当前地图
export function updateCurrentMap(mapEngine: MapEngineType): void {
  const preference = getUserMapPreference() || {
    currentMap: mapEngine,
    configs: {},
    lastUpdated: new Date().toISOString()
  };

  if (!preference.configs[mapEngine]) {
    preference.configs[mapEngine] = {};
  }

  preference.currentMap = mapEngine;
  saveUserMapPreference(preference);
}

// 更新特定地图的配置
export function updateMapConfig(mapEngine: MapEngineType, config: Partial<UserMapPreference['configs'][string]>): void {
  const preference = getUserMapPreference() || {
    currentMap: mapEngine,
    configs: {},
    lastUpdated: new Date().toISOString()
  };

  if (!preference.configs[mapEngine]) {
    preference.configs[mapEngine] = {};
  }

  preference.configs[mapEngine] = {
    ...preference.configs[mapEngine],
    ...config
  };

  saveUserMapPreference(preference);
}

// 获取当前地图引擎
export function getCurrentMapEngine(availableMaps: MapEngineType[], defaultMap: MapEngineType): MapEngineType {
  const preference = getUserMapPreference();

  if (preference && preference.currentMap && availableMaps.includes(preference.currentMap)) {
    return preference.currentMap;
  }

  return defaultMap;
}

// 清除用户偏好
export function clearUserMapPreference(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear map preference:', error);
  }
}
