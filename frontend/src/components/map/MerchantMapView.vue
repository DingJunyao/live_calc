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
        <v-btn-group v-if="isDesktop && availableMaps.length > 1" class="desktop-layer-selector" density="compact">
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
          v-else-if="!isDesktop && availableMaps.length > 1"
          :model-value="currentMapLayer"
          :items="availableMaps"
          item-title="label"
          item-value="value"
          density="compact"
          variant="solo"
          hide-details
          class="mobile-layer-selector"
          @update:model-value="handleMobileMapChange"
          style="max-width: 120px"
        />

        <!-- 地点切换器（仅在有地点时显示） -->
        <v-select
          v-if="placeOptions.length > 1"
          :model-value="props.currentPlaceId"
          :items="placeOptions"
          item-title="label"
          item-value="id"
          density="compact"
          variant="solo"
          hide-details
          :style="{ maxWidth: isDesktop ? '150px' : '110px' }"
          @update:model-value="onPlaceChange"
        />

        <!-- 当前位置按钮 -->
        <v-btn
          :icon="isLocating ? 'mdi-crosshairs-gps' : 'mdi-crosshairs-gps'"
          size="small"
          :color="hasCurrentLocation ? 'primary' : 'surface'"
          variant="elevated"
          :title="'显示当前位置（5km 范围）'"
          @click="showCurrentLocation"
          class="control-btn"
        />

        <!-- 居中按钮 -->
        <v-btn
          icon="mdi-fit-to-page-outline"
          size="small"
          color="surface"
          variant="elevated"
          title="缩放到所有商家"
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
  is_open?: boolean
}

interface PlaceOption {
  id: number
  name: string
  kind: string
  latitude: number
  longitude: number
  is_default?: boolean
  view_radius_km?: number
}

interface Props {
  merchants: Merchant[]
  selectedMerchant?: Merchant | null
  engine?: MapEngineType
  apiKey?: string
  isDesktop?: boolean
  places?: PlaceOption[]
  currentPlaceId?: number | null
  allCoordinates?: { latitude: number; longitude: number }[]
}

const props = withDefaults(defineProps<Props>(), {
  merchants: () => [],
  selectedMerchant: null,
  engine: 'osm',
  apiKey: '',
  isDesktop: true,
  places: () => [],
  currentPlaceId: null,
  allCoordinates: () => []
})

const emit = defineEmits<{
  (e: 'update:currentPlaceId', value: number | null): void
}>()

// 当前地点中心：currentPlaceId 命中 places 则取其坐标 + 视野半径；null 表示「全部商家」走 fitAll
const initialCenter = computed<{ lat: number; lng: number; radiusKm: number } | null>(() => {
  if (props.currentPlaceId == null) return null
  const p = props.places.find(pl => pl.id === props.currentPlaceId)
  if (!p || !isValidCoordinate(p.latitude, p.longitude)) return null
  return { lat: p.latitude, lng: p.longitude, radiusKm: p.view_radius_km ?? 5 }
})

// 视野半径（km）→ zoom 近似映射（中纬度）
function radiusKmToZoom(km: number): number {
  if (km <= 1) return 14
  if (km <= 2) return 13
  if (km <= 5) return 12
  if (km <= 10) return 11
  if (km <= 20) return 10
  if (km <= 50) return 9
  return 8
}

// 切换器选项：用户地点 + 「全部商家」（places 为空时 length=1，不显示切换器）
const placeOptions = computed(() => {
  const opts: { id: number | null; label: string }[] = props.places.map(p => ({
    id: p.id,
    label: p.name
  }))
  opts.push({ id: null, label: '全部商家' })
  return opts
})

function onPlaceChange(val: any) {
  emit('update:currentPlaceId', (val as number | null) ?? null)
}

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

