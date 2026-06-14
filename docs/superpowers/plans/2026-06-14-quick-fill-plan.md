# 快速填写功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 来逐步实施。步骤使用复选框（`- [ ]`）语法跟踪。

**目标：** 在价格记录页面增加「快速填写」入口，进入独立页面，让用户按商家批量填写商品价格。

**架构：** 纯前端改动。新增 `/prices/quick-fill` 路由和 `QuickFillView.vue` 页面，复用现有 API（`GET /merchants`、`GET /merchants/{id}/product-prices`、`GET /products/autocomplete`、`POST /products`）。

**涉及文件：**

| 操作 | 文件 |
|------|------|
| 修改 | `frontend/src/router/index.ts` |
| 修改 | `frontend/src/views/prices/PricesView.vue` |
| 新建 | `frontend/src/views/prices/QuickFillView.vue` |

---

### Task 1: 路由和入口按钮

**文件：**
- 修改：`frontend/src/router/index.ts`
- 修改：`frontend/src/views/prices/PricesView.vue`

- [ ] **Step 1: 添加路由**

在 `frontend/src/router/index.ts` 中 `/prices` 路由的同级下添加 `/prices/quick-fill` 子路由：

```ts
// 在 routes 数组的 children 中，prices 路由定义之后添加：
{
  path: 'prices/quick-fill',
  name: 'quick-fill',
  component: () => import('@/views/prices/QuickFillView.vue'),
  meta: { title: '快速填写' },
},
```

- [ ] **Step 2: 在 PricesView app-bar 添加入口按钮**

在 `frontend/src/views/prices/PricesView.vue` 的 `<v-app-bar>` → `<template #append>` 中，在刷新按钮后面添加：

```html
<v-btn icon="mdi-lightning-bolt" variant="text" @click="$router.push('/prices/quick-fill')" />
```

修改后的 `#append` 区域：

```html
<template #append>
  <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadRecords" />
  <v-btn icon="mdi-lightning-bolt" variant="text" @click="$router.push('/prices/quick-fill')" />
</template>
```

- [ ] **Step 3: 验证构建通过**

```bash
cd frontend && npx vue-tsc --noEmit && npx vite build
```

---

### Task 2: QuickFillView.vue — 页面骨架和商家选择

**文件：**
- 新建：`frontend/src/views/prices/QuickFillView.vue`

- [ ] **Step 1: 创建组件骨架**

创建 `frontend/src/views/prices/QuickFillView.vue`，包含 app-bar、商家选择器、空状态：

```vue
<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push('/prices')" />
    <v-app-bar-title class="text-h6">快速填写</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-check-all" variant="text" :loading="saving" @click="saveAll" />
    </template>
  </v-app-bar>

  <v-container fluid class="pa-4 list-grid-container" style="margin-top: 56px;">
    <v-autocomplete
      v-model="selectedMerchantId"
      :items="merchants"
      item-title="name"
      item-value="id"
      label="选择商家"
      variant="outlined"
      density="compact"
      hide-details
      class="mb-3"
      @update:model-value="onMerchantChange"
    />

    <template v-if="!selectedMerchantId">
      <div class="text-center py-8 text-medium-emphasis">请先选择商家</div>
    </template>

    <template v-else>
      <div class="text-caption text-medium-emphasis mb-3">
        选商家后自动列出历史所有商品，只保存填了价格的
      </div>
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'

interface Merchant {
  id: number
  name: string
}

const merchants = ref<Merchant[]>([])
const selectedMerchantId = ref<number | null>(null)
const saving = ref(false)

// 加载商家列表
const loadMerchants = async () => {
  try {
    const res = await api.get('/merchants', { params: { limit: 100 } })
    merchants.value = res.items || []
  } catch {
    merchants.value = []
  }
}

const onMerchantChange = (val: number | null) => {
  // 将在 Task 3 中实现
}

loadMerchants()
</script>
```

- [ ] **Step 2: 验证构建通过**

```bash
cd frontend && npx vue-tsc --noEmit && npx vite build
```

---

### Task 3: QuickFillView.vue — 历史商品列表和隐藏逻辑

**文件：**
- 修改：`frontend/src/views/prices/QuickFillView.vue`

- [ ] **Step 1: 定义行数据接口和隐藏逻辑工具函数**

在 `<script setup>` 中添加：

