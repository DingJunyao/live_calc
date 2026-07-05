<template>
  <v-app-bar elevation="0" color="background" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">
      <div class="d-flex align-center ga-2">
        <span class="text-truncate">{{ overlaidMerchantName || '商家详情' }}</span>
        <v-chip size="x-small" variant="tonal" color="primary">商家</v-chip>
      </div>
    </v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-pencil" variant="text" @click="openEditDialog" />
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadData" />
    </template>
  </v-app-bar>

  <v-container fluid class="pa-0">
    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="ma-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadData">重试</v-btn>
      </template>
    </v-alert>

    <template v-else-if="merchant">
      <div class="px-4 pt-4 pb-0">
        <PendingProposalBanner :proposal="pendingProposal" />
      </div>
      <div class="merchant-layout">
        <!-- 基本信息 -->
        <v-card elevation="0" class="grid-item item-basic-info">
          <v-card-title class="d-flex align-center pb-2">
            <v-icon start color="primary">mdi-information-outline</v-icon>
            基本信息
          </v-card-title>
          <v-divider />
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template #prepend>
                  <v-icon size="small" color="medium-emphasis">mdi-store</v-icon>
                </template>
                <v-list-item-title>名称</v-list-item-title>
                <v-list-item-subtitle>{{ overlaidMerchantName }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="overlaidAddress">
                <template #prepend>
                  <v-icon size="small" color="medium-emphasis">mdi-map-marker</v-icon>
                </template>
                <v-list-item-title>地址</v-list-item-title>
                <v-list-item-subtitle>{{ overlaidAddress }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="overlaidLatitude != null && overlaidLongitude != null">
                <template #prepend>
                  <v-icon size="small" color="medium-emphasis">mdi-crosshairs-gps</v-icon>
                </template>
                <v-list-item-title>坐标</v-list-item-title>
                <v-list-item-subtitle class="font-family-monospace">
                  {{ overlaidLatitude.toFixed(4) }}, {{ overlaidLongitude.toFixed(4) }}
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-else>
                <template #prepend>
                  <v-icon size="small" color="medium-emphasis">mdi-crosshairs-gps</v-icon>
                </template>
                <v-list-item-title>坐标</v-list-item-title>
                <v-list-item-subtitle class="text-medium-emphasis">未设置位置</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="merchant.created_at">
                <template #prepend>
                  <v-icon size="small" color="medium-emphasis">mdi-calendar</v-icon>
                </template>
                <v-list-item-title>创建时间</v-list-item-title>
                <v-list-item-subtitle>{{ formatToLocalDateTimeShort(merchant.created_at) }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon size="small" :color="overlaidIsOpen !== false ? 'success' : 'warning'">
                    {{ overlaidIsOpen !== false ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                </template>
                <v-list-item-title>营业状态</v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip
                    :color="overlaidIsOpen !== false ? 'success' : 'warning'"
                    size="small"
                    variant="tonal"
                  >
                    {{ overlaidIsOpen !== false ? '营业中' : '已关闭' }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- 位置 -->
        <v-card elevation="0" class="grid-item item-location">
          <v-card-title class="d-flex align-center pb-2">
            <v-icon start color="secondary">mdi-map</v-icon>
            位置
          </v-card-title>
          <v-divider />
          <v-card-text>
            <div class="location-map">
              <MerchantMapView
                :merchants="overlaidMerchant ? [overlaidMerchant] : []"
                :selected-merchant="overlaidMerchant"
                :is-desktop="isDesktop"
              />
            </div>
          </v-card-text>
        </v-card>

        <!-- 商品价格列表 -->
        <v-card elevation="0" class="grid-item item-prices">
          <v-card-title class="d-flex align-center pb-2">
            <v-icon start color="tertiary">mdi-cart-outline</v-icon>
            商品价格
            <v-chip v-if="priceTotal > 0" size="x-small" variant="tonal" color="tertiary" class="ml-2">
              {{ priceTotal }}
            </v-chip>
          </v-card-title>
          <v-divider />

          <!-- 加载中 -->
          <div v-if="loadingPrices" class="text-center py-8">
            <v-progress-circular indeterminate color="primary" size="32" />
          </div>

          <!-- 移动端：列表样式 -->
          <v-list v-else-if="productPrices.length > 0 && smAndDown" lines="two">
            <v-list-item
              v-for="record in productPrices"
              :key="record.product_id"
              class="cursor-pointer"
              @click="goToProduct(record.product_id)"
            >
              <template #prepend>
                <v-avatar color="tertiary-container" size="40">
                  <v-icon color="tertiary">mdi-package-variant-closed</v-icon>
                </v-avatar>
              </template>

              <v-list-item-title class="d-flex align-center">
                {{ record.product_name }}
                <v-icon size="small" color="primary" class="ml-1">mdi-arrow-right</v-icon>
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ formatToLocalDateTimeShort(record.recorded_at) }}
              </v-list-item-subtitle>

              <template #append>
                <div class="text-tertiary font-weight-bold text-body-1">
                  <template v-if="record.standard_unit_price != null">
                    ¥{{ formatUnitPrice(record.standard_unit_price) }}{{ formatUnitSuffix(record.standard_unit_label) }}
                  </template>
                  <template v-else>¥{{ formatPrice(record.price) }}</template>
                </div>
              </template>
            </v-list-item>
          </v-list>

          <!-- 桌面端：卡片网格 -->
          <v-row v-else-if="productPrices.length > 0" dense class="price-grid px-2 pt-2 pb-1">
            <v-col
              v-for="record in productPrices"
              :key="record.product_id"
              cols="12"
              sm="6"
              md="4"
              lg="3"
              xl="2"
            >
              <v-card elevation="0" class="list-grid-card cursor-pointer h-100" @click="goToProduct(record.product_id)">
                <v-card-text>
                  <div class="d-flex align-center mb-2">
                    <v-avatar color="primary" size="40" class="mr-3">
                      <span class="text-white">{{ record.product_name?.charAt(0) }}</span>
                    </v-avatar>
                    <div class="text-body-2 font-weight-medium text-truncate">{{ record.product_name }}</div>
                  </div>
                  <div class="text-h6 font-weight-bold text-tertiary mb-1">
                    <template v-if="record.standard_unit_price != null">
                      ¥{{ formatUnitPrice(record.standard_unit_price) }}<span class="text-caption font-weight-regular text-medium-emphasis">{{ formatUnitSuffix(record.standard_unit_label) }}</span>
                    </template>
                    <template v-else>¥{{ formatPrice(record.price) }}</template>
                  </div>
                  <div class="d-flex flex-wrap align-center ga-2">
                    <span class="text-caption text-medium-emphasis">
                      {{ formatToLocalDateTimeShort(record.recorded_at) }}
                    </span>
                  </div>
                </v-card-text>
                <v-divider />
                <v-card-actions>
                  <v-spacer />
                  <v-btn icon="mdi-open-in-new" size="small" variant="text" color="primary" @click.stop="goToProduct(record.product_id)" />
                </v-card-actions>
              </v-card>
            </v-col>
          </v-row>

          <!-- 空状态 -->
          <!-- 分页器 -->
          <div v-if="priceTotal > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
            <v-pagination
              :model-value="pricePage"
              :length="priceTotalPages"
              :total-visible="priceTotalVisible"
              rounded="circle"
              density="comfortable"
              @update:model-value="onPricePageChange"
            />
            <div class="d-flex align-center ga-2">
              <v-select
                v-model="pricePageSize"
                :items="[10, 20, 50, 100]"
                label="每页"
                variant="outlined"
                density="compact"
                hide-details
                style="max-width: 90px"
                @update:model-value="handlePricePageSizeChange"
              />
              <span class="text-caption text-medium-emphasis">共 {{ priceTotal }} 条</span>
            </div>
          </div>

          <v-card-text v-else-if="productPrices.length === 0" class="text-center py-8">
            <v-icon size="64" color="medium-emphasis">mdi-cart-outline</v-icon>
            <div class="text-body-1 text-medium-emphasis mt-4">该商家暂无价格记录</div>
          </v-card-text>


        </v-card>
      </div>

      <!-- 编辑对话框 -->
      <v-dialog v-model="addDialog" max-width="500">
        <v-card>
          <v-card-title>编辑商家</v-card-title>
          <v-card-text>
            <v-form>
              <v-text-field
                v-model="editingForm.name"
                label="商家名称"
                variant="outlined"
                required
                class="mb-4"
              />
              <v-text-field
                v-model="editingForm.address"
                label="地址"
                variant="outlined"
                class="mb-4"
              />

              <v-switch
                v-model="editingForm.is_open"
                label="营业中"
                color="success"
                class="mb-4"
                hide-details
              />

              <!-- 地图选点 -->
              <div class="mb-4">
                <div class="text-subtitle-2 mb-2">商家位置</div>
                <MapPicker v-model="pickerCoords" :show-switcher="true" />
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
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { getErrorMessage } from '@/utils/errorHandler'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { usePageTitle } from '@/composables/usePageTitle'
import { useDisplay } from 'vuetify'
import MerchantMapView from '@/components/map/MerchantMapView.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import type { Coordinate } from '@/utils/map/mapTypes'
import { formatToLocalDateTimeShort } from '@/utils/timezone'
import { useUserStore } from '@/stores/user'
import PendingProposalBanner from '@/components/proposals/PendingProposalBanner.vue'
import { useGlobalSnackbar } from '@/composables/useGlobalSnackbar'

const route = useRoute()
const router = useRouter()
const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { setDetailTitle } = usePageTitle()
const { notify } = useGlobalSnackbar()
const { smAndDown, md, lgAndUp } = useDisplay()

interface Merchant {
  id: number
  name: string
  address?: string | null
  latitude?: number | null
  longitude?: number | null
  is_open?: boolean
  created_at?: string
}

interface ProductPrice {
  product_id: number
  product_name: string
  price: number
  standard_unit_price: number | null
  standard_unit_label: string | null
  original_quantity: number
  recorded_at: string
}

const merchantId = computed(() => Number(route.params.id))
const merchant = ref<Merchant | null>(null)
const pendingProposal = ref<{ id: number; action: string; payload: Record<string, any> } | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const userStore = useUserStore()

// 展示值——如果有待审核的 update 提议，则用提议中的值覆盖原值
const overlaidMerchantName = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.name) {
    return pendingProposal.value.payload.name
  }
  return merchant.value?.name || ''
})

const overlaidAddress = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.address !== undefined) {
    return pendingProposal.value.payload.address
  }
  return merchant.value?.address
})

