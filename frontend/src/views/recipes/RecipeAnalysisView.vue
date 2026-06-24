<template>
  <v-app-bar elevation="0" color="background" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">
      <div class="d-flex align-center ga-2">
        <span class="text-truncate">{{ recipe?.name || '菜谱分析' }}</span>
        <v-chip size="x-small" variant="tonal" color="primary">分析</v-chip>
      </div>
    </v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadAllData" />
    </template>
  </v-app-bar>

  <v-container fluid class="pa-0">
    <div v-if="!recipe && loading" class="text-center py-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <v-alert v-else-if="error" type="error" class="ma-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="retry">重试</v-btn>
      </template>
    </v-alert>

    <template v-else-if="recipe">
      <!-- 模块 ① + ② -->
      <v-row no-gutters>
        <v-col cols="12" md="6">
          <CostProportionChart
            :cost-breakdown="costData?.cost_breakdown"
            :total-cost="costData?.total_cost"
            :loading="loadingCostData"
          />
        </v-col>
        <v-col cols="12" md="6">
          <CostTrendAnalysis
            :recipe-id="recipe.id"
            :cost-history="costHistoryRecords"
            :ingredients="recipe.ingredients"
            :cost-breakdown="costData?.cost_breakdown"
            :loading="loadingCostHistory"
            @filter-change="onCostTrendFilterChange"
          />
        </v-col>
      </v-row>

      <!-- 模块 ③ -->
      <NutritionSourceGrid
        :nutrition-data="nutritionData"
        :loading="loadingNutritionData"
      />

      <!-- 模块 ⑤ + ④ -->
      <div class="ma-4">
        <MerchantCostCards
          :merchant-costs="merchantCosts"
          :loading="loadingMerchantCosts"
        />
        <MerchantPriceMatrix
          :recipe-ingredients="recipe.ingredients"
          :merchant-prices="merchantPriceData"
          :loading="loadingMerchantPrices"
        />
      </div>
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { api } from '@/api/client'
import CostProportionChart from '@/components/recipes/CostProportionChart.vue'
import CostTrendAnalysis from '@/components/recipes/CostTrendAnalysis.vue'
import NutritionSourceGrid from '@/components/recipes/NutritionSourceGrid.vue'
import MerchantCostCards from '@/components/recipes/MerchantCostCards.vue'
import MerchantPriceMatrix from '@/components/recipes/MerchantPriceMatrix.vue'

const route = useRoute()
const router = useRouter()
const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const recipeId = Number(route.params.id)

const recipe = ref<any>(null)
const costData = ref<any>(null)
const nutritionData = ref<any>(null)
const costHistoryRecords = ref<any[]>([])
const merchantCosts = ref<any>(null)
const merchantPriceData = ref<any[]>([])

const loading = ref(true)
const error = ref<string | null>(null)
const loadingCostData = ref(false)
const loadingNutritionData = ref(false)
const loadingCostHistory = ref(false)
const loadingMerchantCosts = ref(false)
const loadingMerchantPrices = ref(false)

function goBack() {
  router.push(`/recipes/${recipeId}`)
}

async function retry() {
  costData.value = null
  nutritionData.value = null
  costHistoryRecords.value = []
  merchantCosts.value = null
  merchantPriceData.value = []
  await loadAllData()
}

async function loadAllData() {
  loading.value = true
  error.value = null

  try {
    const [recipeRes, costRes, nutritionRes] = await Promise.all([
      api.get(`/recipes/${recipeId}`),
      api.get(`/recipes/${recipeId}/cost`).catch(() => null),
      api.get(`/recipes/${recipeId}/nutrition`).catch(() => null),
    ])

    recipe.value = recipeRes
    costData.value = costRes
    nutritionData.value = nutritionRes
    loading.value = false

    // 并行加载成本和商家数据
    loadCostHistory('quarter')
    loadMerchantCosts()
    loadMerchantPrices()

  } catch (e: any) {
    error.value = e?.userMessage || '加载菜谱失败'
    loading.value = false
  }
}

async function loadCostHistory(filter: string) {
  loadingCostHistory.value = true
  try {
    const daysMap: Record<string, number> = { week: 7, month: 30, quarter: 90, year: 365, all: 3650 }
    const days = daysMap[filter] || 90
    const res = await api.get(`/recipes/${recipeId}/cost-history-range`, {
      params: { days, offset_days: 0 },
      timeout: 30000,
    })
    costHistoryRecords.value = Array.isArray(res) ? res : []
  } catch { /* 忽略 */ }
  finally {
    loadingCostHistory.value = false
  }
}

