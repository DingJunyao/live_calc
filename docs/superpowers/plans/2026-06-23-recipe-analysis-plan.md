# 菜谱成本与营养分析面板 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增独立分析页面（`/recipes/:id/analysis`），展示菜谱的成本构成、营养贡献溯源和商家比价信息

**Architecture:** 后端最小改动（仅新增 `GET /recipes/{id}/merchant-costs` 端点），前端通过组合 5 个现有 API + 新增端点实现。新增 1 个路由视图 + 5 个展示组件，均为纯展示无副作用。

**Tech Stack:** Python FastAPI (backend), Vue 3 + TypeScript + ECharts (frontend)

---

### Task 0: Spec & Plan Review Pre-Flight

- [ ] **Verify spec coverage against plan**

  对比 spec 需求逐项确认：
  - ① 成本占比环形图 → Task 3
  - ② 堆叠面积图 + 食材选择器 → Task 4
  - ③ 多环形图营养网格 → Task 5
  - ④ 食材×商家价格矩阵表 → Task 6
  - ⑤ 商家成本卡片对比 → Task 6
  - 新后端端点 `merchant-costs` → Task 1
  - 路由 + 页面骨架 → Task 2
  - 详情页入口按钮 → Task 7

- [ ] **Verify type consistency across tasks**

  确认跨任务类型/方法名/属性名一致：
  - `RecipeMerchantCostResponse` / `MerchantCostItem`（Task 1 定义）→ Task 6 前端消费
  - `CostProportionChart` props（Task 3 定义）→ 与 `RecipeAnalysisView`（Task 2）中 `costData` 类型匹配
  - `CostTrendAnalysis` props（Task 4 定义）→ 与 `costHistoryRecords` 类型匹配
  - `ingredient_details` 格式（Task 5 消费）→ 后端已在 `RecipeNutritionResponse` 中返回
  - `latest-price-by-merchant` 响应格式（Task 6 消费）→ 后端已在 `nutrition.py` 中定义

---

### Task 1: New Backend Endpoint — `GET /recipes/{id}/merchant-costs`

**Files:**
- Modify: `backend/app/schemas/recipe.py` — 新增 `MerchantCostItem` 和 `RecipeMerchantCostResponse`
- Modify: `backend/app/api/recipes.py` — 新增 GET 端点 + 业务逻辑

- [ ] **Step 1: Add response schemas**

  在 `backend/app/schemas/recipe.py` 文件末尾，`RecipeCostRangeResponse` 之后添加：

```python
class MerchantCostItem(BaseModel):
    """按商家维度计算的菜谱成本项"""
    merchant_id: int
    merchant_name: str
    total_cost: float
    covered_count: int          # 该商家能覆盖的食材数
    total_ingredients: int      # 菜谱所需食材总数
    missing_ingredients: List[str] = []  # 缺失的食材名称列表
    is_recommended: bool = False


class RecipeMerchantCostResponse(BaseModel):
    """菜谱按商家成本估算响应"""
    currency: str = "CNY"
    merchants: List[MerchantCostItem]
```

  注意在文件顶部添加 `List` 的导入（如已导入 `from typing import Optional, List, Union` 则无需重复添加）。

- [ ] **Step 2: Add the new endpoint**

  在 `backend/app/api/recipes.py` 中，`get_recipe_nutrition` 之后（约第 680 行）添加新端点：

