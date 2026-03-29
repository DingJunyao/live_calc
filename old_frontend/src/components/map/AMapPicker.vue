<template>
  <div class="amap-picker">
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
  securityCode?: string
  markers?: MarkerData[]  // 多标记支持（用于地图展示多个点）
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({ lat: 39.9042, lng: 116.4074 }),
  height: '300px',
  readonly: false,
  apiKey: '',
  securityCode: '',
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

// 加载高德地图 JS API
async function loadAMapScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    // 使用 v1.4 版本，更稳定
    if ((window as any).AMap) {
      resolve()
      return
    }

    if (!props.apiKey) {
      reject(new Error('AMap API Key is required'))
      return
    }

    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.async = true

    // 设置安全密钥
    if (props.securityCode) {
      (window as any)._AMapSecurityConfig = {
        securityJsCode: props.securityCode
      }
    }

    // 使用 v1.4.15 版本（更稳定）
    script.src = `https://webapi.amap.com/maps?v=1.4.15&key=${props.apiKey}`
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load AMap script'))

    document.head.appendChild(script)
  })
}

// 等待 AMap 就绪
function waitForAMap(): Promise<void> {
  return new Promise((resolve) => {
    const check = () => {
      if ((window as any).AMap) {
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
    console.log('[AMapPicker] 容器不存在')
    return
  }

  console.log('[AMapPicker] 开始初始化...')
  console.log('[AMapPicker] apiKey:', props.apiKey)
  console.log('[AMapPicker] modelValue:', props.modelValue)
  console.log('[AMapPicker] markers:', props.markers)

  try {
    await loadAMapScript()
    await waitForAMap()

    console.log('[AMapPicker] AMap 脚本加载完成')

    // 检查容器尺寸
    const rect = mapContainer.value.getBoundingClientRect()
    console.log('[AMapPicker] 容器尺寸:', rect.width, 'x', rect.height)

    const AMap = (window as any).AMap

    // 使用固定的默认中心点
    const centerLng = 116.4074
    const centerLat = 39.9042

    console.log('[AMapPicker] 创建地图实例，中心点:', centerLng, centerLat)

    // 创建地图实例
    mapInstance = new AMap.Map(mapContainer.value, {
      zoom: 13,
      center: [centerLng, centerLat],
      viewMode: '2D'
    })

    console.log('[AMapPicker] 地图实例创建成功')

    // 添加点击事件
    mapInstance.on('click', (e: any) => {
      if (props.readonly) return
      const coord = { lat: e.lnglat.lat, lng: e.lnglat.lng }
      setMarker(coord)
      currentCoordinate.value = coord
      emit('update:modelValue', coord)
    })

    isMapReady = true

    // 渲染多标记（如果有）
    if (props.markers && props.markers.length > 0) {
      console.log('[AMapPicker] 渲染多标记:', props.markers.length, '个')
      updateMarkers(props.markers)
    }
  } catch (error) {
    console.error('[AMapPicker] 初始化地图失败:', error)
    if (mapContainer.value) {
      mapContainer.value.textContent = '高德地图加载失败'
      mapContainer.value.style.cssText = 'padding: 20px; color: #999; text-align: center;'
    }
  }
}

// 设置标记
function setMarker(coord: Coordinate) {
  if (!mapInstance || !isMapReady) return

  const AMap = (window as any).AMap

  // 移除旧标记
  if (markerInstance) {
    mapInstance.remove(markerInstance)
  }

  // 创建新标记
  markerInstance = new AMap.Marker({
    position: [coord.lng, coord.lat],  // 高德使用 [lng, lat]
    draggable: !props.readonly
  })

  mapInstance.add(markerInstance)

  // 监听拖拽事件
  if (!props.readonly) {
    markerInstance.on('dragend', (e: any) => {
      const pos = e.target.getPosition()
      const newCoord = { lat: pos.lat, lng: pos.lng }
      currentCoordinate.value = newCoord
      emit('update:modelValue', newCoord)
    })
  }

  // 更新当前坐标
  currentCoordinate.value = coord

  // 移动地图中心
  mapInstance.setCenter([coord.lng, coord.lat])
}

// 更新多标记（用于商家地图等场景）
function updateMarkers(markers: MarkerData[]) {
  if (!mapInstance || !isMapReady) {
    console.log('[AMapPicker] updateMarkers: 地图未就绪')
    return
  }

  const AMap = (window as any).AMap

  // 清除旧的多标记
  multiMarkers.forEach(m => mapInstance.remove(m))
  multiMarkers = []

  console.log('[AMapPicker] updateMarkers: 处理', markers.length, '个标记')

  // 添加新标记 - 使用简单的默认标记
  markers.forEach(marker => {
    console.log('[AMapPicker] 处理标记:', marker.name, marker.lat, marker.lng)

    // 检查坐标有效性
    if (!isValidCoordinate(marker.lat, marker.lng)) {
      console.warn('[AMapPicker] 无效坐标，跳过:', marker.name, marker.lat, marker.lng)
      return
    }

    // 使用简单的默认标记，不带自定义 HTML
    const markerObj = new AMap.Marker({
      position: [marker.lng, marker.lat],
      title: marker.name  // 使用 title 而非 setContent
    })

    mapInstance.add(markerObj)
    multiMarkers.push(markerObj)
  })

  console.log('[AMapPicker] 成功添加', multiMarkers.length, '个标记')
}

// 检查坐标是否有效
function isValidCoordinate(lat: number, lng: number): boolean {
  return typeof lat === 'number' && typeof lng === 'number' &&
         !isNaN(lat) && !isNaN(lng) &&
         lat !== 0 && lng !== 0
}

// 缩放到所有标记范围
function fitMarkers() {
  console.log('[AMapPicker] fitMarkers 被调用')

  if (!mapInstance || !isMapReady) {
    console.log('[AMapPicker] fitMarkers: 地图未就绪')
    return
  }

  // 使用 multiMarkers 中已添加的标记来计算范围，而不是 props.markers
  if (multiMarkers.length === 0) {
    console.log('[AMapPicker] fitMarkers: 没有标记')
    return
  }

  console.log('[AMapPicker] fitMarkers: 缩放到', multiMarkers.length, '个标记')

  try {
    // 获取所有标记的位置并构建 bounds
    let minLng = Infinity, maxLng = -Infinity
    let minLat = Infinity, maxLat = -Infinity

    multiMarkers.forEach(marker => {
      const pos = marker.getPosition()
      console.log('[AMapPicker] 标记位置:', pos)
      // 高德地图 getPosition 返回 {lng, lat}
      if (pos && typeof pos.lng === 'number' && typeof pos.lat === 'number' &&
          !isNaN(pos.lng) && !isNaN(pos.lat)) {
        minLng = Math.min(minLng, pos.lng)
        maxLng = Math.max(maxLng, pos.lng)
        minLat = Math.min(minLat, pos.lat)
        maxLat = Math.max(maxLat, pos.lat)
      }
    })

    if (minLng === Infinity) {
      console.log('[AMapPicker] fitMarkers: 没有有效坐标')
      return
    }

    console.log('[AMapPicker] fitMarkers: 范围', minLng, minLat, '-', maxLng, maxLat)

    // 使用 setZoomAndCenter 设置范围
    const centerLng = (minLng + maxLng) / 2
    const centerLat = (minLat + maxLat) / 2
    mapInstance.setZoomAndCenter(14, [centerLng, centerLat])
    console.log('[AMapPicker] fitMarkers: 成功')
  } catch (e) {
    console.error('[AMapPicker] fitMarkers 失败:', e)
  }
}

// 搜索地址
async function searchAddress(query: string): Promise<SearchResult[]> {
  if (!query || !props.apiKey) return []

  try {
    const url = `https://restapi.amap.com/v3/place/text?keywords=${encodeURIComponent(query)}&city=全国&output=json&key=${props.apiKey}`
    const response = await fetch(url)
    const data = await response.json()

    if (data.pois && data.pois.length > 0) {
      return data.pois.slice(0, 5).map((poi: any) => ({
        address: poi.address || poi.name,
        lat: parseFloat(poi.location.split(',')[1]),
        lng: parseFloat(poi.location.split(',')[0]),
        name: poi.name
      }))
    }
  } catch (error) {
    console.error('[AMapPicker] 地址搜索失败:', error)
  }

  return []
}

// 反向地理编码
async function reverseGeocode(lat: number, lng: number): Promise<string> {
  if (!props.apiKey) return ''

  try {
    const url = `https://restapi.amap.com/v3/geocode/regeo?key=${props.apiKey}&location=${lng},${lat}&output=json`
    const response = await fetch(url)
    const data = await response.json()

    if (data.regeocode && data.regeocode.formatted_address) {
      return data.regeocode.formatted_address
    }
  } catch (error) {
    console.error('[AMapPicker] 反向地理编码失败:', error)
  }

  return ''
}

// 设置中心点
function setCenter(lat: number, lng: number) {
  if (mapInstance && isMapReady) {
    mapInstance.setCenter([lng, lat])
  }
}

// 销毁地图
function destroyMap() {
  // 清除多标记
  multiMarkers.forEach(m => mapInstance?.remove(m))
  multiMarkers = []
  // 清除单标记
  if (markerInstance) {
    mapInstance?.remove(markerInstance)
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
  console.log('[AMapPicker] apiKey 变化:', oldVal, '->', newVal)
  if (newVal && newVal !== oldVal) {
    destroyMap()
    nextTick(() => initMap())
  }
})

// 监听 markers 变化
watch(() => props.markers, (newVal) => {
  console.log('[AMapPicker] markers 变化:', newVal?.length, '个')
  if (isMapReady && newVal && newVal.length > 0) {
    // 延迟更新标记
    setTimeout(() => updateMarkers(newVal), 100)
  }
}, { deep: true })

onMounted(() => {
  console.log('[AMapPicker] onMounted, apiKey:', props.apiKey)
  if (props.apiKey) {
    // 延迟初始化，确保 DOM 完全渲染
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
.amap-picker {
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