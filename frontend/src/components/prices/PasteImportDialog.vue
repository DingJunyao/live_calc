<template>
  <v-dialog :model-value="modelValue" max-width="720" persistent @update:model-value="emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="d-flex align-center">
        粘贴导入价格
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="emit('update:modelValue', false)" />
      </v-card-title>

      <v-card-text>
        <v-text-field
          v-model="dateTime"
          label="记录时间"
          type="datetime-local"
          variant="outlined"
          density="compact"
          class="mb-3"
          hide-details
        />

        <v-textarea
          v-model="rawText"
          label="粘贴价格文本（每行一条，格式：名称 价格[/单位]）"
          variant="outlined"
          rows="6"
          :placeholder="`芹菜 1.88\n芽菇 4/袋\n嫩豆腐 5.18/kg\n土豆粉 2.5/200g`"
          hide-details
          class="mb-3"
        />

        <div class="d-flex align-center mb-3">
          <v-btn color="primary" variant="tonal" prepend-icon="mdi-text-search" :loading="parsing" @click="doParse">
            解析并匹配
          </v-btn>
          <span v-if="summaryText" class="text-caption text-medium-emphasis ml-3">{{ summaryText }}</span>
        </div>

        <v-table v-if="rows.length > 0" density="compact" class="paste-preview-table">
          <thead>
            <tr>
              <th style="width: 36px"></th>
              <th>商品</th>
              <th style="width: 90px">价格</th>
              <th style="width: 70px">数量</th>
              <th style="width: 70px">单位</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in rows" :key="i">
              <td class="text-center">
                <v-icon v-if="row.status === 'matched'" color="success" size="small">mdi-check-circle</v-icon>
                <v-icon v-else-if="row.status === 'unmatched'" color="warning" size="small">mdi-alert-circle</v-icon>
                <v-icon v-else color="error" size="small">mdi-close-circle</v-icon>
              </td>
              <td>
                <template v-if="row.status === 'invalid'">{{ row.name || '（' + row.error + '）' }}</template>
                <template v-else>
                  <!-- 未展开：可点击商品名 -->
                  <span v-if="!row.editing" class="paste-editable" @click="openEditor(row)">
                    {{ row.name }}<v-icon size="x-small" class="ml-1">mdi-chevron-down</v-icon>
                  </span>
                  <!-- 展开：内联搜索面板 -->
                  <div v-else class="paste-inline-panel">
                    <v-autocomplete
                      v-model:search="row.productSearch"
                      :items="row.suggestions"
                      item-title="name"
                      item-value="id"
                      placeholder="搜索关联已有商品…"
                      variant="outlined"
                      density="compact"
                      hide-details
                      hide-no-data
                      hide-selected
                      return-object
                      :custom-filter="() => true"
                      class="paste-inline-field"
                      @update:search="onProductSearch(row, $event)"
                      @update:model-value="(v: any) => { if (v) chooseExisting(row, v) }"
                    />
                    <v-autocomplete
                      v-model:search="row.ingredientSearch"
                      :items="row.ingredientSuggestions"
                      item-title="name"
                      item-value="id"
                      placeholder="或搜索挂靠原料…"
                      variant="outlined"
                      density="compact"
                      hide-details
                      hide-no-data
                      hide-selected
                      return-object
                      :custom-filter="() => true"
                      class="paste-inline-field"
                      @update:search="onIngredientSearch(row, $event)"
                      @update:model-value="(v: any) => { if (v) chooseAttach(row, v) }"
                    />
                    <div class="d-flex align-center ga-2 mt-1">
                      <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-plus" @click="chooseNewSame(row)">
                        创建同名原料 + 商品
                      </v-btn>
                      <v-btn size="small" variant="text" @click="cancelEdit(row)">取消</v-btn>
                    </div>
                  </div>
                </template>
              </td>
              <td>{{ row.price ?? '—' }}</td>
              <td>{{ row.quantity }}</td>
              <td>{{ row.unit }}</td>
            </tr>
          </tbody>
        </v-table>

        <div v-if="importableCount > 0" class="mt-3">
          <v-progress-linear
            v-if="importing"
            :model-value="progressPct"
            height="8"
            color="primary"
            class="mb-2"
          />
          <div v-if="importing && progressText" class="text-caption text-medium-emphasis mb-2">{{ progressText }}</div>
          <v-btn color="primary" :loading="importing" :disabled="importing" prepend-icon="mdi-database-import" @click="doImport">
            全部导入（{{ importableCount }} 条）
          </v-btn>
        </div>
      </v-card-text>

      <v-alert v-if="result" :type="result.fail === 0 ? 'success' : 'warning'" variant="tonal" class="mx-4 mb-2">
        导入完成：成功 {{ result.success }} 条，失败 {{ result.fail }} 条
        <div v-if="result.failures.length" class="text-caption mt-1">
          失败项目：{{ result.failures.map(f => `${f.name}（${f.reason}）`).join('、') }}
        </div>
      </v-alert>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">关闭</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { api } from '@/api/client'
