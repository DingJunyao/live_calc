<template>
  <PageHeader title="商家管理" :show-back="true">
    <template #extra>
      <button @click="showAddModal = true" class="btn-square add-btn" title="添加商家">
        <i class="mdi mdi-plus"></i>
      </button>
    </template>
  </PageHeader>

  <div class="merchant-map-page">
    <!-- 左侧/上方：商家列表 -->
    <div class="merchant-list-panel">
      <div class="search-filter">
        <input v-model="searchTerm" placeholder="搜索商家名称或地址..." class="search-input" />
        <button @click="loadMerchants" class="btn-search" title="搜索">
          <i class="mdi mdi-magnify"></i>
        </button>
      </div>

      <div v-if="loading" class="loading">加载中...</div>

      <div v-else-if="merchants.length === 0" class="empty-state">
        暂无商家记录
      </div>

      <div v-else class="merchant-list">
        <div
          v-for="merchant in merchants"
          :key="merchant.id"
          :class="['merchant-card', { active: selectedMerchantId === merchant.id }]"
          @click="selectMerchant(merchant)"
        >
          <div class="merchant-header">
            <h3>{{ merchant.name }}</h3>
            <div class="merchant-actions">
              <button @click.stop="editMerchant(merchant)" class="btn-edit" title="编辑">
                <i class="mdi mdi-pencil"></i>
              </button>
              <button @click.stop="deleteMerchant(merchant)" class="btn-delete" title="删除">
                <i class="mdi mdi-delete"></i>
              </button>
            </div>
          </div>
          <div class="merchant-info">
            <p v-if="merchant.address" class="merchant-address">{{ merchant.address }}</p>
          </div>
        </div>
      </div>

      <Pagination
        v-if="total > 0"
        :current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        @change-page="handlePageChange"
        @change-page-size="handlePageSizeChange"
      />
    </div>

    <!-- 右侧/下方：地图 -->
    <div class="merchant-map-panel" ref="mapPanelRef">
      <!-- 地图控件 -->
      <div class="map-controls">
        <!-- 地图切换按钮组（桌面端） -->
        <div class="desktop-layer-selector">
          <button
            v-for="map in availableMaps"
            :key="map.value"
            :class="['layer-btn', { active: currentMapLayer === map.value }]"
            @click="switchMapLayer(map.value)"
          >
            {{ map.label }}
          </button>
        </div>
        <!-- 地图切换下拉（移动端） -->
        <select v-model="currentMapLayer" class="mobile-layer-selector" @change="handleMapLayerChange">
          <option v-for="map in availableMaps" :key="map.value" :value="map.value">
            {{ map.label }}
          </option>
        </select>
        <!-- 居中按钮 -->
        <button @click="fitAllMerchants" class="control-btn" title="居中显示所有商家">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>
            <line x1="12" y1="2" x2="12" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="12" y1="16" x2="12" y2="22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="2" y1="12" x2="8" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="16" y1="12" x2="22" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
        <!-- 全屏按钮 -->
        <button @click="toggleFullscreen" class="control-btn" title="全屏">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>

      <!-- 地图容器 - 根据配置动态选择引擎 -->
      <!-- 高德地图 SDK -->
      <AMapPicker
        v-if="useAMapSDK"
        ref="sdkMapRef"
        :model-value="mapCenter"
        height="100%"
        :readonly="true"
        :api-key="apiKeys.amap || ''"
        :security-code="apiKeys.amapSecurity || ''"
        :markers="sdkMarkers"
        @update:model-value="handleSDKMapClick"
      />
      <!-- 百度地图 SDK -->
      <BMapPicker
        v-else-if="useBMapSDK"
        ref="sdkMapRef"
        :model-value="mapCenter"
        height="100%"
        :readonly="true"
        :api-key="apiKeys.baidu || ''"
        :markers="sdkMarkers"
        @update:model-value="handleSDKMapClick"
      />
      <!-- 腾讯地图 SDK -->
      <TencentMapPicker
        v-else-if="useTencentMapSDK"
        ref="sdkMapRef"
        :model-value="mapCenter"
        height="100%"
        :readonly="true"
        :api-key="apiKeys.tencent || ''"
        :markers="sdkMarkers"
        @update:model-value="handleSDKMapClick"
      />
      <!-- Leaflet 引擎（无 SDK Key 时回退） -->
      <div v-else ref="mapContainer" class="map-container"></div>
    </div>

    <!-- 添加/编辑商家模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingMerchant ? '编辑商家' : '添加商家' }}</h2>
        <form @submit.prevent="addMerchant">
          <div class="form-group">
            <label for="merchantName">商家名称:</label>
            <input v-model="newMerchant.name" type="text" id="merchantName" required />
          </div>
          <div class="form-group">
            <label for="address">地址:</label>
            <div class="address-input-group">
              <input v-model="newMerchant.address" type="text" id="address" class="address-input" />
              <button type="button" @click="searchAddressFromInput" class="search-address-btn" :disabled="!newMerchant.address.trim()">
                搜索地址
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>地图位置:</label>
            <MapPicker
              v-model="merchantCoordinate"
              height="300px"
              :show-search="false"
              :show-switcher="true"
              @address-selected="handleAddressSelected"
            />
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">{{ editingMerchant ? '更新' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'
import MapPicker from '@/components/MapPicker.vue'
import type { Coordinate, MapEngineType, MapConfig } from '@/utils/mapTypes'
import { mapEngineNames, defaultMapConfig } from '@/utils/mapTypes'
import { mapEngineManager } from '@/utils/mapEngineManager'
import { convertCoordinate, getCoordinateSystem } from '@/utils/coordinateTransform'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// 引入 SDK 地图组件
import AMapPicker from '@/components/map/AMapPicker.vue'
import BMapPicker from '@/components/map/BMapPicker.vue'
import TencentMapPicker from '@/components/map/TencentMapPicker.vue'

