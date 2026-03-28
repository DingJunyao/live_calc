<template>
  <div class="map-picker">
    <!-- 地图切换按钮 -->
    <div v-if="showSwitcher && availableMaps.length > 1" class="map-switcher mb-2">
      <v-btn-group density="compact">
        <v-btn
          v-for="map in availableMaps"
          :key="map.value"
          :color="currentMap === map.value ? 'primary' : 'default'"
          :variant="currentMap === map.value ? 'elevated' : 'text'"
          size="small"
          @click="switchMap(map.value)"
        >
          {{ map.label }}
        </v-btn>
      </v-btn-group>
    </div>

    <!-- 地图容器 -->
    <div class="map-picker-container" :class="{ 'is-loading': isLoading }">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="map-loading-overlay">
        <v-progress-circular indeterminate color="primary" size="48" />
        <p class="mt-3 text-body-2">地图加载中...</p>
      </div>

      <!-- 地图 -->
      <div v-show="!isLoading" ref="mapContainer" class="map-container" :style="{ height: height }"></div>
    </div>

    <!-- 坐标显示 -->
    <div class="coord-display mt-3">
      <v-chip size="small" variant="tonal">
        <v-icon start size="small">mdi-crosshairs-gps</v-icon>
        纬度: {{ wgs84Coordinate ? wgs84Coordinate.lat.toFixed(6) : '-' }}
      </v-chip>
      <v-chip size="small" variant="tonal" class="ml-2">
        <v-icon start size="small">mdi-crosshairs-gps</v-icon>
        经度: {{ wgs84Coordinate ? wgs84Coordinate.lng.toFixed(6) : '-' }}
      </v-chip>
    </div>

    <!-- 操作提示 -->
    <div class="map-hint mt-2">
      <v-icon size="small" color="medium-emphasis">mdi-information-outline</v-icon>
      <span class="text-caption text-medium-emphasis ml-1">
        点击地图选择商家位置
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue'
import type { MapEngineType, Coordinate, MapConfig } from '@/utils/map/mapTypes'
import { mapEngineNames, defaultMapConfig } from '@/utils/map/mapTypes'
import { mapEngineManager } from '@/utils/mapEngineManager'
import { getUserMapPreference } from '@/utils/mapConfig'
import { convertCoordinate, getCoordinateSystem } from '@/utils/coordinateTransform'
import { api } from '@/api/client'

// Props
interface Props {
  modelValue?: Coordinate
  height?: string
  readonly?: boolean
  showSwitcher?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({ lat: 39.9042, lng: 116.4074 }),
  height: '300px',
  readonly: false,
  showSwitcher: true
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [coordinate: Coordinate]
  'mapChange': [mapEngine: MapEngineType]
}>()

// 响应式数据
const mapContainer = ref<HTMLElement | null>(null)
const currentMap = ref<MapEngineType>('osm')
const availableMaps = ref<{ value: MapEngineType; label: string }[]>([])
const apiKeys = ref<any>({})
const isLoading = ref(true)

// 核心坐标状态：始终使用 WGS84 坐标系
const wgs84Coordinate = ref<Coordinate | null>(null)

// Leaflet 引擎相关
let markerId: any = null
let currentLeafletEngine: any = null

// 所有地图选项
const allMapsOptions: { value: MapEngineType; label: string }[] = [
  { value: 'amap', label: '高德' },
  { value: 'baidu', label: '百度' },
  { value: 'tencent', label: '腾讯' },
  { value: 'tianditu', label: '天地图' },
  { value: 'osm', label: 'OSM' }
]

// 计算当前地图需要显示的坐标（从 WGS84 转换到当前地图坐标系）
const displayCoordinate = computed(() => {
  if (!wgs84Coordinate.value) {
    return props.modelValue || { lat: 39.9042, lng: 116.4074 }
  }

  const coordSystem = getCoordinateSystem(currentMap.value)
  if (coordSystem === 'wgs84') {
    return wgs84Coordinate.value
  } else if (coordSystem === 'gcj02') {
    return convertCoordinate(
      wgs84Coordinate.value.lat,
      wgs84Coordinate.value.lng,
      'wgs84',
      'gcj02'
    )
  } else {
    return convertCoordinate(
      wgs84Coordinate.value.lat,
      wgs84Coordinate.value.lng,
      'wgs84',
      'bd09'
    )
  }
})

// 将当前地图坐标转换为 WGS84
function convertToWGS84(coord: Coordinate): Coordinate {
  const coordSystem = getCoordinateSystem(currentMap.value)
  if (coordSystem === 'wgs84') {
    return coord
  } else if (coordSystem === 'gcj02') {
    return convertCoordinate(coord.lat, coord.lng, 'gcj02', 'wgs84')
  } else {
    return convertCoordinate(coord.lat, coord.lng, 'bd09', 'wgs84')
  }
}

// 初始化
onMounted(async () => {
  // 从后端获取配置
  await loadMapConfig()

  // 获取用户偏好
  const preference = getUserMapPreference()
  const userMap = preference?.currentMap

  // 确定使用的地图
  if (userMap && availableMaps.value.find(m => m.value === userMap)) {
    currentMap.value = userMap
  }

  // 初始化 WGS84 坐标
  if (props.modelValue && props.modelValue.lat && props.modelValue.lng) {
    wgs84Coordinate.value = props.modelValue
  }

  // 初始化 Leaflet 地图
  await nextTick()
  await initLeafletMap()
})