import { getLocalDateTimeString } from '@/utils/timezone'
import { getErrorMessage } from '@/utils/errorHandler'
import { parsePasteText, type ParsedPriceLine } from '@/utils/pastePriceParser'

interface ImportRow extends ParsedPriceLine {
  status: 'matched' | 'unmatched' | 'invalid'
  productId: number | null
  ingredientId: number | null
  mode: 'existing' | 'new_same' | 'new_attach'
  editing: boolean
  productSearch: string
  ingredientSearch: string
  suggestions: { id: number; name: string }[]
  ingredientSuggestions: { id: number; name: string }[]
}

interface ImportResult {
  success: number
  fail: number
  failures: { name: string; reason: string }[]
}

const props = defineProps<{
  modelValue: boolean
  merchantId: number | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'imported', productIds?: number[]): void
}>()

const dateTime = ref(getLocalDateTimeString())
const rawText = ref('')
const parsing = ref(false)
const importing = ref(false)
const rows = ref<ImportRow[]>([])
const result = ref<ImportResult | null>(null)
const progress = ref({ current: 0, total: 0 })

// 模块级 timer（WeakMap 以 row 为 key，随 row 回收自动清理，避免内存泄漏）
const productTimers = new WeakMap<ImportRow, ReturnType<typeof setTimeout>>()
const ingredientTimers = new WeakMap<ImportRow, ReturnType<typeof setTimeout>>()

const summaryText = computed(() => {
  if (rows.value.length === 0) return ''
  const matched = rows.value.filter(r => r.status === 'matched').length
  const unmatched = rows.value.filter(r => r.status === 'unmatched').length
  const invalid = rows.value.filter(r => r.status === 'invalid').length
  return `已匹配 ${matched} · 待处理 ${unmatched} · 无法识别 ${invalid}`
})

const importableRows = computed(() => rows.value.filter(r => r.status === 'matched' && r.ok))
const importableCount = computed(() => importableRows.value.length)
const progressPct = computed(() => {
  if (progress.value.total === 0) return 0
  return Math.round((progress.value.current / progress.value.total) * 100)
})
const progressText = computed(() =>
  progress.value.total > 0 ? `正在导入 ${progress.value.current}/${progress.value.total}…` : ''
)

watch(() => props.modelValue, (val) => {
  if (val) {
    dateTime.value = getLocalDateTimeString()
    rawText.value = ''
    rows.value = []
    result.value = null
  }
})

// 解析 + 自动精确匹配
async function doParse() {
  result.value = null
  parsing.value = true
  try {
    // 清理旧行的搜索 timer，避免悬挂请求写入已被替换的旧 row
    for (const r of rows.value) {
      const pt = productTimers.get(r)
      if (pt) clearTimeout(pt)
      const it = ingredientTimers.get(r)
      if (it) clearTimeout(it)
    }
    const parsed = parsePasteText(rawText.value)
    rows.value = parsed.map(p => ({
      ...p,
      status: p.ok ? 'unmatched' : 'invalid',
      productId: null,
      ingredientId: null,
      mode: 'new_same',
      editing: false,
      productSearch: '',
      ingredientSearch: '',
      suggestions: [],
      ingredientSuggestions: [],
    }))
    const okRows = rows.value.filter(r => r.ok)
    await Promise.all(okRows.map(r => tryAutoMatch(r)))
  } finally {
    parsing.value = false
  }
}

