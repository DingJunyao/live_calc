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

      <!-- A. 地图启用：左列表 + 右地图（原布局，整块包起来） -->
      <template v-if="mapEnabled">
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
                  {{ pendingName(item) }}
                  <v-chip
                    v-if="pendingIsOpen(item) === false"
                    size="x-small"
                    color="warning"
                    variant="tonal"
                    class="ms-2"
                  >已关闭</v-chip>
                  <v-chip
                    v-if="hasPending('merchant', item.id)"
                    size="x-small"
                    color="info"
                    variant="tonal"
                    class="ms-2"
                  >修改待审</v-chip>
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ pendingAddress(item) || '暂无地址' }}
                </v-list-item-subtitle>
                <template #append>
                  <div class="d-flex ga-1 align-center">
                    <!-- 定位按钮：高频操作，留在列表项上 -->
                    <v-btn
                      icon="mdi-crosshairs-gps"
                      size="small"
                      variant="text"
                      color="secondary"
                      :disabled="!isValidCoordinate(item.latitude, item.longitude)"
                      :title="isValidCoordinate(item.latitude, item.longitude) ? '在地图上定位' : '未设置位置'"
                      @click.stop="locateMerchant(item)"
                    />
                    <!-- 收藏 / 编辑 / 删除 收进三点溢出菜单 -->
                    <v-menu :close-on-content-click="true" location="bottom end">
                      <template #activator="{ props: menuProps }">
                        <v-btn icon="mdi-dots-vertical" size="small" variant="text" v-bind="menuProps" />
                      </template>
                      <v-list density="compact" nav>
                        <v-list-item
                          :prepend-icon="favoriteIds.has(item.id) ? 'mdi-heart' : 'mdi-heart-outline'"
                          :base-color="favoriteIds.has(item.id) ? 'error' : undefined"
                          :title="favoriteIds.has(item.id) ? '取消收藏' : '收藏'"
                          @click="toggleFavorite(item.id)"
                        />
                        <v-list-item
                          prepend-icon="mdi-pencil"
                          base-color="primary"
                          title="编辑"
                          @click="openEditDialog(item)"
                        />
                        <v-list-item
                          prepend-icon="mdi-delete"
                          base-color="error"
                          title="删除"
                          @click="deleteItem(item.id)"
                        />
                      </v-list>
                    </v-menu>
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
      </template>

      <!-- B. 地图禁用：卡片网格（桌面）/ 列表（移动），无地图 -->
      <template v-else>
        <div class="w-100">
          <!-- 搜索 + 筛选 -->
          <div class="d-flex ga-2 mb-4 align-center">
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
            <FilterBar :filters="merchantFilters" :mobile="!isDesktop" @change="onFilterChange" />
          </div>

          <!-- 移动端：列表 -->
          <v-card v-if="!isDesktop" elevation="0">
            <v-list lines="three">
              <v-list-item
                v-for="item in items"
                :key="item.id"
                @click="selectMerchant(item)"
              >
                <template #prepend>
                  <v-avatar color="tertiary" size="40"><v-icon>mdi-store</v-icon></v-avatar>
                </template>
                <v-list-item-title>
                  {{ pendingName(item) }}
                  <v-chip v-if="pendingIsOpen(item) === false" size="x-small" color="warning" variant="tonal" class="ms-2">已关闭</v-chip>
                  <v-chip v-if="hasPending('merchant', item.id)" size="x-small" color="info" variant="tonal" class="ms-2">修改待审</v-chip>
                </v-list-item-title>
                <v-list-item-subtitle>{{ pendingAddress(item) || '暂无地址' }}</v-list-item-subtitle>
                <template #append>
                  <v-menu :close-on-content-click="true" location="bottom end">
                    <template #activator="{ props: menuProps }">
                      <v-btn icon="mdi-dots-vertical" size="small" variant="text" v-bind="menuProps" />
                    </template>
                    <v-list density="compact" nav>
                      <v-list-item
                        :prepend-icon="favoriteIds.has(item.id) ? 'mdi-heart' : 'mdi-heart-outline'"
                        :base-color="favoriteIds.has(item.id) ? 'error' : undefined"
                        :title="favoriteIds.has(item.id) ? '取消收藏' : '收藏'"
                        @click="toggleFavorite(item.id)"
                      />
                      <v-list-item prepend-icon="mdi-pencil" base-color="primary" title="编辑" @click="openEditDialog(item)" />
                      <v-list-item prepend-icon="mdi-delete" base-color="error" title="删除" @click="deleteItem(item.id)" />
                    </v-list>
                  </v-menu>
                </template>
              </v-list-item>
              <v-list-item v-if="items.length === 0">
                <v-list-item-title class="text-center text-medium-emphasis">暂无商家</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card>

          <!-- 桌面端：卡片网格 -->
          <v-row v-else>
            <v-col v-for="item in items" :key="item.id" cols="12" sm="6" md="4" lg="3" xl="2">
              <v-card elevation="0" class="list-grid-card cursor-pointer h-100" @click="selectMerchant(item)">
                <v-card-text>
                  <div class="d-flex align-center mb-2">
                    <v-avatar color="tertiary" size="40" class="mr-3"><v-icon>mdi-store</v-icon></v-avatar>
                    <div class="text-body-2 font-weight-medium text-truncate">
                      {{ pendingName(item) }}
                      <v-chip v-if="pendingIsOpen(item) === false" size="x-small" color="warning" variant="tonal" class="ms-1">已关闭</v-chip>
                    </div>
                  </div>
                  <div class="text-caption text-medium-emphasis mb-1 text-truncate">{{ pendingAddress(item) || '暂无地址' }}</div>
                </v-card-text>
                <v-divider />
                <v-card-actions>
                  <v-spacer />
                  <v-btn
                    :icon="favoriteIds.has(item.id) ? 'mdi-heart' : 'mdi-heart-outline'"
                    size="small"
                    variant="text"
                    :color="favoriteIds.has(item.id) ? 'error' : undefined"
                    @click.stop="toggleFavorite(item.id)"
                  />
                  <v-btn icon="mdi-pencil" size="small" variant="text" color="primary" @click.stop="openEditDialog(item)" />
                  <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click.stop="deleteItem(item.id)" />
                </v-card-actions>
              </v-card>
            </v-col>
            <v-col v-if="items.length === 0" cols="12">
              <div class="text-center py-8 text-medium-emphasis">暂无商家</div>
            </v-col>
          </v-row>

          <!-- 分页（禁用态共用） -->
          <div v-if="total > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
            <v-pagination
              :model-value="currentPage"
              :length="totalPages"
              :total-visible="totalVisible"
              rounded="circle"
              density="comfortable"
              @update:model-value="onPageChange"
            />
            <v-select
              v-model="pageSize"
              :items="[10, 20, 50, 100]"
              label="每页"
              variant="outlined"
              density="compact"
              hide-details
              style="max-width: 90px"
              @update:model-value="handlePageSizeChange"
            />
            <span class="text-caption text-medium-emphasis">共 {{ total }} 条</span>
          </div>
        </div>
      </template>

      <!-- 禁用态独立 FAB（启用态 FAB 在 left-panel 内） -->
      <v-btn
        v-if="!mapEnabled"
        icon="mdi-plus"
        color="primary"
        size="large"
        elevation="8"
        class="position-fixed"
        style="bottom: 80px; right: 24px"
        @click="openEditDialog()"
      />
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

            <!-- 地图选点（地图禁用时隐藏，提交不带坐标，后端保留原值） -->
            <div v-if="mapEnabled" class="mb-4">
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
import { useUserStore } from '@/stores/user'
import { getErrorMessage } from '@/utils/errorHandler'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useGlobalSnackbar } from '@/composables/useGlobalSnackbar'
import FilterBar, { type FilterConfig } from '@/components/common/FilterBar.vue'
import MerchantMapView from '@/components/map/MerchantMapView.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import type { Coordinate } from '@/utils/map/mapTypes'
import { usePendingProposals } from '@/composables/usePendingProposals'
import { useMapConfig } from '@/composables/useMapConfig'

