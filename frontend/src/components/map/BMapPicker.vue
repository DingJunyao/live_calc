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
interface Props {
  modelValue?: Coordinate
  height?: string
  readonly?: boolean
  apiKey?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({ lat: 39.9042, lng: 116.4074 }),
  height: '300px',
  readonly: false,
  apiKey: ''
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
  if (!mapContainer.value) return

  try {
    await loadBMapScript()
    await waitForBMap()

    const center = props.modelValue && props.modelValue.lat && props.modelValue.lng
      ? new BMap.Point(props.modelValue.lng, props.modelValue.lat)  // 百度使用 [lng, lat]
      : new BMap.Point(116.4074, 39.9042)

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
        // GL 版本可能使用 latLng
        lat = e.latLng.lat
        lng = e.latLng.lng
      } else if (e.latlng) {
        // 某些版本使用 latlng
        lat = e.latlng.lat
        lng = e.latlng.lng
      } else if (e.point) {
        // Legacy 版本使用 point
        lat = e.point.lat
        lng = e.point.lng
      }

      if (lat !== undefined && lng !== undefined) {
        const coord = { lat, lng }
        setMarker(coord)
        currentCoordinate.value = coord
        emit('update:modelValue', coord)
      } else {
        console.warn('[BMapPicker] 无法获取点击坐标:', e)
      }
    })

    isMapReady = true

    // 如果有初始坐标，显示标记
    if (props.modelValue && props.modelValue.lat && props.modelValue.lng) {
      setMarker(props.modelValue)
      currentCoordinate.value = props.modelValue
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
  if (newVal && newVal !== oldVal) {
    destroyMap()
    nextTick(() => initMap())
  }
})

onMounted(() => {
  if (props.apiKey) {
    initMap()
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
  setMarker
})
</script>

<style scoped>
.bmap-picker {
  display: flex;
  flex-direction: column;
}

.map-container {
  width: 100%;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #ddd;
}
</style>