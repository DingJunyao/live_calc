<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push('/prices')" />
    <v-app-bar-title class="text-h6">快速填写</v-app-bar-title>
    <template #append>
      <div class="d-flex align-center">
        <span v-if="saveProgress" class="text-caption text-medium-emphasis mr-2">
          {{ saveProgress.current }}/{{ saveProgress.total }}
        </span>
        <v-btn
          icon="mdi-content-paste"
          variant="text"
          :disabled="!selectedMerchantId"
          @click="pasteDialog = true"
        />
        <v-btn icon="mdi-check-all" variant="text" :loading="saving" @click="saveAll" />
      </div>
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

      <!-- 历史商品（按分类分组） -->
      <div v-if="groupedHistoryRows.length > 0" class="mb-4">
        <div class="text-subtitle-2 mb-2">历史商品</div>
        <v-list v-for="group in groupedHistoryRows" :key="group.categoryName" class="fill-list" density="compact">
          <div class="text-caption text-medium-emphasis px-4 py-1 font-weight-medium">{{ group.categoryName }}</div>
          <v-list-item v-for="(row, i) in group.rows" :key="'h-' + group.categoryName + '-' + i">
            <div class="fill-row">
              <div class="fill-row__name">{{ row.productName }}</div>
              <div class="fill-row__inputs">
                <v-text-field
                  v-model="row.price"
                  type="number"
                  step="0.01"
                  placeholder="¥0.00"
                  variant="outlined"
                  density="compact"
                  hide-details
                  class="fill-row__price"
                />
                <span class="fill-row__sep">/</span>
                <template v-if="row.isEditingQuantity">
                  <v-text-field
                    v-model.number="row.quantity"
                    type="number"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="fill-row__qty-input"
                    @blur="row.isEditingQuantity = false"
                  />
                </template>
                <template v-else>
                  <span class="fill-row__edit-text" @click="row.isEditingQuantity = true">
                    {{ row.quantity }}
                  </span>
                </template>
                <v-menu
                  :close-on-content-click="true"
                  location="bottom"
                  origin="bottom"
                >
                  <template #activator="{ props: menuProps }">
                    <span class="fill-row__edit-text" v-bind="menuProps">
                      {{ row.unit }}
                    </span>
                  </template>
                  <v-list density="compact" max-height="300">
                    <v-list-item
                      v-for="opt in unitOptions"
                      :key="opt.value"
                      :title="opt.title"
                      :active="row.unit === opt.value"
                      @click="row.unit = opt.value"
                    />
                  </v-list>
                </v-menu>
              </div>
            </div>
          </v-list-item>
        </v-list>
        <div v-if="hiddenCount > 0" class="text-caption text-center text-medium-emphasis py-2">
          ── 近 1h 已填商品已隐藏（{{ hiddenCount }} 个）──
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" size="24" width="2" />
        <div class="text-medium-emphasis text-caption mt-2">加载中…</div>
      </div>
      <!-- 空状态 -->
      <div v-else-if="allHistoryRows.length === 0" class="text-center py-4 text-medium-emphasis">
        该商家暂无历史商品
      </div>
      <div v-else-if="groupedHistoryRows.length === 0" class="text-center py-4 text-medium-emphasis">
        本期所有商品已填写完成
      </div>

      <!-- 新增商品 -->
      <div class="mb-4">
        <div class="text-subtitle-2 mb-2">新增商品</div>
        <v-list class="fill-list" density="compact">
          <v-list-item v-for="(row, i) in newRows" :key="'n-' + i">
            <div class="fill-row">
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
                auto-select-first
                hide-selected
                return-object
                attach
                :custom-filter="() => true"
                class="fill-row__product-search"
                @update:search="onNewRowSearch(i, $event)"
              >
                <template #no-data>
                  {{ row.searchText ? '没有找到商品，将创建新商品' : '输入商品名称搜索' }}
                </template>
              </v-autocomplete>
              <div class="fill-row__inputs">
                <v-text-field
                  v-model="row.price"
                  type="number"
                  step="0.01"
                  placeholder="¥0.00"
                  variant="outlined"
                  density="compact"
                  hide-details
                  class="fill-row__price"
                />
                <span class="fill-row__sep">/</span>
                <template v-if="row.isEditingQuantity">
                  <v-text-field
                    v-model.number="row.quantity"
                    type="number"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="fill-row__qty-input"
                    @blur="row.isEditingQuantity = false"
                  />
                </template>
                <template v-else>
                  <span class="fill-row__edit-text" @click="row.isEditingQuantity = true">
                    {{ row.quantity }}
                  </span>
                </template>
                <v-menu
                  :close-on-content-click="true"
                  location="bottom"
                  origin="bottom"
                >
                  <template #activator="{ props: menuProps }">
                    <span class="fill-row__edit-text" v-bind="menuProps">
                      {{ row.unit }}
                    </span>
                  </template>
                  <v-list density="compact" max-height="300">
                    <v-list-item
                      v-for="opt in unitOptions"
                      :key="opt.value"
                      :title="opt.title"
                      :active="row.unit === opt.value"
                      @click="row.unit = opt.value"
                    />
                  </v-list>
                </v-menu>
                <v-btn v-if="!row.price" icon="mdi-close" size="x-small" variant="text" @click="removeNewRow(i)" />
              </div>
            </div>
          </v-list-item>
        </v-list>
        <v-btn variant="text" color="primary" prepend-icon="mdi-plus" @click="addNewRow">
          添加新行
        </v-btn>
      </div>
    </template>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000" location="top">
      {{ snackbar.message }}
    </v-snackbar>

    <PasteImportDialog
      v-model="pasteDialog"
      :merchant-id="selectedMerchantId"
      @imported="onPasteImported"
    />
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/api/client'
import PasteImportDialog from '@/components/prices/PasteImportDialog.vue'

