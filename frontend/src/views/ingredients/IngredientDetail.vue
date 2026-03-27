<template>
  <v-container fluid class="pa-0">
    <!-- 顶部导航 -->
    <v-app-bar elevation="0" color="background">
      <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
      <v-app-bar-title class="text-h6 text-truncate">
        {{ ingredient?.name || '原料详情' }}
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

    <template v-else-if="ingredient">
      <!-- 基本信息卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-information-outline</v-icon>
          基本信息
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-list density="compact">
            <v-list-item v-if="ingredient.default_unit_name">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-scale</v-icon>
              </template>
              <v-list-item-title>默认单位</v-list-item-title>
              <v-list-item-subtitle>{{ ingredient.default_unit_name }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="ingredient.aliases?.length">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-tag-outline</v-icon>
              </template>
              <v-list-item-title>别名</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  v-for="alias in ingredient.aliases"
                  :key="alias"
                  size="x-small"
                  class="mr-1"
                >
                  {{ alias }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-calendar</v-icon>
              </template>
              <v-list-item-title>创建时间</v-list-item-title>
              <v-list-item-subtitle>{{ formatDateTime(ingredient.created_at) }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>

      <!-- 最新价格卡片 -->
      <v-card elevation="0" class="ma-4" v-if="latestPrice">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="tertiary">mdi-currency-cny</v-icon>
          最新价格
          <span class="text-caption text-medium-emphasis ml-2">（每{{ ingredient.default_unit_name || 'g' }}）</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="text-center py-6">
          <div class="text-h3 font-weight-bold text-tertiary">
            ¥{{ formatPrice(latestPrice) }}
          </div>
        </v-card-text>
      </v-card>

      <!-- 价格趋势图表 -->
      <PriceTrendChart
        v-if="ingredient"
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

      <!-- 关联商品卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-package-variant</v-icon>
          关联商品
          <v-chip size="small" class="ml-2" v-if="products.length > 0">
            {{ products.length }}
          </v-chip>
        </v-card-title>
        <v-divider />

        <v-list v-if="products.length > 0" lines="one">
          <v-list-item
            v-for="product in products"
            :key="product.id"
            @click="goToProduct(product.id)"
          >
            <template #prepend>
              <v-avatar color="primary" size="36">
                <span class="text-white text-caption">{{ product.name?.charAt(0) }}</span>
              </v-avatar>
            </template>
            <v-list-item-title>{{ product.name }}</v-list-item-title>
            <v-list-item-subtitle v-if="product.brand">{{ product.brand }}</v-list-item-subtitle>
            <template #append>
              <v-icon>mdi-chevron-right</v-icon>
            </template>
          </v-list-item>
        </v-list>

        <v-card-text v-else class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-package-variant-closed</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无关联商品</div>
        </v-card-text>
      </v-card>

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
              {{ record.product_name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              ¥{{ formatPrice(record.price) }} / {{ record.original_quantity }}{{ record.original_unit }}
              <template v-if="record.merchant_name"> · {{ record.merchant_name }}</template>
            </v-list-item-subtitle>

            <template #append>
              <div class="text-caption text-medium-emphasis">
                {{ formatDate(record.recorded_at) }}
              </div>
            </template>
          </v-list-item>
        </v-list>

        <!-- 空状态 -->
        <v-card-text v-else class="text-center py-8">
          <v-icon size="64" color="medium-emphasis">mdi-receipt-text-outline</v-icon>
          <div class="text-body-1 text-medium-emphasis mt-4">暂无价格记录</div>
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

      <!-- 关联菜谱卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-chef-hat</v-icon>
          相关菜谱
          <v-chip size="small" class="ml-2" v-if="recipes.length > 0">
            {{ recipes.length }}
          </v-chip>
        </v-card-title>
        <v-divider />

        <v-list v-if="recipes.length > 0" lines="one">
          <v-list-item
            v-for="recipe in recipes"
            :key="recipe.id"
            @click="goToRecipe(recipe.id)"
          >
            <template #prepend>
              <v-avatar color="secondary" size="36">
                <v-icon color="white">mdi-food</v-icon>
              </v-avatar>
            </template>
            <v-list-item-title>{{ recipe.name }}</v-list-item-title>
            <v-list-item-subtitle v-if="recipe.category">{{ recipe.category }}</v-list-item-subtitle>
            <template #append>
              <v-icon>mdi-chevron-right</v-icon>
            </template>
          </v-list-item>
        </v-list>

        <v-card-text v-else class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-book-open-variant</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无相关菜谱</div>
        </v-card-text>
      </v-card>

      <!-- 操作按钮 -->
      <div class="pa-4">
        <v-btn
          color="warning"
          variant="tonal"
          block
          prepend-icon="mdi-merge"
          class="mb-2"
          @click="showMergeDialog = true"
        >
          合并到其他原料
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          block
          prepend-icon="mdi-delete"
          @click="confirmDelete"
        >
          删除原料
        </v-btn>
      </div>
    </template>

    <!-- 编辑对话框 -->
    <v-dialog v-model="showEditDialog" max-width="500">
      <v-card>
        <v-card-title>编辑原料</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEdit">
            <v-text-field
              v-model="editForm.name"
              label="原料名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-autocomplete
              v-model="editForm.default_unit_id"
              :items="units"
              item-title="name"
              item-value="id"
              label="默认单位"
              variant="outlined"
              clearable
              class="mb-4"
            />
            <v-combobox
              v-model="editForm.aliases"
              label="别名"
              variant="outlined"
              multiple
              chips
              closable-chips
              hint="按回车添加别名"
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
          <v-alert type="info" class="mb-4">
            请先选择一个关联商品，然后为其添加价格记录
          </v-alert>
          <v-autocomplete
            v-model="priceForm.product_id"
            :items="products"
            item-title="name"
            item-value="id"
            label="选择商品"
            variant="outlined"
            required
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddPriceDialog = false">取消</v-btn>
          <v-btn
            color="primary"
            :disabled="!priceForm.product_id"
            @click="goToAddPrice"
          >
            前往添加
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 合并对话框 -->
    <v-dialog v-model="showMergeDialog" max-width="500">
      <v-card>
        <v-card-title>合并原料</v-card-title>
        <v-card-text>
          <v-alert type="warning" class="mb-4">
            合并后，当前原料的菜谱引用、商品关联将迁移到目标原料，此操作不可恢复！
          </v-alert>
          <v-autocomplete
            v-model="mergeTargetId"
            :items="mergeTargets"
            item-title="name"
            item-value="id"
            label="选择目标原料"
            variant="outlined"
            :loading="loadingMergeTargets"
            @update:search="searchMergeTargets"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showMergeDialog = false">取消</v-btn>
          <v-btn
            color="warning"
            :loading="merging"
            :disabled="!mergeTargetId"
            @click="mergeIngredient"
          >
            确认合并
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 确认删除对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">确认删除</v-card-title>
        <v-card-text>
          确定要删除原料「{{ ingredient?.name }}」吗？此操作不可恢复。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteIngredient">删除</v-btn>
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

interface Ingredient {
  id: number
  name: string
  aliases?: string[]
  default_unit_id?: number
  default_unit_name?: string
  created_at: string
  updated_at?: string
}

interface Product {
  id: number
  name: string
  brand?: string
  ingredient_id?: number
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

interface Recipe {
  id: number
  name: string
  category?: string
}

interface Unit {
  id: number
  name: string
  abbreviation?: string
}

const route = useRoute()
const router = useRouter()

const ingredientId = computed(() => Number(route.params.id))

const ingredient = ref<Ingredient | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// 最新价格
const latestPrice = ref<number | null>(null)

// 关联商品
const products = ref<Product[]>([])

// 价格记录相关
const priceRecords = ref<PriceRecord[]>([])
const loadingPrices = ref(false)
const pricePage = ref(1)
const pricePageSize = ref(10)
const priceTotal = ref(0)
const priceTotalPages = computed(() => Math.ceil(priceTotal.value / pricePageSize.value))

// 营养数据
const nutritionData = ref<any>(null)

// 关联菜谱
const recipes = ref<Recipe[]>([])

// 单位列表
const units = ref<Unit[]>([])

// 对话框状态
const showEditDialog = ref(false)
const showAddPriceDialog = ref(false)
const showMergeDialog = ref(false)
const showDeleteDialog = ref(false)
const saving = ref(false)
const merging = ref(false)
const deleting = ref(false)

// 表单数据
const editForm = ref({
  name: '',
  default_unit_id: null as number | null,
  aliases: [] as string[]
})

const priceForm = ref({
  product_id: null as number | null
})

// 合并相关
const mergeTargetId = ref<number | null>(null)
const mergeTargets = ref<Ingredient[]>([])
const loadingMergeTargets = ref(false)

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

// 聚合价格数据用于图表（按日期分组）
const chartData = computed(() => {
  if (!priceRecords.value || priceRecords.value.length === 0) return []

  const dailyMap = new Map<string, number[]>()

  for (const record of priceRecords.value) {
    if (!record.recorded_at) continue
    const date = new Date(record.recorded_at)
    if (isNaN(date.getTime())) continue
    const dateKey = date.toISOString().split('T')[0]

    // 计算单价
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
  return ingredient.value?.default_unit_name || ''
})

// 加载数据
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    // 加载原料详情
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}`)
    ingredient.value = response

    // 并行加载其他数据
    await Promise.all([
      loadLatestPrice(),
      loadProducts(),
      loadPriceRecords(),
      loadNutritionData(),
      loadRecipes()
    ])
  } catch (e: any) {
    console.error('加载原料失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 加载最新价格
const loadLatestPrice = async () => {
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/latest-price`)
    latestPrice.value = response.average_price
  } catch (e) {
    latestPrice.value = null
  }
}

// 加载关联商品
const loadProducts = async () => {
  try {
    const response = await api.get('/products/entity', {
      params: {
        ingredient_id: ingredientId.value,
        limit: 50
      }
    })
    products.value = response.items || []
  } catch (e) {
    products.value = []
  }
}

// 加载价格记录
const loadPriceRecords = async () => {
  loadingPrices.value = true
  try {
    const skip = (pricePage.value - 1) * pricePageSize.value
    const response = await api.get('/products', {
      params: {
        ingredient_id: ingredientId.value,
        skip,
        limit: pricePageSize.value,
        target_unit: ingredient.value?.default_unit_name
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
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/nutrition`)
    nutritionData.value = response
  } catch (e) {
    nutritionData.value = null
  }
}

// 加载关联菜谱
const loadRecipes = async () => {
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/recipes`, {
      params: { limit: 50 }
    })
    recipes.value = response.items || []
  } catch (e) {
    recipes.value = []
  }
}

// 加载单位列表
const loadUnits = async () => {
  try {
    const response = await api.get('/units/', { params: { limit: 100 } })
    units.value = response.items || response || []
  } catch (e) {
    units.value = []
  }
}

// 打开编辑对话框
const openEditDialog = () => {
  if (!ingredient.value) return
  editForm.value = {
    name: ingredient.value.name || '',
    default_unit_id: ingredient.value.default_unit_id || null,
    aliases: ingredient.value.aliases || []
  }
  showEditDialog.value = true
}

// 保存编辑
const saveEdit = async () => {
  if (!editForm.value.name.trim()) return

  saving.value = true
  try {
    const response = await api.put(`/nutrition/ingredients/${ingredientId.value}`, editForm.value)
    ingredient.value = response
    showEditDialog.value = false
    showMessage('保存成功', 'success')
  } catch (e: any) {
    showMessage(e.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 前往添加价格
const goToAddPrice = () => {
  if (priceForm.value.product_id) {
    router.push(`/data/products/${priceForm.value.product_id}`)
  }
}

// 搜索合并目标
const searchMergeTargets = async (search: string) => {
  if (!search || search.length < 1) {
    mergeTargets.value = []
    return
  }

  loadingMergeTargets.value = true
  try {
    const response = await api.get('/ingredients', {
      params: { q: search, limit: 20 }
    })
    // 过滤掉当前原料
    mergeTargets.value = (response.items || []).filter(
      (item: Ingredient) => item.id !== ingredientId.value
    )
  } catch (e) {
    mergeTargets.value = []
  } finally {
    loadingMergeTargets.value = false
  }
}

// 合并原料
const mergeIngredient = async () => {
  if (!mergeTargetId.value) return

  merging.value = true
  try {
    const response = await api.post('/ingredients/merge', {
      source_id: ingredientId.value,
      target_id: mergeTargetId.value
    })
    showMessage(response.message || '合并成功', 'success')
    // 跳转到目标原料
    router.push(`/data/ingredients/${mergeTargetId.value}`)
  } catch (e: any) {
    showMessage(e.message || '合并失败', 'error')
  } finally {
    merging.value = false
  }
}

// 确认删除
const confirmDelete = () => {
  showDeleteDialog.value = true
}

// 删除原料
const deleteIngredient = async () => {
  deleting.value = true
  try {
    await api.delete(`/nutrition/ingredients/${ingredientId.value}`)
    showMessage('删除成功', 'success')
    router.push('/data/ingredients')
  } catch (e: any) {
    showMessage(e.message || '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

// 跳转到商品详情
const goToProduct = (id: number) => {
  router.push(`/data/products/${id}`)
}

// 跳转到菜谱详情
const goToRecipe = (id: number) => {
  router.push(`/recipes/${id}`)
}

// 返回
const goBack = () => {
  router.push('/data/ingredients')
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
  loadUnits()
})
</script>

<style scoped>
.nutrition-item {
  background: rgb(var(--v-theme-surface-variant));
  text-align: center;
}
</style>
