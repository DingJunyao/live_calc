<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">
      <div class="d-flex align-center ga-2">
        <span class="text-truncate">{{ product?.name || '商品详情' }}</span>
        <v-chip size="x-small" variant="tonal" color="primary">商品</v-chip>
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

            <v-list-item v-if="product.ingredient_name" @click="goToIngredient" class="cursor-pointer">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-leaf</v-icon>
              </template>
              <v-list-item-title>关联原料</v-list-item-title>
              <v-list-item-subtitle class="d-flex align-center">
                <span class="text-primary text-decoration-underline">{{ product.ingredient_name }}</span>
                <v-icon size="small" color="primary" class="ml-1">mdi-arrow-right</v-icon>
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
            @click="openAddPriceDialog"
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
                <v-icon color="tertiary">mdi-receipt-text</v-icon>
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
            @click="openAddPriceDialog"
          >
            添加价格记录
          </v-btn>
        </v-card-text>

        <!-- 分页器 -->
        <div v-if="priceTotal > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
          <v-pagination
            v-model="pricePage"
            :length="priceTotalPages"
            :total-visible="3"
            rounded="circle"
            density="comfortable"
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
          <v-spacer />
          <v-btn
            v-if="otherNutrientsCount > 0"
            size="small"
            variant="text"
            color="primary"
            class="text-caption"
            @click="showAllNutrients = !showAllNutrients"
          >
            {{ showAllNutrients ? '收起' : `展开 +${otherNutrientsCount} 项` }}
            <v-icon :icon="showAllNutrients ? 'mdi-chevron-up' : 'mdi-chevron-down'" end />
          </v-btn>
        </v-card-title>
        <v-divider />

        <v-card-text class="pa-0">
          <div class="nutrition-header d-flex py-2 border-bottom">
            <div class="text-caption text-medium-emphasis ps-4 flex-grow-1">营养素</div>
            <div class="text-caption text-medium-emphasis text-end pe-4" style="min-width: 80px">数量</div>
            <div class="text-caption text-medium-emphasis text-end pe-4" style="min-width: 60px">NRV%</div>
          </div>
          <div
            v-for="item in displayNutritionItems"
            :key="item.key"
            class="nutrition-row d-flex py-2"
            :class="{ 'border-bottom': item.key !== displayNutritionItems[displayNutritionItems.length - 1].key }"
          >
            <div class="text-body-2 ps-4 flex-grow-1">{{ item.label }}</div>
            <div class="text-body-2 text-end pe-4" style="min-width: 80px">
              {{ formatNutritionValue(getNutritionValue(item), getNutritionUnit(item) || item.unit) }}
            </div>
            <div class="text-body-2 text-end pe-4" style="min-width: 60px">
              {{ getNutritionNRV(item) }}%
            </div>
          </div>

          <div class="mt-4 text-caption text-medium-emphasis ps-4">
            NRV = 营养素参考值百分比
          </div>
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
              class="mb-4"
            />

            <!-- 营养成分折叠面板 -->
            <v-expansion-panels class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <div class="d-flex align-center ga-2">
                    <v-icon>mdi-food</v-icon>
                    <span>营养成分（可选）</span>
                    <v-chip v-if="hasCustomNutrition" size="x-small" color="primary">已设置</v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                    如果填写营养成分，将优先使用此处设置的数据；否则将使用所属原料的营养成分
                  </v-alert>

                  <v-row>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.energy_kcal"
                        label="能量 (kcal)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.protein"
                        label="蛋白质 (g)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.fat"
                        label="脂肪 (g)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.carbohydrates"
                        label="碳水化合物 (g)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.dietary_fiber"
                        label="膳食纤维 (g)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.calcium"
                        label="钙 (mg)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.iron"
                        label="铁 (mg)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.sodium"
                        label="钠 (mg)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                    <v-col cols="6">
                      <v-text-field
                        v-model.number="editForm.nutrition.potassium"
                        label="钾 (mg)"
                        type="number"
                        variant="outlined"
                        hide-details
                        class="mb-2"
                      />
                    </v-col>
                  </v-row>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
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
                <v-select
                  v-model="priceForm.unit"
                  :items="unitOptions"
                  label="单位"
                  variant="outlined"
                  required
                  :hint="currentIngredientDefaultUnit ? `原料默认单位: ${currentIngredientDefaultUnit}` : ''"
                  :persistent-hint="!!currentIngredientDefaultUnit"
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
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { NUTRITION_LABEL_MAP } from '@/utils/nutritionLabels'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

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