// 卸载时销毁
onUnmounted(() => {
  if (currentLeafletEngine) {
    currentLeafletEngine.destroy()
    currentLeafletEngine = null
  }
})

// 从后端加载地图配置
async function loadMapConfig() {
  try {
    const backendMapConfig = await api.get('/merchants/map-config')

    if (backendMapConfig) {
      const enabledMaps = backendMapConfig.available_maps || ['amap', 'baidu', 'tencent', 'tianditu', 'osm']
      availableMaps.value = allMapsOptions.filter(m => enabledMaps.includes(m.value))
      apiKeys.value = backendMapConfig.map_api_keys || {}

      if (backendMapConfig.default_map && enabledMaps.includes(backendMapConfig.default_map)) {
        currentMap.value = backendMapConfig.default_map
      }
    }
  } catch (e) {
    console.warn('获取地图配置失败，使用默认配置:', e)
    availableMaps.value = allMapsOptions
  }
}

// 初始化 Leaflet 地图
async function initLeafletMap() {
  if (!mapContainer.value) return

  const coord = displayCoordinate.value

  const config: MapConfig = {
    ...defaultMapConfig,
    availableMaps: availableMaps.value.map(m => m.value),
    defaultMap: currentMap.value,
    mapApiKeys: apiKeys.value
  }

  mapEngineManager.setConfig(config)

  // 加载引擎
  currentLeafletEngine = await mapEngineManager.createEngine(
    currentMap.value,
    mapContainer.value,
    {
      center: [coord.lat, coord.lng],
      zoom: 13,
      enableClick: !props.readonly,
      enableDrag: !props.readonly
    }
  )

  isLoading.value = false

  // 绑定事件
  currentLeafletEngine.on('click', handleLeafletClick)
  currentLeafletEngine.on('markerDragend', handleLeafletMarkerDrag)

  // 设置初始标记
  if (wgs84Coordinate.value) {
    setLeafletMarker(displayCoordinate.value)
  }

  // 额外的尺寸修复（对话框中的地图需要额外处理）
  setTimeout(() => {
    if (currentLeafletEngine) {
      const leafletMap = currentLeafletEngine.getMap()
      if (leafletMap) {
        leafletMap.invalidateSize()
      }
    }
  }, 200)

  setTimeout(() => {
    if (currentLeafletEngine) {
      const leafletMap = currentLeafletEngine.getMap()
      if (leafletMap) {
        leafletMap.invalidateSize()
      }
    }
  }, 500)
}

// 处理 Leaflet 地图点击
function handleLeafletClick(data: { lat: number; lng: number }) {
  if (props.readonly) return

  // Leaflet 返回的坐标可能是当前地图坐标系，需要转换为 WGS84
  const wgs84 = convertToWGS84({ lat: data.lat, lng: data.lng })
  wgs84Coordinate.value = wgs84
  setLeafletMarker({ lat: data.lat, lng: data.lng })
  emit('update:modelValue', wgs84)
}

// 处理 Leaflet 标记拖拽
function handleLeafletMarkerDrag(data: { lat: number; lng: number }) {
  if (props.readonly) return

  const wgs84 = convertToWGS84({ lat: data.lat, lng: data.lng })
  wgs84Coordinate.value = wgs84
  emit('update:modelValue', wgs84)
}

// 设置 Leaflet 标记
function setLeafletMarker(coord: Coordinate) {
  if (!currentLeafletEngine || !currentLeafletEngine.getMap()) return

  // 移除旧标记
  if (markerId) {
    currentLeafletEngine.removeMarker(markerId)
  }

  // 添加新标记
  markerId = currentLeafletEngine.addMarker(coord.lat, coord.lng, {
    draggable: !props.readonly
  })
}

// 切换地图（不改变 WGS84 坐标）
async function switchMap(mapType: MapEngineType) {
  if (mapType === currentMap.value) return

  // 销毁 Leaflet 引擎（如果存在）
  if (currentLeafletEngine) {
    currentLeafletEngine.destroy()
    currentLeafletEngine = null
    markerId = null
  }

  currentMap.value = mapType

  // 等待视图更新
  await nextTick()

  // 重新初始化
  await initLeafletMap()

  // 触发地图切换事件
  emit('mapChange', mapType)
}

// 监听 v-model 变化（外部传入的应该是 WGS84 坐标）
watch(() => props.modelValue, (newVal) => {
  if (newVal && newVal.lat && newVal.lng) {
    if (!wgs84Coordinate.value ||
        wgs84Coordinate.value.lat !== newVal.lat ||
        wgs84Coordinate.value.lng !== newVal.lng) {
      wgs84Coordinate.value = newVal
      if (currentLeafletEngine) {
        setLeafletMarker(displayCoordinate.value)
      }
    }
  }
}, { deep: true })
</script>

<style scoped>
.map-picker {
  width: 100%;
}

.map-switcher {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.map-picker-container {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  background-color: rgb(var(--v-theme-surface-variant));
  position: relative;
}

.map-picker-container.is-loading {
  pointer-events: none;
}

.map-container {
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

.map-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgba(var(--v-theme-surface), 0.9);
  z-index: 10;
}

.coord-display {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.map-hint {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 隐藏 Leaflet 默认缩放控件 */
:deep(.leaflet-control-zoom) {
  display: none;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .map-switcher {
    flex-wrap: nowrap;
    overflow-x: auto;
  }
}
</style>
