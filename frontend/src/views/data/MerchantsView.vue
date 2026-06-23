<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">商家管理</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadMerchants" />
    </template>
  </v-app-bar>

  <!-- 主内容容器：固定高度，flex 布局 -->
  <div class="merchants-page-container">
    <!-- 错误提示 -->
    <v-alert v-if="error" type="error" class="ma-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadMerchants">重试</v-btn>
      </template>
    </v-alert>

    <!-- 主内容区：列表 + 地图（加载中用叠加层遮罩，避免 FilterBar 因 v-if 销毁丢失状态） -->
    <div v-else class="main-content">
      <!-- 加载叠加层 -->
      <div v-if="loading" class="fullpage-loading" style="position: absolute; inset: 0; z-index: 10; background: rgba(var(--v-theme-background), 0.7);">
        <v-progress-circular indeterminate color="primary" size="64" />
        <div class="text-body-1 mt-4">加载中...</div>
      </div>

      <!-- 左边：搜索框 + 商家列表 -->
      <div class="left-panel">
        <div class="search-wrapper">
          <div class="d-flex align-center ga-2">
            <v-text-field
              v-model="search"
              label="搜索商家..."
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              class="flex-grow-1"
              @update:model-value="debouncedSearch"
            />
            <FilterBar
              :filters="merchantFilters"
              mobile
              @change="onFilterChange"
            />
          </div>
        </div>

        <div class="list-scroll-area">
          <v-list lines="two" class="merchant-list">
            <v-list-item
              v-for="item in items"
              :key="item.id"
              @click="selectMerchant(item)"
              :active="selectedMerchant?.id === item.id"
            >
              <template #prepend>
                <v-avatar color="tertiary" size="40">
                  <v-icon>mdi-store</v-icon>
                </v-avatar>
              </template>

              <v-list-item-title>
                {{ item.name }}
                <v-chip
                  v-if="item.is_open === false"
                  size="x-small"
                  color="warning"
                  variant="tonal"
                  class="ms-2"
                >已关闭</v-chip>
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ item.address || '暂无地址' }}
              </v-list-item-subtitle>
              <v-list-item-subtitle v-if="item.latitude && item.longitude" class="text-caption">
                <v-icon size="x-small" class="mr-1">mdi-map-marker</v-icon>
                {{ item.latitude.toFixed(4) }}, {{ item.longitude.toFixed(4) }}
              </v-list-item-subtitle>

              <template #append>
                <div class="d-flex ga-1">
                  <v-btn
                    icon="mdi-crosshairs-gps"
                    size="small"
                    variant="text"
                    color="secondary"
                    :disabled="!isValidCoordinate(item.latitude, item.longitude)"
                    :title="isValidCoordinate(item.latitude, item.longitude) ? '在地图上定位' : '未设置位置'"
                    @click.stop="locateMerchant(item)"
                  />
                  <v-btn
                    icon="mdi-pencil"
                    size="small"
                    variant="text"
                    color="primary"
                    @click.stop="openEditDialog(item)"
                  />
                  <v-btn
                    icon="mdi-delete"
                    size="small"
                    variant="text"
                    color="error"
                    @click.stop="deleteItem(item.id)"
                  />
                </div>
              </template>
            </v-list-item>

            <v-list-item v-if="items.length === 0">
              <v-list-item-title class="text-center text-medium-emphasis">
                暂无商家
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </div>

        <!-- 分页器 -->
        <div v-if="total > 0" class="pagination-wrapper">
          <div class="pagination-content">
            <v-pagination
              :model-value="currentPage"
              :length="totalPages"
              :total-visible="totalVisible"
              @update:model-value="onPageChange"
              rounded="circle"
              :density="isDesktop ? 'comfortable' : 'compact'"
              :size="isDesktop ? 'small' : 'x-small'"
              class="flex-shrink-0"
            />
            <div class="pagination-controls">
              <v-select
                v-model="pageSize"
                :items="[10, 20, 50, 100]"
                :label="isDesktop ? '每页' : undefined"
                variant="outlined"
                density="compact"
                hide-details
                class="page-size-select"
                @update:model-value="handlePageSizeChange"
              />
              <span v-if="isDesktop" class="text-caption text-medium-emphasis total-count">共 {{ total }} 条</span>
              <span v-else class="text-caption text-medium-emphasis total-count">{{ total }}条</span>
            </div>
          </div>
        </div>

        <!-- FAB 添加按钮 -->
        <v-btn
          icon="mdi-plus"
          color="primary"
          size="large"
          elevation="6"
          class="fab-button"
          @click="openEditDialog()"
        />
      </div>

      <!-- 右边：地图 -->
      <div class="right-panel" ref="rightPanelRef">
        <MerchantMapView
          :merchants="items"
          :selected-merchant="selectedMerchant"
          :is-desktop="isDesktop"
          :places="places"
          :current-place-id="currentPlaceId"
          :all-coordinates="allCoordinates"
          @update:current-place-id="onPlaceChange"
        />
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <v-dialog v-model="addDialog" max-width="500">
      <v-card>
        <v-card-title>{{ editingItem ? '编辑商家' : '添加商家' }}</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="form.name"
              label="商家名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-text-field
              v-model="form.address"
              label="地址"
              variant="outlined"
              class="mb-4"
            />

            <v-switch
              v-model="form.is_open"
              label="营业中"
              color="success"
              class="mb-4"
              hide-details
            />

            <!-- 地图选点 -->
            <div class="mb-4">
              <div class="text-subtitle-2 mb-2">商家位置</div>
              <MapPicker
                v-model="pickerCoords"
                :show-switcher="true"
              />
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="addDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveItem">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { api } from '@/api/client'
import { getErrorMessage } from '@/utils/errorHandler'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import FilterBar, { type FilterConfig } from '@/components/common/FilterBar.vue'
import MerchantMapView from '@/components/map/MerchantMapView.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import type { Coordinate } from '@/utils/map/mapTypes'

