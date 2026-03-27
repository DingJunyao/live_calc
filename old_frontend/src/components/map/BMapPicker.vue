<template>
  <div class="bmap-picker">
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
let multiMarkers: any[] = []  // 多标记数组
let isMapReady = false
let BMap: any = null

// 加载百度地图 JS API
async function loadBMapScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    // GL 版本
    if ((window as any).BMapGL) {
      resolve()
      return
    }

    // Legacy 版本
    if ((window as any).BMap) {
      resolve()
      return
    }

    if (!props.apiKey) {
      reject(new Error('Baidu Map API Key is required'))
      return
    }

    // 使用 JSONP 方式加载
    const callbackName = 'initBMapPickerCallback'
    ;(window as any)[callbackName] = () => resolve()

    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.async = true
    script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${props.apiKey}&callback=${callbackName}`
    script.onerror = () => reject(new Error('Failed to load Baidu Map script'))

    document.head.appendChild(script)
  })
}

// 等待 BMap 就绪
function waitForBMap(): Promise<void> {
  return new Promise((resolve) => {
    const check = () => {
      // 优先使用 GL 版本
      if ((window as any).BMapGL) {
        BMap = (window as any).BMapGL
        resolve()
      } else if ((window as any).BMap) {
        BMap = (window as any).BMap
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
    console.log('[BMapPicker] 容器不存在')
    return
  }

  console.log('[BMapPicker] 开始初始化...')
  console.log('[BMapPicker] apiKey:', props.apiKey)

  // 检查容器尺寸
  const rect = mapContainer.value.getBoundingClientRect()
  console.log('[BMapPicker] 容器尺寸:', rect.width, 'x', rect.height)

  if (rect.width === 0 || rect.height === 0) {
    console.warn('[BMapPicker] 容器尺寸为 0，延迟初始化')
    setTimeout(() => initMap(), 200)
    return
  }

  try {
    await loadBMapScript()
    await waitForBMap()

    console.log('[BMapPicker] BMap 脚本加载完成')

    // 使用固定默认中心点
    const centerLng = 116.4074
    const centerLat = 39.9042

    console.log('[BMapPicker] 创建地图实例，中心点:', centerLng, centerLat)

    const center = new BMap.Point(centerLng, centerLat)

    // 创建地图实例
    mapInstance = new BMap.Map(mapContainer.value)
    mapInstance.centerAndZoom(center, 13)

    // 启用滚轮缩放
    mapInstance.enableScrollWheelZoom(true)

    // 添加点击事件
    mapInstance.addEventListener('click', (e: any) => {
      if (props.readonly) return

      // 百度地图事件对象可能有多种属性名，兼容处理
      let lat: number | undefined
      let lng: number | undefined

      if (e.latLng) {
        lat = e.latLng.lat
        lng = e.latLng.lng
      } else if (e.latlng) {
        lat = e.latlng.lat
        lng = e.latlng.lng
      } else if (e.point) {
        lat = e.point.lat
        lng = e.point.lng
      }

      if (lat !== undefined && lng !== undefined) {
        const coord = { lat, lng }
        setMarker(coord)
        currentCoordinate.value = coord
        emit('update:modelValue', coord)
      }
    })

    isMapReady = true
    console.log('[BMapPicker] 地图初始化成功')

    // 渲染多标记（如果有）
    if (props.markers && props.markers.length > 0) {
      console.log('[BMapPicker] 渲染多标记:', props.markers.length, '个')
      updateMarkers(props.markers)
    }
  } catch (error) {
    console.error('[BMapPicker] 初始化地图失败:', error)
    if (mapContainer.value) {
      mapContainer.value.textContent = '百度地图加载失败'
      mapContainer.value.style.cssText = 'padding: 20px; color: #999; text-align: center;'
    }
  }
}

// 设置标记
function setMarker(coord: Coordinate) {
  if (!mapInstance || !isMapReady || !BMap) return

  // 移除旧标记
  if (markerInstance) {
    mapInstance.removeOverlay(markerInstance)
  }

  // 创建新标记
  const point = new BMap.Point(coord.lng, coord.lat)
  markerInstance = new BMap.Marker(point, {
    enableDragging: !props.readonly
  })

  mapInstance.addOverlay(markerInstance)

  // 监听拖拽事件
  if (!props.readonly) {
    markerInstance.addEventListener('dragend', (e: any) => {
      // 兼容不同版本的事件对象
      let lat: number | undefined
      let lng: number | undefined

      if (e.point) {
        lat = e.point.lat
        lng = e.point.lng
      } else if (e.latLng) {
        lat = e.latLng.lat
        lng = e.latLng.lng
      } else if (e.latlng) {
        lat = e.latlng.lat
        lng = e.latlng.lng
      }

      if (lat !== undefined && lng !== undefined) {
        const newCoord = { lat, lng }
        currentCoordinate.value = newCoord
        emit('update:modelValue', newCoord)
      }
    })
  }

  // 更新当前坐标
  currentCoordinate.value = coord

  // 移动地图中心
  mapInstance.setCenter(point)
}

// 更新多标记（用于商家地图等场景）
function updateMarkers(markers: MarkerData[]) {
  if (!mapInstance || !isMapReady || !BMap) {
    console.log('[BMapPicker] updateMarkers: 地图未就绪')
    return
  }

  console.log('[BMapPicker] updateMarkers: 处理', markers.length, '个标记')

  // 清除旧的多标记
  multiMarkers.forEach(m => mapInstance.removeOverlay(m))
  multiMarkers = []

  // 添加新标记 - 使用简单默认标记
  markers.forEach(marker => {
    console.log('[BMapPicker] 处理标记:', marker.name, marker.lat, marker.lng)

    if (!isValidCoordinate(marker.lat, marker.lng)) {
      console.warn('[BMapPicker] 无效坐标，跳过:', marker.name)
      return
    }

    const point = new BMap.Point(marker.lng, marker.lat)
    const markerObj = new BMap.Marker(point)
    mapInstance.addOverlay(markerObj)
    multiMarkers.push(markerObj)
  })

  console.log('[BMapPicker] 成功添加', multiMarkers.length, '个标记')
}

// 检查坐标是否有效
function isValidCoordinate(lat: number, lng: number): boolean {
  return typeof lat === 'number' && typeof lng === 'number' &&
         !isNaN(lat) && !isNaN(lng) &&
         lat !== 0 && lng !== 0
}

// 缩放到所有标记范围
function fitMarkers() {
  console.log('[BMapPicker] fitMarkers 被调用')

  if (!mapInstance || !isMapReady) {
    console.log('[BMapPicker] fitMarkers: 地图未就绪')
    return
  }

  // 使用 multiMarkers 中已添加的标记来计算范围
  if (multiMarkers.length === 0) {
    console.log('[BMapPicker] fitMarkers: 没有标记')
    return
  }

  console.log('[BMapPicker] fitMarkers: 缩放到', multiMarkers.length, '个标记')

  try {
    // 重新获取 BMap（确保可用）
    const currentBMap = (window as any).BMapGL || (window as any).BMap
    if (!currentBMap) {
      console.error('[BMapPicker] BMap 不可用')
      return
    }

    // 获取所有标记的位置
    const points: any[] = []
    multiMarkers.forEach(marker => {
      const pos = marker.getPosition()
      console.log('[BMapPicker] 标记位置:', pos)
      if (pos && typeof pos.lng === 'number' && typeof pos.lat === 'number' &&
          !isNaN(pos.lng) && !isNaN(pos.lat)) {
        points.push(new currentBMap.Point(pos.lng, pos.lat))
      }
    })

    if (points.length === 0) {
      console.log('[BMapPicker] fitMarkers: 没有有效坐标')
      return
    }

    console.log('[BMapPicker] fitMarkers: 计算 viewport，', points.length, '个点')
    const viewport = mapInstance.getViewport(points)
    mapInstance.centerAndZoom(viewport.center, viewport.zoom)
    console.log('[BMapPicker] fitMarkers: 成功')
  } catch (e) {
    console.error('[BMapPicker] fitMarkers 失败:', e)
  }
}

// 搜索地址
async function searchAddress(query: string): Promise<SearchResult[]> {
  if (!query || !props.apiKey) return []

  try {
    const url = `https://api.map.baidu.com/place/v2/search?query=${encodeURIComponent(query)}&region=全国&output=json&ak=${props.apiKey}`
    const response = await fetch(url)
    const data = await response.json()

    if (data.results && data.results.length > 0) {
      return data.results.slice(0, 5).map((poi: any) => ({
        address: poi.address || poi.name,
        lat: poi.location.lat,
        lng: poi.location.lng,
        name: poi.name
      }))
    }
  } catch (error) {
    console.error('[BMapPicker] 地址搜索失败:', error)
  }

  return []
}