const overlaidIsOpen = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.is_open !== undefined) {
    return pendingProposal.value.payload.is_open
  }
  return merchant.value?.is_open
})

const overlaidLatitude = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.latitude !== undefined) {
    return pendingProposal.value.payload.latitude
  }
  return merchant.value?.latitude
})

const overlaidLongitude = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.longitude !== undefined) {
    return pendingProposal.value.payload.longitude
  }
  return merchant.value?.longitude
})

// 合并了待审覆盖的虚拟 merchant 对象，用于传给地图等子组件
const overlaidMerchant = computed(() => {
  if (!merchant.value) return null
  const m = merchant.value
  if (pendingProposal.value?.action === 'update') {
    const p = pendingProposal.value.payload
    return {
      ...m,
      name: p.name ?? m.name,
      address: p.address !== undefined ? p.address : m.address,
      latitude: p.latitude !== undefined ? p.latitude : m.latitude,
      longitude: p.longitude !== undefined ? p.longitude : m.longitude,
      is_open: p.is_open !== undefined ? p.is_open : m.is_open,
    }
  }
  return m
})

// 各商品最新价格
const productPrices = ref<ProductPrice[]>([])
const loadingPrices = ref(false)
const pricePage = ref(1)
const pricePageSize = ref(20)
const priceTotal = ref(0)
const priceTotalPages = computed(() => Math.ceil(priceTotal.value / pricePageSize.value) || 1)
const priceTotalVisible = computed(() => lgAndUp.value ? 7 : md.value ? 5 : 3)