```python
@router.get("/{recipe_id}/merchant-costs", response_model=RecipeMerchantCostResponse)
async def get_recipe_merchant_costs(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱按商家购买的总成本估算"""
    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        recipe_ingredients = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()

        if not recipe_ingredients:
            return RecipeMerchantCostResponse(merchants=[])

        from app.models.product_entity import Product
        from app.models.product import ProductRecord
        from app.models.merchant import Merchant
        from app.services.unit_conversion_service import UnitConversionService
        from decimal import Decimal

        unit_service = UnitConversionService(db)
        total_ingredients = len(recipe_ingredients)

        # merchant_id → { merchant_name, ingredients: { ingredient_id → cost }, missing: set }
        merchant_data: dict = {}

        for ri in recipe_ingredients:
            ingredient = ri.ingredient
            if not ingredient or not ingredient.is_active:
                continue

            # 获取该食材的默认单位
            target_unit = ingredient.default_unit.abbreviation if ingredient.default_unit else None

            # 获取该食材下所有活跃商品的价格记录（按商家分组取最新）
            products = db.query(Product).filter(
                Product.ingredient_id == ingredient.id,
                Product.is_active == True
            ).all()

            product_ids = [p.id for p in products if p.id]
            if not product_ids:
                # 该食材没有一个商品 → 对所有商家都缺失
                continue

            # 查询所有有商家关联的价格记录
            records = db.query(ProductRecord).options(
                joinedload(ProductRecord.original_unit),
                joinedload(ProductRecord.merchant)
            ).join(
                Merchant, ProductRecord.merchant_id == Merchant.id
            ).filter(
                ProductRecord.product_id.in_(product_ids),
                ProductRecord.merchant_id.isnot(None),
                ProductRecord.is_active == True,
                Merchant.is_open == True
            ).order_by(ProductRecord.recorded_at.desc()).all()

            # 商家 → 最新一条记录
            merchant_latest: dict = {}
            for record in records:
                mid = record.merchant_id
                if mid not in merchant_latest:
                    merchant_latest[mid] = record

            # 记录哪些商家有这个食材
            covered_merchants = set()
            for mid, record in merchant_latest.items():
                if record.price is None or record.original_quantity is None or record.original_quantity <= 0 or not record.original_unit:
                    continue

                # 计算单价（按食材默认单位）
                unit_price = None
                total_price = float(record.price)
                orig_qty = float(record.original_quantity)
                orig_unit_abbr = record.original_unit.abbreviation

                if target_unit and orig_unit_abbr != target_unit:
                    conv = unit_service.convert(
                        orig_qty, orig_unit_abbr, target_unit,
                        entity_type="ingredient",
                        entity_id=ingredient.id
                    )
                    if conv and conv.get("converted_quantity") and conv["converted_quantity"] > 0:
                        unit_price = total_price / conv["converted_quantity"]
                else:
                    unit_price = total_price / orig_qty if orig_qty > 0 else None

                if unit_price is None or unit_price <= 0:
                    continue

                # 计算该食材在菜谱中的用量成本
                ingredient_qty = 0
                if ri.quantity:
                    try:
                        ingredient_qty = float(ri.quantity)
                    except (ValueError, TypeError):
                        pass
                elif ri.quantity_range:
                    # 取用量区间平均值
                    qr = ri.quantity_range
                    if isinstance(qr, dict):
                        q_min = float(qr.get("min", 0) or 0)
                        q_max = float(qr.get("max", 0) or 0)
                        ingredient_qty = (q_min + q_max) / 2

                ingredient_cost = unit_price * ingredient_qty

                # 按商家维度聚合
                merchant_name = record.merchant.name if record.merchant else f"商家{mid}"
                if mid not in merchant_data:
                    merchant_data[mid] = {
                        "merchant_name": merchant_name,
                        "total_cost": 0.0,
                        "covered_set": set(),
                    }
                merchant_data[mid]["total_cost"] += ingredient_cost
                merchant_data[mid]["covered_set"].add(ri.id)
                covered_merchants.add(mid)

        # 构建返回数据
        merchants_list = []
        for mid, data in merchant_data.items():
            missing_names = []
            for ri in recipe_ingredients:
                if ri.id not in data["covered_set"]:
                    missing_names.append(ri.ingredient.name if ri.ingredient else "未知食材")

            merchants_list.append(MerchantCostItem(
                merchant_id=mid,
                merchant_name=data["merchant_name"],
                total_cost=round(data["total_cost"], 2),
                covered_count=len(data["covered_set"]),
                total_ingredients=total_ingredients,
                missing_ingredients=missing_names,
                is_recommended=False,  # 暂标记，下面计算
            ))

        # 推荐算法：覆盖全食材的商家中总价最低 → 否则按覆盖率降序→总价升序
        if merchants_list:
            merchants_list.sort(key=lambda m: (-m.covered_count, m.total_cost))
            # 第一个是覆盖最多 + 总价最低的
            if merchants_list:
                merchants_list[0].is_recommended = True

        return RecipeMerchantCostResponse(merchants=merchants_list)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算商家成本失败: {str(e)}")
```

  记得在文件顶部的导入中添加 `RecipeMerchantCostResponse, MerchantCostItem`（从 schemas 导入）。

- [ ] **Step 3: Verify no syntax errors**

  运行: `uv run python -c "from app.api.recipes import router; print('OK')"`

  从 `backend/` 目录执行，确认无 import / syntax 错误。

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/recipe.py backend/app/api/recipes.py
git commit -m "feat(api): add GET /recipes/{id}/merchant-costs endpoint"
```

---

### Task 2: Recipe Analysis Route + Page Skeleton

**Files:**
- Create: `frontend/src/views/recipes/RecipeAnalysisView.vue`
- Modify: `frontend/src/router/index.ts` — 新增 `/recipes/:id/analysis` 路由

- [ ] **Step 1: Add route**

  在 `frontend/src/router/index.ts` 中，`recipe-detail` 路由定义（第 50-54 行）之后添加：

```typescript
{
  path: 'recipes/:id/analysis',
  name: 'recipe-analysis',
  component: () => import('@/views/recipes/RecipeAnalysisView.vue'),
  meta: { detailType: '菜谱', title: '菜谱分析' },
},
```

- [ ] **Step 2: Create RecipeAnalysisView.vue skeleton**

  在 `frontend/src/views/recipes/RecipeAnalysisView.vue` 创建页面骨架，包含：

```vue
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
    <!-- 加载骨架 -->
    <div v-if="!recipe && loading" class="text-center py-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <v-alert v-else-if="error" type="error" class="ma-4">{{ error }}</v-alert>

    <template v-else-if="recipe">
      <!-- 模块 ① + ②：宽屏两栏 -->
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
            :serving-ratio="servingRatio"
            @filter-change="onCostTrendFilterChange"
          />
        </v-col>
      </v-row>

      <!-- 模块 ③：营养贡献 -->
      <NutritionSourceGrid
        :nutrition-data="nutritionData"
        :loading="loadingNutritionData"
      />

      <!-- 模块 ⑤ + ④：商家 -->
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
import { ref, computed, onMounted } from 'vue'
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

const servingRatio = computed(() => 1) // 固定 1:1，分析页不切换份数

function goBack() {
  router.push(`/recipes/${recipeId}`)
}

const COST_HISTORY_BATCH_DAYS = 90