// 商家数据
const merchants = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const editingMerchant = ref<any>(null)
const searchTerm = ref('')
const selectedMerchantId = ref<number | null>(null)
const newMerchant = ref({
  name: '',
  address: '',
  latitude: 0,
  longitude: 0
})

// 商家的坐标（用于 MapPicker v-model）
const merchantCoordinate = ref<Coordinate>({ lat: 39.9042, lng: 116.4074 })

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 地图相关
const mapContainer = ref<HTMLElement | null>(null)
const mapPanelRef = ref<HTMLElement | null>(null)
const sdkMapRef = ref<any>(null)
const currentMapLayer = ref<MapEngineType>('amap')
const availableMaps = ref<{ value: MapEngineType; label: string }[]>([])
const apiKeys = ref<any>({})

// 地图中心坐标（用于 SDK 组件）
const mapCenter = ref<Coordinate>({ lat: 39.9042, lng: 116.4074 })

// 计算是否使用 SDK
const useAMapSDK = computed(() => {
  return currentMapLayer.value === 'amap' && !!apiKeys.value.amap
})

const useBMapSDK = computed(() => {
  return currentMapLayer.value === 'baidu' && !!apiKeys.value.baidu
})

const useTencentMapSDK = computed(() => {
  return currentMapLayer.value === 'tencent' && !!apiKeys.value.tencent
})

const useLeaflet = computed(() => {
  return !useAMapSDK.value && !useBMapSDK.value && !useTencentMapSDK.value
})

// 检查坐标是否有效
function isValidCoordinate(lat: any, lng: any): boolean {
  return typeof lat === 'number' && typeof lng === 'number' &&
         !isNaN(lat) && !isNaN(lng) &&
         lat !== 0 && lng !== 0
}

// 计算商家标记数据（用于 SDK 组件）
interface MarkerData {
  id: number
  lat: number
  lng: number
  name: string
  selected: boolean
}