interface Merchant {
  id: number
  name: string
}

interface FillRow {
  productId: number | any | null
  productName: string
  price: string
  quantity: number
  unit: string
  isEditingQuantity: boolean
  isNew: boolean
  searchText?: string
  loading?: boolean
  categoryId: number | null
  categoryName: string
}

interface HiddenItem {
  productId: number
  filledAt: string
}

interface UnitOption {
  title: string
  value: string
}

// 中文拼音/字母排序 collator（模块级缓存复用）
const zhCollator: Intl.Collator = (() => {
  for (const loc of ['zh-Hans-CN-u-co-pinyin', 'zh-Hans-CN', 'zh']) {
    if (Intl.Collator.supportedLocalesOf([loc]).length > 0) {
      return new Intl.Collator(loc, { numeric: true, sensitivity: 'base' })
    }
  }
  return new Intl.Collator()
})()

// --- 隐藏逻辑 (sessionStorage) ---
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
    /* silent degrade */
  }
}

// --- 状态 ---
const merchants = ref<Merchant[]>([])
const selectedMerchantId = ref<number | null>(null)
const saving = ref(false)
const saveProgress = ref<{ current: number; total: number } | null>(null)
const loading = ref(false)
const historyRows = ref<FillRow[]>([])
const newRows = ref<FillRow[]>([])
const newRowSuggestions = ref<Record<number, any[]>>({})
const searchDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {}
const snackbar = ref({ show: false, message: '', color: 'success' })
const unitOptions = ref<UnitOption[]>([])
const pasteDialog = ref(false)

function showSnackbar(message: string, color: string = 'success') {
  snackbar.value = { show: true, message, color }
}

// 获取行的商品 ID（兼容历史行的 number 和新增行的对象）
const getRowProductId = (row: FillRow): number | null => {
  if (row.productId == null) return null
  if (typeof row.productId === 'object') return (row.productId as any).id ?? null
  return row.productId
}

// 已有商品 ID 集合（用于过滤新行建议）— 包含历史行和已选的新增行
const existingProductIds = computed(() => {
  const ids = new Set<number>()
  for (const row of [...historyRows.value, ...newRows.value]) {
    const pid = getRowProductId(row)
    if (pid) ids.add(pid)
  }
  return ids
})