interface Ingredient {
  id: number
  name: string
  aliases?: string[]
  default_unit?: string
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

// 原料列表
const ingredients = ref<Ingredient[]>([])
const loadingIngredients = ref(false)
const ingredientSearch = ref('')
const selectedIngredient = ref<Ingredient | null>(null)

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
  ingredient_id: null as number | null,
  tags: [] as string[],
  // 营养成分
  nutrition: {
    energy_kcal: null as number | null,
    protein: null as number | null,
    fat: null as number | null,
    carbohydrates: null as number | null,
    dietary_fiber: null as number | null,
    calcium: null as number | null,
    iron: null as number | null,
    sodium: null as number | null,
    potassium: null as number | null
  }
})

// 营养成分编辑状态
const showNutritionEditor = ref(false)
const hasCustomNutrition = ref(false)

const priceForm = ref({
  price: 0,
  quantity: 1,
  unit: 'g',
  merchant_id: null as number | null
})

// 打开添加价格记录对话框时，自动填充默认单位
const openAddPriceDialog = () => {
  // 如果原料有默认单位，使用默认单位；否则使用 'g'
  priceForm.value = {
    price: 0,
    quantity: 1,
    unit: currentIngredientDefaultUnit.value || 'g',
    merchant_id: null
  }
  showAddPriceDialog.value = true
}

// 提示消息
const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// 营养素配置（默认显示的营养素）
const coreNutritionItems = [
  { key: '能量', label: '能量', unit: 'kcal' },
  { key: '蛋白质', label: '蛋白质', unit: 'g' },
  { key: '脂肪', label: '脂肪', unit: 'g' },
  { key: '碳水化合物', label: '碳水化合物', unit: 'g' },
  { key: '钠', label: '钠', unit: 'mg' }
]

// 营养素排序顺序（展开时这些营养素排在前面）
const nutrientSortOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '钠',
  '膳食纤维', '钙', '铁', '钾',
  '维生素A', '维生素B1', '维生素B2', '维生素B12', '维生素C',
  '维生素D', '维生素E', '维生素K'
]

// 展开状态
const showAllNutrients = ref(false)

// 营养素排序辅助函数
const sortNutrients = (items: any[]) => {
  return items.sort((a, b) => {
    const indexA = nutrientSortOrder.indexOf(a.key)
    const indexB = nutrientSortOrder.indexOf(b.key)

    // 如果都在排序列表中，按排序顺序
    if (indexA !== -1 && indexB !== -1) {
      return indexA - indexB
    }
    // 如果只有A在排序列表中，A排在前面
    if (indexA !== -1) {
      return -1
    }
    // 如果只有B在排序列表中，B排在前面
    if (indexB !== -1) {
      return 1
    }
    // 都不在排序列表中，按原顺序
    return 0
  })
}

// 根据展开状态返回要显示的营养素列表
const displayNutritionItems = computed(() => {
  if (!nutritionData.value?.nutrition) return []

  const coreNutrients = nutritionData.value.nutrition.core_nutrients || {}
  const allNutrients = nutritionData.value.nutrition.all_nutrients || {}

  // 常用营养素（从 core_nutrients 获取，因为键名是中文）
  const coreItems = coreNutritionItems
    .filter(item => coreNutrients[item.key])
    .map(item => ({
      key: item.key,
      label: item.label,
      unit: (coreNutrients[item.key] as any).unit || item.unit,
      isCore: true
    }))

  if (!showAllNutrients.value) {
    return coreItems
  }

  // 获取核心营养素的键集合（用于过滤）
  const coreKeys = new Set(coreNutritionItems.map(ci => ci.key))

  // 其他营养素（从 all_nutrients 获取，键已经是中文了）
  const availableKeys = Object.keys(allNutrients).filter(key => {
    const data = allNutrients[key]
    return data && typeof data === 'object' && 'value' in data
  })

  const otherItems = availableKeys
    .filter(key => {
      // 后端已经将键转为中文，直接检查是否是核心营养素
      return !coreKeys.has(key)
    })
    .map(key => {
      return {
        key: key,
        label: NUTRITION_LABEL_MAP[key] || key,
        unit: (allNutrients[key] as any).unit || '',
        isCore: false
      }
    })

  // 排序
  const sortedItems = sortNutrients([...coreItems, ...otherItems])

  return sortedItems
})