// 自动匹配：按优先级识别商品主名、原料主名、商品别名、原料别名
// 命中原料时解析最合适的商品（唯一商品 > 同名商品 > 最早创建）
async function tryAutoMatch(row: ImportRow) {
  try {
    const list: any[] = await api.get('/products/autocomplete', { params: { q: row.name, limit: 20 } })
    if (!list || list.length === 0) return

    // Priority 1: 商品主名精确匹配
    const nameMatch = list.find((it: any) => it.match_type === 'name' && it.name === row.name)
    if (nameMatch) {
      setAutoMatched(row, nameMatch.id)
      return
    }

    // Priority 2: 原料主名匹配 → 解析最佳商品
    const ingNameMatch = list.find((it: any) => it.match_type === 'ingredient_name')
    if (ingNameMatch && ingNameMatch.ingredient_id) {
      const bestId = resolveIngredientProduct(list, ingNameMatch.ingredient_id, ingNameMatch.ingredient_name)
      if (bestId) {
        setAutoMatched(row, bestId)
        return
      }
    }

    // Priority 3: 商品别名匹配
    // 后端 autocomplete 按名字子串判定 name，子串命中时（如「青茄」→「青茄子」）
    // 会被标成 name 而非 alias，故前端同时用返回的 aliases 数组独立判一次
    const aliasMatch = list.find((it: any) =>
      it.match_type === 'alias' ||
      (Array.isArray(it.aliases) && it.aliases.includes(row.name))
    )
    if (aliasMatch) {
      setAutoMatched(row, aliasMatch.id)
      return
    }

    // Priority 4: 原料别名匹配 → 解析最佳商品
    const ingAliasMatch = list.find((it: any) =>
      it.match_type === 'ingredient_alias' ||
      (Array.isArray(it.ingredient_aliases) && it.ingredient_aliases.includes(row.name))
    )
    if (ingAliasMatch && ingAliasMatch.ingredient_id) {
      const bestId = resolveIngredientProduct(list, ingAliasMatch.ingredient_id, ingAliasMatch.ingredient_name)
      if (bestId) {
        setAutoMatched(row, bestId)
        return
      }
    }
  } catch {
    /* 保持 unmatched，用户手动处理 */
  }
}

// 原料匹配时解析最佳商品：仅一个 → 同名 → 最早创建
function resolveIngredientProduct(list: any[], ingredientId: number, ingredientName: string): number | null {
  const products = list.filter((it: any) => it.ingredient_id === ingredientId)
  if (products.length === 0) return null

  // 实际只有唯一商品
  const totalCount = products[0]?.ingredient_product_count ?? products.length
  if (totalCount === 1) return products[0].id

  // 存在与原料同名的商品
  const sameName = products.find((p: any) => p.name === ingredientName)
  if (sameName) return sameName.id

  // 取最早创建的商品
  const sorted = [...products].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
  return sorted[0]?.id ?? null
}

function setAutoMatched(row: ImportRow, productId: number) {
  row.productId = productId
  row.status = 'matched'
  row.mode = 'existing'
}

// 展开内联面板：预填搜索词为商品名，触发首次搜索
function openEditor(row: ImportRow) {
  row.editing = true
  if (!row.productSearch) {
    row.productSearch = row.name
    onProductSearch(row, row.name)
  }
}

// 取消编辑：清理该行已排队的搜索 timer
function cancelEdit(row: ImportRow) {
  const pt = productTimers.get(row)
  if (pt) clearTimeout(pt)
  const it = ingredientTimers.get(row)
  if (it) clearTimeout(it)
  row.editing = false
}

// 商品搜索（debounce 300ms）
function onProductSearch(row: ImportRow, query: string) {
  row.productSearch = query
  const prev = productTimers.get(row)
  if (prev) clearTimeout(prev)
  const timer = setTimeout(async () => {
    if (!query || query.length < 1) { row.suggestions = []; return }
    try {
      const list: any[] = await api.get('/products/autocomplete', { params: { q: query, limit: 20 } })
      row.suggestions = (list || []).map((it: any) => ({ id: it.id, name: it.name }))
    } catch {
      row.suggestions = []
    }
  }, 300)
  productTimers.set(row, timer)
}

// 原料搜索（debounce 300ms）
function onIngredientSearch(row: ImportRow, query: string) {
  row.ingredientSearch = query
  const prev = ingredientTimers.get(row)
  if (prev) clearTimeout(prev)
  const timer = setTimeout(async () => {
    if (!query || query.length < 1) { row.ingredientSuggestions = []; return }
    try {
      const res: any = await api.get('/ingredients', { params: { q: query, limit: 20 } })
      row.ingredientSuggestions = ((res.items || []) as any[]).map((it: any) => ({ id: it.id, name: it.name }))
    } catch {
      row.ingredientSuggestions = []
    }
  }, 300)
  ingredientTimers.set(row, timer)
}

