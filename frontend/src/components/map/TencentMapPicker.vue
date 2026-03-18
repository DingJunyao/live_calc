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
  if (!mapContainer.value) return

  try {
    await loadTMapScript()
    await waitForTMap()

    const TMap = (window as any).TMap
    const center = props.modelValue && props.modelValue.lat && props.modelValue.lng
      ? new TMap.LatLng(props.modelValue.lat, props.modelValue.lng)
      : new TMap.LatLng(39.9042, 116.4074)

    // 创建地图实例
    mapInstance = new TMap.Map(mapContainer.value, {
      zoom: 13,
      center: center,
      viewMode: '2D'
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

    // 如果有初始坐标，显示标记
    if (props.modelValue && props.modelValue.lat && props.modelValue.lng) {
      setMarker(props.modelValue)
      currentCoordinate.value = props.modelValue
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
.tencent-map-picker {
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