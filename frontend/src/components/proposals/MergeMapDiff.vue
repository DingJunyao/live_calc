<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Proposal } from '@/api/proposals'
import { api } from '@/api'

const props = defineProps<{ proposal: Proposal }>()

const entityType = computed(() => props.proposal.entity_type)
const isIngredient = computed(() => entityType.value === 'ingredient')
const snap = computed(() => props.proposal.snapshot || {})
const payload = computed(() => props.proposal.payload || {})

// ── 自动回填（snapshot 无数据时调用预览 API） ──
const previewBackfill = ref<Record<string, any> | null>(null)
const loadingPreview = ref(false)

async function fetchPreview() {
  // 已有 snapshot 数据 → 不重复加载
  if (isIngredient.value) {
    if (snap.value.recipe_ingredients?.length || snap.value.product_links?.length) return
  } else {
    if (snap.value.product_records?.length) return
  }
  loadingPreview.value = true
  try {
    const res = await api.post('/proposals/preview', {
      entity_type: props.proposal.entity_type,
      entity_id: props.proposal.entity_id,
      action: props.proposal.action,
      payload: props.proposal.payload,
    })
    previewBackfill.value = res
  } catch { /* ignore */ }
  finally { loadingPreview.value = false }
}

onMounted(fetchPreview)

// ── 数据源 ──
// 优先 snapshot，其次预填 payload.preview（旧前端提交式），其次自动回填
function pv(key: string): any {
  const pb = previewBackfill.value
  const pp = (payload.value.preview as Record<string, any>) || {}
  return pb?.[key] ?? pp?.[key]
}

// 来源列表
const sources = computed<string[]>(() => {
  const s = snap.value.sources as any[] | undefined
  if (s?.length) return s.map((x: any) => x.name || `#${x.id}`)
  const ps = pv('sources') as any[] | undefined
  if (ps?.length) return ps.map((x: any) => x.name || `#${x.id}`)
  return []
})

const sourceCount = computed(() => sources.value.length || pv('source_count') || 0)
const targetName = computed(() =>
  snap.value.target_name || pv('target_name') || `#${payload.value.target_id}`
)

/** 预览 API 字段名与影响范围标签的映射。
 *  食材合并预览返 affected_recipe_ingredients（数字），
 *  snapshot 存 recipe_ingredients（数组），统一取数。 */
const INGREDIENT_PREVIEW_KEYS: Record<string, string> = {
  recipe_ingredients: 'affected_recipe_ingredients',
  product_links: 'affected_product_links',
  hierarchies: 'affected_hierarchies',
  nutrition_mappings: 'affected_nutrition_mappings',
}
const MERCHANT_PREVIEW_KEYS: Record<string, string> = {
  product_records: 'affected_price_records',
  favorites: 'affected_favorites',
}

/** 预制食材合并 5 个影响维度标签，按此顺序渲染。 */
const INGREDIENT_CARD_LABELS = [
  { key: 'recipe_ingredients', label: '菜谱引用' },
  { key: 'product_links', label: '商品关联' },
  { key: 'hierarchies', label: '层级关系' },
  { key: 'nutrition_mappings', label: '营养映射' },
  { key: 'price_records', label: '价格记录' },
]

function snapCount(key: string): number {
  // 优先后端实时补充的平字段（如 recipe_ingredients_count）
  const flat = snap.value[`${key}_count`] as number | undefined
  if (flat != null) return flat
  // 其次 snapshot 数组长度（build_snapshot/apply 存了完整数组）
  const arr = snap.value[key] as any[] | undefined
  if (arr?.length) return arr.length
  // 最后回退预览 API
  const ings = isIngredient.value ? INGREDIENT_PREVIEW_KEYS : MERCHANT_PREVIEW_KEYS
  const pvKey = ings[key]
  return pvKey ? (pv(pvKey) as number) ?? 0 : 0
}

function ingredientPriceCount(): number {
  // 后端实时补充的平字段
  const flat = snap.value.affected_price_records as number | undefined
  if (flat != null) return flat
  // 预览 API 回填
  return (pv('affected_price_records') as number) ?? 0
}

