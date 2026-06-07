# 多实体筛选功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为价格记录、菜谱、原料、商品四个列表页增加筛选器功能，在搜索基础上通过多选下拉和日期范围过滤列表。

**Architecture:** 后端每个 API 列表端点新增逗号分隔的多选查询参数，使用 SQLAlchemy `in_()` 和 `has()` 实现跨表筛选；前端新增通用 `<FilterBar>` 组件，各视图通过配置数组声明筛选维度。

**Tech Stack:** FastAPI (Python), SQLAlchemy, Vue 3 + Vuetify + TypeScript

---

## File Structure

### 新增文件
| 文件 | 职责 |
|------|------|
| `frontend/src/components/common/FilterBar.vue` | 通用筛选器组件，渲染多选下拉和日期范围控件，emit change 事件 |

### 修改文件
| 文件 | 职责 |
|------|------|
| `backend/app/api/products.py` | `GET /products/` 增加 merchant_ids, record_types, ingredient_category_ids 参数 |
| `backend/app/api/recipes.py` | `GET /recipes/` 增加 categories, difficulties 参数 |
| `backend/app/api/nutrition.py` | `GET /ingredients` 增加 category_ids 参数 |
| `backend/app/api/products_entity.py` | `GET /products/entity/` 增加 ingredient_ids, ingredient_category_ids, brands 参数 |
| `frontend/src/views/prices/PricesView.vue` | 集成 FilterBar 并加载商家/分类选项 |
| `frontend/src/views/recipes/RecipesView.vue` | 集成 FilterBar (分类/难度预置) |
| `frontend/src/views/data/IngredientsView.vue` | 集成 FilterBar (从 API 加载分类) |
| `frontend/src/views/data/ProductsView.vue` | 集成 FilterBar 并加载原料/分类/品牌选项 |

---

## Pre-flight: 确认后端虚拟环境和构建工具

- [ ] **Step 1: 确认后端虚拟环境有效**

```bash
cd d:\code\live_calc\backend && .\.venv\Scripts\python -c "from fastapi import FastAPI; print('OK')"
```
Expected: `OK`

- [ ] **Step 2: 确认前端构建可运行**

```bash
cd d:\code\live_calc\frontend && npx vue-tsc --noEmit 2>&1 | head -5
```
Expected: 无类型错误或少量已知错误

---

## Task 1: 后端 API - 价格记录增加多选筛选参数

**Files:**
- Modify: `backend/app/api/products.py` (GET /products/ 函数，约 line 214-466)

**分析：** 当前 `get_product_records` 已经有 `merchant_id` (单值)、`start_date`、`end_date` 参数。需要新增 `merchant_ids` (逗号分隔)、`record_types` (逗号分隔)、`ingredient_category_ids` (逗号分隔)。现有 `merchant_id` 保留兼容，`merchant_ids` 优先级更高。

- [ ] **Step 1: 修改函数签名，新增三个可选字符串参数**

在 `get_product_records` 函数的参数列表中添加以下参数（放在 `target_unit` 之前）：

```python
merchant_ids: Optional[str] = Query(None, description="商家ID列表，逗号分隔"),
record_types: Optional[str] = Query(None, description="记录类型列表，逗号分隔（purchase,price）"),
ingredient_category_ids: Optional[str] = Query(None, description="原料分类ID列表，逗号分隔"),
```

- [ ] **Step 2: 在 `sort_by == "price_records"` 分支中应用新筛选条件**

在约 line 291 处 `record_counts` 子查询构建完成后，添加：

```python
# 多选商家筛选
if merchant_ids:
    ids = [int(x.strip()) for x in merchant_ids.split(',') if x.strip()]
    if ids:
        record_counts = record_counts.filter(ProductRecord.merchant_id.in_(ids))

# 多选记录类型筛选
if record_types:
    types = [x.strip() for x in record_types.split(',') if x.strip()]
    if types:
        record_counts = record_counts.filter(ProductRecord.record_type.in_(types))

# 跨表：按原料分类筛选
if ingredient_category_ids:
    cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
    if cat_ids:
        record_counts = record_counts.join(ProductRecord.product).join(
            Product.ingredient
        ).filter(Ingredient.category_id.in_(cat_ids))
```

