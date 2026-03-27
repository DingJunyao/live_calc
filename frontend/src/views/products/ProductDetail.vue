<template>
  <v-container fluid class="pa-0">
    <!-- 顶部导航 -->
    <v-app-bar elevation="0" color="background">
      <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
      <v-app-bar-title class="text-h6 text-truncate">
        {{ product?.name || '商品详情' }}
      </v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-pencil" variant="text" @click="openEditDialog" />
        <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadData" />
      </template>
    </v-app-bar>

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

    <template v-else-if="product">
      <!-- 基本信息卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-information-outline</v-icon>
          基本信息
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-list density="compact">
            <v-list-item v-if="product.brand">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-tag-outline</v-icon>
              </template>
              <v-list-item-title>品牌</v-list-item-title>
              <v-list-item-subtitle>{{ product.brand }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="product.barcode">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-barcode</v-icon>
              </template>
              <v-list-item-title>条码</v-list-item-title>
              <v-list-item-subtitle class="font-family-monospace">{{ product.barcode }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="product.ingredient_name">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-leaf</v-icon>
              </template>
              <v-list-item-title>关联原料</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  size="small"
                  color="secondary"
                  variant="flat"
                  class="cursor-pointer"
                  @click="goToIngredient"
                >
                  {{ product.ingredient_name }}
                  <v-icon end size="small">mdi-chevron-right</v-icon>
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="product.tags?.length">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-tag-multiple-outline</v-icon>
              </template>
              <v-list-item-title>标签</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  v-for="tag in product.tags"
                  :key="tag"
                  size="x-small"
                  class="mr-1"
                >
                  {{ tag }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-calendar</v-icon>
              </template>
              <v-list-item-title>创建时间</v-list-item-title>
              <v-list-item-subtitle>{{ formatDateTime(product.created_at) }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>

      <!-- 最新价格卡片 -->
      <v-card elevation="0" class="ma-4" v-if="product.latest_price">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="tertiary">mdi-currency-cny</v-icon>
          最新价格
        </v-card-title>
        <v-divider />
        <v-card-text class="text-center py-6">
          <div class="text-h3 font-weight-bold text-tertiary">
            ¥{{ formatPrice(product.latest_price) }}
          </div>
          <div class="text-caption text-medium-emphasis mt-2">
            {{ formatDate(product.latest_price_date) }}
          </div>
        </v-card-text>
      </v-card>

      <!-- 价格趋势图表 -->
      <PriceTrendChart
        v-if="product"
        title="价格趋势"
        icon="mdi-chart-line"
        icon-color="tertiary"
        :unit="chartUnit"
        empty-text="暂无价格历史数据"
        :data="chartData"
        :loading="loadingPrices"
        color="#ff9800"
        class="ma-4"
      />

      <!-- 价格记录列表 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-history</v-icon>
          价格记录
          <v-spacer />
          <v-btn
            v-if="priceRecords.length > 0"
            size="small"
            variant="text"
            color="primary"
            @click="showAddPriceDialog = true"
          >
            添加记录
          </v-btn>
        </v-card-title>
        <v-divider />

        <!-- 价格记录加载中 -->
        <div v-if="loadingPrices" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" size="32" />
        </div>

        <!-- 价格记录列表 -->
        <v-list v-else-if="priceRecords.length > 0" lines="two">
          <v-list-item v-for="record in priceRecords" :key="record.id">
            <template #prepend>
              <v-avatar color="tertiary-container" size="40">
                <span class="text-tertiary font-weight-bold">
                  ¥{{ formatPrice(record.price) }}
                </span>
              </v-avatar>
            </template>

            <v-list-item-title>
              ¥{{ formatPrice(record.price) }} / {{ record.original_quantity }}{{ record.original_unit }}
            </v-list-item-title>
            <v-list-item-subtitle>
              <template v-if="record.merchant_name">
                {{ record.merchant_name }} ·
              </template>
              {{ formatDateTime(record.recorded_at) }}
            </v-list-item-subtitle>

            <template #append>
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="deletePriceRecord(record.id)"
              />
            </template>
          </v-list-item>
        </v-list>

        <!-- 空状态 -->
        <v-card-text v-else class="text-center py-8">
          <v-icon size="64" color="medium-emphasis">mdi-receipt-text-outline</v-icon>
          <div class="text-body-1 text-medium-emphasis mt-4">暂无价格记录</div>
          <v-btn
            color="primary"
            variant="tonal"
            class="mt-4"
            prepend-icon="mdi-plus"
            @click="showAddPriceDialog = true"
          >
            添加价格记录
          </v-btn>
        </v-card-text>

        <!-- 分页器 -->
        <div v-if="priceTotal > 0" class="d-flex justify-center align-center ga-2 py-4">
          <v-pagination
            v-model="pricePage"
            :length="priceTotalPages"
            :total-visible="3"
            rounded="circle"
            density="compact"
          />
          <span class="text-caption text-medium-emphasis">共 {{ priceTotal }} 条</span>
        </div>
      </v-card>

      <!-- 营养数据卡片 -->
      <v-card elevation="0" class="ma-4" v-if="nutritionData">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="success">mdi-food-apple-outline</v-icon>
          营养成分
          <span class="text-caption text-medium-emphasis ml-2">（每100g）</span>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-row dense>
            <v-col cols="6" sm="4" v-for="item in nutritionItems" :key="item.key">
              <div class="nutrition-item pa-3 rounded">
                <div class="text-caption text-medium-emphasis">{{ item.label }}</div>
                <div class="text-h6 font-weight-bold">
                  {{ formatNutritionValue(nutritionData[item.key], item.unit) }}
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- 操作按钮 -->
      <div class="pa-4">
        <v-btn
          color="error"
          variant="tonal"
          block
          prepend-icon="mdi-delete"
          @click="confirmDelete"
        >
          删除商品
        </v-btn>
      </div>
    </template>

    <!-- 编辑对话框 -->
    <v-dialog v-model="showEditDialog" max-width="500">
      <v-card>
        <v-card-title>编辑商品</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEdit">
            <v-text-field
              v-model="editForm.name"
              label="商品名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-text-field
              v-model="editForm.brand"
              label="品牌"
              variant="outlined"
              class="mb-4"
            />
            <v-text-field
              v-model="editForm.barcode"
              label="条码"
              variant="outlined"
              class="mb-4"
            />
            <v-combobox
              v-model="editForm.tags"
              label="标签"
              variant="outlined"
              multiple
              chips
              closable-chips
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showEditDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveEdit">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 添加价格记录对话框 -->
    <v-dialog v-model="showAddPriceDialog" max-width="500">
      <v-card>
        <v-card-title>添加价格记录</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="savePriceRecord">
            <v-text-field
              v-model.number="priceForm.price"
              label="价格（元）"
              variant="outlined"
              type="number"
              step="0.01"
              required
              class="mb-4"
            />
            <v-row dense>
              <v-col cols="6">
                <v-text-field
                  v-model.number="priceForm.quantity"
                  label="数量"
                  variant="outlined"
                  type="number"
                  required
                />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model="priceForm.unit"
                  label="单位"
                  variant="outlined"
                  required
                />
              </v-col>
            </v-row>
            <v-autocomplete
              v-model="priceForm.merchant_id"
              :items="merchants"
              item-title="name"
              item-value="id"
              label="商家（可选）"
              variant="outlined"
              clearable
              class="mt-4"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddPriceDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingPrice" @click="savePriceRecord">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 确认删除对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">确认删除</v-card-title>
        <v-card-text>
          确定要删除商品「{{ product?.name }}」吗？此操作不可恢复。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteProduct">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 提示消息 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import PriceTrendChart from '@/components/charts/PriceTrendChart.vue'

interface Product {
  id: number
  name: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id?: number
  ingredient_name?: string
  tags?: string[]
  latest_price?: number | string
  latest_price_date?: string
  created_at: string
  updated_at?: string
}

interface PriceRecord {
  id: number
  product_id: number
  product_name: string
  price: number | string
  original_quantity: number | string
  original_unit: string
  merchant_name?: string
  recorded_at: string
}

interface Merchant {
  id: number
  name: string
}

const route = useRoute()
const router = useRouter()

const productId = computed(() => Number(route.params.id))

const product = ref<Product | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// 价格记录相关
const priceRecords = ref<PriceRecord[]>([])
const loadingPrices = ref(false)
const pricePage = ref(1)
const pricePageSize = ref(10)
const priceTotal = ref(0)
const priceTotalPages = computed(() => Math.ceil(priceTotal.value / pricePageSize.value))

// 营养数据
const nutritionData = ref<any>(null)

// 商家列表
const merchants = ref<Merchant[]>([])

// 对话框状态
const showEditDialog = ref(false)
const showAddPriceDialog = ref(false)
const showDeleteDialog = ref(false)
const saving = ref(false)
const savingPrice = ref(false)
const deleting = ref(false)

// 表单数据
const editForm = ref({
  name: '',
  brand: '',
  barcode: '',
  tags: [] as string[]
})

const priceForm = ref({
  price: 0,
  quantity: 1,
  unit: 'g',
  merchant_id: null as number | null
})

// 提示消息
const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// 营养素配置
const nutritionItems = [
  { key: 'calories', label: '热量', unit: 'kcal' },
  { key: 'protein', label: '蛋白质', unit: 'g' },
  { key: 'fat', label: '脂肪', unit: 'g' },
  { key: 'carbs', label: '碳水', unit: 'g' },
  { key: 'fiber', label: '膳食纤维', unit: 'g' },
  { key: 'sodium', label: '钠', unit: 'mg' }
]

// 聚合价格数据用于图表（按日期分组，计算最小、最大、平均价格）
const chartData = computed(() => {
  if (!priceRecords.value || priceRecords.value.length === 0) return []

  // 按日期分组
  const dailyMap = new Map<string, number[]>()

  for (const record of priceRecords.value) {
    if (!record.recorded_at) continue

    const date = new Date(record.recorded_at)
    if (isNaN(date.getTime())) continue

    const dateKey = date.toISOString().split('T')[0]

    // 计算单价（价格/数量）
    const quantity = parseFloat(String(record.original_quantity)) || 1
    const price = parseFloat(String(record.price)) || 0
    const unitPrice = price / quantity

    if (!dailyMap.has(dateKey)) {
      dailyMap.set(dateKey, [])
    }
    dailyMap.get(dateKey)!.push(unitPrice)
  }

  // 计算每日统计值
  return Array.from(dailyMap.entries())
    .map(([date, prices]) => {
      const sorted = prices.sort((a, b) => a - b)
      return {
        date,
        min: sorted[0] || 0,
        max: sorted[sorted.length - 1] || 0,
        avg: prices.reduce((a, b) => a + b, 0) / prices.length,
        count: prices.length
      }
    })
    .sort((a, b) => a.date.localeCompare(b.date))
})

// 获取实际使用的单位
const chartUnit = computed(() => {
  if (priceRecords.value && priceRecords.value.length > 0 && priceRecords.value[0].original_unit) {
    return priceRecords.value[0].original_unit
  }
  return ''
})

// 加载数据
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    // 加载商品详情
    const response = await api.get(`/products/entity/${productId.value}`)
    product.value = response

    // 并行加载其他数据
    await Promise.all([
      loadPriceRecords(),
      loadNutritionData()
    ])
  } catch (e: any) {
    console.error('加载商品失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 加载价格记录
const loadPriceRecords = async () => {
  loadingPrices.value = true
  try {
    const skip = (pricePage.value - 1) * pricePageSize.value
    const response = await api.get('/products', {
      params: {
        product_id: productId.value,
        skip,
        limit: pricePageSize.value
      }
    })
    priceRecords.value = response.items || []
    priceTotal.value = response.total || 0
  } catch (e) {
    console.error('加载价格记录失败', e)
    priceRecords.value = []
  } finally {
    loadingPrices.value = false
  }
}

// 加载营养数据
const loadNutritionData = async () => {
  if (!product.value?.ingredient_id) {
    nutritionData.value = null
    return
  }

  try {
    const response = await api.get(`/nutrition/products/${productId.value}/nutrition`)
    nutritionData.value = response
  } catch (e) {
    nutritionData.value = null
  }
}

// 加载商家列表
const loadMerchants = async () => {
  try {
    const response = await api.get('/merchants', { params: { limit: 100 } })
    merchants.value = response.items || []
  } catch (e) {
    merchants.value = []
  }
}

// 打开编辑对话框
const openEditDialog = () => {
  if (!product.value) return
  editForm.value = {
    name: product.value.name || '',
    brand: product.value.brand || '',
    barcode: product.value.barcode || '',
    tags: product.value.tags || []
  }
  showEditDialog.value = true
}

// 保存编辑
const saveEdit = async () => {
  if (!editForm.value.name.trim()) return

  saving.value = true
  try {
    const response = await api.put(`/products/entity/${productId.value}`, editForm.value)
    product.value = response
    showEditDialog.value = false
    showMessage('保存成功', 'success')
  } catch (e: any) {
    showMessage(e.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 保存价格记录
const savePriceRecord = async () => {
  if (!priceForm.value.price || !priceForm.value.quantity) return

  savingPrice.value = true
  try {
    await api.post('/products', {
      product_id: productId.value,
      product_name: product.value?.name,
      price: priceForm.value.price,
      original_quantity: priceForm.value.quantity,
      original_unit: priceForm.value.unit,
      merchant_id: priceForm.value.merchant_id
    })
    showAddPriceDialog.value = false
    // 重置表单
    priceForm.value = { price: 0, quantity: 1, unit: 'g', merchant_id: null }
    // 重新加载数据
    await loadData()
    showMessage('添加成功', 'success')
  } catch (e: any) {
    showMessage(e.message || '添加失败', 'error')
  } finally {
    savingPrice.value = false
  }
}

// 删除价格记录
const deletePriceRecord = async (id: number) => {
  if (!confirm('确定删除此价格记录？')) return

  try {
    await api.delete(`/products/${id}`)
    await loadPriceRecords()
    showMessage('删除成功', 'success')
  } catch (e: any) {
    showMessage(e.message || '删除失败', 'error')
  }
}

// 确认删除商品
const confirmDelete = () => {
  showDeleteDialog.value = true
}

// 删除商品
const deleteProduct = async () => {
  deleting.value = true
  try {
    await api.delete(`/products/entity/${productId.value}`)
    showMessage('删除成功', 'success')
    router.push('/data/products')
  } catch (e: any) {
    showMessage(e.message || '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

// 跳转到原料详情
const goToIngredient = () => {
  if (product.value?.ingredient_id) {
    router.push(`/data/ingredients/${product.value.ingredient_id}`)
  }
}

// 返回
const goBack = () => {
  router.push('/data/products')
}

// 格式化函数
const formatPrice = (price: any) => {
  const num = parseFloat(price) || 0
  return num.toFixed(2)
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatNutritionValue = (value: any, unit: string) => {
  const num = parseFloat(value) || 0
  return `${num.toFixed(1)} ${unit}`
}

// 显示消息
const showMessage = (message: string, color: string = 'success') => {
  snackbar.value = { show: true, message, color }
}

// 监听分页变化
watch(pricePage, loadPriceRecords)

// 初始化
onMounted(() => {
  loadData()
  loadMerchants()
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.font-family-monospace {
  font-family: monospace;
}

.nutrition-item {
  background: rgb(var(--v-theme-surface-variant));
  text-align: center;
}
</style>