// 编辑
const addDialog = ref(false)
const editingForm = ref({ name: '', address: '', is_open: true })
const pickerCoords = ref<Coordinate | undefined>()
const saving = ref(false)

const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    merchant.value = await api.get(`/merchants/${merchantId.value}`)
    pendingProposal.value = merchant.value.pending_proposal || null
    setDetailTitle(merchant.value.name, '商家', '商家详情')
    await loadProductPrices()
  } catch (e: any) {
    console.error('加载商家详情失败', e)
    error.value = getErrorMessage(e, '加载失败')
  } finally {
    loading.value = false
  }
}

const loadProductPrices = async () => {
  loadingPrices.value = true
  try {
    const skip = (pricePage.value - 1) * pricePageSize.value
    const response = await api.get(`/merchants/${merchantId.value}/product-prices`, {
      params: { skip, limit: pricePageSize.value }
    })
    productPrices.value = response.items || []
    priceTotal.value = response.total || 0
  } catch (e) {
    productPrices.value = []
    priceTotal.value = 0
  } finally {
    loadingPrices.value = false
  }
}

const onPricePageChange = (page: number) => {
  pricePage.value = page
  loadProductPrices()
}

const handlePricePageSizeChange = () => {
  pricePage.value = 1
  loadProductPrices()
}