// 可见历史行（过滤掉已隐藏的）
const visibleHistoryRows = computed(() => {
  const hiddenIds = selectedMerchantId.value
    ? getHiddenProductIds(selectedMerchantId.value)
    : new Set<number>()
  return historyRows.value.filter(r => {
    const pid = getRowProductId(r)
    return !pid || !hiddenIds.has(pid)
  })
})

const allHistoryRows = computed(() => historyRows.value)

// 历史商品按分类分组（组内已按拼音排序）
const groupedHistoryRows = computed(() => {
  const hiddenIds = selectedMerchantId.value
    ? getHiddenProductIds(selectedMerchantId.value)
    : new Set<number>()
  const groups: Array<{ categoryName: string; rows: FillRow[] }> = []
  const groupMap = new Map<string, typeof groups[0]>()
  for (const row of historyRows.value) {
    const pid = getRowProductId(row)
    if (pid && hiddenIds.has(pid)) continue
    const name = row.categoryName || '其他'
    if (!groupMap.has(name)) {
      const g = { categoryName: name, rows: [] }
      groupMap.set(name, g)
      groups.push(g)
    }
    groupMap.get(name)!.rows.push(row)
  }
  return groups
})

const hiddenCount = computed(() => {
  const hiddenIds = selectedMerchantId.value
    ? getHiddenProductIds(selectedMerchantId.value)
    : new Set<number>()
  return historyRows.value.filter(r => {
    const pid = getRowProductId(r)
    return pid && hiddenIds.has(pid)
  }).length
})

// --- 单位加载 ---
const loadUnits = async () => {
  try {
    const res = await api.get('/units/', { params: { is_common: true } })
    const items = Array.isArray(res) ? res : ((res as any).items || [])
    unitOptions.value = items.map((u: any) => ({
      title: `${u.name} (${u.abbreviation})`,
      value: u.abbreviation,
    }))
  } catch {
    unitOptions.value = [
      { title: '斤 (斤)', value: '斤' },
      { title: '个 (个)', value: '个' },
    ]
  }
}

// --- 商家加载 ---
const loadMerchants = async () => {
  try {
    const res = await api.get('/merchants', { params: { limit: 100 } })
    merchants.value = (res as any).items || []
  } catch {
    merchants.value = []
  }
}

// --- 商家切换 -> 加载历史商品 ---
const onMerchantChange = async (val: number | null) => {
  historyRows.value = []
  if (!val) return
  loading.value = true
  try {
    const res = await api.get(`/merchants/${val}/product-prices`, {
      params: { skip: 0, limit: 200 },
    })
    const items = (res as any).items || (res as any[]) || []
    // 后端已按 category sort_order 排序；前端在组内按拼音/字母顺序重排
    items.sort((a: any, b: any) => {
      const aScore = a.custom_sort_score
      const bScore = b.custom_sort_score
      // 有分数的排前面，没分数的排后面
      if (aScore != null && bScore == null) return -1
      if (aScore == null && bScore != null) return 1
      if (aScore != null && bScore != null) return aScore - bScore
      // 都没分数 → 默认分类 > 拼音
      const catCmp = (a.category_sort_order ?? 999999) - (b.category_sort_order ?? 999999)
      if (catCmp !== 0) return catCmp
      return zhCollator.compare(String(a.product_name ?? ''), String(b.product_name ?? ''))
    })
    historyRows.value = items.map((item: any) => ({
      productId: item.product_id,
      productName: item.product_name,
      price: '',
      quantity: 1,
      unit: '斤',
      isEditingQuantity: false,
      isNew: false,
      categoryId: item.category_id ?? null,
      categoryName: item.category_display_name ?? '其他',
    }))
  } catch {
    historyRows.value = []
    showSnackbar('加载历史商品失败，请重试', 'error')
  } finally {
    loading.value = false
  }
}

// --- 新行操作 ---
function addNewRow() {
  const newRow: FillRow = {
    productId: null,
    productName: '',
    price: '',
    quantity: 1,
    unit: '斤',
    isEditingQuantity: false,
    isNew: true,
    searchText: '',
    loading: false,
    categoryId: null,
    categoryName: '',
  }
  newRows.value.push(newRow)
}