const impactCards = computed(() => {
  if (isIngredient.value) {
    return INGREDIENT_CARD_LABELS.map(c => ({
      label: c.label,
      count: c.key === 'price_records'
        ? ingredientPriceCount()
        : snapCount(c.key),
    }))
  }
  return [
    { label: '价格记录', count: snapCount('product_records') },
    { label: '收藏', count: snapCount('favorites') },
  ]
})

interface DetailRow { category: string; name: string }
const details = computed<DetailRow[]>(() => {
  const out: DetailRow[] = []
  if (isIngredient.value) {
    for (const r of (snap.value.recipe_ingredients || [])) {
      out.push({ category: '菜谱', name: r.recipe_name || `菜谱 #${r.recipe_id}` })
    }
    for (const l of (snap.value.product_links || [])) {
      out.push({ category: '商品', name: l.product_name || `商品 #${l.product_id}` })
    }
  } else {
    for (const r of (snap.value.product_records || [])) {
      out.push({ category: '价格记录', name: r.product_name || `记录 #${r.id}` })
    }
  }
  return out
})

const DETAIL_PREVIEW = 5
const showAllDetails = ref(false)
const visibleDetails = computed(() =>
  showAllDetails.value ? details.value : details.value.slice(0, DETAIL_PREVIEW))
</script>

<template>
  <div>
    <!-- merge direction -->
    <div class="d-flex align-center flex-wrap mb-3" style="gap: 4px">
      <div class="d-flex flex-wrap ga-1">
        <v-chip v-for="(s, i) in sources" :key="i" size="small" color="error" variant="tonal">
          <span class="text-decoration-line-through">{{ s }}</span>
        </v-chip>
      </div>
      <v-icon class="mx-2" size="small">mdi-arrow-right</v-icon>
      <v-chip size="small" color="success" variant="flat">{{ targetName }}</v-chip>
      <v-progress-circular v-if="loadingPreview" indeterminate size="14" width="2" class="ms-1" />
    </div>

    <!-- source handling note -->
    <v-alert type="info" variant="tonal" density="compact" class="mb-3">
      <template v-if="sources.length">
        源 <strong>{{ sourceCount }}</strong> 个（{{ sources.join('、') }}）将软停用（保留名称追溯），所有引用迁至目标「<strong>{{ targetName }}</strong>」。
      </template>
      <template v-else-if="loadingPreview">
        正在加载预览数据…
      </template>
      <template v-else>
        无源食材信息（待审批执行后更新）。
      </template>
    </v-alert>

    <!-- impact counts -->
    <div class="text-subtitle-2 mb-2">影响范围</div>
    <div class="d-flex mb-2" style="gap: 4px">
      <div v-for="card in impactCards" :key="card.label" style="flex: 1; min-width: 0">
        <v-card variant="outlined" density="compact" class="text-center pa-2">
          <div class="text-h6">{{ card.count }}</div>
          <div class="text-caption text-medium-emphasis">{{ card.label }}</div>
        </v-card>
      </div>
    </div>

    <!-- migration details (default expanded) -->
    <div v-if="details.length" class="text-subtitle-2 mb-1">迁移明细</div>
    <v-list v-if="details.length" density="compact" class="bg-transparent">
      <v-list-item v-for="(d, i) in visibleDetails" :key="i" class="px-0">
        <template #prepend>
          <v-chip size="x-small" variant="outlined">{{ d.category }}</v-chip>
        </template>
        <v-list-item-title class="text-body-2">{{ d.name }}</v-list-item-title>
      </v-list-item>
      <v-list-item v-if="details.length > DETAIL_PREVIEW" class="px-0">
        <v-btn variant="text" size="small" @click="showAllDetails = !showAllDetails">
          {{ showAllDetails ? '收起' : `展开剩余 ${details.length - DETAIL_PREVIEW} 项` }}
        </v-btn>
      </v-list-item>
    </v-list>
  </div>
</template>