const route = useRoute()
const router = useRouter()
const { isDesktop, toggleSidebar } = useMobileDrawerControl()

interface Merchant {
  id: number
  name: string
  address?: string
  phone?: string
  latitude?: number | null
  longitude?: number | null
  is_open?: boolean
  created_at?: string
}

const items = ref<Merchant[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref((route.query.search as string) || '')
const addDialog = ref(false)
const editingItem = ref<Merchant | null>(null)
const selectedMerchant = ref<Merchant | null>(null)

// 用户常用地点 + 全部商家坐标（地图默认范围用）
interface PlaceOption {
  id: number
  name: string
  kind: string
  latitude: number
  longitude: number
  is_default?: boolean
  view_radius_km?: number
}
const places = ref<PlaceOption[]>([])
const allCoordinates = ref<{ latitude: number; longitude: number }[]>([])
const currentPlaceId = ref<number | null>(null)
const PLACES_STORAGE_KEY = 'merchants_map_current_place_id'
const saving = ref(false)
const form = ref({
  name: '',
  address: '',
  is_open: true,
})

// 选点器坐标
const pickerCoords = ref<Coordinate | undefined>()

// 分页相关（从 URL 查询参数初始化）
const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(Number(route.query.pageSize) || 20)
const total = ref(0)
// 筛选器相关
const requestFilters = ref<Record<string, any>>({})

const merchantFilters: FilterConfig[] = [
  {
    key: 'include_closed',
    label: '显示已关闭商家',
    type: 'toggle',
    minWidth: '160px',
  },
  {
    key: 'special_conditions',
    label: '特殊条件',
    type: 'multicheck',
    items: [
      { value: 'no_price', title: '未维护过价格' },
    ],
    minWidth: '180px',
  },
]

const onFilterChange = (filterState: Record<string, any>) => {
  requestFilters.value = filterState
  currentPage.value = 1
  loadMerchants()
  loadAllCoordinates()
}

const showAllMerchants = computed(() => requestFilters.value.include_closed === true)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const { md, lgAndUp } = useDisplay()
const totalVisible = computed(() => lgAndUp.value ? 7 : md.value ? 5 : 3)

// 同步分页状态到 URL 查询参数
const syncToUrl = () => {
  router.replace({
    query: {
      ...route.query,
      page: String(currentPage.value),
      pageSize: String(pageSize.value),
      ...(search.value ? { search: search.value } : {}),
    }
  })
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    syncToUrl()
    loadMerchants()
    loadAllCoordinates()
  }, 300)
}

const loadMerchants = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = {
      skip,
      limit: pageSize.value,
      include_closed: showAllMerchants.value
    }
    if (search.value) {
      params.search = search.value
    }
    // 特殊条件参数
    if (requestFilters.value.special_conditions?.length) {
      for (const cond of requestFilters.value.special_conditions) {
        params[cond] = 'true'
      }
    }

    const response = await api.get('/merchants', { params })
    items.value = response.items || []
    total.value = response.total || 0
  } catch (e: any) {
    console.error('加载商家失败', e)
    error.value = getErrorMessage(e, '加载失败')
  } finally {
    loading.value = false
  }
}

