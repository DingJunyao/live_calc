/**
 * 地图引擎 Composable
 *
 * 封装地图初始化、标记管理等核心逻辑
 */

import { ref, onUnmounted } from 'vue'
import type { Ref } from 'vue'
import type {
  LatLng,
  MapEngine,
  MapInstance,
  MapOptions,
  Marker,
  MarkerOptions
} from '@/types/map'
import { MapAdapterFactory } from '@/utils/mapAdapters'

/**
 * 地图引擎 composable 返回值
 */
export interface UseMapEngineReturn {
  // 状态
  mapInstance: Ref<MapInstance | null>
  currentEngine: Ref<MapEngine>
  isLoading: Ref<boolean>
  error: Ref<string | null>
  markers: Ref<Map<number, Marker>>

  // 方法
  initMap: (container: HTMLElement, options?: Partial<MapOptions>) => Promise<void>
  addMarker: (position: LatLng, options?: MarkerOptions) => Marker | null
  removeMarker: (marker: Marker) => void
  highlightMarker: (marker: Marker, highlighted: boolean) => void
  setCenter: (position: LatLng) => void
  setZoom: (level: number) => void
  clearMarkers: () => void
  destroyMap: () => void
}

/**
 * 地图引擎 composable
 *
 * @param engine - 地图引擎类型
 * @param apiKey - API 密钥（可选）
 * @returns 地图引擎控制对象
 */
export function useMapEngine(engine: MapEngine = 'osm', apiKey?: string): UseMapEngineReturn {
  // 状态
  const mapInstance = ref<MapInstance | null>(null)
  const currentEngine = ref<MapEngine>(engine)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)
  const markers = ref<Map<number, Marker>>(new Map())

  // 适配器实例
  let adapter: ReturnType<typeof MapAdapterFactory.create> | null = null

  /**
   * 初始化地图
   */
  const initMap = async (container: HTMLElement, options?: Partial<MapOptions>) => {
    if (!container) {
      error.value = '地图容器不存在'
      return
    }

    isLoading.value = true
    error.value = null

    try {
      // 创建适配器
      adapter = MapAdapterFactory.create(currentEngine.value, apiKey)

      // 合并选项
      const mapOptions: MapOptions = {
        engine: currentEngine.value,
        apiKey,
        ...options
      }

      // 初始化地图
      const map = await adapter.init(container, mapOptions)
      mapInstance.value = map

      // 保存适配器引用到 map 实例（用于后续操作）
      ;(map as any)._adapter = adapter
    } catch (err) {
      console.error('地图初始化失败:', err)
      error.value = '地图加载失败，请检查网络或刷新页面重试'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 添加标记
   */
  const addMarker = (position: LatLng, options?: MarkerOptions): Marker | null => {
    if (!mapInstance.value || !adapter) {
      console.warn('地图未初始化，无法添加标记')
      return null
    }

    try {
      const marker = adapter.addMarker(mapInstance.value, position, options)

      // 如果有 merchantId，保存到 markers Map
      if (options?.merchantId !== undefined) {
        markers.value.set(options.merchantId, marker)
      }

      return marker
    } catch (err) {
      console.error('添加标记失败:', err)
      return null
    }
  }

  /**
   * 移除标记
   */
  const removeMarker = (marker: Marker) => {
    if (!adapter) return

    try {
      adapter.removeMarker(marker)

      // 从 markers Map 中移除
      for (const [id, m] of markers.value.entries()) {
        if (m === marker) {
          markers.value.delete(id)
          break
        }
      }
    } catch (err) {
      console.error('移除标记失败:', err)
    }
  }

  /**
   * 高亮标记
   */
  const highlightMarker = (marker: Marker, highlighted: boolean) => {
    if (!adapter) return

    try {
      adapter.highlightMarker(marker, highlighted)
    } catch (err) {
      console.error('高亮标记失败:', err)
    }
  }

  /**
   * 根据 merchantId 高亮标记
   */
  const highlightMerchantMarker = (merchantId: number, highlighted: boolean) => {
    const marker = markers.value.get(merchantId)
    if (marker) {
      highlightMarker(marker, highlighted)
    }
  }

  /**
   * 设置地图中心
   */
  const setCenter = (position: LatLng) => {
    if (!mapInstance.value || !adapter) return

    try {
      adapter.setCenter(mapInstance.value, position)
    } catch (err) {
      console.error('设置地图中心失败:', err)
    }
  }

  /**
   * 设置缩放级别
   */
  const setZoom = (level: number) => {
    if (!mapInstance.value || !adapter) return

    try {
      adapter.setZoom(mapInstance.value, level)
    } catch (err) {
      console.error('设置缩放级别失败:', err)
    }
  }

  /**
   * 清除所有标记
   */
  const clearMarkers = () => {
    if (!adapter) return

    try {
      markers.value.forEach((marker) => {
        adapter!.removeMarker(marker)
      })
      markers.value.clear()
    } catch (err) {
      console.error('清除标记失败:', err)
    }
  }

  /**
   * 销毁地图
   */
  const destroyMap = () => {
    if (!mapInstance.value || !adapter) return

    try {
      // 清除所有标记
      clearMarkers()

      // 销毁地图
      adapter.destroy(mapInstance.value)

      // 清理引用
      mapInstance.value = null
      adapter = null
    } catch (err) {
      console.error('销毁地图失败:', err)
    }
  }

  // 组件卸载时自动销毁地图
  onUnmounted(() => {
    destroyMap()
  })

  return {
    mapInstance,
    currentEngine,
    isLoading,
    error,
    markers,
    initMap,
    addMarker,
    removeMarker,
    highlightMarker,
    highlightMerchantMarker,
    setCenter,
    setZoom,
    clearMarkers,
    destroyMap
  }
}

/**
 * 从 API 加载地图配置
 */
export async function fetchMapConfig(): Promise<{
  defaultMap: MapEngine
  apiKey?: string
}> {
  try {
    const response = await fetch('/api/v1/admin/map-config')
    if (!response.ok) {
      throw new Error('获取地图配置失败')
    }

    const config = await response.json()

    return {
      defaultMap: config.default_map || 'osm',
      apiKey: config.map_api_keys?.[config.default_map] || undefined
    }
  } catch (err) {
    console.warn('加载地图配置失败，使用默认配置:', err)
    return {
      defaultMap: 'osm'
    }
  }
}
