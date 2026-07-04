<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

const entityType = computed(() => props.proposal.entity_type)
const isIngredient = computed(() => entityType.value === 'ingredient')
const snap = computed(() => props.proposal.snapshot || {})
const payload = computed(() => props.proposal.payload || {})
const preview = computed(() => payload.value.preview || {})

// 来源列表：优先 snapshot（已审批），回退 payload.preview（待审）
const sources = computed<string[]>(() => {
  const s = snap.value.sources as any[] | undefined
  if (s?.length) return s.map((x: any) => x.name || `#${x.id}`)
  const ps = preview.value.sources as any[] | undefined
  if (ps?.length) return ps.map((x: any) => x.name || `#${x.id}`)
  return []
})

const sourceCount = computed(() => sources.value.length || preview.value.source_count || 0)

// 快照里取的优先，pending 时从 payload 取
const targetName = computed(() =>
  snap.value.target_name || preview.value.target_name || `#${payload.value.target_id}`
)

const impactCards = computed(() => {
  if (isIngredient.value) {
    const ri = (snap.value.recipe_ingredients as any[])?.length ?? preview.value.recipe_ingredients_count ?? 0
    const pl = (snap.value.product_links as any[])?.length ?? preview.value.product_links_count ?? 0
    const hi = (snap.value.hierarchies as any[])?.length ?? preview.value.hierarchies_count ?? 0
    const nm = (snap.value.nutrition_mappings as any[])?.length ?? preview.value.nutrition_mappings_count ?? 0
    return [
      { label: '菜谱引用', count: ri },
      { label: '商品关联', count: pl },
      { label: '层级关系', count: hi },
      { label: '营养映射', count: nm },
    ]
  }
  const pr = (snap.value.product_records as any[])?.length ?? preview.value.product_records_count ?? 0
  const fav = (snap.value.favorites as any[])?.length ?? preview.value.favorites_count ?? 0
  return [
    { label: '价格记录', count: pr },
    { label: '收藏', count: fav },
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
    </div>

    <!-- source handling note -->
    <v-alert type="info" variant="tonal" density="compact" class="mb-3">
      <template v-if="sources.length">
        源 <strong>{{ sourceCount }}</strong> 个（{{ sources.join('、') }}）将软停用（保留名称追溯），所有引用迁至目标「<strong>{{ targetName }}</strong>」。
      </template>
      <template v-else>
        无源食材信息（待审批执行后更新）。
      </template>
    </v-alert>

    <!-- impact counts -->
    <div class="text-subtitle-2 mb-2">影响范围</div>
    <v-row dense class="mb-2">
      <v-col v-for="card in impactCards" :key="card.label" cols="6" sm="3">
        <v-card variant="outlined" density="compact" class="text-center pa-2">
          <div class="text-h6">{{ card.count }}</div>
          <div class="text-caption text-medium-emphasis">{{ card.label }}</div>
        </v-card>
      </v-col>
    </v-row>

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
