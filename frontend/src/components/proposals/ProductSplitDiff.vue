<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Proposal } from '@/api/proposals'
import { api } from '@/api'

const props = defineProps<{ proposal: Proposal }>()

const snap = computed(() => props.proposal.snapshot || {})
const payload = computed(() => props.proposal.payload || {})

const recordsCountFallback = ref<number | null>(null)
const loadingRecords = ref(false)

function extractLabelName(label: string | null): string {
  if (!label) return ''
  const m = label.match(/「(.+?)」/)
  return m ? m[1] : label
}

const productName = computed(() =>
  snap.value.product_name || extractLabelName(props.proposal.entity_label) || '?',
)
const currentIngredient = computed(() => snap.value.current_ingredient_name || '原原料')
const newName = computed(() =>
  snap.value.new_ingredient_name || payload.value.new_name || extractLabelName(props.proposal.entity_label) || '新原料',
)
const priceCount = computed(() => snap.value.affected_price_records_count ?? recordsCountFallback.value ?? 0)

async function loadBackfill() {
  const sourceId = props.proposal.entity_id
  if (!sourceId || snap.value.affected_price_records_count != null) return
  loadingRecords.value = true
  try {
    const res = await api.get('/products', { params: { product_id: sourceId, limit: 1 } })
    if (res?.total != null) recordsCountFallback.value = res.total
  } catch { /* ignore */ }
  finally { loadingRecords.value = false }
}

onMounted(loadBackfill)
</script>

<template>
  <div class="pa-2">
    <v-alert type="info" variant="tonal" density="compact" class="mb-2">
      <div class="text-body-2">
        将商品<strong>「{{ productName }}」</strong>
        从原料<strong>「{{ currentIngredient }}」</strong>中拆出，
        以「<strong>{{ newName }}</strong>」创建新原料。
      </div>
    </v-alert>
    <div class="d-flex align-center ga-2 mt-1">
      <v-chip size="x-small" color="info" variant="tonal" label>
        <template v-if="loadingRecords">
          <v-progress-circular indeterminate size="12" width="2" class="me-1" />
          查价格记录…
        </template>
        <template v-else>
          影响 <strong>{{ priceCount }}</strong> 条价格记录
        </template>
      </v-chip>
      <span class="text-caption text-medium-emphasis">（营养数据将合并到新原料）</span>
    </div>
  </div>
</template>