function chooseExisting(row: ImportRow, opt: { id: number; name: string }) {
  row.productId = opt.id
  row.ingredientId = null
  row.mode = 'existing'
  row.status = 'matched'
  row.editing = false
}

function chooseNewSame(row: ImportRow) {
  row.productId = null
  row.ingredientId = null
  row.mode = 'new_same'
  row.status = 'matched'
  row.editing = false
}

function chooseAttach(row: ImportRow, ing: { id: number; name: string }) {
  row.productId = null
  row.ingredientId = ing.id
  row.mode = 'new_attach'
  row.status = 'matched'
  row.editing = false
}

// 并发导入（并发数 5）
async function doImport() {
  if (!props.merchantId) return
  if (importableRows.value.length === 0) return

  importing.value = true
  result.value = null
  const targets = importableRows.value
  const savedProductIds: (number | null)[] = new Array(targets.length).fill(null)
  progress.value = { current: 0, total: targets.length }

  const recordedAt = dateTime.value ? new Date(dateTime.value).toISOString() : undefined

  const payloads = targets.map(row => {
    const payload: Record<string, any> = {
      price: row.price,
      original_quantity: row.quantity,
      original_unit: row.unit,
      merchant_id: props.merchantId,
      record_type: 'price',
    }
    if (recordedAt) payload.recorded_at = recordedAt
    if (row.mode === 'existing' && row.productId) {
      payload.product_id = row.productId
    } else {
      payload.product_name = row.name
      if (row.mode === 'new_attach' && row.ingredientId) {
        payload.ingredient_id = row.ingredientId
      }
    }
    return { row, payload }
  })

  const CONCURRENCY = 5
  let success = 0
  const failures: { name: string; reason: string }[] = []

  for (let i = 0; i < payloads.length; i += CONCURRENCY) {
    const batch = payloads.slice(i, i + CONCURRENCY)
    const settled = await Promise.allSettled(
      batch.map(async p => {
        const res = await api.post('/products', p.payload)
        // 将导入的商品名添加为别名（existing→已有商品ID/new_attach→从响应取新建商品ID）
        const aliasProductId: number | null =
          p.row.mode === 'existing' ? p.row.productId
          : p.row.mode === 'new_attach' ? res?.data?.product_id ?? null
          : null
        if (aliasProductId) {
          try {
            await api.post(`/products/entity/${aliasProductId}/add-import-alias`, {
              name: p.row.name
            })
          } catch (e: any) {
            console.error('[paste-import] 添加别名失败:', e?.response?.status, e?.response?.data || e?.message || e)
          }
        }
        return res
      })
    )
    settled.forEach((s, j) => {
      const idx = i + j
      if (s.status === 'fulfilled') {
        success++
        const rowData = batch[j]
        if (rowData.row.mode === 'existing' && rowData.row.productId) {
          savedProductIds[idx] = rowData.row.productId
        } else if (rowData.row.mode === 'new_attach') {
          const res = (s as PromiseFulfilledResult<any>).value
          if (res?.data?.product_id) {
            savedProductIds[idx] = res.data.product_id
          }
        }
      } else {
        const reason = getErrorMessage((s as PromiseRejectedResult).reason, '导入失败')
        failures.push({ name: batch[j].row.name, reason })
      }
      progress.value.current++
    })
  }

  const validIds = savedProductIds.filter((id): id is number => id != null)
  emit('imported', validIds.length > 0 ? validIds : undefined)

  importing.value = false
  progress.value = { current: 0, total: 0 }
  result.value = { success, fail: failures.length, failures }

  if (failures.length === 0) {
    emit('update:modelValue', false)
  }
}
</script>

<style scoped>
.paste-preview-table :deep(th),
.paste-preview-table :deep(td) {
  padding: 4px 8px !important;
  font-size: 13px;
}
.paste-editable {
  cursor: pointer;
  border-radius: 4px;
  padding: 2px 4px;
}
.paste-editable:hover {
  background: rgba(0, 0, 0, 0.06);
}
.paste-inline-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0;
}
.paste-inline-field :deep(input) {
  font-size: 16px; /* 防 iOS 缩放 */
}
</style>