在约 line 339 处主查询构建后添加相同的筛选条件：

```python
# 多选商家筛选
if merchant_ids:
    ids = [int(x.strip()) for x in merchant_ids.split(',') if x.strip()]
    if ids:
        query = query.filter(ProductRecord.merchant_id.in_(ids))

# 多选记录类型筛选
if record_types:
    types = [x.strip() for x in record_types.split(',') if x.strip()]
    if types:
        query = query.filter(ProductRecord.record_type.in_(types))

# 跨表：按原料分类筛选
if ingredient_category_ids:
    cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
    if cat_ids:
        query = query.join(ProductRecord.product).join(
            Product.ingredient
        ).filter(Ingredient.category_id.in_(cat_ids))
```

- [ ] **Step 3: 在 `else` 分支（非 price_records 排序）中应用相同筛选条件**

在约 line 354 `else` 分支中，在现有过滤条件后面添加与 Step 2 完全相同的三组筛选代码（`merchant_ids`、`record_types`、`ingredient_category_ids`）。

注意：需要避免重复 join。如果本分支中已经因为 `search` 条件 join 了 `product` 和 `ingredient`，则 `ingredient_category_ids` 的 filter 可以直接用，不需要 join。写法参考：

```python
# 直接 filter 即可（但如果之前已有 join 则不需要重复 join）
# 由于跨表筛选需要的 join 可能已被 search 条件触发，使用 has() 避免重复 join
if ingredient_category_ids:
    cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
    if cat_ids:
        query = query.filter(
            ProductRecord.product.has(
                Product.ingredient.has(
                    Ingredient.category_id.in_(cat_ids)
                )
            )
        )
```

对 `merchant_ids` 和 `record_types` 保持与 Step 2 相同的 `.in_()` 方式。

- [ ] **Step 4: 验证无语法错误**

```bash
cd d:\code\live_calc\backend && .\.venv\Scripts\python -c "import ast; ast.parse(open('app/api/products.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
cd d:\code\live_calc && git add backend/app/api/products.py
git commit -m "feat(api): 价格记录列表接口支持多选商家/记录类型/原料分类筛选"
```

---

## Task 2: 后端 API - 菜谱列表增加 categories 和 difficulties 参数

**Files:**
- Modify: `backend/app/api/recipes.py` (GET /recipes/ 函数，约 line 93-223)

- [ ] **Step 1: 新增两个可选字符串参数**

在 `get_recipes` 函数参数中，在 `search` 参数之后添加：

```python
categories: Optional[str] = Query(None, description="菜谱分类列表，逗号分隔"),
difficulties: Optional[str] = Query(None, description="难度列表，逗号分隔"),
```

- [ ] **Step 2: 在查询构建后添加筛选逻辑**

在约 line 126 处 `all_recipes_query` 构建后，`total = all_recipes_query.count()` 之前添加：

```python
if categories:
    cat_list = [c.strip() for c in categories.split(',') if c.strip()]
    if cat_list:
        all_recipes_query = all_recipes_query.filter(Recipe.category.in_(cat_list))

if difficulties:
    diff_list = [d.strip() for d in difficulties.split(',') if d.strip()]
    if diff_list:
        all_recipes_query = all_recipes_query.filter(Recipe.difficulty.in_(diff_list))
```

- [ ] **Step 3: 验证无语法错误**

```bash
cd d:\code\live_calc\backend && .\.venv\Scripts\python -c "import ast; ast.parse(open('app/api/recipes.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd d:\code\live_calc && git add backend/app/api/recipes.py
git commit -m "feat(api): 菜谱列表接口支持分类和难度多选筛选"
```

---

## Task 3: 后端 API - 原料列表增加 category_ids 参数

