<template>
  <v-app-bar elevation="0" color="background" fixed>
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

  <v-container fluid class="pa-0 pt-16">
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
import { api } from '@/api/client'
import CostProportionChart from '@/components/recipes/CostProportionChart.vue'
import CostTrendAnalysis from '@/components/recipes/CostTrendAnalysis.vue'
import NutritionSourceGrid from '@/components/recipes/NutritionSourceGrid.vue'
import MerchantCostCards from '@/components/recipes/MerchantCostCards.vue'
import MerchantPriceMatrix from '@/components/recipes/MerchantPriceMatrix.vue'

const route = useRoute()
const router = useRouter()
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
  loadingCostHistory.value = false
}

async function loadMerchantCosts() {
  loadingMerchantCosts.value = true
  try {
    const res = await api.get(`/recipes/${recipeId}/merchant-costs`)
    merchantCosts.value = res
  } catch { /* 忽略 */ }
  loadingMerchantCosts.value = false
}

async function loadMerchantPrices() {
  const ingredients = recipe.value?.ingredients
  if (!ingredients?.length) return

  loadingMerchantPrices.value = true
  try {
    const results = await Promise.allSettled(
      ingredients
        .filter((i: any) => i.ingredient_id)
        .map((i: any) =>
          api.get(`/nutrition/ingredients/${i.ingredient_id}/latest-price-by-merchant`)
            .then((res: any) => ({
              recipeIngredientId: i.id,
              ingredientId: i.ingredient_id,
              ingredientName: i.name,
              prices: res?.prices || [],
              unit: res?.unit || null,
            }))
        )
    )
    merchantPriceData.value = results
      .filter((r): r is PromiseFulfilledResult<any> => r.status === 'fulfilled')
      .map(r => r.value)
  } catch { /* 忽略 */ }
  loadingMerchantPrices.value = false
}

function onCostTrendFilterChange(filter: string) {
  loadCostHistory(filter)
}

onMounted(loadAllData)
</script>