const sdkMarkers = computed<MarkerData[]>(() => {
  const coordSystem = getCoordinateSystem(currentMapLayer.value)

  return merchants.value
    .filter(m => isValidCoordinate(m.latitude, m.longitude))
    .map(merchant => {
      let displayCoord: Coordinate

      if (coordSystem === 'wgs84') {
        displayCoord = { lat: merchant.latitude, lng: merchant.longitude }
      } else if (coordSystem === 'gcj02') {
        displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'gcj02')
      } else {
        displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'bd09')
      }

      // 再次检查转换后的坐标有效性
      if (!isValidCoordinate(displayCoord.lat, displayCoord.lng)) {
        console.warn('[MerchantMap] 坐标转换后无效:', merchant.name, merchant.latitude, merchant.longitude)
        return null
      }

      return {
        id: merchant.id,
        lat: displayCoord.lat,
        lng: displayCoord.lng,
        name: merchant.name,
        selected: selectedMerchantId.value === merchant.id
      }
    })
    .filter((m): m is MarkerData => m !== null)
})

// 地图引擎和标记
let currentEngine: any = null
let markersMap: Map<number, any> = new Map()

// 地图配置选项
const allMapsOptions: { value: MapEngineType; label: string }[] = [
  { value: 'amap', label: '高德地图' },
  { value: 'baidu', label: '百度地图' },
  { value: 'tencent', label: '腾讯地图' },
  { value: 'tianditu', label: '天地图' },
  { value: 'osm', label: 'OpenStreetMap' }
]

// 处理地址选择
function handleAddressSelected(data: { address: string; lat: number; lng: number }) {
  newMerchant.value.address = data.address
  newMerchant.value.latitude = data.lat
  newMerchant.value.longitude = data.lng
}