function removeNewRow(index: number) {
  if (searchDebounceTimers[index]) {
    clearTimeout(searchDebounceTimers[index])
    delete searchDebounceTimers[index]
  }
  newRows.value.splice(index, 1)
  // 移位 suggestions
  const shiftedSuggestions: Record<number, any[]> = {}
  const keys = Object.keys(newRowSuggestions.value).map(Number).sort((a, b) => a - b)
  for (const k of keys) {
    if (k > index) {
      shiftedSuggestions[k - 1] = newRowSuggestions.value[k]
    } else if (k < index) {
      shiftedSuggestions[k] = newRowSuggestions.value[k]
    }
  }
  newRowSuggestions.value = shiftedSuggestions
  // 同样移位 timers
  const shiftedTimers: Record<number, ReturnType<typeof setTimeout>> = {}
  for (const k of Object.keys(searchDebounceTimers).map(Number).sort((a, b) => a - b)) {
    if (k > index) {
      shiftedTimers[k - 1] = searchDebounceTimers[k]
    } else if (k < index) {
      shiftedTimers[k] = searchDebounceTimers[k]
    }
  }
  for (const k of Object.keys(searchDebounceTimers)) {
    delete searchDebounceTimers[Number(k)]
  }
  Object.assign(searchDebounceTimers, shiftedTimers)
}

const onNewRowSearch = (index: number, query: string) => {
  if (searchDebounceTimers[index]) {
    clearTimeout(searchDebounceTimers[index])
  }
  searchDebounceTimers[index] = setTimeout(async () => {
    const row = newRows.value[index]
    if (!row) return
    if (!query || query.length < 1) {
      newRowSuggestions.value[index] = []
      return
    }
    row.loading = true
    try {
      const response: any[] = await api.get('/products/autocomplete', {
        params: { q: query, limit: 20 },
      })
      const items = response || []
      newRowSuggestions.value[index] = items.filter(
        (item: any) => !existingProductIds.value.has(item.id)
      )
    } catch {
      newRowSuggestions.value[index] = []
    } finally {
      const curRow = newRows.value[index]
      if (curRow) curRow.loading = false
    }
  }, 300)
}

onUnmounted(() => {
  for (const k of Object.keys(searchDebounceTimers)) {
    clearTimeout(searchDebounceTimers[Number(k)])
  }
})

