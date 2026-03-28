<template>
  <v-card elevation="2" class="merchant-map-view">
    <!-- 地图容器 -->
    <div class="map-wrapper" ref="mapWrapperRef">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="map-loading-overlay">
        <v-progress-circular indeterminate color="primary" size="64" />
        <p class="mt-4 text-body-1">地图加载中...</p>
      </div>

      <!-- 空状态 -->
      <div v-else-if="validMerchants.length === 0" class="map-empty-state">
        <v-icon size="64" color="medium-emphasis">mdi-map-marker-off</v-icon>
        <p class="mt-4 text-body-1 text-medium-emphasis">暂无商家位置信息</p>
        <p class="text-caption text-medium-emphasis mt-2">
          在商家信息中添加坐标后即可在地图上显示
        </p>
      </div>

      <!-- 地图控制按钮 -->
      <div v-show="!isLoading && validMerchants.length > 0" class="map-controls">
        <!-- 地图切换器（桌面端） -->
        <v-btn-group v-if="availableMaps.length > 1" class="desktop-layer-selector" density="compact">
          <v-btn
            v-for="map in availableMaps"
            :key="map.value"
            :color="currentMapLayer === map.value ? 'primary' : 'default'"
            :variant="currentMapLayer === map.value ? 'elevated' : 'text'"
            size="small"
            @click="switchMapLayer(map.value)"
          >
            {{ map.label }}
          </v-btn>
        </v-btn-group>

        <!-- 地图切换下拉（移动端） -->
        <v-select
          v-else-if="availableMaps.length > 1"
          v-model="currentMapLayer"
          :items="availableMaps"
          item-title="label"
          item-value="value"
          density="compact"
          variant="solo"
          hide-details
          class="mobile-layer-selector"
          @update:model-value="handleMapLayerChange"
          style="max-width: 120px"
        />

        <!-- 居中按钮 -->
        <v-btn
          icon="mdi-crosshairs-gps"
          size="small"
          color="surface"
          variant="elevated"
          @click="fitAllMerchants"
          class="control-btn"
        />

        <!-- 全屏按钮 -->
        <v-btn
          :icon="isFullscreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'"
          size="small"
          color="surface"
          variant="elevated"
          @click="toggleFullscreen"
          class="control-btn"
        />
      </div>

      <!-- Leaflet 地图容器 -->
      <div v-show="!isLoading && validMerchants.length > 0" ref="mapContainer" class="map-container"></div>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import type { MapEngineType, Coordinate, MapConfig } from '@/utils/map/mapTypes'
import { mapEngineNames, defaultMapConfig } from '@/utils/map/mapTypes'
import { mapEngineManager } from '@/utils/mapEngineManager'
import { convertCoordinate, getCoordinateSystem } from '@/utils/coordinateTransform'
import { api } from '@/api/client'
import L from 'leaflet'

// Props
interface Merchant {
  id: number
  name: string
  address?: string
  latitude?: number | null
  longitude?: number | null
}

interface Props {
  merchants: Merchant[]
  selectedMerchant?: Merchant | null
  engine?: MapEngineType
  apiKey?: string
  isDesktop?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  merchants: () => [],
  selectedMerchant: null,
  engine: 'osm',
  apiKey: '',
  isDesktop: true
})

// 地图相关
const mapContainer = ref<HTMLElement | null>(null)
const mapWrapperRef = ref<HTMLElement | null>(null)
const currentMapLayer = ref<MapEngineType>(props.engine)
const availableMaps = ref<{ value: MapEngineType; label: string }[]>([])
const apiKeys = ref<any>({})
const isFullscreen = ref(false)
const isLoading = ref(true)

// 地图引擎和标记
let currentEngine: any = null
let markersMap: Map<number, any> = new Map()

// 所有地图选项
const allMapsOptions: { value: MapEngineType; label: string }[] = [
  { value: 'amap', label: '高德' },
  { value: 'baidu', label: '百度' },
  { value: 'tencent', label: '腾讯' },
  { value: 'tianditu', label: '天地图' },
  { value: 'osm', label: 'OSM' }
]