// 从地址输入框搜索地址
async function searchAddressFromInput() {
  const address = newMerchant.value.address?.trim()
  if (!address) return

  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`
    const response = await fetch(url)
    const data = await response.json()

    if (data && data.length > 0) {
      const result = data[0]
      const lat = parseFloat(result.lat)
      const lng = parseFloat(result.lon)

      merchantCoordinate.value = { lat, lng }
      newMerchant.value.latitude = lat
      newMerchant.value.longitude = lng
      newMerchant.value.address = result.display_name

      alert(`找到位置: ${result.display_name}`)
    } else {
      alert('未找到该地址')
    }
  } catch (error) {
    console.error('Search address error:', error)
    alert('搜索地址失败，请重试')
  }
}

// 监听 MapPicker 坐标变化
watch(merchantCoordinate, (newCoord) => {
  if (newCoord) {
    newMerchant.value.latitude = newCoord.lat
    newMerchant.value.longitude = newCoord.lng
  }
})

// 监听商家标记数据变化，更新 SDK 地图标记并缩放到范围
watch(sdkMarkers, (newMarkers) => {
  if (!useLeaflet.value && newMarkers.length > 0) {
    // 延迟调用 fitMarkers 确保 SDK 地图已渲染标记
    setTimeout(() => {
      if (sdkMapRef.value && sdkMapRef.value.fitMarkers) {
        sdkMapRef.value.fitMarkers()
      }
    }, 800)
  }
}, { immediate: true })

// 加载地图配置
async function loadMapConfig() {
  try {
    const config = await api.get('/admin/map-config')
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

// 初始化地图引擎（仅 Leaflet）
async function initMap() {
  // 如果使用 SDK，不需要初始化 Leaflet
  if (!useLeaflet.value) return
  if (!mapContainer.value) return

  const config: MapConfig = {
    ...defaultMapConfig,
    availableMaps: availableMaps.value.map(m => m.value),
    defaultMap: currentMapLayer.value,
    mapApiKeys: apiKeys.value
  }

  mapEngineManager.setConfig(config)

  try {
    currentEngine = await mapEngineManager.loadEngine(
      currentMapLayer.value,
      mapContainer.value,
      {
        center: [39.9042, 116.4074],
        zoom: 12,
        enableClick: true,
        enableDrag: true
      }
    )

    // 绑定地图点击事件
    currentEngine.on('click', handleMapClick)

    // 等待地图渲染
    await nextTick()

    // 更新商家标记
    updateMerchantsMarkers()

    // 延迟后缩放到商家范围
    setTimeout(() => {
      fitAllMerchants()
    }, 500)
  } catch (error) {
    console.error('Failed to init map:', error)
  }
}

// 处理地图点击
function handleMapClick(data: { lat: number; lng: number }) {
  console.log('Map clicked:', data)
}

// 处理 SDK 地图点击
function handleSDKMapClick(coord: Coordinate) {
  console.log('SDK map clicked:', coord)
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
  merchants.value.forEach(merchant => {
    if (merchant.latitude && merchant.longitude) {
      // 数据库存储的是 WGS84，根据当前地图类型转换
      const coordSystem = getCoordinateSystem(currentMapLayer.value)
      let displayCoord: Coordinate

      if (coordSystem === 'wgs84') {
        displayCoord = { lat: merchant.latitude, lng: merchant.longitude }
      } else if (coordSystem === 'gcj02') {
        displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'gcj02')
      } else {
        displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'bd09')
      }

      // 添加标记
      const markerId = currentEngine.addMarker(displayCoord.lat, displayCoord.lng, {
        draggable: false
      })

      markersMap.set(merchant.id, markerId)

      // 获取 Leaflet 地图实例并设置自定义图标
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
                const isSelected = selectedMerchantId.value === merchant.id
                const displayName = merchant.name.length > 10 ? merchant.name.substring(0, 10) + '…' : merchant.name
                const icon = L.divIcon({
                  className: 'merchant-marker',
                  html: `<div class="marker-icon ${isSelected ? 'selected' : ''}">
                    <span class="marker-label">${displayName}</span>
                  </div>`,
                  iconSize: [100, 30],  // 固定尺寸，实际宽度由 CSS 控制
                  iconAnchor: [50, 36]  // 水平居中，底部（高度30 + 箭头6）
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

// 选中商家
function selectMerchant(merchant: any) {
  selectedMerchantId.value = merchant.id

  // 更新标记样式
  updateMerchantsMarkers()

  // 地图居中到该商家
  if (merchant.latitude && merchant.longitude && currentEngine) {
    const coordSystem = getCoordinateSystem(currentMapLayer.value)
    let displayCoord: Coordinate

    if (coordSystem === 'wgs84') {
      displayCoord = { lat: merchant.latitude, lng: merchant.longitude }
    } else if (coordSystem === 'gcj02') {
      displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'gcj02')
    } else {
      displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'bd09')
    }

    currentEngine.setCenter(displayCoord.lat, displayCoord.lng)
    currentEngine.setZoom(15)
  }
}

// 居中显示所有商家
function fitAllMerchants() {
  // 如果是 SDK 地图，调用 SDK 组件的 fitMarkers 方法
  if (!useLeaflet.value && sdkMapRef.value && sdkMapRef.value.fitMarkers) {
    sdkMapRef.value.fitMarkers()
    return
  }

  // Leaflet 地图逻辑
  if (!currentEngine || merchants.value.length === 0) return

  const leafletMap = currentEngine.getMap()
  if (!leafletMap) return

  const bounds: L.LatLngBoundsExpression = []

  merchants.value.forEach(merchant => {
    if (merchant.latitude && merchant.longitude) {
      const coordSystem = getCoordinateSystem(currentMapLayer.value)
      let displayCoord: Coordinate

      if (coordSystem === 'wgs84') {
        displayCoord = { lat: merchant.latitude, lng: merchant.longitude }
      } else if (coordSystem === 'gcj02') {
        displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'gcj02')
      } else {
        displayCoord = convertCoordinate(merchant.latitude, merchant.longitude, 'wgs84', 'bd09')
      }

      bounds.push([displayCoord.lat, displayCoord.lng])
    }
  })

  if (bounds.length > 0) {
    if (bounds.length === 1) {
      leafletMap.setView(bounds[0] as L.LatLngExpression, 15)
    } else {
      leafletMap.fitBounds(bounds as L.LatLngBoundsExpression, { padding: [50, 50] })
    }
  }
}

// 切换地图图层
async function switchMapLayer(layer: MapEngineType) {
  console.log('[MerchantMap] switchMapLayer 被调用:', layer, '当前:', currentMapLayer.value)

  if (layer === currentMapLayer.value) {
    console.log('[MerchantMap] 相同地图，跳过')
    return
  }

  console.log('[MerchantMap] 销毁当前引擎')
  currentMapLayer.value = layer

  // 销毁 Leaflet 引擎（如果存在）
  mapEngineManager.destroy()
  currentEngine = null
  markersMap.clear()

  // 重新初始化
  await nextTick()

  console.log('[MerchantMap] 重新初始化，当前地图:', currentMapLayer.value, 'useLeaflet:', useLeaflet.value)

  if (useLeaflet.value) {
    await initMap()
  }

  setTimeout(() => fitAllMerchants(), 100)
}

function handleMapLayerChange() {
  switchMapLayer(currentMapLayer.value)
}

// 全屏切换
function toggleFullscreen() {
  if (!mapPanelRef.value) return

  if (!document.fullscreenElement) {
    mapPanelRef.value.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

// 加载商家数据
async function loadMerchants() {
  loading.value = true
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    let url = `/merchants?skip=${skip}&limit=${pageSize.value}`
    if (searchTerm.value) {
      url += `&search=${encodeURIComponent(searchTerm.value)}`
    }
    const data = await api.get<{
      items: any[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(url)
    merchants.value = data?.items || []
    total.value = data?.total || 0

    await nextTick()
    updateMerchantsMarkers()
    setTimeout(() => fitAllMerchants(), 100)
  } catch (error) {
    console.error('Failed to load merchants:', error)
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadMerchants()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadMerchants()
}

// 模态框操作
function editMerchant(merchant: any) {
  editingMerchant.value = merchant
  const lat = merchant.latitude || 0
  const lng = merchant.longitude || 0
  newMerchant.value = {
    name: merchant.name,
    address: merchant.address || '',
    latitude: lat,
    longitude: lng
  }
  merchantCoordinate.value = lat && lng ? { lat, lng } : { lat: 39.9042, lng: 116.4074 }
  showAddModal.value = true
}

function closeModal() {
  showAddModal.value = false
  editingMerchant.value = null
}

async function addMerchant() {
  try {
    if (editingMerchant.value) {
      await api.put(`/merchants/${editingMerchant.value.id}`, newMerchant.value)
      alert('商家更新成功')
    } else {
      await api.post('/merchants', newMerchant.value)
      alert('商家添加成功')
    }
    closeModal()
    await loadMerchants()
  } catch (error: any) {
    console.error('Failed to save merchant:', error)
    alert(error?.response?.data?.detail || '保存商家失败，请重试')
  }
}

async function deleteMerchant(merchant: any) {
  if (confirm(`确定要删除商家 "${merchant.name}" 吗？`)) {
    try {
      await api.delete(`/merchants/${merchant.id}`)
      alert('商家删除成功')
      await loadMerchants()
    } catch (error: any) {
      console.error('Failed to delete merchant:', error)
      alert(error?.response?.data?.detail || '删除商家失败，请重试')
    }
  }
}

onMounted(async () => {
  await loadMapConfig()
  await loadMerchants()
  await nextTick()
  await initMap()
})

onUnmounted(() => {
  mapEngineManager.destroy()
  currentEngine = null
  markersMap.clear()
})
</script>

<style scoped>
.merchant-map-page {
  display: flex;
  height: calc(100vh - 120px);
  gap: 1rem;
  padding: 0 1rem;
}

/* 左侧商家列表面板 */
.merchant-list-panel {
  width: 350px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 0.5rem;
  overflow: hidden;
}

.search-filter {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

.search-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.btn-search {
  width: 40px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.btn-search:hover {
  background: #5a6fd8;
}

.merchant-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.merchant-card {
  padding: 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 0.5rem;
  border: 2px solid transparent;
  background: #f9f9f9;
}

.merchant-card:hover {
  background: #f0f0f0;
}

.merchant-card.active {
  border-color: #667eea;
  background: #f0f4ff;
}

.merchant-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.merchant-header h3 {
  font-size: 0.9375rem;
  margin: 0;
  color: #333;
}

.merchant-actions {
  display: flex;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.merchant-card:hover .merchant-actions {
  opacity: 1;
}

.merchant-actions button {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-edit {
  background: #667eea;
  color: white;
}

.btn-delete {
  background: #de350b;
  color: white;
}

.merchant-info {
  margin-top: 0.25rem;
}

.merchant-address {
  font-size: 0.8125rem;
  color: #666;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading, .empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}

/* 右侧地图面板 */
.merchant-map-panel {
  flex: 1;
  position: relative;
  border-radius: 0.5rem;
  overflow: hidden;
  background: #e5e5e5;
}

.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2000;
  display: flex;
  gap: 8px;
  align-items: center;
}

.desktop-layer-selector {
  display: flex;
  background: white;
  border-radius: 0.25rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.layer-btn {
  padding: 0.375rem 0.75rem;
  border: none;
  background: white;
  cursor: pointer;
  font-size: 0.8125rem;
  transition: all 0.2s;
  border-right: 1px solid #eee;
}

.layer-btn:last-child {
  border-right: none;
}

.layer-btn:hover {
  background: #f5f5f5;
}

.layer-btn.active {
  background: #667eea;
  color: white;
}

.mobile-layer-selector {
  display: none;
  padding: 0.375rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  background: white;
  font-size: 0.8125rem;
}

.control-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: white;
  border-radius: 0.25rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.control-btn:hover {
  background: #f5f5f5;
}

.control-btn svg {
  width: 16px;
  height: 16px;
}

.map-container {
  width: 100%;
  height: 100%;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.modal-content {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-content h2 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
}

.form-group {
  margin-bottom: 0.75rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  box-sizing: border-box;
}

.address-input-group {
  display: flex;
  gap: 0.5rem;
}

.address-input {
  flex: 1;
}

.search-address-btn {
  padding: 0.5rem 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.75rem;
  white-space: nowrap;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.btn-primary {
  padding: 0.5rem 1rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  cursor: pointer;
}

/* 地图标记样式 */
:deep(.merchant-marker) {
  background: transparent !important;
  border: none !important;
  width: 100px !important;
  height: 30px !important;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

:deep(.marker-icon) {
  background: #667eea;
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
  border-color: #667eea transparent transparent transparent;
}

:deep(.marker-icon.selected) {
  background: #e74c3c;
}

:deep(.marker-icon.selected::after) {
  border-color: #e74c3c transparent transparent transparent;
}

:deep(.marker-label) {
  display: inline;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .merchant-map-page {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - 120px);
  }

  .merchant-list-panel {
    width: 100%;
    height: 45vh;
    min-height: 300px;
  }

  .merchant-map-panel {
    height: 45vh;
    min-height: 300px;
  }

  .desktop-layer-selector {
    display: none;
  }

  .mobile-layer-selector {
    display: block;
    width: 100px;
  }

  .map-controls {
    top: 5px;
    right: 5px;
  }

  .merchant-actions {
    opacity: 1;
  }
}

/* 超小屏幕适配 */
@media (max-width: 480px) {
  .merchant-map-page {
    padding: 0 0.5rem;
    gap: 0.5rem;
  }

  .merchant-list-panel {
    height: 40vh;
    min-height: 250px;
  }

  .merchant-map-panel {
    height: 40vh;
    min-height: 250px;
  }

  .search-filter {
    padding: 0.5rem;
  }

  .search-input {
    font-size: 16px;
  }

  .modal-content {
    padding: 1rem;
  }
}

/* 隐藏 Leaflet 默认缩放控件 */
:deep(.leaflet-control-zoom) {
  display: none;
}

/* 腾讯地图控件位置调整 - 下移避开地图切换按钮 */
:deep(.map-container > div > div:nth-child(2) > div:nth-child(2)) {
  inset: auto !important;
  top: 50px !important;
  right: 10px !important;
}
</style>