const route = useRoute()
const router = useRouter()
const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { notify } = useGlobalSnackbar()
const userStore = useUserStore()
const { mapEnabled, ensureLoaded } = useMapConfig()

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
// 待审提议标记
const { load: loadPendingProposals, has: hasPending, getPayload: getPendingPayload } = usePendingProposals()
// 待审草稿覆盖：普通用户提交后，列表显示提议中的新值（name/address/is_open）
const pendingName = (item: Merchant) => {
  const p = getPendingPayload('merchant', item.id)
  return p?.name ?? item.name
}
const pendingAddress = (item: Merchant) => {
  const p = getPendingPayload('merchant', item.id)
  if (p?.address !== undefined) return p.address
  return item.address
}
const pendingIsOpen = (item: Merchant) => {
  const p = getPendingPayload('merchant', item.id)
  if (p?.is_open !== undefined) return p.is_open
  return item.is_open
}
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
// 收藏的商家 id 集合（共享池下「我的收藏」由 user_merchant_favorites 表达）
const favoriteIds = ref<Set<number>>(new Set())
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
    key: 'favorites_only',
    label: '仅看我的收藏',
    type: 'toggle',
    minWidth: '140px',
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
const favoritesOnly = computed(() => requestFilters.value.favorites_only === true)

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
    // 收藏筛选：后端列表端点不支持 favorites 过滤，改用 /merchants/favorites
    // 全量拉取后在客户端做搜索/营业/分页过滤（收藏量通常不大，可接受）
    if (favoritesOnly.value) {
      const favs: Merchant[] = await api.get('/merchants/favorites')
      let filtered = Array.isArray(favs) ? favs : []
      if (!showAllMerchants.value) {
        filtered = filtered.filter(m => m.is_open !== false)
      }
      if (search.value) {
        const kw = search.value.toLowerCase()
        filtered = filtered.filter(m =>
          (m.name || '').toLowerCase().includes(kw) ||
          (m.address || '').toLowerCase().includes(kw)
        )
      }
      total.value = filtered.length
      const skip = (currentPage.value - 1) * pageSize.value
      items.value = filtered.slice(skip, skip + pageSize.value)
      return
    }

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