```ts
import { ref, computed } from 'vue'

interface FillRow {
  productId: number | null
  productName: string
  price: string
  quantity: number
  unit: string
  isEditingQuantity: boolean
  isEditingUnit: boolean
  isNew: boolean
  searchText?: string
  loading?: boolean
}

interface HiddenItem {
  productId: number
  filledAt: string
}

const HIDDEN_KEY_PREFIX = 'quick-fill-hidden-'

function getHiddenItems(merchantId: number): HiddenItem[] {
  try {
    const raw = sessionStorage.getItem(`${HIDDEN_KEY_PREFIX}${merchantId}`)
    if (!raw) return []
    return JSON.parse(raw).filter((item: HiddenItem) =>
      Date.now() - new Date(item.filledAt).getTime() < 3600000
    )
  } catch {
    return []
  }
}

function getHiddenProductIds(merchantId: number): Set<number> {
  return new Set(getHiddenItems(merchantId).map(i => i.productId))
}

function addHiddenItems(merchantId: number, productIds: number[]) {
  try {
    const existing = getHiddenItems(merchantId)
    const now = new Date().toISOString()
    const updated = [...existing, ...productIds.map(pid => ({ productId: pid, filledAt: now }))]
    sessionStorage.setItem(`${HIDDEN_KEY_PREFIX}${merchantId}`, JSON.stringify(updated))
  } catch {
    // sessionStorage 满时静默降级
  }
}
```

- [ ] **Step 2: 添加历史商品数据和可见行计算属性**

```ts
interface ProductPriceItem {
  product_id: number
  product_name: string
  price: number
  standard_unit_price: number | null
  standard_unit_label: string | null
  original_quantity: number
  recorded_at: string
}

const allHistoryRows = ref<FillRow[]>([])
const hiddenProductIds = ref<Set<number>>(new Set())

const visibleHistoryRows = computed(() =>
  allHistoryRows.value.filter(row => !hiddenProductIds.value.has(row.productId!))
)

const hiddenCount = computed(() =>
  allHistoryRows.value.length - visibleHistoryRows.value.length
)
```

- [ ] **Step 3: 实现 onMerchantChange 加载历史商品**

替换 `onMerchantChange`：

```ts
const onMerchantChange = async (merchantId: number | null) => {
  allHistoryRows.value = []
  if (!merchantId) return

  try {
    const res = await api.get(`/merchants/${merchantId}/product-prices`, {
      params: { skip: 0, limit: 100 }
    })
    const items: ProductPriceItem[] = res.items || []
    allHistoryRows.value = items.map(item => ({
      productId: item.product_id,
      productName: item.product_name,
      price: '',
      quantity: 1,
      unit: '斤',
      isEditingQuantity: false,
      isEditingUnit: false,
      isNew: false,
    }))
    hiddenProductIds.value = getHiddenProductIds(merchantId)
  } catch {
    allHistoryRows.value = []
    hiddenProductIds.value = new Set()
  }
}
```

- [ ] **Step 4: 渲染历史商品列表**

在 `<template>` 的 `v-else` 块中添加，在提示信息下方：

```html
<!-- 历史商品 -->
<template v-if="visibleHistoryRows.length > 0">
  <div class="text-subtitle-2 font-weight-bold mb-1">历史商品</div>
  <v-list class="fill-list pa-0" lines="one">
    <v-list-item v-for="(row, i) in visibleHistoryRows" :key="row.productId">
      <div class="fill-row">
        <span class="fill-row__name">{{ row.productName }}</span>
        <div class="fill-row__inputs">
          <v-text-field
            v-model="row.price"
            density="compact"
            variant="outlined"
            type="number"
            step="0.01"
            placeholder="¥0.00"
            hide-details
            class="fill-row__price"
          />
          <span class="fill-row__sep">/</span>
          <template v-if="row.isEditingQuantity">
            <v-text-field
              v-model="row.quantity"
              density="compact"
              variant="outlined"
              type="number"
              step="1"
              min="0.01"
              hide-details
              class="fill-row__qty-input"
              @keyup.enter="row.isEditingQuantity = false"
              @blur="row.isEditingQuantity = false"
            />
          </template>
          <span v-else class="fill-row__edit-text" @click="row.isEditingQuantity = true">
            {{ row.quantity }}
          </span>
          <template v-if="row.isEditingUnit">
            <v-select
              v-model="row.unit"
              :items="unitOptions"
              density="compact"
              variant="outlined"
              hide-details
              class="fill-row__unit-select"
              @update:model-value="row.isEditingUnit = false"
            />
          </template>
          <span v-else class="fill-row__edit-text" @click="row.isEditingUnit = true">
            {{ row.unit }}
          </span>
        </div>
      </div>
    </v-list-item>
  </v-list>
</template>

<!-- 隐藏提示 -->
<div v-if="hiddenCount > 0" class="text-caption text-center text-disabled py-2">
  ── 近 1h 已填商品已隐藏（{{ hiddenCount }} 个） ──
</div>

<!-- 空历史 -->
<div v-if="allHistoryRows.length === 0" class="text-caption text-medium-emphasis py-4 text-center">
  该商家暂无历史商品
</div>

<!-- 全部隐藏 -->
<div v-else-if="visibleHistoryRows.length === 0" class="text-caption text-medium-emphasis py-4 text-center">
  本期所有商品已填写完成
</div>
```

