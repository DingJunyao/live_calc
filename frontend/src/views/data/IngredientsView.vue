<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">原料管理</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadIngredients" />
    </template>
  </v-app-bar>

  <v-container fluid class="list-grid-container">
    <div class="d-flex ga-2 mb-4 align-center">
      <v-text-field
        v-model="search"
        label="搜索原料..."
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        class="flex-grow-1"
        @update:model-value="debouncedSearch"
      />
      <FilterBar
        :filters="ingredientFilters"
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
        <v-btn variant="text" @click="loadIngredients">重试</v-btn>
      </template>
    </v-alert>

    <!-- 原料列表 -->
    <template v-else>
      <!-- 移动端：列表样式 -->
      <v-card v-if="smAndDown" elevation="0">
        <v-list lines="two">
          <v-list-item
            v-for="item in items"
            :key="item.id"
            :to="`/data/ingredients/${item.id}`"
          >
            <template #prepend>
              <v-avatar color="secondary" size="40">
                <span class="text-white font-weight-bold">{{ item.name?.charAt(0) }}</span>
              </v-avatar>
            </template>

            <v-list-item-title>{{ item.name }}</v-list-item-title>
            <v-list-item-subtitle>
              <span>{{ item.category || '未分类' }}</span>
              <span v-if="item.latest_price != null" class="text-tertiary font-weight-bold ms-2">
                ¥{{ formatUnitPrice(item.latest_price) }}<span v-if="item.latest_price_unit" class="text-caption font-weight-regular text-medium-emphasis">/{{ item.latest_price_unit }}</span>
              </span>
            </v-list-item-subtitle>

            <template #append>
              <div
                v-if="item.sparkline_data"
                style="width: 64px; height: 36px; position: relative; flex-shrink: 0; margin-right: 4px"
              >
                <SparklineBackground :data="item.sparkline_data" color="secondary" height="36" />
              </div>
              <v-btn
                icon="mdi-tag-plus"
                size="small"
                variant="text"
                :loading="loadingProductsFor === item.id"
                @click.prevent="openPriceDialog(item)"
              />
              <v-btn icon="mdi-chevron-right" size="small" variant="text" />
            </template>
          </v-list-item>

          <v-list-item v-if="items.length === 0">
            <v-list-item-title class="text-center text-medium-emphasis">
              暂无原料
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
            :to="`/data/ingredients/${item.id}`"
            hover
          >
            <SparklineBackground
              v-if="item.sparkline_data"
              :data="item.sparkline_data"
              color="secondary"
            />
            <v-card-text style="position: relative; z-index: 1">
              <div class="d-flex align-center mb-2">
                <v-avatar color="secondary" size="40" class="mr-3">
                  <span class="text-white font-weight-bold">{{ item.name?.charAt(0) }}</span>
                </v-avatar>
                <div class="text-body-2 font-weight-medium text-truncate">{{ item.name }}</div>
              </div>
              <v-chip size="x-small" color="default" variant="outlined">
                {{ item.category || '未分类' }}
              </v-chip>
              <div v-if="item.latest_price != null" class="text-subtitle-1 font-weight-bold text-tertiary mb-1">
                ¥{{ formatUnitPrice(item.latest_price) }}<span v-if="item.latest_price_unit" class="text-caption font-weight-regular text-medium-emphasis">/{{ item.latest_price_unit }}</span>
              </div>
            </v-card-text>
            <v-divider />
            <v-card-actions style="position: relative; z-index: 1">
              <v-spacer />
              <v-btn
                icon="mdi-tag-plus"
                size="small"
                variant="text"
                :loading="loadingProductsFor === item.id"
                @click.prevent="openPriceDialog(item)"
              />
            </v-card-actions>
          </v-card>
        </v-col>

        <v-col v-if="items.length === 0" cols="12">
          <div class="text-center py-8 text-medium-emphasis">暂无原料</div>
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
      :products="priceDialogProducts"
      @saved="onPriceSaved"
    />

    <!-- 提示消息 -->
    <v-snackbar v-model="showSnackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>

    <!-- 添加对话框 -->
    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>添加原料</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="form.name"
              label="原料名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-combobox
              v-model="form.aliases"
              label="别名"
              variant="outlined"
              class="mb-4"
              chips
              multiple
              closable-chips
              hide-selected
              placeholder="输入别名后按回车添加，可添加多个"
              no-data-text="输入别名后按回车"
              :delimiters="[',', '，', ' ']"
            />
            <v-select
              v-model="form.category_id"
              :items="categories"
              item-title="display_name"
              item-value="id"
              label="分类"
              variant="outlined"
              class="mb-4"
              clearable
              placeholder="请选择分类"
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

interface Ingredient {
  id: number
  name: string
  category?: string
  default_unit?: string
  created_at?: string
}