**Files:**
- Modify: `backend/app/api/nutrition.py` (GET /ingredients 函数，约 line 85-183)

- [ ] **Step 1: 新增 category_ids 可选字符串参数**

在 `get_ingredients` 函数参数中，在 `search` 参数之后添加：

```python
category_ids: Optional[str] = Query(None, description="原料分类ID列表，逗号分隔"),
```

- [ ] **Step 2: 在查询中添加筛选逻辑**

在约 line 109 处 `base_query` 构建后，在 `if search is not None:` 之后添加：

```python
if category_ids:
    ids = [int(x.strip()) for x in category_ids.split(',') if x.strip()]
    if ids:
        base_query = base_query.filter(Ingredient.category_id.in_(ids))
```

这个 filter 需要加到所有三个查询位置（`base_query`、`subquery`、`query`），确保计数和分页一致。

具体：
1. `base_query` (约 line 106-110) — 添加
2. `subquery` (约 line 114-127) 的 `if search is not None:` 之后添加
3. `query` (约 line 130-142) 的 `if search is not None:` 之后添加
4. `total` 计数查询 (约 line 158-169) 的两个位置也添加

- [ ] **Step 3: 验证无语法错误**

```bash
cd d:\code\live_calc\backend && .\.venv\Scripts\python -c "import ast; ast.parse(open('app/api/nutrition.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd d:\code\live_calc && git add backend/app/api/nutrition.py
git commit -m "feat(api): 原料列表接口支持分类多选筛选"
```

---

## Task 4: 后端 API - 商品列表增加多选筛选参数

**Files:**
- Modify: `backend/app/api/products_entity.py` (GET /products/entity/ 函数，约 line 73-191)

- [ ] **Step 1: 新增三个可选字符串参数**

在 `list_products` 函数参数中，在 `sort_by` 参数之后添加：

```python
ingredient_ids: Optional[str] = Query(None, description="原料ID列表，逗号分隔"),
ingredient_category_ids: Optional[str] = Query(None, description="原料分类ID列表，逗号分隔"),
brands: Optional[str] = Query(None, description="品牌列表，逗号分隔"),
```

- [ ] **Step 2: 在 `sort_by == "price_records"` 分支中添加筛选**

在约 line 107 `if ingredient_id:` 块之后添加：

```python
if ingredient_ids:
    ids = [int(x.strip()) for x in ingredient_ids.split(',') if x.strip()]
    if ids:
        query = query.filter(Product.ingredient_id.in_(ids))

if ingredient_category_ids:
    cat_ids = [int(x.strip()) for x in ingredient_category_ids.split(',') if x.strip()]
    if cat_ids:
        query = query.filter(Product.ingredient.has(Ingredient.category_id.in_(cat_ids)))

if brands:
    brand_list = [b.strip() for b in brands.split(',') if b.strip()]
    if brand_list:
        query = query.filter(Product.brand.in_(brand_list))
```

- [ ] **Step 3: 在 `else` 分支中添加相同筛选**

在约 line 134 `if ingredient_id:` 块之后添加与 Step 2 完全相同的三组筛选代码。

- [ ] **Step 4: 验证无语法错误**

```bash
cd d:\code\live_calc\backend && .\.venv\Scripts\python -c "import ast; ast.parse(open('app/api/products_entity.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
cd d:\code\live_calc && git add backend/app/api/products_entity.py
git commit -m "feat(api): 商品列表接口支持原料/原料分类/品牌多选筛选"
```

---

## Task 5: 前端 - FilterBar 通用组件

**Files:**
- Create: `frontend/src/components/common/FilterBar.vue`
- Test: 确认 Vuetify 构建通过

- [ ] **Step 1: 创建 FilterBar.vue 组件**

完整组件代码如下：