// 当前位置相关
const isLocating = ref(false)
const hasCurrentLocation = ref(false)
let currentLocationMarker: any = null
let currentLocationCircle: any = null

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

    // 延迟后应用初始视角（有地点中心则居中约 5km，否则 fitAll）
    setTimeout(() => {
      applyInitialView()
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
  if (isLeafletMap.value) {
    markersMap.forEach(markerId => {
      currentEngine.removeMarker(markerId)
    })
  } else {
    // SDK 引擎：直接操作原生地图对象移除
    const nativeMap = currentEngine.getMap()
    const engineName = currentEngine.name
    markersMap.forEach((nativeMarker) => {
      try {
        if (engineName === 'amap-sdk' && nativeMap?.remove) {
          nativeMap.remove(nativeMarker)
        } else if (engineName === 'baidu-sdk' && nativeMap?.removeOverlay) {
          nativeMap.removeOverlay(nativeMarker)
        } else if (engineName === 'tencent-sdk') {
          // 腾讯：标记是 { dot, label } 对象
          if (nativeMarker?.dot?.setMap) nativeMarker.dot.setMap(null)
          if (nativeMarker?.label?.setMap) nativeMarker.label.setMap(null)
        }
      } catch (e) { /* ignore */ }
    })
  }
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

    const isSelected = props.selectedMerchant?.id === merchant.id
    const isClosed = merchant.is_open === false
    const displayName = merchant.name.length > 8 ? merchant.name.substring(0, 8) + '…' : merchant.name

    if (isLeafletMap.value) {
      // Leaflet：通过引擎添加标记，再设置自定义图标
      const markerId = currentEngine.addMarker(displayCoord.lat, displayCoord.lng, {
        draggable: false
      })
      markersMap.set(merchant.id, markerId)

      const leafletMap = currentEngine.getMap()
      if (leafletMap) {
        leafletMap.eachLayer((layer: any) => {
          if (layer instanceof L.Marker) {
            const latLng = layer.getLatLng()
            if (Math.abs(latLng.lat - displayCoord.lat) < 0.0001 &&
                Math.abs(latLng.lng - displayCoord.lng) < 0.0001) {
              const icon = L.divIcon({
                className: 'merchant-marker',
                html: `<div class="marker-icon ${isSelected ? 'selected' : ''} ${isClosed ? 'closed' : ''}">
                  <span class="marker-label">${displayName}</span>
                </div>`,
                iconSize: [80, 30],
                iconAnchor: [40, 30]
              })
              layer.setIcon(icon)
              const popupLines = [`<strong>${merchant.name}</strong>`]
              if (isClosed) {
                popupLines.push('<span style="color:#f57c00;">（已关闭）</span>')
              }
              popupLines.push(merchant.address || '无地址')
              layer.bindPopup(popupLines.join('<br>'))
            }
          }
        })
      }
    } else {
      // SDK 引擎：直接创建带名称标签的自定义商家标记
      const engineName = currentEngine.name
      const nativeMap = currentEngine.getMap()
      const bgColor = isClosed ? '#757575' : (isSelected ? '#d32f2f' : '#1976d2')

      if (engineName === 'amap-sdk' && window.AMap) {
        const marker = new window.AMap.Marker({
          position: [displayCoord.lng, displayCoord.lat],
          content: `<div style="background:${bgColor};color:#fff;padding:3px 7px;border-radius:3px;font-size:11px;font-weight:500;white-space:nowrap;box-shadow:0 2px 4px rgba(0,0,0,0.2);position:relative;">
            ${displayName}
            <div style="position:absolute;bottom:-5px;left:50%;transform:translateX(-50%);width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:5px solid ${bgColor};"></div>
          </div>`,
          offset: new window.AMap.Pixel(-40, -28)
        })
        nativeMap.add(marker)
        markersMap.set(merchant.id, marker)
      } else if (engineName === 'baidu-sdk') {
        const BMap = window.BMapGL || window.BMap
        if (BMap) {
          const point = new BMap.Point(displayCoord.lng, displayCoord.lat)
          const marker = new BMap.Marker(point)
          const label = new BMap.Label(displayName, {
            offset: new BMap.Size(20, -20),
            position: point
          })
          label.setStyle({
            color: '#fff',
            backgroundColor: bgColor,
            border: 'none',
            borderRadius: '3px',
            padding: '2px 6px',
            fontSize: '11px',
            fontWeight: '500',
            whiteSpace: 'nowrap',
            boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
          })
          marker.setLabel(label)
          nativeMap.addOverlay(marker)
          markersMap.set(merchant.id, marker)
        }
      } else if (engineName === 'tencent-sdk' && window.TMap) {
        // 腾讯：MultiMarker（小圆点）+ MultiLabel（名称标签）
        const TMap = window.TMap
        const pos = new TMap.LatLng(displayCoord.lat, displayCoord.lng)
        const dotSVG = 'data:image/svg+xml,' + encodeURIComponent(
          `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">` +
          `<circle cx="6" cy="6" r="5" fill="${bgColor.replace('#', '%23')}" stroke="white" stroke-width="2"/></svg>`
        )
        const dot = new TMap.MultiMarker({
          map: nativeMap,
          styles: {
            'm': new TMap.MarkerStyle({
              width: 12, height: 12, anchor: { x: 6, y: 12 },
              src: dotSVG
            })
          },
          geometries: [{ id: `m-${merchant.id}`, styleId: 'm', position: pos }]
        })
        const label = new TMap.MultiLabel({
          map: nativeMap,
          styles: {
            'l': new TMap.LabelStyle({
              color: '#fff',
              size: 12,
              offset: { x: 0, y: -18 },
              alignment: 'center',
              backgroundColor: bgColor,
              borderColor: bgColor,
              borderWidth: 0,
              borderRadius: 3,
              padding: '3px 7px'
            })
          },
          geometries: [{
            id: `l-${merchant.id}`,
            styleId: 'l',
            position: pos,
            content: displayName
          }]
        })
        markersMap.set(merchant.id, { dot, label })
      }
    }
  })
}

