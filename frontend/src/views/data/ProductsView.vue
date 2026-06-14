<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">商品管理</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadProducts" />
    </template>
  </v-app-bar>

  <v-container fluid class="list-grid-container">
    <div class="d-flex ga-2 mb-4 align-center">
      <v-text-field
        v-model="search"
        label="搜索商品..."
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        class="flex-grow-1"
        @update:model-value="debouncedSearch"
      />
      <FilterBar
        :filters="productFilters"
        :mobile="mdAndDown"
        @change="onFilterChange"
      />
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadProducts">重试</v-btn>
      </template>
    </v-alert>

    <!-- 商品列表 -->
    <template v-else>
      <!-- 移动端：列表样式 -->
      <v-card v-if="smAndDown" elevation="0">
        <v-list lines="two">
          <v-list-item
            v-for="item in items"
            :key="item.id"
            :to="`/data/products/${item.id}`"
          >
            <template #prepend>
              <v-avatar color="primary" size="40">
                <span class="text-white">{{ item.name?.charAt(0) }}</span>
              </v-avatar>
            </template>

            <v-list-item-title>
              {{ item.name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              <template v-if="item.aliases?.length">
                <v-chip
                  v-for="alias in item.aliases"
                  :key="alias"
                  size="x-small"
                  variant="tonal"
                  class="mr-1"
                >{{ alias }}</v-chip>
                <br>
              </template>
              <span>{{ item.brand || '无品牌' }}</span>
              <span v-if="item.latest_price != null" class="text-tertiary font-weight-bold ms-2">
                ¥{{ formatUnitPrice(item.latest_price) }}<span v-if="item.latest_price_unit" class="text-caption font-weight-regular text-medium-emphasis">/{{ item.latest_price_unit }}</span>
              </span>
            </v-list-item-subtitle>

            <template #append>
              <div
                v-if="item.sparkline_data"
                style="width: 64px; height: 36px; position: relative; flex-shrink: 0; margin-right: 4px"
              >
                <SparklineBackground :data="item.sparkline_data" color="primary" height="36" />
              </div>
              <v-btn icon="mdi-tag-plus" size="small" variant="text" @click.prevent="openPriceDialog(item)" />
              <v-btn icon="mdi-chevron-right" size="small" variant="text" />
            </template>
          </v-list-item>

          <v-list-item v-if="items.length === 0">
            <v-list-item-title class="text-center text-medium-emphasis">
              暂无商品
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- 桌面端：卡片网格 -->
      <v-row v-else>
        <v-col
          v-for="item in items"
          :key="item.id"
          cols="12"
          sm="6"
          md="4"
          lg="3"
          xl="2"
        >
          <v-card
            elevation="0"
            class="list-grid-card"
            :to="`/data/products/${item.id}`"
            hover
          >
            <SparklineBackground
              v-if="item.sparkline_data"
              :data="item.sparkline_data"
              color="primary"
            />
            <v-card-text style="position: relative; z-index: 1">
              <div class="d-flex align-center mb-2">
                <v-avatar color="primary" size="40" class="mr-3">
                  <span class="text-white">{{ item.name?.charAt(0) }}</span>
                </v-avatar>
                <div class="text-body-2 font-weight-medium text-truncate">{{ item.name }}</div>
              </div>
              <div v-if="item.aliases?.length" class="text-caption mb-1">
                <v-chip
                  v-for="alias in item.aliases"
                  :key="alias"
                  size="x-small"
                  variant="tonal"
                  class="mr-1"
                >{{ alias }}</v-chip>
              </div>
              <div class="text-caption text-medium-emphasis">{{ item.brand || '无品牌' }}</div>
              <div v-if="item.latest_price != null" class="text-subtitle-1 font-weight-bold text-tertiary">
                ¥{{ formatUnitPrice(item.latest_price) }}<span v-if="item.latest_price_unit" class="text-caption font-weight-regular text-medium-emphasis">/{{ item.latest_price_unit }}</span>
              </div>
            </v-card-text>
            <v-divider />
            <v-card-actions style="position: relative; z-index: 1">
              <v-spacer />
              <v-btn icon="mdi-tag-plus" size="small" variant="text" @click.prevent="openPriceDialog(item)" />
            </v-card-actions>
          </v-card>
        </v-col>

        <v-col v-if="items.length === 0" cols="12">
          <div class="text-center py-8 text-medium-emphasis">暂无商品</div>
        </v-col>
      </v-row>
    </template>

    <!-- 分页器 -->
    <div v-if="total > 0" class="d-flex flex-wrap justify-center align-center ga-2 pa-4">
      <v-pagination
        :model-value="currentPage"
        :length="totalPages"
        :total-visible="totalVisible"
        rounded="circle"
        density="comfortable"
        @update:model-value="onPageChange"
      />
      <div class="d-flex align-center ga-2">
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

    <!-- FAB 浮动添加按钮 -->
    <v-btn
      icon="mdi-plus"
      color="primary"
      size="large"
      elevation="8"
      class="position-fixed"
      style="bottom: 80px; right: 24px"
      @click="showAddDialog = true"
    />

    <!-- 快速记录价格对话框 -->
    <QuickPriceRecordDialog
      v-model="showPriceDialog"
      :product-id="priceDialogProduct?.id ?? null"
      :product-name="priceDialogProduct?.name ?? ''"
      @saved="onPriceSaved"
    />

    <!-- 添加对话框 -->
    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>添加商品</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="form.name"
              label="商品名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-autocomplete
              v-model="selectedIngredient"
              v-model:search="ingredientSearch"
              :items="ingredients"
              item-title="name"
              item-value="id"
              label="关联原料 *"
              variant="outlined"
              required
              :loading="loadingIngredients"
              :no-data-text="ingredientSearch ? '未找到匹配的原料' : '请输入搜索关键词'"
              placeholder="输入关键词搜索原料"
              clearable
              return-object
              auto-select-first
              hide-selected
              :custom-filter="() => true"
              class="mb-4"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <v-list-item-subtitle v-if="item.raw.aliases && item.raw.aliases.length > 0">
                    别名: {{ item.raw.aliases.join(', ') }}
                  </v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-autocomplete>
            <v-text-field
              v-model="form.brand"
              label="品牌"
              variant="outlined"
              class="mb-4"
            />
            <v-text-field
              v-model="form.barcode"
              label="条码"
              variant="outlined"
              class="mb-4"
            />
            <v-combobox
              v-model="form.aliases"
              label="别名"
              variant="outlined"
              multiple
              chips
              closable-chips
              hint="输入后回车添加多个别名"
              persistent-hint
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveItem">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { api } from '@/api/client'
import { getErrorMessage } from '@/utils/errorHandler'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import QuickPriceRecordDialog from '@/components/prices/QuickPriceRecordDialog.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import type { FilterConfig } from '@/components/common/FilterBar.vue'
import { useLatestPrices, formatUnitPrice } from '@/composables/useLatestPrices'
import SparklineBackground from '@/components/charts/SparklineBackground.vue'

const route = useRoute()
const router = useRouter()
const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { smAndDown, mdAndDown, md, lgAndUp } = useDisplay()

interface Product {
  id: number
  name: string
  brand?: string
  barcode?: string
  aliases?: string[]
  description?: string
  created_at?: string
}

interface Ingredient {
  id: number
  name: string
  aliases?: string[]
  default_unit?: string
}

const items = ref<Product[]>([])

// 当天平均单价
const { load: loadLatestPrices } = useLatestPrices(
  items,
  (item) => `/products/entity/${item.id}/latest-price`
)
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref((route.query.search as string) || '')
const showAddDialog = ref(false)
const saving = ref(false)

// 快速记录价格相关
const showPriceDialog = ref(false)
const priceDialogProduct = ref<Product | null>(null)

// 原料列表
const ingredients = ref<Ingredient[]>([])
const loadingIngredients = ref(false)
const ingredientSearch = ref('')
const selectedIngredient = ref<Ingredient | null>(null)

const form = ref({
  name: '',
  brand: '',
  barcode: '',
  aliases: [] as string[],
  ingredient_id: null as number | null
})

// 分页相关（从 URL 查询参数初始化）
const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(Number(route.query.pageSize) || 20)
const total = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
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

// 筛选器相关
const categoryOptions = ref<{ value: number; title: string }[]>([])
const brandOptions = ref<{ value: string; title: string }[]>([])
const requestFilters = ref<Record<string, any>>({})

const productFilters = computed<FilterConfig[]>(() => [
  {
    key: 'ingredient_ids',
    label: '关联原料',
    type: 'select',
    items: ingredients.value.map(i => ({ value: i.id, title: i.name })),
    minWidth: '180px',
    maxWidth: '240px',
  },
  {
    key: 'ingredient_category_ids',
    label: '原料分类',
    type: 'select',
    items: categoryOptions.value,
    minWidth: '160px',
    maxWidth: '220px',
  },
  {
    key: 'brands',
    label: '品牌',
    type: 'select',
    items: brandOptions.value,
    minWidth: '140px',
    maxWidth: '200px',
  },
])

const onFilterChange = (filterState: Record<string, any>) => {
  currentPage.value = 1
  requestFilters.value = filterState
  loadProducts()
}

const loadCategories = async () => {
  try {
    const response = await api.get('/ingredients/categories')
    categoryOptions.value = (response || []).map((c: any) => ({
      value: c.id,
      title: c.display_name,
    }))
  } catch (e: any) {
    console.error('加载分类失败', e)
  }
}

const loadBrands = async () => {
  try {
    const response = await api.get('/products/entity', { params: { limit: 1000 } })
    const products: any[] = response.items || []
    const uniqueBrands = [...new Set(products.map((p: any) => p.brand).filter(Boolean))]
    brandOptions.value = uniqueBrands.map(b => ({ value: b, title: b }))
  } catch (e: any) {
    console.error('加载品牌列表失败', e)
  }
}

// 加载原料列表
const loadIngredients = async (searchText?: string) => {
  loadingIngredients.value = true
  try {
    const params: Record<string, any> = { limit: 100 }
    if (searchText) {
      params.q = searchText
    }
    const response = await api.get('/ingredients', { params })
    ingredients.value = response.items || []
  } catch (e: any) {
    console.error('加载原料列表失败', e)
  } finally {
    loadingIngredients.value = false
  }
}

// 监听原料搜索输入，防抖处理
let ingredientSearchTimeout: ReturnType<typeof setTimeout> | null = null
watch(ingredientSearch, (newVal) => {
  if (ingredientSearchTimeout) clearTimeout(ingredientSearchTimeout)
  ingredientSearchTimeout = setTimeout(() => {
    loadIngredients(newVal)
  }, 300)
})

// 监听选中的原料对象，同步 ingredient_id 到表单
watch(selectedIngredient, (newIngredient) => {
  form.value.ingredient_id = newIngredient?.id || null
}, { immediate: true })

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    syncToUrl()
    loadProducts()
  }, 300)
}