async function loadAllData() {
  loading.value = true
  error.value = null

  try {
    // 并行加载基础数据
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
    const daysMap: Record<string, number> = { week: 7, month: 30, quarter: 90, year: 365 }
    const days = daysMap[filter] || 90
    const res = await api.get(`/recipes/${recipeId}/cost-history-range`, {
      params: { days, offset_days: 0 },
      timeout: 30000,
    })
    costHistoryRecords.value = Array.isArray(res) ? res : []
  } catch { /* 忽略错误 */ }
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
```

  注意：这是一个骨架，各子组件 props 名需要与后续 Task 实际定义对齐。Task 3-6 会创建各子组件文件。

- [ ] **Step 3: Build check**

  运行: 从 `frontend/` 目录执行 `npx vue-tsc --noEmit` 确认无类型错误（或 `npm run build`）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/views/recipes/RecipeAnalysisView.vue
git commit -m "feat: add recipe analysis route and page skeleton"
```

---

### Task 3: Cost Proportion Chart Component

**Files:**
- Create: `frontend/src/components/recipes/CostProportionChart.vue`

- [ ] **Step 1: Create component**

  ECharts 环形图展示食材成本占比。扇区标签显示食材名/金额/百分比，中心显示总成本。

```vue
<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="tertiary">mdi-chart-pie</v-icon>
      食材成本占比
    </v-card-title>
    <v-divider />
    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate size="32" />
      </div>
      <div v-else-if="!chartData.length" class="text-center py-8 text-medium-emphasis">
        <v-icon size="48" color="medium-emphasis">mdi-chart-pie</v-icon>
        <div class="text-body-2 mt-2">暂无成本数据</div>
      </div>
      <div v-else ref="chartRef" class="cost-proportion-chart" style="width:100%;height:320px" />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  costBreakdown?: any[] | null
  totalCost?: number | string | null
  loading?: boolean
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

// 统一色盘（与成本趋势、营养溯源共用）
const COLOR_PALETTE = [
  '#ff9800', '#4caf50', '#2196f3', '#9c27b0',
  '#f44336', '#00bcd4', '#ff5722', '#607d8b',
  '#e91e63', '#3f51b5', '#009688', '#795548',
]

interface ChartItem {
  name: string
  value: number
  itemStyle: { color: string }
}

const chartData = computed<ChartItem[]>(() => {
  const breakdown = props.costBreakdown
  if (!breakdown?.length) return []

  const items: ChartItem[] = breakdown.map((b: any, i: number) => ({
    name: b.ingredient_name || `食材${i + 1}`,
    value: parseFloat(b.cost) || 0,
    itemStyle: { color: COLOR_PALETTE[i % COLOR_PALETTE.length] },
  }))

  // 只显示前 5 + 其他
  if (items.length > 6) {
    const top5 = items.slice(0, 5)
    const otherValue = items.slice(5).reduce((s, i) => s + i.value, 0)
    top5.push({
      name: '其他',
      value: otherValue,
      itemStyle: { color: '#e0e0e0' },
    })
    return top5
  }
  return items
})

const totalCostDisplay = computed(() => {
  if (props.totalCost !== null && props.totalCost !== undefined) {
    return `¥${parseFloat(String(props.totalCost)).toFixed(2)}`
  }
  const total = chartData.value.reduce((s, i) => s + i.value, 0)
  return `¥${total.toFixed(2)}`
})

function renderChart() {
  if (!chartRef.value || !chartData.value.length) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}: ¥${p.value.toFixed(2)} (${p.percent}%)`,
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        show: true,
        formatter: (p: any) => `{b|${p.name}}\n{c|¥${p.value.toFixed(2)}} {per|${p.percent}%}`,
        rich: {
          b: { fontSize: 12, lineHeight: 20 },
          c: { fontSize: 13, fontWeight: 'bold' },
          per: { fontSize: 11, color: '#999' },
        },
      },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
      },
      data: chartData.value,
    }],
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: totalCostDisplay.value,
        textAlign: 'center',
        fill: '#333',
        fontSize: 20,
        fontWeight: 'bold',
      },
      z: 100,
    }],
  }, true)
}