// 加载当前用户收藏的商家 id 集合（共享池下「我的收藏」）
const loadFavorites = async () => {
  try {
    const favs: Merchant[] = await api.get('/merchants/favorites')
    favoriteIds.value = new Set((Array.isArray(favs) ? favs : []).map(m => m.id))
  } catch (e: any) {
    console.error('加载收藏列表失败', e)
  }
}

// 收藏 / 取消收藏商家（共享池任意商家均可收藏）
const toggleFavorite = async (id: number) => {
  const wasFav = favoriteIds.value.has(id)
  // 乐观更新
  const next = new Set(favoriteIds.value)
  if (wasFav) next.delete(id); else next.add(id)
  favoriteIds.value = next
  try {
    if (wasFav) {
      await api.delete(`/merchants/${id}/favorite`)
      notify('已取消收藏', 'info')
    } else {
      await api.post(`/merchants/${id}/favorite`)
      notify('已收藏', 'success')
    }
    // 若当前处于「仅看收藏」视图，移除后需重新加载列表
    if (favoritesOnly.value) {
      loadMerchants()
    }
  } catch (e: any) {
    // 回滚
    favoriteIds.value = wasFav
      ? new Set([...favoriteIds.value, id])
      : (() => { const r = new Set(favoriteIds.value); r.delete(id); return r })()
    notify(getErrorMessage(e, wasFav ? '取消收藏失败' : '收藏失败'), 'error')
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

    // 仅地图启用时才提交坐标；禁用时不传，靠后端 exclude_unset 保留原值
    if (mapEnabled.value && pickerCoords.value) {
      data.latitude = pickerCoords.value.lat
      data.longitude = pickerCoords.value.lng
    }

    if (editingItem.value) {
      const response = await api.put(`/merchants/${editingItem.value.id}`, data)
      // 共享池分流：管理员直写返回更新后的商家；普通用户走提议（merchant.update=manual
      // → 待审，值未变，返回原商家）。两端点均返回商家对象（无 message 字段），
      // 故用 userStore.is_admin 区分提示，避免普通用户待审时误报「已保存」。
      if (userStore.user?.is_admin) {
        notify('已保存', 'success')
        await loadMerchants()
      } else {
        notify('编辑提议已提交，待管理员审核', 'info')
      }
      // 编辑后若当前视图筛掉了该商家（如改了 is_open），无需特殊处理
      void response
    } else {
      const response = await api.post('/merchants', data)
      if (showAllMerchants.value || response.is_open !== false) {
        items.value.unshift(response)
        total.value++
      }
      notify('已创建商家', 'success')
    }
    addDialog.value = false
  } catch (e: any) {
    console.error('保存商家失败', e)
    notify(getErrorMessage(e, '保存商家失败'), 'error')
  } finally {
    saving.value = false
  }
}

const deleteItem = async (id: number) => {
  try {
    const result = await api.delete(`/merchants/${id}`)
    // 共享池分流：普通用户提交提议（返回 {message: ... proposal_id ...}），
    // 管理员直写软删（返回 {message: ...}）。普通用户提议待审，列表暂不移除。
    const msg: string = (result && result.message) || ''
    if (msg.includes('提议') || msg.includes('proposal')) {
      notify('删除提议已提交，待管理员审核', 'info')
    } else {
      notify('商家已删除', 'success')
      const index = items.value.findIndex(i => i.id === id)
      if (index !== -1) {
        items.value.splice(index, 1)
        total.value--
      }
      // 如果删除的是选中的商家，清除选中状态
      if (selectedMerchant.value?.id === id) {
        selectedMerchant.value = null
      }
    }
  } catch (e: any) {
    console.error('删除商家失败', e)
    notify(getErrorMessage(e, '删除商家失败'), 'error')
  }
}

onMounted(() => {
  ensureLoaded()
  loadMerchants()
  loadPlaces()
  loadAllCoordinates()
  loadFavorites()
  loadPendingProposals()
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

/* 通用工具类 */
.cursor-pointer { cursor: pointer; }
.font-family-monospace { font-family: monospace; }

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