const loadProducts = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = {
      skip,
      limit: pageSize.value,
      sort_by: 'price_records'  // 按价格记录次数排序
    }
    if (search.value) {
      params.search = search.value
    }
    // 筛选参数
    if (requestFilters.value.ingredient_ids?.length) {
      params.ingredient_ids = requestFilters.value.ingredient_ids.join(',')
    }
    if (requestFilters.value.ingredient_category_ids?.length) {
      params.ingredient_category_ids = requestFilters.value.ingredient_category_ids.join(',')
    }
    if (requestFilters.value.brands?.length) {
      params.brands = requestFilters.value.brands.join(',')
    }

    const response = await api.get('/products/entity', { params })
    items.value = response.items || []
    total.value = response.total || 0
    // 基本数据到位，立即渲染页面
    loading.value = false
    // 后台加载价格和迷你图，互不影响
    loadLatestPrices()
    if (items.value.length > 0) loadProductSparklines()
  } catch (e: any) {
    console.error('加载商品失败', e)
    error.value = getErrorMessage(e, '加载失败')
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  syncToUrl()
  loadProducts()
}

const onPageChange = (page: number) => {
  currentPage.value = page
  syncToUrl()
  loadProducts()
}

const openPriceDialog = (product: Product) => {
  priceDialogProduct.value = product
  showPriceDialog.value = true
}

const loadProductSparklines = async () => {
  const ids = items.value.map((i: Product) => i.id).join(',')
  if (!ids) return
  try {
    const sparklines = await api.get('/sparklines/products', { params: { ids } })
    if (sparklines) {
      items.value = items.value.map((item: any) => ({
        ...item,
        sparkline_data: sparklines[String(item.id)] || undefined
      }))
    }
  } catch (e) {
    console.error('加载商品迷你图失败', e)
  }
}

const onPriceSaved = () => {
  // 价格记录保存成功后无需刷新商品列表
}

const saveItem = async () => {
  if (!form.value.name.trim()) return
  if (!form.value.ingredient_id) {
    alert('请选择关联的原料')
    return
  }

  saving.value = true
  try {
    const response = await api.post('/products/entity', form.value)
    items.value.unshift(response)
    total.value++
    showAddDialog.value = false
    form.value = { name: '', brand: '', barcode: '', aliases: [], ingredient_id: null }
    selectedIngredient.value = null
    ingredientSearch.value = ''
  } catch (e: any) {
    console.error('保存商品失败', e)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadProducts()
  loadIngredients()
  loadCategories()
  loadBrands()
  window.addEventListener('app-refresh', loadProducts)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', loadProducts)
})
</script>