interface Category {
  id: number
  name: string
  display_name: string
  description?: string
}

const items = ref<Ingredient[]>([])

// 当天平均单价
const { load: loadLatestPrices } = useLatestPrices(
  items,
  (item) => `/nutrition/ingredients/${item.id}/latest-price`
)
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref((route.query.search as string) || '')
const showAddDialog = ref(false)
const saving = ref(false)

// 快速记录价格相关
const showPriceDialog = ref(false)
const priceDialogProduct = ref<{ id: number; name: string } | null>(null)
const priceDialogProducts = ref<{ id: number; name: string }[]>([])
const loadingProductsFor = ref<number | null>(null)

// 提示消息
const showSnackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('info')

// 分类列表
const categories = ref<Category[]>([])

const form = ref({
  name: '',
  category_id: null as number | null,
  aliases: [] as string[],
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
const requestFilters = ref<Record<string, any>>({})

const ingredientFilters = computed<FilterConfig[]>(() => [
  {
    key: 'category_ids',
    label: '分类',
    type: 'select',
    items: categoryOptions.value,
    minWidth: '160px',
    maxWidth: '240px',
  },
])

const onFilterChange = (filterState: Record<string, any>) => {
  currentPage.value = 1
  requestFilters.value = filterState
  loadIngredients()
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

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    syncToUrl()
    loadIngredients()
  }, 300)
}

interface ProductItem {
  id: number
  name: string
}

const openPriceDialog = async (ingredient: Ingredient) => {
  loadingProductsFor.value = ingredient.id
  try {
    const response = await api.get('/products/entity', {
      params: { ingredient_id: ingredient.id, limit: 50 }
    })
    const products: ProductItem[] = response.items || []

    if (products.length === 0) {
      snackbarText.value = '该原料暂无关联商品，请先添加商品'
      snackbarColor.value = 'warning'
      showSnackbar.value = true
      return
    }

    // 优先匹配同名商品，否则取第一个
    const matched = products.find(p => p.name === ingredient.name) || products[0]
    priceDialogProduct.value = matched
    priceDialogProducts.value = products
    showPriceDialog.value = true
  } catch (e: any) {
    console.error('加载商品失败', e)
    snackbarText.value = '加载商品失败'
    snackbarColor.value = 'error'
    showSnackbar.value = true
  } finally {
    loadingProductsFor.value = null
  }
}

const loadIngredientSparklines = async () => {
  const ids = items.value.map((i: Ingredient) => i.id).join(',')
  if (!ids) return
  try {
    const sparklines = await api.get('/sparklines/ingredients', { params: { ids } })
    if (sparklines) {
      items.value = items.value.map((item: any) => ({
        ...item,
        sparkline_data: sparklines[String(item.id)] || undefined
      }))
    }
  } catch (e) {
    console.error('加载原料迷你图失败', e)
  }
}

const onPriceSaved = () => {
  // 价格记录保存成功后无需刷新原料列表
}

// 加载选项数据（分类和单位）
const loadOptions = async () => {
  try {
    const categoriesRes = await api.get('/ingredients/categories')
    categories.value = categoriesRes || []
  } catch (e: any) {
    console.error('加载分类失败', e)
  }
}

const loadIngredients = async () => {
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
      params.q = search.value
    }
    // 筛选参数
    if (requestFilters.value.category_ids?.length) {
      params.category_ids = requestFilters.value.category_ids.join(',')
    }

    const response = await api.get('/ingredients', { params })
    items.value = response.items || []
    total.value = response.total || 0
    // 基本数据到位，立即渲染页面
    loading.value = false
    // 后台加载价格和迷你图，互不影响
    loadLatestPrices()
    if (items.value.length > 0) loadIngredientSparklines()
  } catch (e: any) {
    console.error('加载原料失败', e)
    error.value = getErrorMessage(e, '加载失败')
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  syncToUrl()
  loadIngredients()
}

const onPageChange = (page: number) => {
  currentPage.value = page
  syncToUrl()
  loadIngredients()
}

const saveItem = async () => {
  if (!form.value.name.trim()) return

  saving.value = true
  try {
    const payload: any = {
      name: form.value.name,
    }

    // 只添加有值的字段
    if (form.value.category_id) {
      payload.category_id = form.value.category_id
    }
    if (form.value.aliases && form.value.aliases.length > 0) {
      payload.aliases = form.value.aliases
    }

    const response = await api.post('/ingredients', payload)
    items.value.unshift(response)
    total.value++
    showAddDialog.value = false
    form.value = {
      name: '',
      category_id: null,
      aliases: [],
    }
  } catch (e: any) {
    console.error('保存原料失败', e)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadIngredients()
  loadOptions()
  loadCategories()
  window.addEventListener('app-refresh', loadIngredients)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', loadIngredients)
})
</script>