- [ ] **Step 5: 添加 unitOptions 加载**

```ts
interface UnitOption {
  title: string
  value: string
}

const unitOptions = ref<UnitOption[]>([])

const loadUnits = async () => {
  try {
    const res = await api.get('/units', { params: { limit: 100 } })
    const items = res.items || res || []
    unitOptions.value = items.map((u: any) => ({
      title: `${u.name} (${u.abbreviation})`,
      value: u.abbreviation,
    }))
  } catch {
    unitOptions.value = [
      { title: '斤 (斤)', value: '斤' },
      { title: '个 (个)', value: '个' },
      { title: '千克 (kg)', value: 'kg' },
      { title: '克 (克)', value: '克' },
    ]
  }
}

loadUnits()
```

- [ ] **Step 6: 验证构建通过**

```bash
cd frontend && npx vue-tsc --noEmit && npx vite build
```

---

### Task 4: QuickFillView.vue — 新增商品区域和验证 Vue 3 编译

**文件：**
- 修改：`frontend/src/views/prices/QuickFillView.vue`

- [ ] **Step 1: 添加新增商品状态和方法**

```ts
const newRows = ref<FillRow[]>([])
// 每行新增行的 autocomplete 建议结果
const newRowSuggestions = ref<Record<number, any[]>>({})

function addNewRow() {
  newRows.value.push({
    productId: null,
    productName: '',
    price: '',
    quantity: 1,
    unit: '斤',
    isEditingQuantity: false,
    isEditingUnit: false,
    isNew: true,
    searchText: '',
    loading: false,
  })
}

function removeNewRow(index: number) {
  newRows.value.splice(index, 1)
  // 清除对应的建议结果
  delete newRowSuggestions.value[index]
  // 重新编号
  const reindexed: Record<number, any[]> = {}
  Object.entries(newRowSuggestions.value).forEach(([k, v]) => {
    const idx = parseInt(k)
    if (idx < index) reindexed[idx] = v
    else if (idx > index) reindexed[idx - 1] = v
  })
  newRowSuggestions.value = reindexed
}

let searchDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {}

const onNewRowSearch = (index: number, query: string) => {
  if (searchDebounceTimers[index]) {
    clearTimeout(searchDebounceTimers[index])
  }
  searchDebounceTimers[index] = setTimeout(async () => {
    if (!query || query.length < 1) {
      newRowSuggestions.value[index] = []
      return
    }
    newRows.value[index].loading = true
    try {
      const existingProductIds = new Set(allHistoryRows.value.map(r => r.productId!))
      const res = await api.get('/products/autocomplete', { params: { q: query, limit: 20 } })
      const items = Array.isArray(res) ? res : (res.items || [])
      // 过滤掉已在历史列表中的商品
      newRowSuggestions.value[index] = items.filter((p: any) => !existingProductIds.has(p.id))
    } catch {
      newRowSuggestions.value[index] = []
    } finally {
      newRows.value[index].loading = false
    }
  }, 300)
}
```

- [ ] **Step 2: 渲染新增商品区域**

在 `<template>` 的 `v-else` 块中添加，在历史商品列表下方：

