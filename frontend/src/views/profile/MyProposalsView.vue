<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">我的提议</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" @click="loadList" />
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 待审提示 -->
    <v-alert
      v-if="pendingProposals.length > 0"
      type="info"
      variant="tonal"
      density="comfortable"
      class="mb-4"
    >
      您有 {{ pendingProposals.length }} 条提议待审核。
    </v-alert>

    <!-- 状态筛选 -->
    <v-card class="rounded-lg mb-4">
      <v-card-text class="d-flex flex-wrap align-center ga-3 py-3">
        <div class="text-subtitle-2 text-medium-emphasis me-2">状态：</div>
        <v-chip-group v-model="statusFilter" mandatory column>
          <v-chip
            v-for="opt in statusOptions"
            :key="opt.value"
            :value="opt.value"
            :color="opt.color"
            filter
            variant="tonal"
            size="small"
          >
            <v-icon start size="small">{{ opt.icon }}</v-icon>
            {{ opt.label }}
          </v-chip>
        </v-chip-group>
        <v-spacer />
        <div class="text-caption text-medium-emphasis">
          共 {{ proposals.length }} 条
        </div>
      </v-card-text>
    </v-card>

    <!-- 提议列表 -->
    <v-card class="rounded-lg">
      <v-data-table
        :headers="headers"
        :items="proposals"
        :loading="loading"
        item-value="id"
        hover
        density="comfortable"
        no-data-text="暂无提议"
      >
        <template #item.status="{ item }">
          <v-chip :color="statusColor(item.status)" size="small" variant="tonal">
            <v-icon start size="small">{{ statusIcon(item.status) }}</v-icon>
            {{ statusLabel(item.status) }}
          </v-chip>
        </template>

        <template #item.type="{ item }">
          <div class="d-flex flex-column">
            <span class="text-body-2 font-weight-medium">
              {{ entityTypeLabel(item.entity_type) }} · {{ actionLabel(item.action) }}
            </span>
            <span class="text-caption text-medium-emphasis">#{{ item.id }}</span>
          </div>
        </template>

        <template #item.summary="{ item }">
          <span class="text-body-2 text-medium-emphasis">
            {{ payloadSummary(item) }}
          </span>
        </template>

        <template #item.time="{ item }">
          <div class="text-caption">
            <div v-if="item.applied_at" class="text-success">
              生效：{{ formatToLocalDateTimeShort(item.applied_at) }}
            </div>
            <div v-else-if="item.reviewed_at" class="text-medium-emphasis">
              审核：{{ formatToLocalDateTimeShort(item.reviewed_at) }}
            </div>
            <div v-else class="text-warning">
              提交：{{ formatToLocalDateTimeShort(item.created_at) }}
            </div>
          </div>
        </template>

        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-eye-outline"
            size="small"
            variant="text"
            color="primary"
            @click="openDetail(item)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- 详情对话框 -->
    <v-dialog v-model="detailDialog" max-width="780px" scrollable>
      <v-card class="rounded-lg" v-if="detailItem">
        <v-card-title class="d-flex align-center py-4 pe-2">
          <v-icon class="mr-2">mdi-clipboard-text-clock</v-icon>
          <span class="text-h6">提议 #{{ detailItem.id }}</span>
          <v-spacer />
          <v-chip :color="statusColor(detailItem.status)" size="small" variant="tonal">
            {{ statusLabel(detailItem.status) }}
          </v-chip>
          <v-btn icon="mdi-close" variant="text" size="small" @click="detailDialog = false" />
        </v-card-title>
        <v-divider />

        <v-card-text class="py-4">
          <v-alert
            v-if="detailItem.entity_label"
            type="info"
            variant="tonal"
            density="comfortable"
            class="mb-4"
          >
            <div class="text-caption text-medium-emphasis">目标实体</div>
            <div class="text-body-2">{{ detailItem.entity_label }}</div>
          </v-alert>

          <v-row dense>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">实体类型</div>
              <div class="text-body-2">{{ entityTypeLabel(detailItem.entity_type) }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">操作</div>
              <div class="text-body-2">{{ actionLabel(detailItem.action) }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">提交时间</div>
              <div class="text-body-2">{{ formatToLocalDateTimeShort(detailItem.created_at) }}</div>
            </v-col>
            <v-col cols="6" sm="4" v-if="detailItem.review_note">
              <div class="text-caption text-medium-emphasis">审核备注</div>
              <div class="text-body-2">{{ detailItem.review_note }}</div>
            </v-col>
          </v-row>

          <div class="mt-4">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" start>mdi-compare-horizontal</v-icon>
              变更内容
            </div>
            <component
              v-if="detailRenderer"
              :is="detailRenderer"
              :proposal="detailItem"
            />
            <template v-else>
              <v-table v-if="diffRows.length" density="compact" class="diff-table">
                <tbody>
                  <tr v-for="row in diffRows" :key="row.field">
                    <td class="text-caption text-medium-emphasis" style="width: 28%">{{ row.field }}</td>
                    <td class="diff-cell before">{{ row.before ?? '—' }}</td>
                    <td class="text-center text-medium-emphasis" style="width: 32px">→</td>
                    <td class="diff-cell after">{{ row.after ?? '—' }}</td>
                  </tr>
                </tbody>
              </v-table>
            </template>
          </div>
        </v-card-text>

        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="detailDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { formatToLocalDateTimeShort } from '@/utils/timezone'
import { listProposals, getProposal, type Proposal } from '@/api/proposals'
import { resolveProposalRenderer } from '@/proposalRenderers'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()
const goBack = () => router.back()

type FilterValue = 'all' | 'pending' | 'applied' | 'rejected' | 'reverted'
const statusFilter = ref<FilterValue>('all')
const statusOptions = [
  { value: 'all', label: '全部', color: 'default', icon: 'mdi-format-list-bulleted' },
  { value: 'pending', label: '待审', color: 'warning', icon: 'mdi-clock-outline' },
  { value: 'applied', label: '已生效', color: 'success', icon: 'mdi-check-circle' },
  { value: 'rejected', label: '已驳回', color: 'error', icon: 'mdi-close-circle' },
  { value: 'reverted', label: '已回滚', color: 'info', icon: 'mdi-undo' },
]

const proposals = ref<Proposal[]>([])
const loading = ref(false)
const itemsPerPage = ref(20)

const headers = [
  { title: '状态', key: 'status', sortable: false, width: 110 },
  { title: '类型·动作', key: 'type', sortable: false },
  { title: '摘要', key: 'summary', sortable: false },
  { title: '时间', key: 'time', sortable: false, width: 180 },
  { title: '操作', key: 'actions', sortable: false, align: 'end' as const, width: 80 },
]

const pendingProposals = computed(() => proposals.value.filter(p => p.status === 'pending'))

const loadList = async () => {
  loading.value = true
  try {
    const status = statusFilter.value === 'all' ? undefined : statusFilter.value
    proposals.value = await listProposals(status as any, 100)
  } catch (e: any) {
    console.error('加载提议列表失败', e)
  } finally {
    loading.value = false
  }
}

watch(statusFilter, () => loadList())

const detailDialog = ref(false)
const detailItem = ref<Proposal | null>(null)

const openDetail = async (item: Proposal) => {
  detailItem.value = item
  detailDialog.value = true
}

const detailRenderer = computed(() => {
  return detailItem.value ? resolveProposalRenderer(detailItem.value) : null
})

const diffRows = computed(() => {
  const item = detailItem.value
  if (!item) return []
  const before = item.snapshot || {}
  const after = item.payload || {}
  const fields = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
  return fields.map(f => ({
    field: f,
    before: f in before ? before[f] : null,
    after: f in after ? after[f] : null,
  }))
})

function statusColor(s: string): string {
  switch (s) {
    case 'pending': return 'warning'
    case 'applied': return 'success'
    case 'rejected': return 'error'
    case 'reverted': return 'info'
    default: return 'default'
  }
}
function statusIcon(s: string): string {
  switch (s) {
    case 'pending': return 'mdi-clock-outline'
    case 'applied': return 'mdi-check-circle'
    case 'rejected': return 'mdi-close-circle'
    case 'reverted': return 'mdi-undo'
    default: return 'mdi-circle-outline'
  }
}
function statusLabel(s: string): string {
  switch (s) {
    case 'pending': return '待审'
    case 'applied': return '已生效'
    case 'rejected': return '已驳回'
    case 'reverted': return '已回滚'
    default: return s
  }
}
function entityTypeLabel(t: string): string {
  const map: Record<string, string> = {
    ingredient: '原料', nutrition: '营养', unit: '单位',
    merchant: '商家', product: '商品', recipe: '菜谱',
    entity_unit_override: '单位覆盖', entity_density: '密度',
    hierarchy: '层级关系', merchant_merge: '商家合并',
    product_split: '商品拆分', product_merge: '商品合并',
    usda_ingredient_match: 'USDA 原料匹配', usda_product_match: 'USDA 商品匹配',
  }
  return map[t] || t
}
function actionLabel(a: string): string {
  const map: Record<string, string> = {
    create: '创建', update: '更新', delete: '删除',
    merge: '合并', publish: '发布',
  }
  return map[a] || a
}
function payloadSummary(item: Proposal): string {
  const label = item.entity_label ? `${item.entity_label}` : ''
  const p = item.payload || {}
  const candidates = ['name', 'source_name', 'target_name', 'unit_name']
  const parts = candidates.filter(k => p[k] != null).map(k => p[k])
  const detail = parts.length ? parts.slice(0, 2).join('，') : JSON.stringify(p).slice(0, 60)
  return label ? `${label} · ${detail}` : detail
}

onMounted(() => { loadList() })
</script>

<style scoped>
.diff-table .diff-cell { font-size: 0.8rem; word-break: break-all; }
</style>