```vue
<template>
  <div class="filter-bar d-flex flex-wrap ga-2 mb-4">
    <template v-for="f in filters" :key="f.key">
      <!-- 多选下拉 -->
      <v-select
        v-if="f.type === 'select'"
        :model-value="getValue(f.key)"
        :items="f.items || []"
        :label="f.label"
        :multiple="f.multiple !== false"
        :chips="f.multiple !== false"
        :closable-chips="f.multiple !== false"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        :style="{ minWidth: f.minWidth || '180px', maxWidth: f.maxWidth || '280px' }"
        @update:model-value="onSelectChange(f.key, $event)"
      >
        <template #selection="{ item, index }">
          <v-chip v-if="index < 3" size="small" closable @click:close="onRemoveChip(f.key, item.value)">
            <span class="text-truncate" style="max-width: 80px">{{ item.title }}</span>
          </v-chip>
          <span v-if="index === 3" class="text-caption text-medium-emphasis ml-1">
            +{{ getValue(f.key).length - 3 }}
          </span>
        </template>
      </v-select>

      <!-- 日期范围 -->
      <div v-if="f.type === 'date-range'" class="d-flex align-center ga-1" :style="{ minWidth: f.minWidth || '260px' }">
        <span class="text-caption text-medium-emphasis mr-1">{{ f.label }}</span>
        <v-text-field
          :model-value="getValue(f.key)?.start || ''"
          type="date"
          variant="outlined"
          density="compact"
          hide-details
          placeholder="开始日期"
          style="max-width: 140px"
          @update:model-value="onDateChange(f.key, 'start', $event)"
        />
        <span class="text-caption text-medium-emphasis">~</span>
        <v-text-field
          :model-value="getValue(f.key)?.end || ''"
          type="date"
          variant="outlined"
          density="compact"
          hide-details
          placeholder="结束日期"
          style="max-width: 140px"
          @update:model-value="onDateChange(f.key, 'end', $event)"
        />
      </div>
    </template>

    <!-- 有激活的筛选时显示清除按钮 -->
    <v-btn
      v-if="hasActiveFilters"
      variant="text"
      density="compact"
      color="medium-emphasis"
      size="small"
      class="mt-1"
      @click="clearAll"
    >
      <v-icon start size="small">mdi-close</v-icon>
      清除筛选
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'

export interface FilterConfig {
  key: string
  label: string
  type: 'select' | 'date-range'
  items?: { value: any; title: string }[]
  multiple?: boolean
  minWidth?: string
  maxWidth?: string
}

interface DateRangeValue {
  start: string | null
  end: string | null
}

type FilterValue = any[] | DateRangeValue | null

const props = defineProps<{
  filters: FilterConfig[]
  loading?: boolean
}>()

const emit = defineEmits<{
  change: [state: Record<string, any>]
}>()

// 内部状态
const state = reactive<Record<string, FilterValue>>({})

// 按 key 获取值，惰性初始化
const getValue = (key: string): FilterValue => {
  if (!(key in state)) {
    const cfg = props.filters.find(f => f.key === key)
    if (cfg?.type === 'date-range') {
      state[key] = { start: null, end: null } as DateRangeValue
    } else {
      state[key] = []
    }
  }
  return state[key]!
}

// 是否有激活的筛选条件
const hasActiveFilters = computed(() => {
  return Object.entries(state).some(([key, val]) => {
    if (!val) return false
    if (Array.isArray(val)) return val.length > 0
    if (typeof val === 'object') return !!(val as DateRangeValue).start || !!(val as DateRangeValue).end
    return false
  })
})

let timer: ReturnType<typeof setTimeout> | null = null

const emitChange = () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    const payload: Record<string, any> = {}
    for (const [key, val] of Object.entries(state)) {
      if (Array.isArray(val)) {
        payload[key] = val
      } else if (val && typeof val === 'object') {
        const dr = val as DateRangeValue
        if (dr.start) payload[`${key}_start`] = dr.start
        if (dr.end) payload[`${key}_end`] = dr.end
      }
    }
    emit('change', payload)
  }, 300)
}

const onSelectChange = (key: string, val: any) => {
  state[key] = val ?? []
  emitChange()
}

const onRemoveChip = (key: string, value: any) => {
  const current = getValue(key)
  if (Array.isArray(current)) {
    state[key] = current.filter(v => v !== value)
    emitChange()
  }
}

const onDateChange = (key: string, field: 'start' | 'end', val: string) => {
  const current = getValue(key) as DateRangeValue
  current[field] = val || null
  emitChange()
}

const clearAll = () => {
  for (const key of Object.keys(state)) {
    delete state[key]
  }
  emitChange()
}
</script>
```

