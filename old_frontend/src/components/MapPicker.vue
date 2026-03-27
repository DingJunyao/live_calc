<template>
  <div class="map-picker">
    <!-- 地图切换按钮 -->
    <div v-if="showSwitcher && availableMaps.length > 1" class="map-switcher">
      <button
        type="button"
        v-for="map in availableMaps"
        :key="map"
        :class="['map-btn', { active: currentMap === map }]"
        @click="switchMap(map)"
      >
        {{ mapEngineNames[map] }}
      </button>
    </div>

    <!-- 地址搜索栏 -->
    <div v-if="showSearch" class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="输入地址搜索..."
        class="search-input"
        @keyup.enter="searchAddress"
      />
      <button @click="searchAddress" class="search-btn" :disabled="!searchQuery.trim() || searchLoading">
        {{ searchLoading ? '搜索中...' : '搜索地址' }}
      </button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="searchResults.length > 0" class="search-results">
      <div
        v-for="(result, index) in searchResults"
        :key="index"
        class="search-result-item"
        @click="selectSearchResult(result)"
      >
        <span class="result-name">{{ result.name || result.address }}</span>
        <span class="result-address">{{ result.address }}</span>
      </div>
    </div>

    <!-- 地图容器 - 根据 API Key 动态选择引擎 -->
    <!-- 高德地图 SDK -->
    <AMapPicker
      v-if="useAMapSDK"
      ref="sdkMapRef"
      :model-value="displayCoordinate"
      :height="height"
      :readonly="readonly"
      :api-key="apiKeys.amap || ''"
      :security-code="apiKeys.amapSecurity || ''"
      @update:model-value="handleSDKCoordinateUpdate"
    />
    <!-- 百度地图 SDK -->
    <BMapPicker
      v-else-if="useBMapSDK"
      ref="sdkMapRef"
      :model-value="displayCoordinate"
      :height="height"
      :readonly="readonly"
      :api-key="apiKeys.baidu || ''"
      @update:model-value="handleSDKCoordinateUpdate"
    />
    <!-- 腾讯地图 SDK -->
    <TencentMapPicker
      v-else-if="useTencentMapSDK"
      ref="sdkMapRef"
      :model-value="displayCoordinate"
      :height="height"
      :readonly="readonly"
      :api-key="apiKeys.tencent || ''"
      @update:model-value="handleSDKCoordinateUpdate"
    />
    <!-- Leaflet 引擎（默认回退） -->
    <div
      v-else
      ref="leafletContainer"
      class="map-container"
      :style="{ height: height }"
    ></div>

    <!-- 坐标显示（始终显示 WGS84 坐标） -->
    <div class="coordinate-display">
      <span v-if="wgs84Coordinate">
        纬度: {{ wgs84Coordinate.lat.toFixed(6) }}, 经度: {{ wgs84Coordinate.lng.toFixed(6) }}
      </span>
      <span v-else class="no-coordinate">点击地图选择位置</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue'
import type { MapEngineType, Coordinate, SearchResult as SearchResultType, MapConfig } from '@/utils/mapTypes'
import { mapEngineNames, defaultMapConfig } from '@/utils/mapTypes'
import { mapEngineManager } from '@/utils/mapEngineManager'
import { getUserMapPreference } from '@/utils/mapConfig'
import { convertCoordinate, getCoordinateSystem } from '@/utils/coordinateTransform'
import { api } from '@/api/client'

// 引入 SDK 地图组件
import AMapPicker from './map/AMapPicker.vue'
import BMapPicker from './map/BMapPicker.vue'
import TencentMapPicker from './map/TencentMapPicker.vue'

// Props
interface Props {
  modelValue?: Coordinate
  height?: string
  readonly?: boolean
  showSearch?: boolean
  showSwitcher?: boolean
  availableMapsProp?: MapEngineType[]
  defaultMapProp?: MapEngineType
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({ lat: 39.9042, lng: 116.4074 }),
  height: '300px',
  readonly: false,
  showSearch: true,
  showSwitcher: true,
  availableMapsProp: () => ['amap', 'baidu', 'tencent', 'tianditu', 'osm'],
  defaultMapProp: 'amap'
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [coordinate: Coordinate]
  'addressSelected': [result: { address: string; lat: number; lng: number }]
  'mapChange': [mapEngine: MapEngineType]
}>()