// 其他营养素数量（用于按钮文案）
const otherNutrientsCount = computed(() => {
  if (!nutritionData.value?.nutrition?.all_nutrients) return 0

  const allNutrients = nutritionData.value.nutrition.all_nutrients

  // 获取核心营养素的键集合
  const coreKeys = new Set(coreNutritionItems.map(ci => ci.key))

  const availableKeys = Object.keys(allNutrients).filter(key => {
    const data = allNutrients[key]
    return data && typeof data === 'object' && 'value' in data
  })

  return availableKeys.filter(key => {
    // 后端已经将键转为中文，直接检查是否是核心营养素
    return !coreKeys.has(key)
  }).length
})

// 从后端返回的嵌套结构中提取营养值
const getNutritionValue = (item: any) => {
  if (!nutritionData.value?.nutrition) return null

  // 如果是核心营养素，从 core_nutrients 获取（中文键）
  if (item.isCore) {
    const nutrient = nutritionData.value.nutrition.core_nutrients?.[item.key]
    return nutrient?.value
  }

  // 否则从 all_nutrients 获取（使用中文键，后端已转换）
  const nutrient = nutritionData.value.nutrition.all_nutrients?.[item.key]
  return nutrient?.value
}

const getNutritionUnit = (item: any) => {
  if (!nutritionData.value?.nutrition) return null

  // 如果是核心营养素，从 core_nutrients 获取（中文键）
  if (item.isCore) {
    const nutrient = nutritionData.value.nutrition.core_nutrients?.[item.key]
    return nutrient?.unit
  }

  // 否则从 all_nutrients 获取（使用中文键，后端已转换）
  const nutrient = nutritionData.value.nutrition.all_nutrients?.[item.key]
  return nutrient?.unit
}

const getNutritionNRV = (item: any) => {
  if (!nutritionData.value?.nutrition) return '-'

  let nutrient: any

  // 如果是核心营养素，从 core_nutrients 获取（中文键）
  if (item.isCore) {
    nutrient = nutritionData.value.nutrition.core_nutrients?.[item.key]
  } else {
    // 否则从 all_nutrients 获取（使用中文键，后端已转换）
    nutrient = nutritionData.value.nutrition.all_nutrients?.[item.key]
  }

  if (!nutrient) return '-'

  // 如果 standard 是"无标准"或类似的，表示没有推荐摄入量，显示 "-"
  if (nutrient.standard === '无标准' || nutrient.standard === '无标准值') {
    return '-'
  }

  // 如果 nrp_pct 是 undefined 或 null，显示 "-"
  if (nutrient.nrp_pct === undefined || nutrient.nrp_pct === null) {
    return '-'
  }

  // 显示实际百分比
  return nutrient.nrp_pct.toFixed(1)
}

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

// 获取当前商品关联的原料的默认单位
const currentIngredientDefaultUnit = computed(() => {
  // 从 nutritionData 或 product 中获取原料的默认单位
  if (nutritionData.value?.ingredient?.default_unit) {
    return nutritionData.value.ingredient.default_unit
  }
  return null
})

// 单位选项
const unitOptions = [
  'g', 'kg', '斤', '两', 'ml', 'L', '个', '包', '袋', '盒', '瓶', '罐'
]

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
  editForm.value.ingredient_id = newIngredient?.id || null
}, { immediate: true })

// 打开编辑对话框
const openEditDialog = () => {
  if (!product.value) return
  editForm.value = {
    name: product.value.name || '',
    brand: product.value.brand || '',
    barcode: product.value.barcode || '',
    ingredient_id: product.value.ingredient_id || null,
    tags: product.value.tags || [],
    nutrition: {
      energy_kcal: null,
      protein: null,
      fat: null,
      carbohydrates: null,
      dietary_fiber: null,
      calcium: null,
      iron: null,
      sodium: null,
      potassium: null
    }
  }

  // 加载当前关联的原料
  if (product.value.ingredient_id) {
    // 先加载原料列表，然后设置选中的原料
    loadIngredients().then(() => {
      const currentIngredient = ingredients.value.find(i => i.id === product.value.ingredient_id)
      if (currentIngredient) {
        selectedIngredient.value = currentIngredient
        ingredientSearch.value = currentIngredient.name
      }
    })
  } else {
    loadIngredients()
  }

  // 加载商品的自定义营养数据
  loadCustomNutrition()

  showEditDialog.value = true
}