- [ ] **Step 2: 验证前端类型检查**

```bash
cd d:\code\live_calc\frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: 无新增类型错误

- [ ] **Step 3: Commit**

```bash
cd d:\code\live_calc && git add frontend/src/components/common/FilterBar.vue
git commit -m "feat(ui): 新增通用 FilterBar 筛选器组件"
```

---

## Task 6: 前端 - 价格记录页集成 FilterBar

**Files:**
- Modify: `frontend/src/views/prices/PricesView.vue`

- [ ] **Step 1: 引入 FilterBar 组件，添加 import**

在 `<script>` 的 import 区域添加：

```typescript
import FilterBar from '@/components/common/FilterBar.vue'
import type { FilterConfig } from '@/components/common/FilterBar.vue'
```

- [ ] **Step 2: 在 template 搜索框下方插入 FilterBar**

```vue
<FilterBar
  :filters="priceFilters"
  @change="onFilterChange"
/>
```

放在搜索框之后、loading 指示器之前。

- [ ] **Step 3: 添加筛选配置和状态**

在 `<script setup>` 中添加：

```typescript
// 筛选器配置
const priceFilters = computed<FilterConfig[]>(() => [
  {
    key: 'merchant_ids',
    label: '商家',
    type: 'select',
    items: merchantOptions.value.map(m => ({ value: m.id, title: m.name })),
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
    key: 'record_types',
    label: '记录类型',
    type: 'select',
    items: [
      { value: 'purchase', title: '购买' },
      { value: 'price', title: '比价' },
    ],
    minWidth: '140px',
    maxWidth: '180px',
  },
  {
    key: 'date_range',
    label: '日期',
    type: 'date-range',
    minWidth: '260px',
  },
])

// 分类选项
const categoryOptions = ref<{ value: number; title: string }[]>([])

const onFilterChange = (filterState: Record<string, any>) => {
  currentPage.value = 1
  // 合并到请求参数
  requestFilters.value = filterState
  loadRecords()
}

const requestFilters = ref<Record<string, any>>({})
```

- [ ] **Step 4: 加载分类选项（与 loadMerchants 类似）**

```typescript
const loadCategories = async () => {
  try {
    const response = await api.get('/categories')
    categoryOptions.value = (response || []).map((c: any) => ({
      value: c.id,
      title: c.display_name,
    }))
  } catch (e: any) {
    console.error('加载分类失败', e)
  }
}
```

- [ ] **Step 5: 修改 loadRecords 拼合筛选参数**

在 `loadRecords` 函数中，`params` 对象添加：

```typescript
// 筛选参数
if (requestFilters.value.merchant_ids?.length) {
  params.merchant_ids = requestFilters.value.merchant_ids.join(',')
}
if (requestFilters.value.ingredient_category_ids?.length) {
  params.ingredient_category_ids = requestFilters.value.ingredient_category_ids.join(',')
}
if (requestFilters.value.record_types?.length) {
  params.record_types = requestFilters.value.record_types.join(',')
}
if (requestFilters.value.date_range_start) {
  params.start_date = requestFilters.value.date_range_start
}
if (requestFilters.value.date_range_end) {
  params.end_date = requestFilters.value.date_range_end
}
```

- [ ] **Step 6: 在 onMounted 中调用 loadCategories**

```typescript
onMounted(() => {
  loadRecords()
  loadMerchants()
  loadCategories()
  loadUnits()
  window.addEventListener('app-refresh', handleRefresh)
})
```

- [ ] **Step 7: 验证类型检查**

```bash
cd d:\code\live_calc\frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: 无新增类型错误