// 检测当前是否使用 SDK 引擎
const isSDKEngine = computed(() => {
  const type = currentMapLayer.value
  // 检查是否以 -sdk 结尾，或者是高德/百度/腾讯且有 Key
  if (type.endsWith('-sdk')) return true

  // 检查是否是支持 SDK 的地图且配置了 Key
  const hasKey = type === 'amap' ? apiKeys.value.amap :
                type === 'baidu' ? apiKeys.value.baidu :
                type === 'tencent' ? apiKeys.value.tencent :
                false
  return hasKey && ['amap', 'baidu', 'tencent'].includes(type)
})

// 检测当前是否使用 Leaflet 地图
const isLeafletMap = computed(() => !isSDKEngine.value)

// 检查坐标是否有效
function isValidCoordinate(lat: any, lng: any): boolean {
  return typeof lat === 'number' && typeof lng === 'number' &&
         !isNaN(lat) && !isNaN(lng) &&
         lat !== 0 && lng !== 0
}

// 过滤出有坐标的商家
const validMerchants = computed(() => {
  return props.merchants.filter(m =>
    isValidCoordinate(m.latitude, m.longitude)
  )
})

// 加载地图配置
async function loadMapConfig() {
  try {
    const config = await api.get('/merchants/map-config')
    if (config) {
      const enabledMaps = config.available_maps || ['amap', 'baidu', 'tencent', 'tianditu', 'osm']
      availableMaps.value = allMapsOptions.filter(m => enabledMaps.includes(m.value))
      apiKeys.value = config.map_api_keys || {}

      if (config.default_map && enabledMaps.includes(config.default_map)) {
        currentMapLayer.value = config.default_map
      }
    }
  } catch (error) {
    console.error('Failed to load map config:', error)
    availableMaps.value = allMapsOptions
  }
}

// 初始化地图
async function initMap() {
  if (!mapContainer.value) return

  isLoading.value = true

  const config: MapConfig = {
    ...defaultMapConfig,
    availableMaps: availableMaps.value.map(m => m.value),
    defaultMap: currentMapLayer.value,
    mapApiKeys: apiKeys.value
  }

  mapEngineManager.setConfig(config)

  try {
    currentEngine = await mapEngineManager.createEngine(
      currentMapLayer.value,
      mapContainer.value,
      {
        center: [39.9042, 116.4074],
        zoom: 12,
        enableClick: true,
        enableDrag: true
      }
    )

    // 等待地图渲染
    await nextTick()

    // 额外的尺寸修复（针对 Vue 组件的异步渲染）
    // 只对 Leaflet 地图调用 invalidateSize
    setTimeout(() => {
      if (currentEngine && isLeafletMap.value) {
        const leafletMap = currentEngine.getMap()
        if (leafletMap && leafletMap.invalidateSize) {
          leafletMap.invalidateSize()
        }
      }
    }, 200)

    // 更新商家标记
    updateMerchantsMarkers()

    // 延迟后缩放到商家范围
    setTimeout(() => {
      fitAllMerchants()
      // 再次确保尺寸正确（只对 Leaflet 地图）
      if (currentEngine && isLeafletMap.value) {
        const leafletMap = currentEngine.getMap()
        if (leafletMap && leafletMap.invalidateSize) {
          leafletMap.invalidateSize()
        }
      }
    }, 500)
  } catch (error) {
    console.error('Failed to init map:', error)
  } finally {
    isLoading.value = false
  }
}