watch(() => [props.costBreakdown, props.loading], () => {
  nextTick(() => {
    if (!props.loading) renderChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => { if (!props.loading) renderChart() })
})

// 响应式 resize
import { onUnmounted } from 'vue'
onMounted(() => window.addEventListener('resize', () => chartInstance?.resize()))
onUnmounted(() => {
  window.removeEventListener('resize', () => chartInstance?.resize())
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style scoped>
.cost-proportion-chart :deep(canvas) {
  outline: none;
}
</style>
```

- [ ] **Step 2: Build check**

  运行: 从 `frontend/` 执行 `npx vue-tsc --noEmit`（或 `npm run build`）确认无类型错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/recipes/CostProportionChart.vue
git commit -m "feat: add CostProportionChart donut chart component"
```

---

### Task 4: Cost Trend Analysis Component

**Files:**
- Create: `frontend/src/components/recipes/CostTrendAnalysis.vue`

- [ ] **Step 1: Create component**

  堆叠面积图 + 食材标签列表，点击食材显示单食材价格趋势。

```vue
<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="tertiary">mdi-chart-timeline-variant</v-icon>
      成本趋势
      <v-spacer />
      <v-btn-toggle v-model="selectedFilter" mandatory density="compact" variant="outlined" divided>
        <v-btn v-for="f in filters" :key="f.value" :value="f.value" size="small">
          {{ f.label }}
        </v-btn>
      </v-btn-toggle>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate size="32" />
      </div>
      <div v-else-if="!chartData.length" class="text-center py-8 text-medium-emphasis">
        <v-icon size="48" color="medium-emphasis">mdi-chart-line</v-icon>
        <div class="text-body-2 mt-2">暂无成本趋势数据</div>
      </div>
      <template v-else>
        <!-- 宽屏：图左 + 标签右 -->
        <div class="trend-layout">
          <div ref="chartRef" class="trend-chart" style="flex:1;min-height:260px" />
          <div class="ingredient-tags">
            <div class="text-caption text-medium-emphasis mb-2">点击查看单食材趋势</div>
            <v-btn
              v-for="(item, i) in ingredientItems"
              :key="i"
              size="small"
              variant="tonal"
              class="mb-1"
              :color="item.color"
              :class="{ 'font-weight-bold': selectedIngredientIndex === i }"
              @click="selectIngredient(i)"
              block
            >
              <template #prepend>
                <v-icon size="small" :color="item.color">mdi-circle</v-icon>
              </template>
              {{ item.name }}
              <template #append>
                <span class="text-caption text-medium-emphasis">{{ item.percent }}</span>
              </template>
            </v-btn>
          </div>
        </div>
        <!-- 选中单食材时的趋势 -->
        <div v-if="selectedIngredientName" class="mt-2 pa-3 bg-surface-variant rounded">
          <div class="text-body-2 font-weight-medium mb-1">
            {{ selectedIngredientName }} — 价格趋势
          </div>
          <div ref="ingredientChartRef" class="ingredient-trend-chart" style="height:100px" />
        </div>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { api } from '@/api/client'

const props = defineProps<{
  recipeId: number
  costHistory: any[]
  ingredients?: any[]
  costBreakdown?: any[] | null
  loading?: boolean
  servingRatio?: number
}>()

const emit = defineEmits<{
  'filter-change': [filter: string]
}>()

const COLOR_PALETTE = [
  '#ff9800', '#4caf50', '#2196f3', '#9c27b0',
  '#f44336', '#00bcd4', '#ff5722', '#607d8b',
]

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null
const ingredientChartRef = ref<HTMLElement | null>(null)
let ingredientChartInstance: echarts.ECharts | null = null

const filters = [
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '季', value: 'quarter' },
  { label: '年', value: 'year' },
  { label: '全部', value: 'all' },
]
const selectedFilter = ref('quarter')

const selectedIngredientIndex = ref<number | null>(null)
const selectedIngredientName = ref('')
const ingredientTrendData = ref<any[]>([])
const loadingIngredientTrend = ref(false)

// 计算食材标签
const ingredientItems = computed(() => {
  if (!props.costBreakdown?.length) return []
  const total = props.costBreakdown.reduce((s: number, b: any) => s + (parseFloat(b.cost) || 0), 0)
  return props.costBreakdown.slice(0, 8).map((b: any, i: number) => ({
    name: b.ingredient_name || `食材${i + 1}`,
    percent: total > 0 ? `${Math.round((parseFloat(b.cost) || 0) / total * 100)}%` : '',
    color: COLOR_PALETTE[i % COLOR_PALETTE.length],
    ingredientId: b.ingredient_id,
  }))
})

// 总趋势图数据
const chartData = computed(() => props.costHistory || [])

function renderTrendChart() {
  if (!chartRef.value || !chartData.value.length) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const dates = chartData.value.map((d: any) => d.date || '')
  const avgValues = chartData.value.map((d: any) => d.avg_cost || 0)
  const minValues = chartData.value.map((d: any) => d.min_cost || 0)
  const maxValues = chartData.value.map((d: any) => d.max_cost || 0)

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        const date = params[0]?.axisValue || ''
        const avg = params.find((p: any) => p.seriesName === '平均成本')
        const min = params.find((p: any) => p.seriesName === '最低')
        const max = params.find((p: any) => p.seriesName === '最高')
        return `${date}<br/>平均: ¥${avg?.value?.toFixed(2) || '-'}<br/>区间: ¥${min?.value?.toFixed(2) || '-'} ~ ¥${max?.value?.toFixed(2) || '-'}`
      },
    },
    grid: { left: 50, right: 16, top: 8, bottom: 24 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 10, rotate: 30 },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '¥{value}',
        fontSize: 10,
      },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series: [
      {
        name: '最低',
        type: 'line',
        data: minValues,
        lineStyle: { width: 0 },
        symbol: 'none',
        areaStyle: { opacity: 0 },
        stack: 'total',
      },
      {
        name: '平均成本',
        type: 'line',
        data: avgValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: '#ff9800' },
        itemStyle: { color: '#ff9800' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255,152,0,0.25)' },
            { offset: 1, color: 'rgba(255,152,0,0.02)' },
          ]),
        },
      },
      {
        name: '最高',
        type: 'line',
        data: maxValues,
        lineStyle: { width: 0 },
        symbol: 'none',
        areaStyle: { opacity: 0 },
        stack: 'total',
      },
    ],
  }, true)
}

async function selectIngredient(index: number) {
  if (selectedIngredientIndex.value === index) {
    // 取消选中
    selectedIngredientIndex.value = null
    selectedIngredientName.value = ''
    ingredientTrendData.value = []
    ingredientChartInstance?.clear()
    return
  }

  selectedIngredientIndex.value = index
  const item = ingredientItems.value[index]
  if (!item) return
  selectedIngredientName.value = item.name
  loadingIngredientTrend.value = true

  try {
    // 获取单食材价格趋势：取近90天数据
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - 90 * 86400000).toISOString().split('T')[0]
    const res = await api.get('/products', {
      params: {
        ingredient_id: item.ingredientId,
        start_date: startDate,
        end_date: endDate,
        limit: 500,
      },
    })

    const records = Array.isArray(res) ? res : res?.items || []
    // 按日期聚合平均单价
    const dateMap: Record<string, number[]> = {}
    for (const r of records) {
      const d = r.recorded_at?.split('T')[0] || r.recorded_at?.slice(0, 10)
      if (!d) continue
      if (!dateMap[d]) dateMap[d] = []
      const price = r.price ? parseFloat(r.price) : 0
      const qty = r.original_quantity ? parseFloat(r.original_quantity) : 1
      dateMap[d].push(qty > 0 ? price / qty : 0)
    }
    ingredientTrendData.value = Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, prices]) => ({
        date,
        avgPrice: prices.reduce((s, p) => s + p, 0) / prices.length,
      }))

    renderIngredientTrend()
  } catch { /* 忽略 */ }
  loadingIngredientTrend.value = false
}

function renderIngredientTrend() {
  if (!ingredientChartRef.value || !ingredientTrendData.value.length) return

  if (!ingredientChartInstance) {
    ingredientChartInstance = echarts.init(ingredientChartRef.value)
  }

  ingredientChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 8, top: 8, bottom: 16 },
    xAxis: {
      type: 'category',
      data: ingredientTrendData.value.map(d => d.date),
      axisLabel: { fontSize: 9, rotate: 30, interval: 'auto' },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '¥{value}', fontSize: 9 },
    },
    series: [{
      type: 'line',
      data: ingredientTrendData.value.map(d => d.avgPrice),
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1.5, color: '#ff9800' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(255,152,0,0.2)' },
          { offset: 1, color: 'rgba(255,152,0,0.02)' },
        ]),
      },
    }],
  }, true)
}

// 监听 filter 变更
watch(selectedFilter, (val) => {
  emit('filter-change', val)
})

watch(() => [props.costHistory, props.loading], () => {
  nextTick(() => {
    if (!props.loading && chartData.value.length) renderTrendChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    if (!props.loading && chartData.value.length) renderTrendChart()
  })
})

onMounted(() => window.addEventListener('resize', () => {
  chartInstance?.resize()
  ingredientChartInstance?.resize()
}))
onUnmounted(() => {
  window.removeEventListener('resize', () => {
    chartInstance?.resize()
    ingredientChartInstance?.resize()
  })
  chartInstance?.dispose()
  ingredientChartInstance?.dispose()
})
</script>

<style scoped>
.trend-layout {
  display: flex;
  gap: 12px;
}
.ingredient-tags {
  width: 120px;
  flex-shrink: 0;
}
@media (max-width: 959px) {
  .trend-layout {
    flex-direction: column;
  }
  .ingredient-tags {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .ingredient-tags .v-btn {
    flex: 0 0 auto;
    min-width: 0;
  }
}
</style>
```

- [ ] **Step 2: Build check**

  运行: `npx vue-tsc --noEmit` 确认无类型错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/recipes/CostTrendAnalysis.vue
git commit -m "feat: add CostTrendAnalysis with stacked area chart and ingredient selector"
```

---

### Task 5: Nutrition Source Grid Component

**Files:**
- Create: `frontend/src/components/recipes/NutritionSourceGrid.vue`

- [ ] **Step 1: Create component**

  多环形图网格，每个营养素一张环图展示食材贡献。显示 NRV 指标，支持切换到全部。

```vue
<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="success">mdi-food-apple-outline</v-icon>
      营养贡献溯源
      <v-spacer />
      <v-btn-toggle v-model="showAll" mandatory density="compact">
        <v-btn :value="false" size="small">NRV 指标</v-btn>
        <v-btn :value="true" size="small">全部</v-btn>
      </v-btn-toggle>
    </v-card-title>
    <v-divider />
    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate size="32" />
      </div>
      <div v-else-if="!displayNutrients.length" class="text-center py-8 text-medium-emphasis">
        <v-icon size="48" color="medium-emphasis">mdi-food-apple-outline</v-icon>
        <div class="text-body-2 mt-2">暂无营养数据</div>
      </div>
      <div v-else class="nutrition-grid">
        <div
          v-for="nutrient in displayNutrients"
          :key="nutrient.key"
          class="nutrition-donut-card"
        >
          <div class="text-body-2 font-weight-medium text-center mb-1">{{ nutrient.label }}</div>
          <div :ref="el => setChartRef(nutrient.key, el as HTMLElement)" class="mini-donut" />
          <div class="text-caption text-center text-medium-emphasis mt-1">
            {{ nutrient.totalText }}
          </div>
          <div class="text-caption text-center text-disabled">
            {{ nutrient.topContributors }}
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  nutritionData?: any | null
  loading?: boolean
}>()

const COLOR_PALETTE = [
  '#ff9800', '#4caf50', '#2196f3', '#9c27b0',
  '#f44336', '#00bcd4', '#ff5722', '#607d8b',
]

const showAll = ref(false)
const chartRefs = new Map<string, HTMLElement>()
const chartInstances = new Map<string, echarts.ECharts>()

function setChartRef(key: string, el: HTMLElement | null) {
  if (el) chartRefs.set(key, el)
}

// NRV 参考值对应的营养素键名
const NRV_KEYS = new Set([
  'energy', 'protein', 'fat', 'carbohydrate', 'fiber',
  'calcium', 'iron', 'sodium', 'potassium',
  'vitamin_a_rae', 'vitamin_c', 'vitamin_b1', 'vitamin_b2',
  'vitamin_b12', 'vitamin_d', 'vitamin_e', 'vitamin_k',
])

// 有 NRV 指标的营养素标签
const NRV_LABELS: Record<string, string> = {
  energy: '能量', protein: '蛋白质', fat: '脂肪', carbohydrate: '碳水化合物',
  fiber: '膳食纤维', calcium: '钙', iron: '铁', sodium: '钠', potassium: '钾',
  vitamin_a_rae: '维生素A', vitamin_c: '维生素C', vitamin_b1: '维生素B1',
  vitamin_b2: '维生素B2', vitamin_b12: '维生素B12', vitamin_d: '维生素D',
  vitamin_e: '维生素E', vitamin_k: '维生素K',
}

interface NutrientDisplay {
  key: string
  label: string
  totalValue: number
  unit: string
  nrpPct: number | null
  totalText: string
  topContributors: string
  items: { name: string; value: number; color: string }[]
}

const displayNutrients = computed<NutrientDisplay[]>(() => {
  const nutrition = props.nutritionData
  if (!nutrition?.ingredient_details?.length) return []

  const perServing = nutrition.per_serving_nutrition
  if (!perServing) return []

  // 从 per_serving_nutrition 获取有数据的营养素
  const allNutrients = perServing.all_nutrients || perServing.core_nutrients || {}
  const coreNutrients = perServing.core_nutrients || {}

  const result: NutrientDisplay[] = []

  for (const [key, data] of Object.entries(allNutrients)) {
    const nData = data as any
    if (!nData || nData.value === undefined || nData.value === null) continue

    const isNrv = NRV_KEYS.has(key)
    if (!showAll.value && !isNrv) continue

    const label = NRV_LABELS[key] || nData.name_zh || key
    const totalValue = typeof nData.value === 'number' ? nData.value : parseFloat(nData.value) || 0
    const unit = nData.unit || ''
    const nrpPct = nData.nrp_pct != null ? Math.round(nData.nrp_pct) : null
    const totalText = nrpPct !== null
      ? `${totalValue}${unit} · NRV ${nrpPct}%`
      : `${totalValue}${unit}`

    // 从 ingredient_details 获取各食材贡献
    const ingredientItems: { name: string; value: number; color: string }[] = []
    let colorIndex = 0
    for (const detail of nutrition.ingredient_details) {
      const contrib = detail.nutrition_contribution?.[label] || detail.nutrition_contribution?.[key]
      if (contrib && contrib.value != null && contrib.value > 0) {
        ingredientItems.push({
          name: detail.ingredient_name || `食材${colorIndex + 1}`,
          value: parseFloat(contrib.value) || 0,
          color: COLOR_PALETTE[colorIndex % COLOR_PALETTE.length],
        })
        colorIndex++
      }
    }

    if (!ingredientItems.length) continue

    // 排序取 TOP 2
    ingredientItems.sort((a, b) => b.value - a.value)
    const totalIngredientValue = ingredientItems.reduce((s, i) => s + i.value, 0)
    const top2 = ingredientItems.slice(0, 2)
    const topContributors = top2
      .map(i => `${i.name} ${Math.round((i.value / totalIngredientValue) * 100)}%`)
      .join(' · ')

    result.push({
      key,
      label,
      totalValue,
      unit,
      nrpPct,
      totalText,
      topContributors,
      items: ingredientItems,
    })
  }

  return result
})

function renderDonuts() {
  for (const nutrient of displayNutrients.value) {
    const el = chartRefs.get(nutrient.key)
    if (!el) continue

    let instance = chartInstances.get(nutrient.key)
    if (!instance) {
      instance = echarts.init(el)
      chartInstances.set(nutrient.key, instance)
    }

    const total = nutrient.items.reduce((s, i) => s + i.value, 0)

    instance.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${p.name}: ${p.value.toFixed(2)}${nutrient.unit} (${p.percent}%)`,
      },
      series: [{
        type: 'pie',
        radius: ['50%', '75%'],
        center: ['50%', '50%'],
        silent: true,
        label: { show: false },
        emphasis: { scale: false },
        itemStyle: {
          borderRadius: 2,
          borderColor: '#fff',
          borderWidth: 1,
        },
        data: nutrient.items.map(i => ({
          name: i.name,
          value: i.value,
          itemStyle: { color: i.color },
        })),
      }],
      graphic: [{
        type: 'text',
        left: 'center',
        top: '48%',
        style: {
          text: `${total.toFixed(1)}${nutrient.unit === 'kcal' ? '' : nutrient.unit}`,
          textAlign: 'center',
          fill: '#666',
          fontSize: 11,
          fontWeight: 'bold',
        },
        z: 100,
      }],
    }, true)
  }
}

watch(showAll, () => nextTick(renderDonuts))
watch(() => [props.nutritionData, props.loading], () => {
  nextTick(() => {
    if (!props.loading && displayNutrients.value.length) renderDonuts()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    if (!props.loading && displayNutrients.value.length) renderDonuts()
  })
})

onMounted(() => window.addEventListener('resize', () => {
  chartInstances.forEach(c => c.resize())
}))
onUnmounted(() => {
  window.removeEventListener('resize', () => {
    chartInstances.forEach(c => c.resize())
  })
  chartInstances.forEach(c => c.dispose())
  chartInstances.clear()
})
</script>

<style scoped>
.nutrition-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}
.nutrition-donut-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.mini-donut {
  width: 120px;
  height: 120px;
}
@media (max-width: 599px) {
  .nutrition-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .mini-donut {
    width: 100px;
    height: 100px;
  }
}
</style>
```

- [ ] **Step 2: Build check**

  运行: `npx vue-tsc --noEmit` 确认无类型错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/recipes/NutritionSourceGrid.vue
git commit -m "feat: add NutritionSourceGrid with multi-donut nutrient breakdown"
```

---

### Task 6: Merchant Cost Cards + Price Matrix Components

**Files:**
- Create: `frontend/src/components/recipes/MerchantCostCards.vue`
- Create: `frontend/src/components/recipes/MerchantPriceMatrix.vue`

- [ ] **Step 1: Create MerchantCostCards.vue**

```vue
<template>
  <div class="mb-4">
    <div class="d-flex align-center mb-3">
      <v-icon start color="info">mdi-store-outline</v-icon>
      <span class="text-h6 font-weight-regular">按商家预估成本</span>
    </div>

    <div v-if="loading" class="d-flex ga-3">
      <v-skeleton-loader v-for="i in 3" :key="i" type="card" class="flex-1-1" max-width="240" />
    </div>
    <div v-else-if="!merchantList.length" class="text-center py-6 text-medium-emphasis">
      <v-icon size="40" color="medium-emphasis">mdi-store-off</v-icon>
      <div class="text-body-2 mt-2">暂无商家价格数据</div>
    </div>
    <div v-else class="merchant-cards">
      <v-card
        v-for="m in merchantList"
        :key="m.merchant_id"
        :class="{ 'merchant-card-recommended': m.is_recommended }"
        :color="m.is_recommended ? 'orange-lighten-5' : undefined"
        class="merchant-card"
        elevation="0"
        variant="outlined"
      >
        <v-card-text>
          <div class="d-flex align-center mb-1">
            <span class="text-body-1 font-weight-medium text-truncate">{{ m.merchant_name }}</span>
            <v-spacer />
            <v-chip v-if="m.is_recommended" size="x-small" color="orange" class="font-weight-bold">
              最实惠 ✓
            </v-chip>
          </div>
          <div class="text-caption text-medium-emphasis mb-2">
            覆盖 {{ m.covered_count }}/{{ m.total_ingredients }} 种食材
          </div>
          <div class="text-h5 font-weight-bold mb-1">
            ¥{{ m.total_cost.toFixed(2) }}
          </div>
          <div v-if="m.missing_ingredients?.length" class="text-caption text-warning">
            <v-icon size="12" color="warning">mdi-alert-circle-outline</v-icon>
            缺 {{ m.missing_ingredients.join('、') }}
          </div>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  merchantCosts?: { merchants?: any[] } | null
  loading?: boolean
}>()

const merchantList = computed(() => {
  return props.merchantCosts?.merchants || []
})
</script>

<style scoped>
.merchant-cards {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.merchant-card {
  min-width: 180px;
  max-width: 240px;
  flex: 1;
}
.merchant-card-recommended {
  border-color: #ff9800 !important;
  border-width: 2px !important;
}
</style>
```

- [ ] **Step 2: Create MerchantPriceMatrix.vue**

```vue
<template>
  <div>
    <div class="d-flex align-center mb-3">
      <v-icon start color="info">mdi-table-compare</v-icon>
      <span class="text-h6 font-weight-regular">商家比价推荐</span>
    </div>

    <v-card elevation="0" variant="outlined">
      <v-card-text class="pa-0">
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate size="24" />
        </div>
        <div v-else-if="!merchantNames.length" class="text-center py-6 text-medium-emphasis">
          <v-icon size="40" color="medium-emphasis">mdi-table-off</v-icon>
          <div class="text-body-2 mt-2">暂无比价数据</div>
        </div>
        <div v-else class="price-table-wrapper">
          <table class="price-matrix">
            <thead>
              <tr>
                <th class="sticky-col">食材</th>
                <th class="sticky-col" style="left:120px">用量</th>
                <th v-for="m in merchantNames" :key="m" class="text-right">{{ m }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in tableRows" :key="row.recipeIngredientId">
                <td class="sticky-col font-weight-medium">{{ row.name }}</td>
                <td class="sticky-col" style="left:120px;color:#888;font-size:12px">
                  {{ row.quantityDisplay }}
                </td>
                <td
                  v-for="(cell, mName) in row.merchantPrices"
                  :key="mName"
                  class="text-right"
                  :class="{ 'price-lowest': cell.isLowest, 'price-missing': !cell.hasPrice }"
                >
                  {{ cell.hasPrice ? `¥${cell.displayValue}` : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  recipeIngredients?: any[] | null
  merchantPrices?: any[] | null
  loading?: boolean
}>()

// 聚合所有商家的名称
const merchantNames = computed(() => {
  if (!props.merchantPrices?.length) return []
  const names = new Set<string>()
  for (const item of props.merchantPrices) {
    for (const p of (item.prices || [])) {
      names.add(p.merchant_name || `商家${p.merchant_id}`)
    }
  }
  return Array.from(names)
})

interface CellData {
  hasPrice: boolean
  displayValue: string
  rawValue: number
  isLowest: boolean
}

interface TableRow {
  recipeIngredientId: number
  name: string
  quantityDisplay: string
  merchantPrices: Record<string, CellData>
}

const tableRows = computed<TableRow[]>(() => {
  const ingredients = props.recipeIngredients || []
  const priceItems = props.merchantPrices || []

  return ingredients
    .filter((ing: any) => ing.ingredient_id)
    .map((ing: any) => {
      const priceItem = priceItems.find(
        (p: any) => p.recipeIngredientId === ing.id
      )

      const merchantPrices: Record<string, CellData> = {}

      // 为该食材的每个商家价格填充
      const merchantPriceList = priceItem?.prices || []
      for (const mName of merchantNames.value) {
        const match = merchantPriceList.find(
          (p: any) => (p.merchant_name || `商家${p.merchant_id}`) === mName
        )
        if (match) {
          merchantPrices[mName] = {
            hasPrice: true,
            displayValue: match.price?.toFixed(2) || '0.00',
            rawValue: match.price || 0,
            isLowest: match.is_lowest || false,
          }
        } else {
          merchantPrices[mName] = {
            hasPrice: false,
            displayValue: '',
            rawValue: 0,
            isLowest: false,
          }
        }
      }

      // 用量显示
      let qtyDisplay = ''
      if (ing.quantity) {
        qtyDisplay = `${ing.quantity}${ing.unit || ''}`
      }

      return {
        recipeIngredientId: ing.id,
        name: ing.name,
        quantityDisplay: qtyDisplay,
        merchantPrices,
      }
    })
})
</script>

<style scoped>
.price-table-wrapper {
  overflow-x: auto;
}
.price-matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.price-matrix th,
.price-matrix td {
  padding: 8px 12px;
  white-space: nowrap;
  border-bottom: 1px solid #e0e0e0;
}
.price-matrix th {
  background: #f5f5f5;
  font-weight: 500;
  position: sticky;
  top: 0;
  z-index: 2;
}
.sticky-col {
  position: sticky;
  left: 0;
  background: white;
  z-index: 1;
  min-width: 100px;
}
.price-matrix th.sticky-col {
  background: #f5f5f5;
  z-index: 3;
}
.price-lowest {
  font-weight: 700;
  color: #e65100;
}
.price-missing {
  color: #ccc;
}
.text-right {
  text-align: right;
}
</style>
```

- [ ] **Step 3: Build check**

  运行: `npx vue-tsc --noEmit` 确认无类型错误。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/recipes/MerchantCostCards.vue frontend/src/components/recipes/MerchantPriceMatrix.vue
git commit -m "feat: add merchant cost cards and price matrix components"
```

---

### Task 7: Add Analysis Entry Button to Recipe Detail

**Files:**
- Modify: `frontend/src/views/recipes/RecipeDetail.vue`

- [ ] **Step 1: Add "分析" button to app-bar**

  在 `RecipeDetail.vue` 中，找到 app-bar 的 `#append` 区域（约第 14-20 行），在删除和刷新按钮之间添加分析按钮：

```vue
<v-btn
  icon="mdi-chart-box-outline"
  variant="text"
  color="tertiary"
  @click="$router.push(`/recipes/${recipe?.id}/analysis`)"
/>
```

  位置：`mdi-delete` 按钮之后，`mdi-refresh` 之前。

  修改后的 #append 区域：

```vue
<template #append>
  <v-btn
    icon="mdi-delete"
    variant="text"
    color="error"
    :disabled="!recipe || deleting"
    @click="showDeleteDialog = true"
  />
  <v-btn
    icon="mdi-chart-box-outline"
    variant="text"
    color="tertiary"
    @click="$router.push(`/recipes/${recipe?.id}/analysis`)"
  />
  <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadData" />
</template>
```

- [ ] **Step 2: Build check**

  运行: `npx vue-tsc --noEmit` 确认无类型错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/recipes/RecipeDetail.vue
git commit -m "feat: add analysis button to recipe detail page"
```

---

### Task 8: Integration, Edge Cases, and Color Consistency

**Files:**
- Modify: `frontend/src/views/recipes/RecipeAnalysisView.vue` — 完善错误处理和空态
- Modify: 各组件 — 确保颜色统一

- [ ] **Step 1: Ensure color consistency across all components**

  确认 `CostProportionChart.vue`、`CostTrendAnalysis.vue`、`NutritionSourceGrid.vue` 使用相同顺序的 `COLOR_PALETTE`：
  - `['#ff9800', '#4caf50', '#2196f3', '#9c27b0', '#f44336', '#00bcd4', '#ff5722', '#607d8b']`

  食材按 `cost_breakdown` 数组顺序分配颜色，确保同一食材在三个模块中颜色一致。

- [ ] **Step 2: Add error retry and empty states in RecipeAnalysisView**

  在 `RecipeAnalysisView.vue` 中完善错误处理：

```typescript
// 在 error ref 后添加重试逻辑
async function retry() {
  // 重置所有状态
  costData.value = null
  nutritionData.value = null
  costHistoryRecords.value = []
  merchantCosts.value = null
  merchantPriceData.value = []
  await loadAllData()
}
```

  在模板中添加重试按钮：

```vue
<v-alert v-else-if="error" type="error" class="ma-4">
  {{ error }}
  <template #append>
    <v-btn variant="text" @click="retry">重试</v-btn>
  </template>
</v-alert>
```

- [ ] **Step 3: Handle edge cases in NutritionSourceGrid**

  确认 `NutritionSourceGrid` 处理以下情况：
  - `ingredient_details` 为空或未提供 → 显示"暂无营养数据"
  - 食材只有 1 种 → 环形图显示 100%
  - 所有食材贡献值为 0 → 跳过该营养素，不显示环形图
  - 营养素键名与预设 `NRV_LABELS` 不匹配 → 回退显示原始 `key`

- [ ] **Step 4: Full build verification**

  运行完整构建检查:
  - 后端: 从 `backend/` 目录 `uv run python -c "from app.main import app; print('Backend OK')"`
  - 前端: 从 `frontend/` 目录 `npx vue-tsc --noEmit && npx vite build`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/recipes/RecipeAnalysisView.vue frontend/src/components/recipes/
git commit -m "fix: add error handling, empty states, and color consistency across analysis components"
```

---

## Implementation Summary

| Task | Files | Type |
|------|-------|------|
| 1 | `backend/app/schemas/recipe.py` + `backend/app/api/recipes.py` | Backend |
| 2 | `frontend/src/router/index.ts` + `frontend/src/views/recipes/RecipeAnalysisView.vue` | Frontend |
| 3 | `frontend/src/components/recipes/CostProportionChart.vue` | Frontend |
| 4 | `frontend/src/components/recipes/CostTrendAnalysis.vue` | Frontend |
| 5 | `frontend/src/components/recipes/NutritionSourceGrid.vue` | Frontend |
| 6 | `frontend/src/components/recipes/MerchantCostCards.vue` + `MerchantPriceMatrix.vue` | Frontend |
| 7 | `frontend/src/views/recipes/RecipeDetail.vue` | Frontend |
| 8 | 多文件 — 集成与边缘情况 | Both |