- [ ] **Step 8: Commit**

```bash
cd d:\code\live_calc && git add frontend/src/views/prices/PricesView.vue
git commit -m "feat(ui): 价格记录页面集成筛选器"
```

---

## Task 7: 前端 - 菜谱页集成 FilterBar

**Files:**
- Modify: `frontend/src/views/recipes/RecipesView.vue`

- [ ] **Step 1: 引入 FilterBar**

在 `<script>` 中添加：

```typescript
import FilterBar from '@/components/common/FilterBar.vue'
import type { FilterConfig } from '@/components/common/FilterBar.vue'
```

- [ ] **Step 2: 在 template 搜索框下方插入 FilterBar**

放在搜索框之后、loading 指示器之前：

```vue
<FilterBar
  :filters="recipeFilters"
  @change="onFilterChange"
/>
```

- [ ] **Step 3: 添加筛选配置和状态**

```typescript
const recipeFilters: FilterConfig[] = [
  {
    key: 'categories',
    label: '分类',
    type: 'select',
    items: [
      { value: '荤菜', title: '荤菜' },
      { value: '素菜', title: '素菜' },
      { value: '水产', title: '水产' },
      { value: '主食', title: '主食' },
      { value: '汤与粥', title: '汤与粥' },
      { value: '早餐', title: '早餐' },
      { value: '甜品', title: '甜品' },
      { value: '调料', title: '调料' },
      { value: '半成品', title: '半成品' },
      { value: '小食', title: '小食' },
    ],
    minWidth: '140px',
    maxWidth: '200px',
  },
  {
    key: 'difficulties',
    label: '难度',
    type: 'select',
    items: [
      { value: '简单', title: '简单' },
      { value: '中等', title: '中等' },
      { value: '困难', title: '困难' },
    ],
    minWidth: '120px',
    maxWidth: '160px',
  },
]

const requestFilters = ref<Record<string, any>>({})

const onFilterChange = (filterState: Record<string, any>) => {
  currentPage.value = 1
  requestFilters.value = filterState
  loadRecipes()
}
```

- [ ] **Step 4: 修改 loadRecipes 拼合筛选参数**

找到 `loadRecipes` 函数中构建 `params` 的位置，添加：

```typescript
if (requestFilters.value.categories?.length) {
  params.categories = requestFilters.value.categories.join(',')
}
if (requestFilters.value.difficulties?.length) {
  params.difficulties = requestFilters.value.difficulties.join(',')
}
```

- [ ] **Step 5: 验证类型检查**

```bash
cd d:\code\live_calc\frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: 无新增类型错误

- [ ] **Step 6: Commit**

```bash
cd d:\code\live_calc && git add frontend/src/views/recipes/RecipesView.vue
git commit -m "feat(ui): 菜谱页面集成筛选器"
```

---

## Task 8: 前端 - 原料页集成 FilterBar

**Files:**
- Modify: `frontend/src/views/data/IngredientsView.vue`

- [ ] **Step 1: 引入 FilterBar**

```typescript
import FilterBar from '@/components/common/FilterBar.vue'
import type { FilterConfig } from '@/components/common/FilterBar.vue'
```

- [ ] **Step 2: 在 template 搜索框下方插入 FilterBar**

```vue
<FilterBar
  :filters="ingredientFilters"
  @change="onFilterChange"
/>
```

- [ ] **Step 3: 添加筛选配置和状态**

```typescript
const categoryOptions = ref<{ value: number; title: string }[]>([])

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

const requestFilters = ref<Record<string, any>>({})

