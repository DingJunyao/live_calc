<template>
  <div class="tencent-map-picker">
    <!-- 地图容器 -->
    <div ref="mapContainer" class="map-container" :style="{ height: height }"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import type { Coordinate, SearchResult } from '@/utils/mapTypes'

// Props
interface MarkerData {
  id: number | string
  lat: number
  lng: number
  name: string
  selected?: boolean
}

interface Props {
  modelValue?: Coordinate
  height?: string
  readonly?: boolean
  apiKey?: string
  markers?: MarkerData[]  // 多标记支持（用于地图展示多个点）
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({ lat: 39.9042, lng: 116.4074 }),
  height: '300px',
  readonly: false,
  apiKey: '',
  markers: () => []
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [coordinate: Coordinate]
  'addressSelected': [result: { address: string; lat: number; lng: number }]
}>()

// 响应式数据
const mapContainer = ref<HTMLElement | null>(null)
const currentCoordinate = ref<Coordinate | null>(null)

// 地图实例和标记
let mapInstance: any = null
let markerInstance: any = null
let multiMarkers: any[] = []  // 多标记数组（InfoWindow）
let isMapReady = false

// 加载腾讯地图 JS API
async function loadTMapScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).TMap) {
      resolve()
      return
    }

    if (!props.apiKey) {
      reject(new Error('Tencent Map API Key is required'))
      return
    }

    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.async = true
    script.src = `https://map.qq.com/api/gljs?v=1.exp&key=${props.apiKey}`
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Tencent Map script'))

    document.head.appendChild(script)
  })
}

// 等待 TMap 就绪
function waitForTMap(): Promise<void> {
  return new Promise((resolve) => {
    const check = () => {
      if ((window as any).TMap) {
        resolve()
      } else {
        setTimeout(check, 50)
      }
    }
    check()
  })
}

// 初始化地图
async function initMap() {
  if (!mapContainer.value) {
    console.log('[TencentMapPicker] 容器不存在')
    return
  }

  console.log('[TencentMapPicker] 开始初始化...')
  console.log('[TencentMapPicker] apiKey:', props.apiKey)

  // 检查容器尺寸
  const rect = mapContainer.value.getBoundingClientRect()
  console.log('[TencentMapPicker] 容器尺寸:', rect.width, 'x', rect.height)

  if (rect.width === 0 || rect.height === 0) {
    console.warn('[TencentMapPicker] 容器尺寸为 0，延迟初始化')
    setTimeout(() => initMap(), 200)
    return
  }

  try {
    await loadTMapScript()
    await waitForTMap()

    console.log('[TencentMapPicker] TMap 脚本加载完成')

    const TMap = (window as any).TMap

    // 使用固定默认中心点
    const centerLat = 39.9042
    const centerLng = 116.4074

    console.log('[TencentMapPicker] 创建地图实例')

    // 创建地图实例 - 隐藏默认控件以避免冲突
    mapInstance = new TMap.Map(mapContainer.value, {
      zoom: 13,
      center: new TMap.LatLng(centerLat, centerLng),
      viewMode: '2D',
      showControl: true  // 显示控件
    })

    // 添加点击事件
    mapInstance.on('click', (e: any) => {
      if (props.readonly) return

      const coord = { lat: e.latLng.lat, lng: e.latLng.lng }
      setMarker(coord)
      currentCoordinate.value = coord
      emit('update:modelValue', coord)
    })

    isMapReady = true
    console.log('[TencentMapPicker] 地图初始化成功')

    // 渲染多标记（如果有）
    if (props.markers && props.markers.length > 0) {
      console.log('[TencentMapPicker] 渲染多标记:', props.markers.length, '个')
      updateMarkers(props.markers)
    }
  } catch (error) {
    console.error('[TencentMapPicker] 初始化地图失败:', error)
    if (mapContainer.value) {
      mapContainer.value.textContent = '腾讯地图加载失败'
      mapContainer.value.style.cssText = 'padding: 20px; color: #999; text-align: center;'
    }
  }
}

// 设置标记（使用 MultiMarker）
function setMarker(coord: Coordinate) {
  if (!mapInstance || !isMapReady) return

  const TMap = (window as any).TMap

  // 移除旧标记
  if (markerInstance) {
    markerInstance.setMap(null)
    markerInstance = null
  }

  // 使用 MultiMarker 创建标记
  markerInstance = new TMap.MultiMarker({
    map: mapInstance,
    styles: {
      'marker': new TMap.MarkerStyle({
        width: 25,
        height: 35,
        anchor: { x: 12.5, y: 35 }
      })
    },
    geometries: [{
      id: 'marker1',
      styleId: 'marker',
      position: new TMap.LatLng(coord.lat, coord.lng)
    }]
  })

  // 更新当前坐标
  currentCoordinate.value = coord

  // 移动地图中心
  mapInstance.setCenter(new TMap.LatLng(coord.lat, coord.lng))
}

// 更新多标记（用于商家地图等场景）
function updateMarkers(markers: MarkerData[]) {
  if (!mapInstance || !isMapReady) {
    console.log('[TencentMapPicker] updateMarkers: 地图未就绪')
    return
  }

  console.log('[TencentMapPicker] updateMarkers: 处理', markers.length, '个标记')

  const TMap = (window as any).TMap

  // 清除旧的多标记
  multiMarkers.forEach(m => {
    if (m.setMap) m.setMap(null)
  })
  multiMarkers = []

  // 使用 MultiMarker 创建标记（更高效）
  const geometries: any[] = []
  markers.forEach(marker => {
    console.log('[TencentMapPicker] 处理标记:', marker.name, marker.lat, marker.lng)

    if (!isValidCoordinate(marker.lat, marker.lng)) {
      console.warn('[TencentMapPicker] 无效坐标，跳过:', marker.name)
      return
    }

    geometries.push({
      id: `marker_${marker.id}`,
      styleId: 'marker',
      position: new TMap.LatLng(marker.lat, marker.lng)
    })
  })

  if (geometries.length > 0) {
    const multiMarker = new TMap.MultiMarker({
      map: mapInstance,
      styles: {
        'marker': new TMap.MarkerStyle({
          width: 25,
          height: 35,
          anchor: { x: 12.5, y: 35 }
        })
      },
      geometries: geometries
    })
    multiMarkers.push(multiMarker)
  }

  console.log('[TencentMapPicker] 成功添加', geometries.length, '个标记')
}