const openEditDialog = () => {
  if (!merchant.value) return
  editingForm.value = {
    name: merchant.value.name || '',
    address: merchant.value.address || '',
    is_open: merchant.value.is_open ?? true,
  }
  if (merchant.value.latitude != null && merchant.value.longitude != null) {
    pickerCoords.value = {
      lat: merchant.value.latitude,
      lng: merchant.value.longitude
    }
  } else {
    pickerCoords.value = undefined
  }
  addDialog.value = true
}

const saveItem = async () => {
  if (!editingForm.value.name.trim()) return

  saving.value = true
  try {
    const data: any = {
      name: editingForm.value.name,
      address: editingForm.value.address || undefined,
      is_open: editingForm.value.is_open,
    }

    if (pickerCoords.value) {
      data.latitude = pickerCoords.value.lat
      data.longitude = pickerCoords.value.lng
    }

    const response = await api.put(`/merchants/${merchantId.value}`, data)
    addDialog.value = false
    if (userStore.user?.is_admin) {
      merchant.value = response
    } else {
      // 普通用户提交提议后返回的是原值（未变），需重新加载详情刷新 pending_proposal
      notify('已提交，待管理员审核', 'info')
      await loadData()
    }
  } catch (e: any) {
    console.error('保存商家失败', e)
  } finally {
    saving.value = false
  }
}

const goBack = () => {
  router.back()
}

const goToProduct = (id: number) => {
  if (id) {
    router.push(`/data/products/${id}`)
  }
}

const formatPrice = (price: any) => {
  const num = parseFloat(price) || 0
  return num.toFixed(2)
}

// 单价智能格式化：整数不带小数，否则最多两位并去尾零（10.30 -> 10.3，10 -> 10）
const formatUnitPrice = (price: any) => {
  const num = parseFloat(price) || 0
  return Number(num.toFixed(2)).toString()
}

// 后端 label 形如 "元/斤"，主行已有 ¥ 前缀，去掉"元"只保留单位后缀
const formatUnitSuffix = (label: string | null) => {
  if (!label) return ''
  return label.replace(/^元/, '')
}

onMounted(() => {
  loadData()
  window.addEventListener('app-refresh', loadData)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', loadData)
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.font-family-monospace {
  font-family: monospace;
}

/* 列内边距微调（与价格管理页保持一致） */
.price-grid .v-col-12 {
  padding-block: 4px;
}

.location-map {
  height: 340px;
  width: 100%;
}

/* 地图卡片扁平化，避免与外层卡片形成双重边框 */
.location-map :deep(.merchant-map-view) {
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
}

/* === 响应式布局 === */
.merchant-layout {
  display: flex;
  flex-direction: column;
}

.merchant-layout > .grid-item {
  margin: 16px;
}

.item-basic-info { order: 1; }
.item-location { order: 2; }
.item-prices { order: 3; }

@media (min-width: 960px) {
  .merchant-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 16px;
  }

  .merchant-layout > .grid-item {
    margin: 0 !important;
  }

  .item-basic-info { grid-column: 1; grid-row: 1; }
  .item-location { grid-column: 2; grid-row: 1; }
  .item-prices { grid-column: 1 / -1; grid-row: 2; }
}
</style>