const onFilterChange = (filterState: Record<string, any>) => {
  currentPage.value = 1
  requestFilters.value = filterState
  loadIngredients()
}
```

- [ ] **Step 4: 加载分类选项**

```typescript
const loadCategories = async () => {
  try {
    const response = await api.get('/categories')
    categoryOptions.value = (response || []).map((c: any) => ({
      value: c.id,
      title: c.display_name,
    }))
  } catch (e: any) {
    console.error('加载分类失败', e)
  }
}
```

- [ ] **Step 5: 在 loadIngredients 中拼合筛选参数**

```typescript
if (requestFilters.value.category_ids?.length) {
  params.category_ids = requestFilters.value.category_ids.join(',')
}
```

- [ ] **Step 6: 在 onMounted 中调用 loadCategories**

```typescript
onMounted(() => {
  loadIngredients()
  loadOptions()
  loadCategories()
  window.addEventListener('app-refresh', loadIngredients)
})
```

- [ ] **Step 7: 验证类型检查**

```bash
cd d:\code\live_calc\frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: 无新增类型错误

- [ ] **Step 8: Commit**

```bash
cd d:\code\live_calc && git add frontend/src/views/data/IngredientsView.vue
git commit -m "feat(ui): 原料页面集成筛选器"
```

---

## Task 9: 前端 - 商品页集成 FilterBar

**Files:**
- Modify: `frontend/src/views/data/ProductsView.vue`

- [ ] **Step 1: 引入 FilterBar**

```typescript
import FilterBar from '@/components/common/FilterBar.vue'
import type { FilterConfig } from '@/components/common/FilterBar.vue'
```

- [ ] **Step 2: 在 template 搜索框下方插入 FilterBar**

```vue
<FilterBar
  :filters="productFilters"
  @change="onFilterChange"
/>
```

- [ ] **Step 3: 添加筛选配置、状态和选项加载**

```typescript
// 分类选项
const categoryOptions = ref<{ value: number; title: string }[]>([])
// 品牌选项（从商品数据提取）
const brandOptions = ref<{ value: string; title: string }[]>([])

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

const requestFilters = ref<Record<string, any>>({})

const onFilterChange = (filterState: Record<string, any>) => {
  currentPage.value = 1
  requestFilters.value = filterState
  loadProducts()
}
```

- [ ] **Step 4: 加载分类和品牌选项**

```typescript
const loadCategories = async () => {
  try {
    const response = await api.get('/categories')
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
    const uniqueBrands = [...new Set(products.map(p => p.brand).filter(Boolean))]
    brandOptions.value = uniqueBrands.map(b => ({ value: b, title: b }))
  } catch (e: any) {
    console.error('加载品牌列表失败', e)
  }
}
```

- [ ] **Step 5: 修改 loadProducts 拼合筛选参数**

```typescript
if (requestFilters.value.ingredient_ids?.length) {
  params.ingredient_ids = requestFilters.value.ingredient_ids.join(',')
}
if (requestFilters.value.ingredient_category_ids?.length) {
  params.ingredient_category_ids = requestFilters.value.ingredient_category_ids.join(',')
}
if (requestFilters.value.brands?.length) {
  params.brands = requestFilters.value.brands.join(',')
}
```

- [ ] **Step 6: 在 onMounted 中调用 loadCategories 和 loadBrands**

```typescript
onMounted(() => {
  loadProducts()
  loadIngredients()
  loadCategories()
  loadBrands()
  window.addEventListener('app-refresh', loadProducts)
})
```

- [ ] **Step 7: 验证类型检查**

```bash
cd d:\code\live_calc\frontend && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: 无新增类型错误

- [ ] **Step 8: Commit**

```bash
cd d:\code\live_calc && git add frontend/src/views/data/ProductsView.vue
git commit -m "feat(ui): 商品页面集成筛选器"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** 所有 spec 中的筛选维度（价格记录 4 维、菜谱 2 维、原料 1 维、商品 3 维）都有对应的后端 API 参数和前端 FilterBar 配置
- [ ] **Placeholder scan:** 无 TBD/TODO 或模糊步骤，所有代码都完整给出
- [ ] **Type consistency:** 前端 FilterConfig 类型在组件中定义，各视图引用一致；后端参数名统一用逗号分隔字符串格式

---

## 执行方式

**Plan complete and saved to `docs/superpowers/plans/2026-06-07-filter-feature.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
