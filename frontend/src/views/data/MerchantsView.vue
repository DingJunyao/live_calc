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
    <!-- 加载中 -->
    <div v-if="loading" class="fullpage-loading">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="ma-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadMerchants">重试</v-btn>
      </template>
    </v-alert>

    <!-- 主内容区：列表 + 地图 -->
    <div v-else class="main-content">
      <!-- 左边：搜索框 + 商家列表 -->
      <div class="left-panel">
        <div class="search-wrapper">
          <v-text-field
            v-model="search"
            label="搜索商家..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @update:model-value="debouncedSearch"
          />
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

              <v-list-item-title>{{ item.name }}</v-list-item-title>
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
          <v-pagination
            v-model="currentPage"
            :length="totalPages"
            :total-visible="3"
            rounded="circle"
            density="comfortable"
            size="small"
          />
          <div class="d-flex align-center ga-2 justify-center mt-2">
            <v-select
              v-model="pageSize"
              :items="[10, 20, 50, 100]"
              label="每页"
              variant="outlined"
              density="compact"
              hide-details
              style="max-width: 80px"
              @update:model-value="handlePageSizeChange"
            />
            <span class="text-caption text-medium-emphasis">共 {{ total }} 条</span>
          </div>
        </div>
      </div>

      <!-- 右边：地图 -->
      <div class="right-panel">
        <MerchantMapView
          :merchants="items"
          :selected-merchant="selectedMerchant"
          :is-desktop="isDesktop"
        />
      </div>
    </div>

    <!-- FAB 浮动添加按钮 -->
    <v-btn
      icon="mdi-plus"
      color="primary"
      size="large"
      elevation="8"
      class="position-fixed"
      style="bottom: 80px; right: 24px"
      @click="openEditDialog()"
    />

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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/api/client'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import MerchantMapView from '@/components/map/MerchantMapView.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import type { Coordinate } from '@/utils/map/mapTypes'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

interface Merchant {
  id: number
  name: string
  address?: string
  phone?: string
  latitude?: number | null
  longitude?: number | null
  created_at?: string
}

const items = ref<Merchant[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const addDialog = ref(false)
const editingItem = ref<Merchant | null>(null)
const selectedMerchant = ref<Merchant | null>(null)
const saving = ref(false)
const form = ref({
  name: '',
  address: '',
})

// 选点器坐标
const pickerCoords = ref<Coordinate | undefined>()

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadMerchants()
  }, 300)
}

const loadMerchants = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = {
      skip,
      limit: pageSize.value
    }
    if (search.value) {
      params.search = search.value
    }

    const response = await api.get('/merchants', { params })
    items.value = response.items || []
    total.value = response.total || 0
  } catch (e: any) {
    console.error('加载商家失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  loadMerchants()
}

watch(currentPage, () => {
  loadMerchants()
})

/**
 * 选择商家
 */
const selectMerchant = (item: Merchant) => {
  selectedMerchant.value = item
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
    form.value = { name: '', address: '' }
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
    }

    // 添加坐标
    if (pickerCoords.value) {
      data.latitude = pickerCoords.value.lat
      data.longitude = pickerCoords.value.lng
    }

    if (editingItem.value) {
      const response = await api.put(`/merchants/${editingItem.value.id}`, data)
      const index = items.value.findIndex(i => i.id === editingItem.value!.id)
      if (index !== -1) {
        items.value[index] = response
      }
    } else {
      const response = await api.post('/merchants', data)
      items.value.unshift(response)
      total.value++
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
  }

  .left-panel {
    width: 100%;
    max-height: 50vh;
  }

  .right-panel {
    height: 50vh;
  }
}
</style>