// WGS84 → 当前地图坐标系（与标记绘制保持一致）
function toDisplayCoord(lat: number, lng: number): Coordinate {
  const coordSystem = getCoordinateSystem(currentMapLayer.value)
  if (coordSystem === 'wgs84') return { lat, lng }
  if (coordSystem === 'gcj02') return convertCoordinate(lat, lng, 'wgs84', 'gcj02')
  return convertCoordinate(lat, lng, 'wgs84', 'bd09')
}

// 应用初始视角：有地点中心则居中 zoom 12（约 5km），否则 fitAllMerchants
function applyInitialView() {
  if (!currentEngine) return
  const c = initialCenter.value
  if (c) {
    const d = toDisplayCoord(c.lat, c.lng)
    currentEngine.setCenter(d.lat, d.lng)
    currentEngine.setZoom(radiusKmToZoom(c.radiusKm))
  } else {
    fitAllMerchants()
  }
}

// SDK 引擎：真正框住所有点（高德 setBounds / 百度 setViewport / 腾讯 fitBounds）
function fitSDKBounds(points: Coordinate[]) {
  if (!currentEngine || points.length === 0) return
  if (points.length === 1) {
    currentEngine.setCenter(points[0].lat, points[0].lng)
    currentEngine.setZoom(13)
    return
  }
  const engineName = currentEngine.name
  const nativeMap = currentEngine.getMap()
  try {
    if (engineName === 'amap-sdk' && window.AMap?.Bounds) {
      const lats = points.map(p => p.lat)
      const lngs = points.map(p => p.lng)
      const sw = new window.AMap.LngLat(Math.min(...lngs), Math.min(...lats))
      const ne = new window.AMap.LngLat(Math.max(...lngs), Math.max(...lats))
      nativeMap.setBounds(new window.AMap.Bounds(sw, ne))
    } else if (engineName === 'baidu-sdk') {
      const BMap = window.BMapGL || window.BMap
      if (BMap) {
        nativeMap.setViewport(points.map((p: Coordinate) => new BMap.Point(p.lng, p.lat)))
      }
    } else if (engineName === 'tencent-sdk' && window.TMap) {
      const latLngs = points.map((p: Coordinate) => new window.TMap.LatLng(p.lat, p.lng))
      const bounds = new window.TMap.LatLngBounds(latLngs[0], latLngs[1])
      for (let i = 2; i < latLngs.length; i++) bounds.extend(latLngs[i])
      nativeMap.fitBounds(bounds, { zoom: 13 })
    } else {
      currentEngine.setCenter(points[0].lat, points[0].lng)
      currentEngine.setZoom(13)
    }
  } catch (e) {
    currentEngine.setCenter(points[0].lat, points[0].lng)
    currentEngine.setZoom(13)
  }
}