// 更新商家标记
function updateMerchantsMarkers() {
  if (!currentEngine) return

  // 清除所有现有标记
  markersMap.forEach(markerId => {
    currentEngine.removeMarker(markerId)
  })
  markersMap.clear()

  // 添加商家标记
  validMerchants.value.forEach(merchant => {
    // 数据库存储的是 WGS84，根据当前地图类型转换
    const coordSystem = getCoordinateSystem(currentMapLayer.value)
    let displayCoord: Coordinate

    if (coordSystem === 'wgs84') {
      displayCoord = { lat: merchant.latitude!, lng: merchant.longitude! }
    } else if (coordSystem === 'gcj02') {
      displayCoord = convertCoordinate(merchant.latitude!, merchant.longitude!, 'wgs84', 'gcj02')
    } else {
      displayCoord = convertCoordinate(merchant.latitude!, merchant.longitude!, 'wgs84', 'bd09')
    }

    // 添加标记
    const markerId = currentEngine.addMarker(displayCoord.lat, displayCoord.lng, {
      draggable: false
    })

    markersMap.set(merchant.id, markerId)

    // 只对 Leaflet 地图设置自定义图标
    if (isLeafletMap.value) {
      const leafletMap = currentEngine.getMap()
      if (leafletMap) {
        const marker = markersMap.get(merchant.id)
        if (marker) {
          // 查找对应的 Leaflet Marker 并更新图标
          leafletMap.eachLayer((layer: any) => {
            if (layer instanceof L.Marker) {
              const latLng = layer.getLatLng()
              if (Math.abs(latLng.lat - displayCoord.lat) < 0.0001 &&
                  Math.abs(latLng.lng - displayCoord.lng) < 0.0001) {
                const isSelected = props.selectedMerchant?.id === merchant.id
                const displayName = merchant.name.length > 8 ? merchant.name.substring(0, 8) + '…' : merchant.name
                const icon = L.divIcon({
                  className: 'merchant-marker',
                  html: `<div class="marker-icon ${isSelected ? 'selected' : ''}">
                    <span class="marker-label">${displayName}</span>
                  </div>`,
                  iconSize: [80, 30],
                  iconAnchor: [40, 30]
                })
                layer.setIcon(icon)
                layer.bindPopup(`<strong>${merchant.name}</strong><br>${merchant.address || '无地址'}`)
              }
            }
          })
        }
      }
    }
  })
}

// 居中显示所有商家
function fitAllMerchants() {
  if (!currentEngine || validMerchants.value.length === 0) return

  // 对 Leaflet 地图使用 fitBounds
  if (isLeafletMap.value) {
    const leafletMap = currentEngine.getMap()
    if (!leafletMap || !leafletMap.fitBounds) return

    const bounds: L.LatLngBoundsExpression = []

    validMerchants.value.forEach(merchant => {
      const coordSystem = getCoordinateSystem(currentMapLayer.value)
      let displayCoord: Coordinate

      if (coordSystem === 'wgs84') {
        displayCoord = { lat: merchant.latitude!, lng: merchant.longitude! }
      } else if (coordSystem === 'gcj02') {
        displayCoord = convertCoordinate(merchant.latitude!, merchant.longitude!, 'wgs84', 'gcj02')
      } else {
        displayCoord = convertCoordinate(merchant.latitude!, merchant.longitude!, 'wgs84', 'bd09')
      }

      bounds.push([displayCoord.lat, displayCoord.lng])
    })

    if (bounds.length > 0) {
      if (bounds.length === 1) {
        leafletMap.setView(bounds[0] as L.LatLngExpression, 15)
      } else {
        leafletMap.fitBounds(bounds as L.LatLngBoundsExpression, { padding: [50, 50] })
      }
    }
  } else {
    // SDK 地图：简单地缩放到第一个商家的位置
    const firstMerchant = validMerchants.value[0]
    if (firstMerchant) {
      currentEngine.setCenter(firstMerchant.latitude!, firstMerchant.longitude!)
      currentEngine.setZoom(13)
    }
  }
}