// --- 保存 ---
const saveAll = async () => {
  if (!selectedMerchantId.value) {
    showSnackbar('请先选择商家', 'warning')
    return
  }

  const rowsToSave = [
    ...visibleHistoryRows.value.filter(r => r.price && parseFloat(r.price) > 0),
    ...newRows.value.filter(r => r.price && parseFloat(r.price) > 0),
  ]

  for (const row of rowsToSave) {
    if (row.isNew && !getRowProductId(row)) {
      showSnackbar(`请先为商品选择或输入名称`, 'warning')
      return
    }
  }

  if (rowsToSave.length === 0) {
    showSnackbar('没有需要保存的价格记录', 'info')
    return
  }

  saving.value = true
  saveProgress.value = { current: 0, total: rowsToSave.length }

  const payloads = rowsToSave.map(row => {
    const pid = getRowProductId(row)
    const payload: Record<string, any> = {
      price: parseFloat(row.price),
      original_quantity: row.quantity,
      original_unit: row.unit,
      merchant_id: selectedMerchantId.value,
      record_type: 'price',
    }
    if (pid) {
      payload.product_id = pid
    } else if (row.searchText) {
      payload.product_name = row.searchText
    }
    return { row, pid, payload }
  })

  // 并发提交（限制并发数避免后端压力）
  const CONCURRENCY = 5
  const results: Array<{ fillRow: FillRow; pid: number | null; ok: boolean }> = []
  for (let i = 0; i < payloads.length; i += CONCURRENCY) {
    const batch = payloads.slice(i, i + CONCURRENCY)
    const settled = await Promise.allSettled(
      batch.map(async (p) => {
        await api.post('/products', p.payload)
        return p
      }),
    )
    for (let j = 0; j < settled.length; j++) {
      const s = settled[j]
      const orig = batch[j]
      if (s.status === 'fulfilled') {
        results.push({ fillRow: orig.row, pid: orig.pid, ok: true })
      } else {
        results.push({ fillRow: orig.row, pid: orig.pid, ok: false })
      }
      saveProgress.value!.current++
    }
  }

  saving.value = false
  saveProgress.value = null

  let successCount = 0
  let failCount = 0
  let newSavedCount = 0
  const savedProductIds: number[] = []

  for (const r of results) {
    if (r.ok) {
      successCount++
      if (!r.fillRow.isNew && r.pid) {
        savedProductIds.push(r.pid)
      } else if (r.fillRow.isNew) {
        newSavedCount++
      }
    } else {
      failCount++
    }
  }

  if (savedProductIds.length > 0) {
    addHiddenItems(selectedMerchantId.value, savedProductIds)
  }

  // 保存排序记录（仅记录有 product_id 的历史商品）
  if (savedProductIds.length > 0 && selectedMerchantId.value) {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
    const sessionDate = new Date().toLocaleDateString('en-CA', { timeZone })
    try {
      await api.post(`/merchants/${selectedMerchantId.value}/product-orders`, {
        product_ids: savedProductIds,
        session_date: sessionDate,
      })
    } catch (e: any) {
      console.warn('[quick-fill] 记录排序失败:', e?.response?.data || e?.message || e)
    }
  }

  if (successCount > 0) {
    await onMerchantChange(selectedMerchantId.value)
  }

  newRows.value = []

  if (failCount === 0) {
    const newHint = newSavedCount > 0 ? `，新增 ${newSavedCount} 个商品已加入历史列表` : ''
    showSnackbar(`成功保存 ${successCount} 条价格记录${newHint}`, 'success')
  } else {
    showSnackbar(`保存完成：${successCount} 成功，${failCount} 失败`, 'warning')
  }
}

async function onPasteImported(savedProductIds?: number[]) {
  if (selectedMerchantId.value && savedProductIds && savedProductIds.length > 0) {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
    const sessionDate = new Date().toLocaleDateString('en-CA', { timeZone })
    try {
      await api.post(`/merchants/${selectedMerchantId.value}/product-orders`, {
        product_ids: savedProductIds,
        session_date: sessionDate,
      })
    } catch (e: any) {
      console.warn('[quick-fill] 记录粘贴导入排序失败:', e?.response?.data || e?.message || e)
    }
  }
  await onMerchantChange(selectedMerchantId.value)
}

onMounted(() => {
  loadMerchants()
  loadUnits()
})
</script>

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
.fill-row__product-search {
  width: 120px;
  flex-shrink: 0;
}
.fill-row__product-search :deep(input) { font-size: 16px; }
.fill-row__inputs {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: flex-end;
}
.fill-row__price { max-width: 100px; min-width: 80px; }
.fill-row__price :deep(input) { font-size: 16px; }
.fill-row__sep { color: rgba(0,0,0,0.38); font-size: 14px; flex-shrink: 0; }
.fill-row__qty-input { max-width: 60px; min-width: 50px; }
.fill-row__qty-input :deep(input) { font-size: 16px; text-align: center; }
.fill-row__edit-text {
  cursor: pointer; font-size: 14px; padding: 6px 10px;
  border-radius: 4px; min-width: 24px; text-align: center;
  display: inline-block; user-select: none;
}
.fill-row__edit-text:hover { background: rgba(0,0,0,0.06); }
.fill-list { background: transparent; }
/* 解除 v-list-item 的 overflow 限制，避免 autocomplete 下拉被裁剪 */
.fill-list :deep(.v-list-item) { overflow: visible; }
.fill-list :deep(.v-list-item__content) { overflow: visible; }
/* attach 模式下下拉列表跟随定位 */
.fill-row__product-search :deep(.v-select__selection) { overflow: visible; }
</style>