// 加载用户常用地点，并初始化 currentPlaceId（localStorage 上次选择 → is_default → null）
const loadPlaces = async () => {
  try {
    const data = await api.get('/places')
    places.value = Array.isArray(data) ? data : []
    if (currentPlaceId.value === null && places.value.length > 0) {
      const saved = localStorage.getItem(PLACES_STORAGE_KEY)
      const savedId = saved != null && saved !== '' ? Number(saved) : null
      if (savedId != null && places.value.some(p => p.id === savedId)) {
        currentPlaceId.value = savedId
      } else {
        const def = places.value.find(p => p.is_default)
        currentPlaceId.value = def ? def.id : null
      }
    }
  } catch (e: any) {
    console.error('加载常用地点失败', e)
  }
}

// 加载全部商家坐标（不分页，供地图 fitAll 用；跟随 search/include_closed）
const loadAllCoordinates = async () => {
  try {
    const data = await api.get('/merchants/coordinates', {
      params: {
        search: search.value || undefined,
        include_closed: showAllMerchants.value
      }
    })
    allCoordinates.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    console.error('加载商家坐标失败', e)
  }
}

// 切换地点中心，持久化到 localStorage
const onPlaceChange = (val: number | null) => {
  currentPlaceId.value = val
  if (val == null) {
    localStorage.removeItem(PLACES_STORAGE_KEY)
  } else {
    localStorage.setItem(PLACES_STORAGE_KEY, String(val))
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  syncToUrl()
  loadMerchants()
}

const onPageChange = (page: number) => {
  currentPage.value = page
  syncToUrl()
  loadMerchants()
}

// 右侧地图面板引用（移动端定位后滚动到地图）
const rightPanelRef = ref<HTMLElement | null>(null)

/**
 * 选择商家
 */
const selectMerchant = (item: Merchant) => {
  // 点击商家进入详情页
  router.push(`/data/merchants/${item.id}`)
}

/**
 * 检查坐标是否有效（与 MerchantMapView 判定保持一致）
 */
const isValidCoordinate = (lat: any, lng: any): boolean => {
  return typeof lat === 'number' && typeof lng === 'number' &&
         !isNaN(lat) && !isNaN(lng) &&
         lat !== 0 && lng !== 0
}

/**
 * 在地图上定位商家：设置为选中（地图会自动居中 + 特殊标记），
 * 移动端额外滚动到地图区域。
 */
const locateMerchant = (item: Merchant) => {
  if (!isValidCoordinate(item.latitude, item.longitude)) return
  selectedMerchant.value = item
  if (!isDesktop.value) {
    nextTick(() => {
      rightPanelRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }
}

/**
 * 打开编辑对话框
 */
const openEditDialog = (item?: Merchant) => {
  editingItem.value = item || null
  if (item) {
    form.value = {
      name: item.name,
      address: item.address || '',
      is_open: item.is_open ?? true,
    }
    // 设置坐标
    if (item.latitude != null && item.longitude != null) {
      pickerCoords.value = {
        lat: item.latitude,
        lng: item.longitude
      }
    } else {
      pickerCoords.value = undefined
    }
  } else {
    form.value = { name: '', address: '', is_open: true }
    pickerCoords.value = undefined
  }
  addDialog.value = true
}

/**
 * 保存商家
 */
const saveItem = async () => {
  if (!form.value.name.trim()) return

  saving.value = true
  try {
    const data: any = {
      name: form.value.name,
      address: form.value.address || undefined,
      is_open: form.value.is_open,
    }

    // 添加坐标
    if (pickerCoords.value) {
      data.latitude = pickerCoords.value.lat
      data.longitude = pickerCoords.value.lng
    }

    if (editingItem.value) {
      const response = await api.put(`/merchants/${editingItem.value.id}`, data)
      if (!showAllMerchants.value && response.is_open === false) {
        // 已关闭且当前视图只显示营业中商家，从列表中移除
        const index = items.value.findIndex(i => i.id === editingItem.value!.id)
        if (index !== -1) {
          items.value.splice(index, 1)
          total.value--
        }
      } else {
        const index = items.value.findIndex(i => i.id === editingItem.value!.id)
        if (index !== -1) {
          items.value[index] = response
        }
      }
    } else {
      const response = await api.post('/merchants', data)
      if (showAllMerchants.value || response.is_open !== false) {
        items.value.unshift(response)
        total.value++
      }
    }
    addDialog.value = false

    // 如果选中的是被编辑的商家，更新选中状态
    if (selectedMerchant.value && editingItem.value && selectedMerchant.value.id === editingItem.value.id) {
      selectedMerchant.value = items.value.find(i => i.id === editingItem.value!.id) || null
    }
  } catch (e: any) {
    console.error('保存商家失败', e)
  } finally {
    saving.value = false
  }
}

const deleteItem = async (id: number) => {
  try {
    await api.delete(`/merchants/${id}`)
    const index = items.value.findIndex(i => i.id === id)
    if (index !== -1) {
      items.value.splice(index, 1)
      total.value--
    }
    // 如果删除的是选中的商家，清除选中状态
    if (selectedMerchant.value?.id === id) {
      selectedMerchant.value = null
    }
  } catch (e: any) {
    console.error('删除商家失败', e)
  }
}

onMounted(() => {
  loadMerchants()
  loadPlaces()
  loadAllCoordinates()
  window.addEventListener('app-refresh', loadMerchants)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', loadMerchants)
})
</script>

<style scoped>
/* 页面容器：固定高度，排除 app-bar 高度 */
.merchants-page-container {
  height: calc(100vh - 56px); /* 减去 app-bar 的高度 */
  display: flex;
  flex-direction: column;
}

/* 全页面加载/错误提示 */
.fullpage-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* 主内容区域：flex 布局 */
.main-content {
  flex: 1;
  display: flex;
  gap: 1rem;
  padding: 1rem;
  overflow: hidden; /* 防止整个页面滚动 */
}

/* 左侧面板：搜索框 + 列表 + 分页 */
.left-panel {
  position: relative; /* 为 FAB 按钮提供定位上下文 */
  width: 350px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex-shrink: 0;
}

/* 搜索框容器 */
.search-wrapper {
  flex-shrink: 0;
}

/* 列表滚动区域 */
.list-scroll-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0; /* 允许 flex 子元素收缩 */
}

.merchant-list {
  background: rgb(var(--v-theme-surface));
  border-radius: 8px;
}

/* 分页器容器 */
.pagination-wrapper {
  flex-shrink: 0;
  padding: 0.5rem 0;
}

/* FAB 浮动按钮 */
.fab-button {
  position: absolute;
  bottom: 16px;
  right: 16px;
  z-index: 10;
}

.pagination-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
}

.page-size-select {
  max-width: 80px;
}

.total-count {
  white-space: nowrap;
}

/* 右侧面板：地图 */
.right-panel {
  flex: 1;
  min-width: 0; /* 允许 flex 子元素收缩 */
  height: 100%;
}

/* 移动端适配 */
@media (max-width: 960px) {
  .main-content {
    flex-direction: column;
    overflow-y: auto; /* 允许整体滚动 */
    display: flex;
    flex: 1;
  }

  .left-panel {
    width: 100%;
    flex: 3; /* 60% 空间 */
    min-height: 0; /* 允许 flex 子元素收缩 */
    display: flex;
    flex-direction: column;
  }

  .right-panel {
    flex: 2; /* 40% 空间 */
    min-height: 0; /* 允许 flex 子元素收缩 */
  }

  /* 移动端分页器紧凑布局 */
  .pagination-wrapper {
    padding: 0.25rem 0; /* 正常的上下 padding */
  }

  .pagination-content {
    flex-direction: row; /* 改为横向布局 */
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0 0.25rem;
  }

  .pagination-controls {
    gap: 0.5rem; /* 增加间距以便容纳选择框 */
  }

  .page-size-select {
    min-width: 85px; /* 确保有足够宽度显示三位数 */
    max-width: 85px;
    font-size: 0.75rem; /* 减小字体 */
  }

  .total-count {
    font-size: 0.7rem; /* 减小字体 */
  }

  /* 让分页按钮更紧凑 */
  :deep(.v-pagination__item) {
    padding: 0 4px;
    min-width: 28px;
    height: 28px;
  }

  /* 移动端 FAB 按钮优化 */
  .fab-button {
    bottom: 12px;
    right: 12px;
    width: 48px !important;
    height: 48px !important;
  }
}
</style>