// 切换地图图层
async function switchMapLayer(layer: MapEngineType) {
  if (layer === currentMapLayer.value) return

  currentMapLayer.value = layer

  // 销毁当前引擎实例
  if (currentEngine) {
    currentEngine.destroy()
    currentEngine = null
  }
  markersMap.clear()

  // 彻底清理容器
  if (mapContainer.value) {
    // 移除所有子元素（地图 SDK 可能添加的 DOM）
    while (mapContainer.value.firstChild) {
      mapContainer.value.removeChild(mapContainer.value.firstChild)
    }
    // 清除可能的类名和样式
    mapContainer.value.className = 'map-container'
    mapContainer.value.style.cssText = ''
  }

  // 重新初始化
  await nextTick()
  await initMap()
}

function handleMapLayerChange() {
  switchMapLayer(currentMapLayer.value)
}

// 全屏切换
function toggleFullscreen() {
  if (!mapWrapperRef.value) return

  if (!document.fullscreenElement) {
    mapWrapperRef.value.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

// 监听商家数据变化
watch(() => props.merchants, () => {
  updateMerchantsMarkers()
  setTimeout(() => fitAllMerchants(), 100)
}, { deep: true })

// 监听选中商家变化
watch(() => props.selectedMerchant, () => {
  updateMerchantsMarkers()

  // 如果有选中的商家，缩放到该商家
  if (props.selectedMerchant && props.selectedMerchant.latitude && props.selectedMerchant.longitude) {
    const coordSystem = getCoordinateSystem(currentMapLayer.value)
    let displayCoord: Coordinate

    if (coordSystem === 'wgs84') {
      displayCoord = {
        lat: props.selectedMerchant.latitude,
        lng: props.selectedMerchant.longitude
      }
    } else if (coordSystem === 'gcj02') {
      displayCoord = convertCoordinate(
        props.selectedMerchant.latitude,
        props.selectedMerchant.longitude,
        'wgs84',
        'gcj02'
      )
    } else {
      displayCoord = convertCoordinate(
        props.selectedMerchant.latitude,
        props.selectedMerchant.longitude,
        'wgs84',
        'bd09'
      )
    }

    if (currentEngine) {
      currentEngine.setCenter(displayCoord.lat, displayCoord.lng)
      currentEngine.setZoom(15)
    }
  }
})

onMounted(async () => {
  await loadMapConfig()
  await nextTick()

  if (validMerchants.value.length > 0) {
    await initMap()
  } else {
    isLoading.value = false
  }
})

onUnmounted(() => {
  if (currentEngine) {
    currentEngine.destroy()
    currentEngine = null
  }
  markersMap.clear()
})
</script>

<style scoped>
.merchant-map-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.map-wrapper {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 9999;
  display: flex;
  gap: 8px;
  align-items: center;
}

.desktop-layer-selector {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.mobile-layer-selector {
  display: none;
}

.control-btn {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.map-container {
  width: 100%;
  height: 100%;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.map-loading-overlay,
.map-empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgb(var(--v-theme-surface));
  z-index: 10;
  padding: 20px;
  text-align: center;
}

/* 自定义商家标记样式 */
:deep(.merchant-marker) {
  background: transparent !important;
  border: none !important;
  width: 80px !important;
  height: 30px !important;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

:deep(.marker-icon) {
  background: #1976d2;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  position: relative;
  display: inline-block;
}

:deep(.marker-icon::after) {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 6px 6px 0 6px;
  border-style: solid;
  border-color: #1976d2 transparent transparent transparent;
}

:deep(.marker-icon.selected) {
  background: #d32f2f;
}

:deep(.marker-icon.selected::after) {
  border-color: #d32f2f transparent transparent transparent;
}

:deep(.marker-label) {
  display: inline;
}

/* 隐藏 Leaflet 默认缩放控件 */
:deep(.leaflet-control-zoom) {
  display: none;
}

/* 移动端适配 */
@media (max-width: 960px) {
  .map-wrapper {
    min-height: 45vh;
  }

  .desktop-layer-selector {
    display: none;
  }

  .mobile-layer-selector {
    display: block;
  }

  :deep(.merchant-marker) {
    width: 60px !important;
  }

  :deep(.marker-icon) {
    font-size: 10px;
    padding: 3px 6px;
  }
}
</style>