```html
<!-- 新增商品 -->
<div class="mt-4">
  <div class="text-subtitle-2 font-weight-bold mb-1">新增商品</div>
  <v-list class="fill-list pa-0" lines="one">
    <v-list-item v-for="(row, i) in newRows" :key="i">
      <div class="fill-row">
        <div class="fill-row__name fill-row__name--new">
          <v-autocomplete
            v-model="row.productId"
            v-model:search="row.searchText"
            :items="newRowSuggestions[i] || []"
            :loading="row.loading"
            item-title="name"
            item-value="id"
            placeholder="搜索商品..."
            variant="outlined"
            density="compact"
            hide-details
            return-object
            auto-select-first
            hide-selected
            :custom-filter="() => true"
            class="fill-row__product-search"
            @update:search="onNewRowSearch(i, $event)"
          >
            <template #no-data>
              {{ row.searchText ? '没有找到商品，将创建新商品' : '输入商品名称搜索' }}
            </template>
          </v-autocomplete>
        </div>
        <div class="fill-row__inputs">
          <v-text-field
            v-model="row.price"
            density="compact"
            variant="outlined"
            type="number"
            step="0.01"
            placeholder="¥0.00"
            hide-details
            class="fill-row__price"
          />
          <span class="fill-row__sep">/</span>
          <template v-if="row.isEditingQuantity">
            <v-text-field
              v-model="row.quantity"
              density="compact"
              variant="outlined"
              type="number"
              step="1"
              min="0.01"
              hide-details
              class="fill-row__qty-input"
              @keyup.enter="row.isEditingQuantity = false"
              @blur="row.isEditingQuantity = false"
            />
          </template>
          <span v-else class="fill-row__edit-text" @click="row.isEditingQuantity = true">
            {{ row.quantity }}
          </span>
          <template v-if="row.isEditingUnit">
            <v-select
              v-model="row.unit"
              :items="unitOptions"
              density="compact"
              variant="outlined"
              hide-details
              class="fill-row__unit-select"
              @update:model-value="row.isEditingUnit = false"
            />
          </template>
          <span v-else class="fill-row__edit-text" @click="row.isEditingUnit = true">
            {{ row.unit }}
          </span>
          <v-btn
            v-if="!row.price"
            icon="mdi-close"
            size="x-small"
            variant="text"
            color="default"
            class="fill-row__remove"
            @click="removeNewRow(i)"
          />
        </div>
      </div>
    </v-list-item>
  </v-list>

  <v-btn
    variant="text"
    color="primary"
    prepend-icon="mdi-plus"
    class="mt-1"
    @click="addNewRow"
  >
    添加新行
  </v-btn>
</div>
```

- [ ] **Step 3: 验证构建通过**

```bash
cd frontend && npx vue-tsc --noEmit && npx vite build
```

---

### Task 5: QuickFillView.vue — 保存逻辑

**文件：**
- 修改：`frontend/src/views/prices/QuickFillView.vue`

- [ ] **Step 1: 添加 saveAll 方法**

在 `<script setup>` 中添加：

```ts
import { useSnackbar } from '@/composables/useSnackbar'  // 按项目实际路径调整

const snackbar = inject('snackbar') as any

interface SaveRow {
  productId: number | null
  productName: string
  price: string
  quantity: number
  unit: string
}

const saveAll = async () => {
  if (!selectedMerchantId.value) {
    showMessage('请先选择商家')
    return
  }

  // 收集所有填了价格的行
  const toSave: SaveRow[] = []

  // 历史行
  for (const row of visibleHistoryRows.value) {
    if (row.price && parseFloat(row.price) > 0) {
      toSave.push({
        productId: row.productId,
        productName: row.productName,
        price: row.price,
        quantity: row.quantity,
        unit: row.unit,
      })
    }
  }

  // 新增行
  for (const row of newRows.value) {
    if (row.price && parseFloat(row.price) > 0) {
      if (!row.productId) {
        showMessage('请选择新增行的商品')
        return
      }
      toSave.push({
        productId: row.productId,
        productName: row.productName,
        price: row.price,
        quantity: row.quantity,
        unit: row.unit,
      })
    }
  }

  if (toSave.length === 0) {
    showMessage('请至少填写一个商品的价格')
    return
  }

  saving.value = true
  let successCount = 0
  let failCount = 0

  for (const item of toSave) {
    try {
      await api.post('/products', {
        product_id: item.productId,
        merchant_id: selectedMerchantId.value,
        price: parseFloat(item.price),
        original_quantity: item.quantity,
        original_unit: item.unit,
        record_type: 'purchase',
      })
      successCount++
    } catch {
      failCount++
    }
  }

  saving.value = false

  if (failCount === 0) {
    showMessage(`已保存 ${successCount} 条`)
    // 更新隐藏状态
    const savedProductIds = toSave
      .filter((_, i) => i < successCount)  // 只隐藏成功的
      .map(item => item.productId!)
    addHiddenItems(selectedMerchantId.value, savedProductIds)
    hiddenProductIds.value = getHiddenProductIds(selectedMerchantId.value)
    // 清空新增行
    newRows.value = []
    newRowSuggestions.value = {}
  } else if (successCount > 0) {
    showMessage(`已保存 ${successCount} 条，${failCount} 条失败`)
    const savedProductIds = toSave
      .slice(0, successCount)
      .map(item => item.productId!)
    addHiddenItems(selectedMerchantId.value, savedProductIds)
    hiddenProductIds.value = getHiddenProductIds(selectedMerchantId.value)
  } else {
    showMessage('保存失败，请重试')
  }
}
```

