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
interface Props {
  modelValue?: Coordinate
  height?: string
  readonly?: boolean
  apiKey?: string
  securityCode?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({ lat: 39.9042, lng: 116.4074 }),
  height: '300px',
  readonly: false,
  apiKey: '',
  securityCode: ''
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

// 加载高德地图 JS API
async function loadAMapScript(): Promise<void> {
  return new Promise((resolve, reject) => {
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

    script.src = `https://webapi.amap.com/maps?v=2.0&key=${props.apiKey}`
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
  if (!mapContainer.value) return

  try {
    await loadAMapScript()
    await waitForAMap()

    const AMap = (window as any).AMap
    const center = props.modelValue && props.modelValue.lat && props.modelValue.lng
      ? [props.modelValue.lng, props.modelValue.lat]  // 高德使用 [lng, lat]
      : [116.4074, 39.9042]

    // 创建地图实例
    mapInstance = new AMap.Map(mapContainer.value, {
      zoom: 13,
      center: center,
      viewMode: '2D'
    })

    // 添加点击事件
    mapInstance.on('click', (e: any) => {
      if (props.readonly) return

      const coord = { lat: e.lnglat.lat, lng: e.lnglat.lng }
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
    console.error('[AMapPicker] 初始化地图失败:', error)
    if (mapContainer.value) {
      // 使用 textContent 替代 innerHTML 避免安全问题
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
.amap-picker {
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