// 反向地理编码
async function reverseGeocode(lat: number, lng: number): Promise<string> {
  if (!props.apiKey) return ''

  try {
    const url = `https://api.map.baidu.com/reverse_geocoding/v3/?ak=${props.apiKey}&output=json&coordtype=wgs84ll&location=${lat},${lng}`
    const response = await fetch(url)
    const data = await response.json()

    if (data.result && data.result.formatted_address) {
      return data.result.formatted_address
    }
  } catch (error) {
    console.error('[BMapPicker] 反向地理编码失败:', error)
  }

  return ''
}

// 设置中心点
function setCenter(lat: number, lng: number) {
  if (mapInstance && isMapReady && BMap) {
    mapInstance.setCenter(new BMap.Point(lng, lat))
  }
}

// 销毁地图
function destroyMap() {
  // 清除多标记
  multiMarkers.forEach(m => mapInstance?.removeOverlay(m))
  multiMarkers = []
  // 清除单标记
  if (markerInstance) {
    mapInstance?.removeOverlay(markerInstance)
    markerInstance = null
  }
  if (mapInstance) {
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
  console.log('[BMapPicker] apiKey 变化:', oldVal, '->', newVal)
  if (newVal && newVal !== oldVal) {
    destroyMap()
    nextTick(() => initMap())
  }
})

// 监听 markers 变化
watch(() => props.markers, (newVal) => {
  console.log('[BMapPicker] markers 变化:', newVal?.length, '个')
  if (isMapReady && newVal && newVal.length > 0) {
    setTimeout(() => updateMarkers(newVal), 100)
  }
}, { deep: true })

onMounted(() => {
  console.log('[BMapPicker] onMounted, apiKey:', props.apiKey)
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
.bmap-picker {
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