// 响应式数据
const leafletContainer = ref<HTMLElement | null>(null)
const sdkMapRef = ref<any>(null)
const currentMap = ref<MapEngineType>('amap')
const searchQuery = ref('')
const searchResults = ref<SearchResultType[]>([])
const searchLoading = ref(false)
const availableMaps = ref<MapEngineType[]>(props.availableMapsProp)
const apiKeys = ref<{
  amap?: string
  amapSecurity?: string
  baidu?: string
  tencent?: string
  tianditu?: { token: string; type: 'vec' | 'img' }
}>({})

// 核心坐标状态：始终使用 WGS84 坐标系
const wgs84Coordinate = ref<Coordinate | null>(null)

// Leaflet 引擎相关
let markerId: any = null
let currentLeafletEngine: any = null

// 配置加载状态
const configLoaded = ref(false)

// 计算是否使用 SDK
const useAMapSDK = computed(() => {
  return currentMap.value === 'amap' && !!apiKeys.value.amap
})

const useBMapSDK = computed(() => {
  return currentMap.value === 'baidu' && !!apiKeys.value.baidu
})

const useTencentMapSDK = computed(() => {
  return currentMap.value === 'tencent' && !!apiKeys.value.tencent
})

const useLeaflet = computed(() => {
  return !useAMapSDK.value && !useBMapSDK.value && !useTencentMapSDK.value
})