// 缩放到全部商家：用父组件传入的 allCoordinates（全集，非当前页）算 bounds
function fitAllMerchants() {
  if (!currentEngine) return

  const source = props.allCoordinates.length > 0
    ? props.allCoordinates
    : validMerchants.value.map(m => ({ latitude: m.latitude!, longitude: m.longitude! }))

  const points = source
    .filter((c: { latitude: number; longitude: number }) => isValidCoordinate(c.latitude, c.longitude))
    .map((c: { latitude: number; longitude: number }) => toDisplayCoord(c.latitude, c.longitude))

  if (points.length === 0) return

  if (isLeafletMap.value) {
    const leafletMap = currentEngine.getMap()
    if (!leafletMap || !leafletMap.fitBounds) return
    if (points.length === 1) {
      leafletMap.setView([points[0].lat, points[0].lng] as L.LatLngExpression, 15)
    } else {
      const bounds = points.map(p => [p.lat, p.lng]) as L.LatLngBoundsExpression
      leafletMap.fitBounds(bounds, { padding: [50, 50] })
    }
  } else {
    fitSDKBounds(points)
  }
}

// 切换地图图层
async function switchMapLayer(layer: MapEngineType) {
  if (layer === currentMapLayer.value) return

  currentMapLayer.value = layer

  // 清除当前位置
  currentLocationMarker = null
  currentLocationCircle = null
  hasCurrentLocation.value = false

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

// 处理移动端地图切换（避免 v-model 竞态问题）
function handleMobileMapChange(newValue: MapEngineType) {
  // 先切换地图，switchMapLayer 会更新 currentMapLayer
  switchMapLayer(newValue)
}

// 清除当前位置标记和圆
function clearCurrentLocation() {
  if (currentLocationMarker) {
    if (isLeafletMap.value) {
      // Leaflet：通过引擎移除
      if (currentEngine) {
        currentEngine.removeMarker(currentLocationMarker)
      }
    } else {
      // SDK 引擎：直接操作原生地图对象移除标记
      try {
        const nativeMap = currentEngine?.getMap()
        const engineName = currentEngine?.name
        if (engineName === 'amap-sdk' && nativeMap?.remove) {
          nativeMap.remove(currentLocationMarker)
        } else if (engineName === 'baidu-sdk' && nativeMap?.removeOverlay) {
          nativeMap.removeOverlay(currentLocationMarker)
        } else if (engineName === 'tencent-sdk' && currentLocationMarker?.setMap) {
          currentLocationMarker.setMap(null)
        }
      } catch (e) {
        console.warn('移除 SDK 当前位置标记失败:', e)
      }
    }
    currentLocationMarker = null
  }
  if (currentLocationCircle) {
    if (isLeafletMap.value) {
      const leafletMap = currentEngine?.getMap()
      if (leafletMap && leafletMap.removeLayer) {
        leafletMap.removeLayer(currentLocationCircle)
      }
    } else {
      // SDK 引擎：移除圆形
      try {
        const nativeMap = currentEngine?.getMap()
        if (nativeMap) {
          const engineName = currentEngine?.name
          if (engineName === 'amap-sdk' && nativeMap.remove) {
            nativeMap.remove(currentLocationCircle)
          } else if (engineName === 'baidu-sdk' && nativeMap.removeOverlay) {
            nativeMap.removeOverlay(currentLocationCircle)
          } else if (engineName === 'tencent-sdk' && currentLocationCircle.setMap) {
            currentLocationCircle.setMap(null)
          }
        }
      } catch (e) {
        console.warn('移除 SDK 圆形失败:', e)
      }
    }
    currentLocationCircle = null
  }
  hasCurrentLocation.value = false
}

// 显示当前位置
async function showCurrentLocation() {
  // 如果已经有当前位置显示，清除它
  if (hasCurrentLocation.value) {
    clearCurrentLocation()
    fitAllMerchants()
    return
  }

  if (!currentEngine) return

  // 检查浏览器是否支持地理位置
  if (!navigator.geolocation) {
    console.warn('浏览器不支持地理位置定位')
    return
  }

  isLocating.value = true

  try {
    const position = await new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
      })
    })

    const { latitude, longitude } = position.coords

    // 转换坐标系：浏览器返回的是 WGS84
    const coordSystem = getCoordinateSystem(currentMapLayer.value)
    let displayCoord: Coordinate

    if (coordSystem === 'wgs84') {
      displayCoord = { lat: latitude, lng: longitude }
    } else if (coordSystem === 'gcj02') {
      displayCoord = convertCoordinate(latitude, longitude, 'wgs84', 'gcj02')
    } else {
      displayCoord = convertCoordinate(latitude, longitude, 'wgs84', 'bd09')
    }

    // 居中到当前位置
    currentEngine.setCenter(displayCoord.lat, displayCoord.lng)
    currentEngine.setZoom(15)

    // 清除旧的位置标记和圆
    if (currentLocationMarker) {
      if (isLeafletMap.value) {
        currentEngine.removeMarker(currentLocationMarker)
      } else {
        // SDK 引擎：直接移除
        try {
          const nm = currentEngine.getMap()
          const en = currentEngine.name
          if (en === 'amap-sdk' && nm?.remove) nm.remove(currentLocationMarker)
          else if (en === 'baidu-sdk' && nm?.removeOverlay) nm.removeOverlay(currentLocationMarker)
          else if (en === 'tencent-sdk' && currentLocationMarker?.setMap) currentLocationMarker.setMap(null)
        } catch (e) { /* ignore */ }
      }
      currentLocationMarker = null
    }
    if (currentLocationCircle) {
      if (isLeafletMap.value) {
        const leafletMap = currentEngine.getMap()
        if (leafletMap?.removeLayer) leafletMap.removeLayer(currentLocationCircle)
      }
      currentLocationCircle = null
    }

    // 添加当前位置标记
    if (isLeafletMap.value) {
      // Leaflet：通过引擎添加标记，再设置自定义图标
      currentLocationMarker = currentEngine.addMarker(displayCoord.lat, displayCoord.lng, {
        draggable: false
      })
      const leafletMap = currentEngine.getMap()
      if (leafletMap) {
        leafletMap.eachLayer((layer: any) => {
          if (layer instanceof L.Marker) {
            const latLng = layer.getLatLng()
            if (Math.abs(latLng.lat - displayCoord.lat) < 0.0001 &&
                Math.abs(latLng.lng - displayCoord.lng) < 0.0001) {
              const icon = L.divIcon({
                className: 'current-location-marker',
                html: `<div style="width:18px;height:18px;border-radius:50%;background:#1976d2;border:3px solid #fff;box-shadow:0 0 6px rgba(0,0,0,0.4);"></div>`,
                iconSize: [18, 18],
                iconAnchor: [9, 9]
              })
              layer.setIcon(icon)
              layer.bindPopup('<strong>当前位置</strong><br>半径 5 km')
            }
          }
        })
      }
    } else {
      // SDK 引擎：直接创建自定义样式的当前位置标记
      const engineName = currentEngine.name
      const nativeMap = currentEngine.getMap()
      const dotHTML = `<div style="width:18px;height:18px;border-radius:50%;background:#1976d2;border:3px solid #fff;box-shadow:0 0 6px rgba(0,0,0,0.4);"></div>`

      if (engineName === 'amap-sdk' && window.AMap) {
        currentLocationMarker = new window.AMap.Marker({
          position: [displayCoord.lng, displayCoord.lat],
          content: dotHTML,
          offset: new window.AMap.Pixel(-9, -9),
          zIndex: 100
        })
        nativeMap.add(currentLocationMarker)
      } else if (engineName === 'baidu-sdk') {
        const BMap = window.BMapGL || window.BMap
        if (BMap) {
          // 使用 SVG data URL 创建蓝点图标
          const svgDot = 'data:image/svg+xml,' + encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24">' +
            '<circle cx="12" cy="12" r="9" fill="#1976d2" stroke="white" stroke-width="3"/>' +
            '</svg>'
          )
          const icon = new BMap.Icon(svgDot, new BMap.Size(24, 24), {
            anchor: new BMap.Size(12, 12)
          })
          const point = new BMap.Point(displayCoord.lng, displayCoord.lat)
          currentLocationMarker = new BMap.Marker(point, { icon })
          nativeMap.addOverlay(currentLocationMarker)
        }
      } else if (engineName === 'tencent-sdk' && window.TMap) {
        currentLocationMarker = new window.TMap.MultiMarker({
          map: nativeMap,
          styles: {
            'loc-dot': new window.TMap.MarkerStyle({
              width: 18,
              height: 18,
              anchor: { x: 9, y: 9 },
              src: 'data:image/svg+xml,' + encodeURIComponent(
                '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18">' +
                '<circle cx="9" cy="9" r="7.5" fill="#1976d2" stroke="white" stroke-width="3"/>' +
                '</svg>'
              )
            })
          },
          geometries: [{
            id: 'current-location',
            styleId: 'loc-dot',
            position: new window.TMap.LatLng(displayCoord.lat, displayCoord.lng)
          }]
        })
      }
    }

    // 添加圆形（Leaflet）
    if (isLeafletMap.value) {
      const leafletMap = currentEngine.getMap()
      if (leafletMap) {
        currentLocationCircle = L.circle([displayCoord.lat, displayCoord.lng], {
          radius: 5000,
          color: '#1976d2',
          fillColor: '#1976d2',
          fillOpacity: 0.1,
          weight: 2,
          dashArray: '5, 5'
        }).addTo(leafletMap)
      }
    } else {
      // SDK 引擎：添加圆形
      const engineName = currentEngine.name
      const nativeMap = currentEngine.getMap()

      if (engineName === 'amap-sdk' && window.AMap) {
        currentLocationCircle = new window.AMap.Circle({
          center: [displayCoord.lng, displayCoord.lat],
          radius: 5000,
          strokeColor: '#1976d2',
          strokeStyle: 'dashed',
          strokeDasharray: [5, 5],
          strokeWeight: 2,
          fillColor: '#1976d2',
          fillOpacity: 0.1,
          zIndex: 10
        })
        nativeMap.add(currentLocationCircle)
      } else if (engineName === 'baidu-sdk') {
        const BMap = window.BMapGL || window.BMap
        if (BMap) {
          const centerPoint = new BMap.Point(displayCoord.lng, displayCoord.lat)
          currentLocationCircle = new BMap.Circle(centerPoint, 5000, {
            strokeColor: '#1976d2',
            strokeWeight: 2,
            strokeOpacity: 0.8,
            fillColor: '#1976d2',
            fillOpacity: 0.1,
            strokeStyle: 'dashed'
          })
          nativeMap.addOverlay(currentLocationCircle)
        }
      } else if (engineName === 'tencent-sdk' && window.TMap) {
        currentLocationCircle = new window.TMap.MultiCircle({
          map: nativeMap,
          styles: {
            'current-location': new window.TMap.CircleStyle({
              color: 'rgba(25, 118, 210, 0.1)',
              showBorder: true,
              borderColor: 'rgba(25, 118, 210, 0.8)',
              borderWidth: 2
            })
          },
          geometries: [{
            styleId: 'current-location',
            center: new window.TMap.LatLng(displayCoord.lat, displayCoord.lng),
            radius: 5000
          }]
        })
      }
    }

    hasCurrentLocation.value = true
  } catch (error: any) {
    console.error('获取当前位置失败:', error)
    let errorMsg = '获取当前位置失败'
    switch (error.code) {
      case error.PERMISSION_DENIED:
        errorMsg = '位置权限被拒绝，请在浏览器设置中允许访问位置信息'
        break
      case error.POSITION_UNAVAILABLE:
        errorMsg = '位置信息不可用'
        break
      case error.TIMEOUT:
        errorMsg = '获取位置超时，请重试'
        break
    }
    // 可以在这里添加一个 snackbar 通知
    console.warn(errorMsg)
  } finally {
    isLocating.value = false
  }
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
  // 若地图尚未初始化（首次加载时数据晚于组件挂载到达），补初始化
  if (!currentEngine && validMerchants.value.length > 0 && !isLoading.value) {
    initMap()
    return
  }
  if (!currentEngine) return
  updateMerchantsMarkers()
  // 仅在「全部商家」模式重新 fit；有地点中心时保持视角，避免翻页飞回全国
  if (!initialCenter.value) {
    setTimeout(() => fitAllMerchants(), 100)
  }
}, { deep: true })