// 加载商品的自定义营养数据
const loadCustomNutrition = async () => {
  try {
    const response = await api.get(`/products/entity/${productId.value}/nutrition`)
    const customData = response.custom_nutrition_data

    hasCustomNutrition.value = !!(customData && Object.keys(customData).length > 0)

    // 如果有自定义营养数据，填充到表单
    if (customData?.all_nutrients) {
      const nutrients = customData.all_nutrients
      editForm.value.nutrition = {
        energy_kcal: nutrients.energy_kcal?.value || null,
        protein: nutrients.protein?.value || null,
        fat: nutrients.fat?.value || null,
        carbohydrates: nutrients.carbohydrates?.value || null,
        dietary_fiber: nutrients.dietary_fiber?.value || null,
        calcium: nutrients.calcium?.value || null,
        iron: nutrients.iron?.value || null,
        sodium: nutrients.sodium?.value || null,
        potassium: nutrients.potassium?.value || null
      }
    }
  } catch (e) {
    // 如果获取失败，保持空值
    console.warn('加载商品营养数据失败:', e)
  }
}

// 保存编辑
const saveEdit = async () => {
  if (!editForm.value.name.trim()) return
  if (!editForm.value.ingredient_id) {
    showMessage('请选择关联的原料', 'error')
    return
  }

  saving.value = true
  try {
    // 先保存基本信息
    const response = await api.put(`/products/entity/${productId.value}`, {
      name: editForm.value.name,
      brand: editForm.value.brand,
      barcode: editForm.value.barcode,
      ingredient_id: editForm.value.ingredient_id,
      tags: editForm.value.tags
    })
    product.value = response

    // 检查是否有营养成分需要保存
    const hasNutritionData = Object.values(editForm.value.nutrition).some(v => v !== null && v !== undefined && v > 0)

    if (hasNutritionData) {
      // 构建营养数据结构
      const nutrients: Record<string, any> = {}

      if (editForm.value.nutrition.energy_kcal) {
        nutrients.energy_kcal = { value: editForm.value.nutrition.energy_kcal, unit: 'kcal' }
      }
      if (editForm.value.nutrition.protein) {
        nutrients.protein = { value: editForm.value.nutrition.protein, unit: 'g' }
      }
      if (editForm.value.nutrition.fat) {
        nutrients.fat = { value: editForm.value.nutrition.fat, unit: 'g' }
      }
      if (editForm.value.nutrition.carbohydrates) {
        nutrients.carbohydrates = { value: editForm.value.nutrition.carbohydrates, unit: 'g' }
      }
      if (editForm.value.nutrition.dietary_fiber) {
        nutrients.dietary_fiber = { value: editForm.value.nutrition.dietary_fiber, unit: 'g' }
      }
      if (editForm.value.nutrition.calcium) {
        nutrients.calcium = { value: editForm.value.nutrition.calcium, unit: 'mg' }
      }
      if (editForm.value.nutrition.iron) {
        nutrients.iron = { value: editForm.value.nutrition.iron, unit: 'mg' }
      }
      if (editForm.value.nutrition.sodium) {
        nutrients.sodium = { value: editForm.value.nutrition.sodium, unit: 'mg' }
      }
      if (editForm.value.nutrition.potassium) {
        nutrients.potassium = { value: editForm.value.nutrition.potassium, unit: 'mg' }
      }

      // 构建完整的营养数据结构
      const nutritionData = {
        all_nutrients: nutrients
      }

      // 保存自定义营养数据
      await api.put(`/products/entity/${productId.value}/nutrition`, nutritionData)
    } else {
      // 如果没有营养数据，清除已有的自定义营养数据
      await api.put(`/products/entity/${productId.value}/nutrition`, {})
    }

    // 重新加载营养数据显示
    await loadNutritionData()

    showEditDialog.value = false
    selectedIngredient.value = null
    ingredientSearch.value = ''
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
  loadIngredients()
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.font-family-monospace {
  font-family: monospace;
}

/* 营养成分表格样式 */
.nutrition-header {
  background: rgb(var(--v-theme-surface-variant));
  font-weight: 500;
}

.nutrition-row:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}
</style>