async function loadMerchantCosts() {
  loadingMerchantCosts.value = true
  try {
    const res = await api.get(`/recipes/${recipeId}/merchant-costs`, { timeout: 30000 })
    merchantCosts.value = res
  } catch { /* 忽略 */ }
  finally {
    loadingMerchantCosts.value = false
  }
}

// 模糊量 → 默认克数（与后端 VAGUE_QUANTITY_GRAM_MAP 对齐）
const VAGUE_QUANTITY_GRAM: Record<string, number> = { '适量': 100, '少许': 5 }

// 从 quantity / quantity_range / original_quantity 中提取有效数量
function getEffectiveQuantity(ingredient: any): { qty: number | null; qtyDisplay: string; qtyUnit: string } {
  let qty: number | null = null
  let qtyDisplay = ''
  let qtyUnit = ingredient.unit || ''

  if (ingredient.quantity) {
    qty = parseFloat(ingredient.quantity)
    qtyDisplay = `${ingredient.quantity}${qtyUnit}`
  } else if (ingredient.quantity_range) {
    let qr = ingredient.quantity_range
    if (typeof qr === 'string') {
      try { qr = JSON.parse(qr) } catch { /* ignore */ }
    }
    if (qr && typeof qr === 'object') {
      const min = parseFloat(qr.min) || 0
      const max = parseFloat(qr.max) || 0
      qty = (min + max) / 2
      qtyDisplay = `${qr.min}-${qr.max}${qtyUnit}`
    }
  }

  // 模糊量回退（original_quantity 中的「适量/少许」→ 克）
  if (qty == null && ingredient.original_quantity) {
    let orig = ingredient.original_quantity
    if (typeof orig !== 'string') {
      try { orig = JSON.stringify(orig) } catch { orig = '' }
    }
    for (const [keyword, gramQty] of Object.entries(VAGUE_QUANTITY_GRAM)) {
      if (orig.includes(keyword)) {
        qty = gramQty
        qtyDisplay = `${keyword}(${gramQty}g)`
        qtyUnit = 'g'
        break
      }
    }
  }

  return { qty, qtyDisplay, qtyUnit }
}

function fetchMerchantPrice(ingredient: any): Promise<any> {
  const { qty, qtyDisplay, qtyUnit } = getEffectiveQuantity(ingredient)
  const params: Record<string, any> = {}
  if (qty != null && !isNaN(qty) && qty > 0) {
    params.quantity = qty
    params.quantity_unit = qtyUnit
  }
  return api.get(`/nutrition/ingredients/${ingredient.ingredient_id}/latest-price-by-merchant`, {
    params,
    timeout: 10000,
  })
    .then((res: any) => ({
      recipeIngredientId: ingredient.id,
      ingredientId: ingredient.ingredient_id,
      ingredientName: ingredient.name,
      prices: res?.prices || [],
      unit: res?.unit || null,
      qtyDisplay,
      fallbackChain: res?.fallback_chain || null,
    }))
    .catch(() => null)
}

// 并发控制：同时最多 3 个比价请求，全局超时 50 秒
async function loadMerchantPrices() {
  const ingredients = recipe.value?.ingredients
  if (!ingredients?.length) {
    loadingMerchantPrices.value = false
    return
  }

  loadingMerchantPrices.value = true
  const startTime = Date.now()
  const GLOBAL_TIMEOUT = 35000
  const CONCURRENCY = 3

  try {
    const validIngredients = ingredients.filter((i: any) => i.ingredient_id)
    const results: any[] = []

    for (let i = 0; i < validIngredients.length; i += CONCURRENCY) {
      // 全局超时检查，超时后至少保留已有结果
      if (Date.now() - startTime > GLOBAL_TIMEOUT) {
        console.warn('[分析页] 商家比价请求超时，显示部分结果')
        break
      }

      const batch = validIngredients.slice(i, i + CONCURRENCY)
      const batchResults = await Promise.allSettled(batch.map(fetchMerchantPrice))
      results.push(...batchResults.map(r => r.status === 'fulfilled' ? r.value : null))
    }
    merchantPriceData.value = results.filter(Boolean)
  } catch {
    /* 忽略 */
  } finally {
    loadingMerchantPrices.value = false
  }
}

function onCostTrendFilterChange(filter: string) {
  loadCostHistory(filter)
}

onMounted(loadAllData)
</script>