// 切换地点中心时重新应用视角
watch(initialCenter, () => {
  if (currentEngine) {
    nextTick(() => applyInitialView())
  }
})

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
  // 清除当前位置标记和圆
  if (currentLocationCircle) {
    // Leaflet 圆没有特别的清理需要（随地图销毁）
    // SDK 圆形随地图销毁自动移除
    currentLocationCircle = null
  }
  currentLocationMarker = null
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
  background: rgb(var(--v-theme-surface));
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

:deep(.marker-icon.closed) {
  background: #757575;
}

:deep(.marker-icon.closed::after) {
  border-color: #757575 transparent transparent transparent;
}

:deep(.marker-icon.closed.selected) {
  background: #d32f2f;
}

:deep(.marker-icon.closed.selected::after) {
  border-color: #d32f2f transparent transparent transparent;
}

:deep(.marker-label) {
  display: inline;
}

/* 隐藏 Leaflet 默认缩放控件 */
:deep(.leaflet-control-zoom) {
  display: none;
}

/* 当前位置标记样式 */
:deep(.current-location-marker) {
  background: transparent !important;
  border: none !important;
  width: 18px !important;
  height: 18px !important;
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

  /* 移动端地图控件缩小 */
  .map-controls {
    gap: 4px; /* 减小间距 */
  }

  :deep(.mobile-layer-selector) {
    max-width: 80px; /* 减小宽度 */
    font-size: 0.7rem; /* 减小字体 */
  }

  :deep(.mobile-layer-selector .v-field__input) {
    padding: 4px 8px; /* 减小内边距 */
    min-height: 28px; /* 减小高度 */
    font-size: 0.7rem;
  }

  .control-btn {
    width: 28px !important; /* 减小按钮宽度 */
    height: 28px !important; /* 减小按钮高度 */
    min-width: 28px !important;
  }

  :deep(.control-btn .v-btn__content) {
    font-size: 16px; /* 减小图标尺寸 */
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