// 缩放到所有标记范围
function fitMarkers() {
  console.log('[TencentMapPicker] fitMarkers 被调用')

  if (!mapInstance || !isMapReady) {
    console.log('[TencentMapPicker] fitMarkers: 地图未就绪')
    return
  }

  // 使用 multiMarkers 中已添加的标记来计算范围
  if (multiMarkers.length === 0) {
    console.log('[TencentMapPicker] fitMarkers: 没有标记')
    return
  }

  console.log('[TencentMapPicker] fitMarkers: 缩放')

  try {
    const TMap = (window as any).TMap
    const bounds = new TMap.LatLngBounds()

    // 从 multiMarkers 获取位置（MultiMarker 的 geometries）
    let hasValidCoord = false

    // 尝试从每个 MultiMarker 获取几何信息
    multiMarkers.forEach((multiMarker: any) => {
      if (multiMarker.getGeometries) {
        const geometries = multiMarker.getGeometries()
        geometries.forEach((geo: any) => {
          if (geo.position) {
            bounds.extend(geo.position)
            hasValidCoord = true
          }
        })
      }
    })

    if (!hasValidCoord) {
      console.log('[TencentMapPicker] fitMarkers: 没有有效坐标')
      return
    }

    mapInstance.fitBounds(bounds, { padding: 50 })
    console.log('[TencentMapPicker] fitMarkers: 成功')
  } catch (e) {
    console.error('[TencentMapPicker] fitMarkers 失败:', e)
  }
}

// 检查坐标是否有效
function isValidCoordinate(lat: number, lng: number): boolean {
  return typeof lat === 'number' && typeof lng === 'number' &&
         !isNaN(lat) && !isNaN(lng) &&
         lat !== 0 && lng !== 0
}

// 搜索地址
async function searchAddress(query: string): Promise<SearchResult[]> {
  if (!query || !props.apiKey) return []

  try {
    const url = `https://apis.map.qq.com/ws/place/v1/search?keyword=${encodeURIComponent(query)}&region=全国&output=json&key=${props.apiKey}`
    const response = await fetch(url)
    const data = await response.json()

    if (data.data && data.data.length > 0) {
      return data.data.slice(0, 5).map((poi: any) => ({
        address: poi.address || poi.title,
        lat: poi.location.lat,
        lng: poi.location.lng,
        name: poi.title
      }))
    }
  } catch (error) {
    console.error('[TencentMapPicker] 地址搜索失败:', error)
  }

  return []
}

// 反向地理编码
async function reverseGeocode(lat: number, lng: number): Promise<string> {
  if (!props.apiKey) return ''

  try {
    const url = `https://apis.map.qq.com/ws/geocoder/v1/?location=${lat},${lng}&key=${props.apiKey}&output=json`
    const response = await fetch(url)
    const data = await response.json()

    if (data.result && data.result.address) {
      return data.result.address
    }
  } catch (error) {
    console.error('[TencentMapPicker] 反向地理编码失败:', error)
  }

  return ''
}

// 设置中心点
function setCenter(lat: number, lng: number) {
  if (mapInstance && isMapReady) {
    const TMap = (window as any).TMap
    mapInstance.setCenter(new TMap.LatLng(lat, lng))
  }
}

// 销毁地图
function destroyMap() {
  // 清除多标记
  multiMarkers.forEach(m => {
    if (m.setMap) m.setMap(null)
  })
  multiMarkers = []
  // 清除单标记
  if (markerInstance) {
    markerInstance.setMap(null)
    markerInstance = null
  }
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
  isMapReady = false
}

// 监听 modelValue 变化
watch(() => props.modelValue, (newVal) => {
  if (newVal && newVal.lat && newVal.lng && isMapReady) {
    if (!currentCoordinate.value ||
        currentCoordinate.value.lat !== newVal.lat ||
        currentCoordinate.value.lng !== newVal.lng) {
      setMarker(newVal)
    }
  }
}, { deep: true })

// 监听 apiKey 变化
watch(() => props.apiKey, (newVal, oldVal) => {
  console.log('[TencentMapPicker] apiKey 变化:', oldVal, '->', newVal)
  if (newVal && newVal !== oldVal) {
    destroyMap()
    nextTick(() => initMap())
  }
})

// 监听 markers 变化
watch(() => props.markers, (newVal) => {
  console.log('[TencentMapPicker] markers 变化:', newVal?.length, '个')
  if (isMapReady && newVal && newVal.length > 0) {
    setTimeout(() => updateMarkers(newVal), 100)
  }
}, { deep: true })

onMounted(() => {
  console.log('[TencentMapPicker] onMounted, apiKey:', props.apiKey)
  if (props.apiKey) {
    setTimeout(() => initMap(), 300)
  }
})

onUnmounted(() => {
  destroyMap()
})

// 暴露方法
defineExpose({
  searchAddress,
  reverseGeocode,
  setCenter,
  setMarker,
  updateMarkers,
  fitMarkers
})
</script>

<style scoped>
.tencent-map-picker {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #ddd;
}
</style>