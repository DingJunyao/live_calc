<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">价格记录</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadRecords" />
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <v-text-field
      v-model="searchQuery"
      label="搜索商品..."
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      density="compact"
      hide-details
      clearable
      class="mb-4"
      @update:model-value="debouncedSearch"
    />

    <v-progress-circular v-if="loading" indeterminate color="primary" class="ma-4" />

    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadRecords">重试</v-btn>
      </template>
    </v-alert>

    <v-card v-else elevation="0">
      <v-list lines="three">
        <v-list-item v-for="record in records" :key="record.id">
          <template #prepend>
            <v-avatar color="primary" size="40">
              <span class="text-white">{{ record.product_name?.charAt(0) }}</span>
            </v-avatar>
          </template>

          <v-list-item-title>{{ record.product_name }}</v-list-item-title>
          <v-list-item-subtitle>
            ¥{{ formatPrice(record.price) }} / {{ record.original_quantity }}{{ record.original_unit }}
          </v-list-item-subtitle>
          <v-list-item-subtitle>
            {{ record.merchant_name || '未知商家' }}
          </v-list-item-subtitle>
          <v-list-item-subtitle>
            {{ formatDateTime(record.recorded_at) }}
          </v-list-item-subtitle>

          <template #append>
            <v-btn icon="mdi-pencil" size="small" variant="text" color="primary" class="mr-1" @click="openEditDialog(record)" />
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="deleteRecord(record.id)" />
          </template>
        </v-list-item>

        <v-list-item v-if="records.length === 0">
          <v-list-item-title class="text-center">暂无记录</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>

    <div v-if="total > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
      <v-pagination
        v-model="currentPage"
        :length="totalPages"
        :total-visible="3"
        rounded="circle"
        density="comfortable"
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
      @click="openAddDialog"
    />

    <!-- 添加/编辑价格记录对话框 -->
    <v-dialog v-model="showDialog" max-width="500" persistent>
      <v-card>
        <v-card-title>{{ isEditing ? '编辑价格记录' : '添加价格记录' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef" v-model="formValid">
            <!-- 商品名称（带自动完成） -->
            <v-autocomplete
              v-model="selectedProduct"
              v-model:search="productSearch"
              :items="productSuggestions"
              :loading="productLoading"
              item-title="name"
              item-value="id"
              label="商品名称"
              variant="outlined"
              :rules="productIdRules"
              :no-data-text="productSearch ? '没有找到商品，将创建新商品' : '输入商品名称搜索'"
              clearable
              auto-select-first
              return-object
              hide-selected
              :custom-filter="() => true"
              class="mb-4"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <template #subtitle>
                    <span v-if="item.raw.matched_alias" class="text-caption">
                      别名: {{ item.raw.matched_alias }}
                    </span>
                    <span v-else-if="item.raw.ingredient_name" class="text-caption">
                      {{ item.raw.ingredient_name }}
                    </span>
                  </template>
                </v-list-item>
              </template>
            </v-autocomplete>

            <!-- 如果没有选择现有商品，显示新商品名称输入框 -->
            <v-text-field
              v-if="!form.product_id && productSearch"
              :model-value="productSearch"
              label="新商品名称"
              variant="outlined"
              density="compact"
              disabled
              hint="将创建新商品"
              class="mb-4"
            />

            <!-- 价格 -->
            <v-text-field
              v-model.number="form.price"
              label="价格 (元)"
              variant="outlined"
              type="number"
              :rules="priceRules"
              class="mb-4"
            />

            <!-- 数量和单位 -->
            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model.number="form.original_quantity"
                  label="数量"
                  variant="outlined"
                  type="number"
                  :rules="quantityRules"
                />
              </v-col>
              <v-col cols="6">
                <v-select
                  v-model="form.original_unit"
                  :items="unitOptions"
                  label="单位"
                  variant="outlined"
                  :rules="unitRules"
                />
              </v-col>
            </v-row>

            <!-- 商家选择 -->
            <v-autocomplete
              v-model="form.merchant_id"
              :items="merchantOptions"
              item-title="name"
              item-value="id"
              label="商家（可选）"
              variant="outlined"
              clearable
              class="mb-4"
            />

            <!-- 计入支出复选框 -->
            <v-checkbox
              v-model="form.is_purchase"
              label="计入支出"
              color="primary"
              density="comfortable"
              class="mb-4"
            >
              <template #append>
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon v-bind="props" size="small" color="grey">mdi-help-circle</v-icon>
                  </template>
                  <span>勾选此项表示此价格记录来自实际购买，将用于支出计算</span>
                </v-tooltip>
              </template>
            </v-checkbox>

            <!-- 记录时间 -->
            <v-text-field
              v-model="form.recorded_at"
              label="记录时间（可选）"
              variant="outlined"
              type="datetime-local"
              class="mb-4"
            />

            <!-- 备注 -->
            <v-textarea
              v-model="form.notes"
              label="备注（可选）"
              variant="outlined"
              rows="2"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeDialog">取消</v-btn>
          <v-btn color="primary" :loading="saving" :disabled="!formValid" @click="saveRecord">
            {{ isEditing ? '保存' : '添加' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/api/client'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

interface PriceRecord {
  id: number
  product_id: number
  product_name: string
  merchant_id?: number
  merchant_name?: string
  price: number | string
  currency: string
  original_quantity: number
  original_unit: string
  recorded_at: string
  notes?: string
  record_type?: string  // 记录类型: 'purchase' | 'price'
}

interface ProductSuggestion {
  id: number
  name: string
  brand?: string
  ingredient_name?: string
  matched_alias?: string
}

interface Merchant {
  id: number
  name: string
}

const records = ref<PriceRecord[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref('')
const pageSize = ref(20)
const currentPage = ref(1)
const total = ref(0)

// 对话框相关
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()
const formValid = ref(false)

// 表单数据
const form = ref({
  product_id: null as number | null,
  product_name: '',  // 用于显示商品名称
  price: null as number | null,
  original_quantity: null as number | null,
  original_unit: '',
  merchant_id: null as number | null,
  recorded_at: '',
  notes: '',
  is_purchase: true  // 是否为购买记录（默认为 true）
})

// 商品自动完成相关
const productSearch = ref('')
const productSuggestions = ref<ProductSuggestion[]>([])
const productLoading = ref(false)
const selectedProduct = ref<ProductSuggestion | null>(null)

// 获取当前时间的本地格式 (YYYY-MM-DDTHH:mm)
const getCurrentLocalDateTime = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

// 商家选项
const merchantOptions = ref<Merchant[]>([])

// 单位选项
const unitOptions = [
  { title: '克 (g)', value: 'g' },
  { title: '千克 (kg)', value: 'kg' },
  { title: '斤', value: '斤' },
  { title: '两', value: '两' },
  { title: '毫升 (ml)', value: 'ml' },
  { title: '升 (L)', value: 'L' },
  { title: '个', value: '个' },
  { title: '包', value: '包' },
  { title: '袋', value: '袋' },
  { title: '盒', value: '盒' },
  { title: '瓶', value: '瓶' },
  { title: '罐', value: '罐' },
]

// 表单验证规则
const productIdRules = [
  (v: number | null) => !!v || '请选择或输入商品名称'
]

const priceRules = [
  (v: number | null) => v !== null && v > 0 || '请输入有效价格'
]

const quantityRules = [
  (v: number | null) => v !== null && v > 0 || '请输入有效数量'
]

const unitRules = [
  (v: string) => !!v || '请选择单位'
]

// 会话记忆的键名
const SESSION_KEYS = {
  MERCHANT_ID: 'price_form_merchant_id',
  IS_PURCHASE: 'price_form_is_purchase'
} as const

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

let searchTimeout: ReturnType<typeof setTimeout> | null = null
let productSearchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadRecords()
  }, 300)
}

// 处理商品选择，确保显示名称而不是ID
const onProductSelect = (productId: number | null) => {
  form.value.product_id = productId
  if (productId) {
    const selectedProduct = productSuggestions.value.find(p => p.id === productId)
    if (selectedProduct) {
      // 更新搜索值为商品名称，防止显示ID
      productSearch.value = selectedProduct.name
    }
  }
}

const loadRecords = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = { skip, limit: pageSize.value }
    if (searchQuery.value) params.search = searchQuery.value
    const response = await api.get('/products', { params })
    records.value = response.items || []
    total.value = response.total || 0
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const loadMerchants = async () => {
  try {
    const response = await api.get('/merchants', { params: { limit: 100 } })
    merchantOptions.value = response.items || []
  } catch (e: any) {
    console.error('加载商家失败', e)
  }
}

const searchProducts = async () => {
  if (!productSearch.value || productSearch.value.length < 1) {
    productSuggestions.value = []
    return
  }

  productLoading.value = true
  try {
    const response = await api.get('/products/autocomplete', {
      params: { q: productSearch.value, limit: 20 }
    })
    productSuggestions.value = response || []
    console.log('[DEBUG] 搜索商品:', productSearch.value, '返回结果:', productSuggestions.value)
  } catch (e: any) {
    console.error('搜索商品失败', e)
    productSuggestions.value = []
  } finally {
    productLoading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  loadRecords()
}

watch(currentPage, loadRecords)

// 监听商品搜索输入，执行防抖搜索
watch(productSearch, (newSearch) => {
  if (productSearchTimeout) clearTimeout(productSearchTimeout)
  productSearchTimeout = setTimeout(() => {
    searchProducts()
  }, 300)
})

// 监听选中的商品对象，同步 product_id 到表单
watch(selectedProduct, (newProduct) => {
  form.value.product_id = newProduct?.id || null
}, { immediate: true })

const formatPrice = (price: any) => (parseFloat(price) || 0).toFixed(2)

const formatDateTime = (dateTimeStr: string) => {
  if (!dateTimeStr) return ''
  const date = new Date(dateTimeStr)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hours}:${minutes}`
}

// 从会话存储加载记忆的值
const loadSessionMemory = () => {
  const savedMerchantId = sessionStorage.getItem(SESSION_KEYS.MERCHANT_ID)
  const savedIsPurchase = sessionStorage.getItem(SESSION_KEYS.IS_PURCHASE)

  return {
    merchantId: savedMerchantId ? parseInt(savedMerchantId, 10) : null,
    isPurchase: savedIsPurchase ? savedIsPurchase === 'true' : true  // 默认为 true
  }
}

// 保存到会话存储
const saveSessionMemory = () => {
  if (form.value.merchant_id !== null && form.value.merchant_id !== undefined) {
    sessionStorage.setItem(SESSION_KEYS.MERCHANT_ID, form.value.merchant_id.toString())
  }
  sessionStorage.setItem(SESSION_KEYS.IS_PURCHASE, String(form.value.is_purchase))
}

const openAddDialog = () => {
  isEditing.value = false
  editingId.value = null

  // 加载会话记忆
  const sessionMemory = loadSessionMemory()

  form.value = {
    product_id: null,
    product_name: '',
    price: null,
    original_quantity: 1,  // 默认数量为 1
    original_unit: '斤',   // 默认单位为斤
    merchant_id: sessionMemory.merchantId,
    recorded_at: getCurrentLocalDateTime(),  // 默认为当前时间
    notes: '',
    is_purchase: sessionMemory.isPurchase
  }
  productSearch.value = ''
  productSuggestions.value = []
  selectedProduct.value = null
  showDialog.value = true
}

const openEditDialog = (record: PriceRecord) => {
  isEditing.value = true
  editingId.value = record.id
  form.value = {
    product_id: record.product_id,
    product_name: record.product_name,
    price: parseFloat(String(record.price)),
    original_quantity: record.original_quantity,
    original_unit: record.original_unit,
    merchant_id: record.merchant_id || null,
    recorded_at: record.recorded_at ? record.recorded_at.slice(0, 16) : '',
    notes: record.notes || '',
    is_purchase: (record as any).record_type !== 'price'  // record_type 为 'price' 时不是购买记录
  }
  productSearch.value = record.product_name
  productSuggestions.value = [{ id: record.product_id, name: record.product_name }]
  selectedProduct.value = { id: record.product_id, name: record.product_name }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
  formRef.value?.reset()
  selectedProduct.value = null
}

const saveRecord = async () => {
  if (!formRef.value?.validate()) return

  saving.value = true
  try {
    const data: Record<string, any> = {
      price: form.value.price,
      original_quantity: form.value.original_quantity,
      original_unit: form.value.original_unit,
      merchant_id: form.value.merchant_id,
      notes: form.value.notes || null,
      record_type: form.value.is_purchase ? 'purchase' : 'price'  // 映射到后端的 record_type
    }

    // 如果有记录时间，添加到数据中
    if (form.value.recorded_at) {
      data.recorded_at = new Date(form.value.recorded_at).toISOString()
    }

    if (isEditing.value && editingId.value) {
      // 更新记录
      await api.put(`/products/${editingId.value}`, data)
    } else {
      // 创建记录
      if (form.value.product_id) {
        data.product_id = form.value.product_id
      } else if (productSearch.value) {
        data.product_name = productSearch.value
      }
      await api.post('/products', data)
    }

    // 保存会话记忆（仅在新增记录时）
    if (!isEditing.value) {
      saveSessionMemory()
    }

    closeDialog()
    loadRecords()
  } catch (e: any) {
    console.error('保存记录失败', e)
    alert(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const deleteRecord = async (id: number) => {
  if (!confirm('确定删除此价格记录?')) return
  try {
    await api.delete(`/products/${id}`)
    loadRecords()
  } catch (e: any) {
    console.error('删除失败', e)
    alert(e.message || '删除失败')
  }
}

// 监听全局刷新事件
const handleRefresh = () => {
  loadRecords()
}

onMounted(() => {
  loadRecords()
  loadMerchants()
  window.addEventListener('app-refresh', handleRefresh)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', handleRefresh)
})
</script>