// 计算当前地图需要显示的坐标（从 WGS84 转换到当前地图坐标系）
const displayCoordinate = computed(() => {
  if (!wgs84Coordinate.value) {
    return props.modelValue || { lat: 39.9042, lng: 116.4074 }
  }

  const coordSystem = getCoordinateSystem(currentMap.value)
  if (coordSystem === 'wgs84') {
    // WGS84 地图，直接返回
    return wgs84Coordinate.value
  } else if (coordSystem === 'gcj02') {
    // 转换为 GCJ02（高德/腾讯）
    return convertCoordinate(
      wgs84Coordinate.value.lat,
      wgs84Coordinate.value.lng,
      'wgs84',
      'gcj02'
    )
  } else {
    // 转换为 BD09（百度）
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
  if (userMap && availableMaps.value.includes(userMap)) {
    currentMap.value = userMap
  } else {
    currentMap.value = props.defaultMapProp
  }

  // 初始化 WGS84 坐标
  if (props.modelValue && props.modelValue.lat && props.modelValue.lng) {
    wgs84Coordinate.value = props.modelValue
  }

  // 如果使用 Leaflet，初始化 Leaflet 地图
  if (useLeaflet.value) {
    await nextTick()
    await initLeafletMap()
  }
})

// 卸载时销毁
onUnmounted(() => {
  mapEngineManager.destroy()
})

// 从后端加载地图配置
async function loadMapConfig() {
  try {
    const backendMapConfig = await api.get('/admin/map-config')
    console.log('[MapPicker] 获取到的后端配置:', backendMapConfig)

    if (backendMapConfig) {
      availableMaps.value = backendMapConfig.available_maps || props.availableMapsProp
      apiKeys.value = {
        amap: backendMapConfig.map_api_keys?.amap || undefined,
        amapSecurity: backendMapConfig.map_api_keys?.amap_security || undefined,
        baidu: backendMapConfig.map_api_keys?.baidu || undefined,
        tencent: backendMapConfig.map_api_keys?.tencent || undefined,
        tianditu: backendMapConfig.map_api_keys?.tianditu || undefined
      }
    }
  } catch (e) {
    console.warn('[MapPicker] 获取地图配置失败，使用默认配置:', e)
  } finally {
    configLoaded.value = true
  }
}

// 初始化 Leaflet 地图
async function initLeafletMap() {
  if (!leafletContainer.value) return

  const coord = displayCoordinate.value

  const config: MapConfig = {
    ...defaultMapConfig,
    availableMaps: availableMaps.value,
    defaultMap: currentMap.value,
    mapApiKeys: apiKeys.value
  }

  mapEngineManager.setConfig(config)

  // 加载引擎
  currentLeafletEngine = await mapEngineManager.loadEngine(
    currentMap.value,
    leafletContainer.value,
    {
      center: [coord.lat, coord.lng],
      zoom: 13,
      enableClick: !props.readonly,
      enableDrag: !props.readonly
    }
  )

  // 绑定事件
  currentLeafletEngine.on('click', handleLeafletClick)
  currentLeafletEngine.on('markerDragend', handleLeafletMarkerDrag)

  // 设置初始标记
  if (wgs84Coordinate.value) {
    setLeafletMarker(displayCoordinate.value)
  }
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

// 处理 SDK 地图坐标更新（SDK 返回的是当前地图坐标系坐标）
function handleSDKCoordinateUpdate(coord: Coordinate) {
  if (props.readonly) return

  // 转换为 WGS84
  const wgs84 = convertToWGS84(coord)
  wgs84Coordinate.value = wgs84
  emit('update:modelValue', wgs84)
}

// 切换地图（不改变 WGS84 坐标）
async function switchMap(mapType: MapEngineType) {
  if (mapType === currentMap.value) return

  // 销毁 Leaflet 引擎（如果存在）
  if (currentLeafletEngine) {
    mapEngineManager.destroy()
    currentLeafletEngine = null
    markerId = null
  }

  currentMap.value = mapType

  // 等待视图更新
  await nextTick()

  // 如果使用 Leaflet，初始化 Leaflet 地图
  if (useLeaflet.value) {
    await initLeafletMap()
  }

  // 触发地图切换事件
  emit('mapChange', mapType)
}

// 搜索地址
async function searchAddress() {
  if (!searchQuery.value.trim()) return

  searchLoading.value = true
  searchResults.value = []

  try {
    let results: SearchResultType[] = []

    // 优先使用 SDK 地图的搜索
    if (sdkMapRef.value && sdkMapRef.value.searchAddress) {
      results = await sdkMapRef.value.searchAddress(searchQuery.value)
    } else if (currentLeafletEngine) {
      // 使用 Leaflet 引擎的搜索
      results = await currentLeafletEngine.searchAddress(searchQuery.value)
    }

    searchResults.value = results
  } catch (error) {
    console.error('[MapPicker] 搜索失败:', error)
  } finally {
    searchLoading.value = false
  }
}

// 选择搜索结果（搜索结果通常是 WGS84 坐标）
function selectSearchResult(result: SearchResultType) {
  // 搜索结果通常是 WGS84 坐标，直接使用
  const wgs84 = { lat: result.lat, lng: result.lng }
  wgs84Coordinate.value = wgs84
  emit('update:modelValue', wgs84)
  emit('addressSelected', {
    address: result.address,
    lat: wgs84.lat,
    lng: wgs84.lng
  })

  // 设置标记（需要转换为当前地图坐标系）
  if (useLeaflet.value && currentLeafletEngine) {
    setLeafletMarker(displayCoordinate.value)
    currentLeafletEngine.setCenter(displayCoordinate.value.lat, displayCoordinate.value.lng)
  }

  // 清除搜索结果
  searchResults.value = []
  searchQuery.value = ''
}

// 监听 v-model 变化（外部传入的应该是 WGS84 坐标）
watch(() => props.modelValue, (newVal) => {
  if (newVal && newVal.lat && newVal.lng) {
    if (!wgs84Coordinate.value ||
        wgs84Coordinate.value.lat !== newVal.lat ||
        wgs84Coordinate.value.lng !== newVal.lng) {
      wgs84Coordinate.value = newVal
      if (useLeaflet.value && currentLeafletEngine) {
        setLeafletMarker(displayCoordinate.value)
      }
    }
  }
}, { deep: true })
</script>

<style scoped>
.map-picker {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.map-switcher {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.map-btn {
  padding: 0.375rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  background: #fff;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.map-btn:hover {
  background: #f5f5f5;
}

.map-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.search-bar {
  display: flex;
  gap: 0.5rem;
}

.search-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.search-btn {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.search-btn:hover:not(:disabled) {
  background: #5a6fd8;
}

.search-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.search-results {
  max-height: 150px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
}

.search-result-item {
  padding: 0.5rem;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover {
  background: #f5f5f5;
}

.result-name {
  display: block;
  font-weight: 500;
  color: #333;
  font-size: 0.875rem;
}

.result-address {
  display: block;
  color: #666;
  font-size: 0.75rem;
}

.map-container {
  width: 100%;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #ddd;
}

.coordinate-display {
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #666;
  text-align: center;
}

.no-coordinate {
  color: #999;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .map-btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.8125rem;
  }

  .search-bar {
    flex-direction: column;
  }

  .search-btn {
    width: 100%;
  }
}
</style>