注：上述 `useSnackbar` 和 `inject('snackbar')` 需要根据项目实际的 snackbar 机制调整。请查看项目中其他组件的消息提示模式。

查看 `PricesView.vue` 中的消息提示模式：

```ts
// 在 PricesView.vue 中，错误处理使用：
import { getErrorMessage } from '@/utils/error'
// 和
import { useSnackbar } from '@/composables/useSnackbar'

const snackbar = useSnackbar()
// 使用: snackbar.show('消息')
```

因此改用：

```ts
import { getErrorMessage } from '@/utils/error'
```

并在 `<script setup>` 顶部添加：

```ts
const showMessage = (msg: string) => {
  // 使用 window.alert 或 Vue 的 inject snackbar
  // 查看项目已有的消息机制后调整
}
```

- [ ] **Step 2: 确认项目 snackbar 机制并修复**

查看 `frontend/src/composables/useSnackbar.ts` 是否存在。若存在，导入并替换 `showMessage`：

```ts
import { useSnackbar } from '@/composables/useSnackbar'

const snackbar = useSnackbar()
const showMessage = (msg: string) => snackbar.show(msg)
```

若不存在，改用其他现有的消息提示模式。

- [ ] **Step 3: 验证构建通过**

```bash
cd frontend && npx vue-tsc --noEmit && npx vite build
```

---

### Task 6: QuickFillView.vue — 样式

**文件：**
- 修改：`frontend/src/views/prices/QuickFillView.vue`

- [ ] **Step 1: 添加样式**

在 `</template>` 后添加 `<style scoped>`：

```vue
<style scoped>
.fill-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.fill-row__name {
  flex-shrink: 0;
  width: 72px;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fill-row__name--new {
  width: 120px;
}

.fill-row__product-search {
  min-width: 0;
}

.fill-row__inputs {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: flex-end;
}

.fill-row__price {
  max-width: 100px;
  min-width: 80px;
}

.fill-row__sep {
  color: rgba(0, 0, 0, 0.38);
  font-size: 14px;
  flex-shrink: 0;
}

.fill-row__qty-input {
  max-width: 60px;
  min-width: 50px;
}

.fill-row__qty-input :deep(input) {
  text-align: center;
}

.fill-row__unit-select {
  max-width: 80px;
  min-width: 60px;
}

.fill-row__edit-text {
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
  min-width: 24px;
  text-align: center;
  display: inline-block;
  user-select: none;
}

.fill-row__edit-text:hover {
  background: rgba(0, 0, 0, 0.06);
}

.fill-row__edit-text:active {
  background: rgba(0, 0, 0, 0.1);
}

.fill-row__remove {
  flex-shrink: 0;
}

.fill-list {
  background: transparent;
}

/* 触摸友好：编辑文本点击区域扩大 */
@media (max-width: 600px) {
  .fill-row__edit-text {
    padding: 6px 10px;
  }

  .fill-row__price :deep(input) {
    font-size: 16px; /* 防止 iOS 缩放 */
  }
}
</style>
```

- [ ] **Step 2: 最终验证构建**

```bash
cd frontend && npx vue-tsc --noEmit && npx vite build
```

确认构建无错误后，下一步进行运行态验证。
