<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">提议审核台</v-app-bar-title>
    <template #append>
      <v-btn color="warning" variant="tonal" @click="antiSpamDialog = true">
        <v-icon start>mdi-shield-account-variant</v-icon>
        反垃圾回退
      </v-btn>
      <v-btn icon="mdi-refresh" variant="text" @click="loadList" />
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 非管理员拦截（双保险：路由守卫 + 页面内判断） -->
    <v-alert
      v-if="!isAdmin"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      无权访问：仅管理员可使用提议审核台。
    </v-alert>

    <template v-else>
      <!-- 顶部 Tab：提议列表 / 策略配置 -->
      <v-tabs v-model="activeTab" color="primary" density="comfortable" class="mb-4">
        <v-tab value="list">
          <v-icon start size="small">mdi-clipboard-list-outline</v-icon>
          提议列表
        </v-tab>
        <v-tab value="policies">
          <v-icon start size="small">mdi-tune-vertical</v-icon>
          策略配置
        </v-tab>
      </v-tabs>

      <!-- ===== 提议列表 ===== -->
      <template v-if="activeTab === 'list'">
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
          <v-spacer class="d-none d-sm-block" />
          <div class="text-caption text-medium-emphasis">
            共 {{ proposals.length }} 条{{ statusFilter ? '' : '（全部）' }}
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
          :items-per-page="itemsPerPage"
          :items-per-page-options="[10, 20, 50, 100]"
          density="comfortable"
          no-data-text="暂无提议"
        >
          <!-- 状态列 -->
          <template #item.status="{ item }">
            <v-chip :color="statusColor(item.status)" size="small" variant="tonal">
              <v-icon start size="small">{{ statusIcon(item.status) }}</v-icon>
              {{ statusLabel(item.status) }}
            </v-chip>
          </template>

          <!-- 类型/动作列 -->
          <template #item.type="{ item }">
            <div class="d-flex flex-column">
              <span class="text-body-2 font-weight-medium">
                {{ entityTypeLabel(item.entity_type) }} · {{ actionLabel(item.action) }}
              </span>
              <span class="text-caption text-medium-emphasis">
                #{{ item.id }}
                <span v-if="item.entity_id">· ID {{ item.entity_id }}</span>
              </span>
            </div>
          </template>

          <!-- payload 摘要 -->
          <template #item.summary="{ item }">
            <span class="text-body-2 text-medium-emphasis">
              {{ payloadSummary(item) }}
            </span>
          </template>

          <!-- 风险等级 -->
          <template #item.risk_level="{ item }">
            <v-chip :color="riskColor(item.risk_level)" size="x-small" variant="outlined">
              {{ riskLabel(item.risk_level) }}
            </v-chip>
          </template>

          <!-- 提议人 -->
          <template #item.proposer_id="{ item }">
            <span class="text-body-2">
              <v-icon size="small" start>mdi-account</v-icon>
              #{{ item.proposer_id }}
            </span>
          </template>

          <!-- 策略 -->
          <template #item.review_policy="{ item }">
            <v-chip size="x-small" variant="text">
              {{ policyLabel(item.review_policy) }}
            </v-chip>
          </template>

          <!-- 创建时间（用 reviewed_at 兜底未审核时显示提交信息） -->
          <template #item.time="{ item }">
            <div class="text-caption">
              <div v-if="item.applied_at" class="text-success">
                生效：{{ formatToLocalDateTimeShort(item.applied_at) }}
              </div>
              <div v-else-if="item.reviewed_at" class="text-medium-emphasis">
                审核：{{ formatToLocalDateTimeShort(item.reviewed_at) }}
              </div>
              <div v-else class="text-warning">
                提交：{{ formatToLocalDateTimeShort(submitTime(item)) }}
              </div>
            </div>
          </template>

          <!-- 操作 -->
          <template #item.actions="{ item }">
            <div class="d-flex ga-1 justify-end flex-wrap">
              <v-tooltip location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon="mdi-eye-outline"
                    size="small"
                    variant="text"
                    color="primary"
                    @click="openDetail(item)"
                  />
                </template>
                <span>详情 / 影响预览</span>
              </v-tooltip>
              <v-tooltip v-if="item.status === 'pending'" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon="mdi-check"
                    size="small"
                    variant="text"
                    color="success"
                    @click="quickApprove(item)"
                  />
                </template>
                <span>批准</span>
              </v-tooltip>
              <v-tooltip v-if="canRevert(item)" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon="mdi-undo"
                    size="small"
                    variant="text"
                    color="error"
                    @click="confirmRevert(item)"
                  />
                </template>
                <span>回滚</span>
              </v-tooltip>
            </div>
          </template>
        </v-data-table>
      </v-card>
      </template>

      <!-- ===== 策略配置 ===== -->
      <template v-else-if="activeTab === 'policies'">
        <v-card class="rounded-lg">
          <v-card-text class="py-3 d-flex align-center ga-2 flex-wrap">
            <v-icon color="primary">mdi-tune-vertical</v-icon>
            <span class="text-body-2 text-medium-emphasis">
              为每种「实体类型 · 动作」配置审核策略。改动即时保存，重启后保持。
            </span>
            <v-spacer />
            <v-btn icon="mdi-refresh" variant="text" size="small" @click="loadPolicies" />
          </v-card-text>
          <v-divider />

          <v-data-table
            :headers="policyHeaders"
            :items="policies"
            :loading="policiesLoading"
            density="comfortable"
            item-value="entity_type"
            no-data-text="暂无已注册的提议类型"
          >
            <template #item.type="{ item }">
              <span class="text-body-2 font-weight-medium">
                {{ entityTypeLabel(item.entity_type) }} · {{ actionLabel(item.action) }}
              </span>
              <div class="text-caption text-medium-emphasis">
                {{ item.entity_type }} / {{ item.action }}
              </div>
            </template>

            <template #item.risk_level="{ item }">
              <v-chip :color="riskColor(item.risk_level)" size="x-small" variant="outlined">
                {{ riskLabel(item.risk_level) }}
              </v-chip>
            </template>

            <template #item.policy="{ item }">
              <div class="d-flex align-center ga-2">
                <v-select
                  :model-value="item.policy"
                  :items="policyOptions"
                  item-title="label"
                  item-value="value"
                  density="compact"
                  variant="outlined"
                  hide-details
                  style="max-width: 200px"
                  :color="policyChipColor(item.policy)"
                  @update:model-value="(v) => onPolicyChange(item, v)"
                />
                <v-chip
                  v-if="!item.is_default"
                  size="x-small"
                  variant="text"
                  color="warning"
                >
                  已自定义
                </v-chip>
              </div>
            </template>
          </v-data-table>
        </v-card>
      </template>
    </template>

    <!-- 详情 + 影响预览 + 审核对话框 -->
    <v-dialog v-model="detailDialog" max-width="780px" scrollable>
      <v-card class="rounded-lg" v-if="detailItem">
        <v-card-title class="d-flex align-center py-4 pe-2">
          <v-icon class="mr-2">mdi-clipboard-text-clock</v-icon>
          <span class="text-h6">提议 #{{ detailItem.id }}</span>
          <v-spacer />
          <v-chip :color="statusColor(detailItem.status)" size="small" variant="tonal" class="me-2">
            {{ statusLabel(detailItem.status) }}
          </v-chip>
          <v-btn icon="mdi-close" variant="text" size="small" @click="detailDialog = false" />
        </v-card-title>
        <v-divider />

        <v-card-text class="py-4">
          <!-- 目标实体标签（醒目置顶） -->
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

          <!-- 基本信息 -->
          <v-row dense>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">实体类型</div>
              <div class="text-body-2">{{ entityTypeLabel(detailItem.entity_type) }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">动作</div>
              <div class="text-body-2">{{ actionLabel(detailItem.action) }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">实体 ID</div>
              <div class="text-body-2">{{ detailItem.entity_id ?? '—' }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">提议人</div>
              <div class="text-body-2">#{{ detailItem.proposer_id }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">审核策略</div>
              <div class="text-body-2">{{ policyLabel(detailItem.review_policy) }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">风险等级</div>
              <v-chip :color="riskColor(detailItem.risk_level)" size="x-small" variant="outlined">
                {{ riskLabel(detailItem.risk_level) }}
              </v-chip>
            </v-col>
            <v-col cols="6" sm="4" v-if="detailItem.applied_at">
              <div class="text-caption text-medium-emphasis">生效时间</div>
              <div class="text-body-2">{{ formatToLocalDateTimeShort(detailItem.applied_at) }}</div>
            </v-col>
            <v-col cols="6" sm="4" v-if="detailItem.revertable_until">
              <div class="text-caption text-medium-emphasis">可回滚至</div>
              <div class="text-body-2">{{ formatToLocalDateTimeShort(detailItem.revertable_until) }}</div>
            </v-col>
            <v-col cols="6" sm="4" v-if="detailItem.reviewer_id">
              <div class="text-caption text-medium-emphasis">审核人</div>
              <div class="text-body-2">#{{ detailItem.reviewer_id }}</div>
            </v-col>
          </v-row>

          <!-- 审核备注（已审核的） -->
          <v-alert
            v-if="detailItem.review_note"
            type="info"
            variant="tonal"
            density="comfortable"
            class="mt-4"
          >
            <div class="text-caption text-medium-emphasis">审核备注</div>
            <div>{{ detailItem.review_note }}</div>
          </v-alert>

          <!-- 变更内容 diff -->
          <div class="mt-4">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" start>mdi-compare-horizontal</v-icon>
              变更内容
              <span v-if="detailItem.action === 'delete'" class="text-caption text-medium-emphasis ms-2">（将删除）</span>
              <span v-else-if="detailItem.action === 'create'" class="text-caption text-medium-emphasis ms-2">（将新增）</span>
            </div>

            <!-- 级联影响提示（如删除商品时连带的价格记录） -->
            <v-alert
              v-if="cascadeEffectInfo"
              :type="cascadeEffectInfo.type"
              variant="tonal"
              density="compact"
              class="mb-3"
            >
              <div class="text-body-2">{{ cascadeEffectInfo.text }}</div>
            </v-alert>

            <!-- 专用渲染器（菜谱 / 营养 / 合并 三类） -->
            <component
              v-if="detailRenderer"
              :is="detailRenderer"
              :proposal="detailItem"
            />

            <!-- 兜底：CRUD 类字段 diff 表（现状逻辑，零改动） -->
            <template v-else>
              <v-table v-if="diffRows.length" density="compact" class="diff-table">
                <tbody>
                  <tr v-for="row in diffRows" :key="row.field">
                    <td class="text-caption text-medium-emphasis" style="width: 28%">{{ fieldLabel(row.field) }}</td>
                    <td :class="['diff-cell', 'before', row.kind]">
                      <span v-if="row.before === null" class="text-medium-emphasis">—</span>
                      <span v-else>{{ formatFieldValue(row.field, row.before) }}</span>
                    </td>
                    <td class="text-center text-medium-emphasis" style="width: 32px">→</td>
                    <td :class="['diff-cell', 'after', row.kind]">
                      <span v-if="row.kind === 'removed'" class="text-medium-emphasis">（删除）</span>
                      <span v-else-if="row.after === null" class="text-medium-emphasis">—</span>
                      <span v-else>{{ formatFieldValue(row.field, row.after) }}</span>
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <div v-else class="text-caption text-medium-emphasis">无变更字段（如仅触发动作，无数据变更）</div>
            </template>
          </div>

          <!-- 影响预览 -->
          <div class="mt-4">
            <div class="d-flex align-center mb-2">
              <div class="text-subtitle-2 me-2">
                <v-icon size="small" start>mdi-file-eye-outline</v-icon>
                影响预览
              </div>
              <v-btn
                size="small"
                variant="tonal"
                color="info"
                :loading="previewing"
                @click="loadPreview"
              >
                <v-icon start>mdi-refresh</v-icon>
                {{ previewData ? '刷新' : '加载预览' }}
              </v-btn>
            </div>
            <v-progress-circular
              v-if="previewing"
              indeterminate
              color="info"
              size="24"
              width="2"
            />
            <pre v-else-if="previewData" class="payload-block pa-3 rounded">{{ formatJson(previewData) }}</pre>
            <div v-else class="text-caption text-medium-emphasis">
              点击「加载预览」查看此变更会影响哪些数据（如合并会影响多少引用）。
            </div>
          </div>

          <!-- 驳回备注输入（仅 pending） -->
          <div v-if="detailItem.status === 'pending'" class="mt-4">
            <v-textarea
              v-model="rejectNote"
              label="审核备注（驳回建议填写理由，批准可留空）"
              variant="outlined"
              density="comfortable"
              rows="2"
              auto-grow
              hide-details
            />
          </div>
        </v-card-text>

        <v-divider />
        <v-card-actions class="pa-4 flex-wrap ga-2">
          <v-btn variant="tonal" @click="detailDialog = false">关闭</v-btn>
          <v-spacer />
          <template v-if="detailItem.status === 'pending'">
            <v-btn
              color="error"
              variant="tonal"
              :loading="reviewing"
              @click="reviewCurrent(false)"
            >
              <v-icon start>mdi-close</v-icon>
              驳回
            </v-btn>
            <v-btn
              color="success"
              :loading="reviewing"
              @click="reviewCurrent(true)"
            >
              <v-icon start>mdi-check</v-icon>
              批准并生效
            </v-btn>
          </template>
          <v-btn
            v-else-if="canRevert(detailItem)"
            color="error"
            :loading="reverting"
            @click="confirmRevert(detailItem)"
          >
            <v-icon start>mdi-undo</v-icon>
            回滚
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 回滚确认 -->
    <v-dialog v-model="revertDialog" max-width="460px">
      <v-card class="rounded-lg">
        <v-card-title class="text-h6">
          <v-icon class="mr-2" color="error">mdi-undo</v-icon>
          确认回滚
        </v-card-title>
        <v-card-text>
          确定要回滚提议 <code>#{{ revertTarget?.id }}</code> 吗？
          <span class="text-medium-emphasis">
            （{{ entityTypeLabel(revertTarget?.entity_type) }} ·
            {{ actionLabel(revertTarget?.action) }}）
          </span>
          此操作将撤销该提议产生的数据变更，操作不可撤销。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="revertDialog = false">取消</v-btn>
          <v-btn color="error" :loading="reverting" @click="doRevert">确认回滚</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 反垃圾批量回退 -->
    <v-dialog v-model="antiSpamDialog" max-width="460px">
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center py-4">
          <v-icon class="mr-2" color="warning">mdi-shield-account-variant</v-icon>
          反垃圾批量回退
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <p class="text-body-2 mb-3">
            输入用户 ID，一键回退该用户全部「已生效」提议。仅管理员可用，常用于处理垃圾提交。
          </p>
          <v-text-field
            v-model.number="antiSpamUserId"
            label="用户 ID"
            prepend-icon="mdi-account"
            variant="outlined"
            density="comfortable"
            type="number"
            min="1"
            hide-details
          />
          <v-alert
            v-if="antiSpamResult !== null"
            :type="antiSpamResult > 0 ? 'success' : 'info'"
            variant="tonal"
            density="comfortable"
            class="mt-3"
          >
            已回退 <strong>{{ antiSpamResult }}</strong> 条提议。
          </v-alert>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="tonal" @click="antiSpamDialog = false">关闭</v-btn>
          <v-btn
            color="warning"
            :loading="antiSpamLoading"
            :disabled="!antiSpamUserId || antiSpamUserId < 1"
            @click="doAntiSpam"
          >
            执行回退
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="approveConfirmDialog" max-width="460px">
      <v-card>
        <v-card-title class="d-flex align-center ga-2">
          <v-icon color="warning">mdi-alert-circle-outline</v-icon>
          确认批准
        </v-card-title>
        <v-card-text>
          确定批准并生效提议 <strong>#{{ approveConfirmItem?.id }}</strong>？
         （{{ entityTypeLabel(approveConfirmItem?.entity_type) }} · {{ actionLabel(approveConfirmItem?.action) }}）
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="approveConfirmDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="reviewing" @click="doQuickApprove">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useUserStore } from '@/stores/user'
import { useGlobalSnackbar } from '@/composables/useGlobalSnackbar'
import { formatToLocalDateTimeShort } from '@/utils/timezone'
import {
  listProposals,
  getProposal,
  previewProposal,
  reviewProposal,
  revertProposal,
  revertByUser,
  listPolicies,
  updatePolicy,
  type Proposal,
  type ProposalStatus,
  type PolicyItem,
  type ReviewPolicy,
} from '@/api/proposals'
import { resolveProposalRenderer } from '@/proposalRenderers'
import api from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()
const userStore = useUserStore()
const { notify } = useGlobalSnackbar()

const goBack = () => router.back()

const isAdmin = computed(() => !!userStore.user?.is_admin)

// ---------- 顶部 Tab ----------
const activeTab = ref<'list' | 'policies'>('list')

// ---------- 策略配置 ----------
const policies = ref<PolicyItem[]>([])
const policiesLoading = ref(false)
const policySavingKey = ref<string | null>(null)

const policyHeaders = [
  { title: '实体类型 · 动作', key: 'type', sortable: false },
  { title: '风险', key: 'risk_level', sortable: false, width: 90 },
  { title: '审核策略', key: 'policy', sortable: false, width: 280 },
]

const policyOptions: { value: ReviewPolicy; label: string }[] = [
  { value: 'auto_approve', label: '自动批准生效' },
  { value: 'auto_review', label: '自动审核（辅助）' },
  { value: 'manual', label: '人工审核' },
]

const loadPolicies = async () => {
  if (!isAdmin.value) return
  policiesLoading.value = true
  try {
    policies.value = await listPolicies()
  } catch (e: any) {
    notify(e?.userMessage || '加载策略配置失败', 'error')
  } finally {
    policiesLoading.value = false
  }
}

const onPolicyChange = async (item: PolicyItem, newPolicy: ReviewPolicy) => {
  if (newPolicy === item.policy) return
  policySavingKey.value = `${item.entity_type}/${item.action}`
  const prev = item.policy
  // 乐观更新
  item.policy = newPolicy
  try {
    const updated = await updatePolicy({
      entity_type: item.entity_type,
      action: item.action,
      policy: newPolicy,
    })
    // 用服务端返回覆盖（含 is_default 重算）
    Object.assign(item, updated)
    notify(
      `${entityTypeLabel(item.entity_type)} · ${actionLabel(item.action)} 策略已更新为「${policyOptionLabel(newPolicy)}」`,
      'success',
    )
  } catch (e: any) {
    item.policy = prev // 回滚
    notify(e?.userMessage || '保存策略失败', 'error')
  } finally {
    policySavingKey.value = null
  }
}

function policyOptionLabel(v: string): string {
  return policyOptions.find((o) => o.value === v)?.label || v
}

function policyChipColor(p: string): string {
  switch (p) {
    case 'auto_approve': return 'success'
    case 'auto_review': return 'info'
    case 'manual': return 'warning'
    default: return 'default'
  }
}

// ---------- 状态筛选 ----------
type FilterValue = 'pending' | 'applied' | 'rejected' | 'reverted' | 'all'
const statusFilter = ref<FilterValue>('pending')
const statusOptions: { value: FilterValue; label: string; color: string; icon: string }[] = [
  { value: 'pending', label: '待审', color: 'warning', icon: 'mdi-clock-outline' },
  { value: 'applied', label: '已生效', color: 'success', icon: 'mdi-check-circle' },
  { value: 'rejected', label: '已驳回', color: 'error', icon: 'mdi-close-circle' },
  { value: 'reverted', label: '已回滚', color: 'info', icon: 'mdi-undo' },
  { value: 'all', label: '全部', color: 'default', icon: 'mdi-format-list-bulleted' },
]

// ---------- 列表 ----------
const proposals = ref<Proposal[]>([])
const loading = ref(false)
const itemsPerPage = ref(20)

const headers = [
  { title: '状态', key: 'status', sortable: false, width: 110 },
  { title: '类型 · 动作', key: 'type', sortable: false },
  { title: '摘要', key: 'summary', sortable: false },
  { title: '风险', key: 'risk_level', sortable: false, width: 90 },
  { title: '提议人', key: 'proposer_id', sortable: false, width: 100 },
  { title: '时间', key: 'time', sortable: false, width: 180 },
  { title: '操作', key: 'actions', sortable: false, align: 'end' as const, width: 130 },
]

const loadList = async () => {
  if (!isAdmin.value) return
  loading.value = true
  try {
    const status = statusFilter.value === 'all' ? undefined : (statusFilter.value as ProposalStatus)
    proposals.value = await listProposals(status, 100)
  } catch (e: any) {
    notify(e?.userMessage || '加载提议列表失败', 'error')
  } finally {
    loading.value = false
  }
}

watch(statusFilter, () => loadList())

watch(activeTab, (t) => {
  if (t === 'policies' && policies.value.length === 0) loadPolicies()
})

// ---------- 详情 + 预览 ----------
const detailDialog = ref(false)
const detailItem = ref<Proposal | null>(null)
const previewData = ref<Record<string, any> | null>(null)
const previewing = ref(false)
const rejectNote = ref('')

const openDetail = (item: Proposal) => {
  detailItem.value = item
  previewData.value = null
  rejectNote.value = ''
  // 后端 _to_response 不返回提交时间字段；用 reviewed_at 兜底仅作展示排序，这里预览不预加载
  detailDialog.value = true
}

const loadPreview = async () => {
  if (!detailItem.value) return
  previewing.value = true
  try {
    previewData.value = await previewProposal({
      entity_type: detailItem.value.entity_type,
      entity_id: detailItem.value.entity_id,
      action: detailItem.value.action,
      payload: detailItem.value.payload,
    })
  } catch (e: any) {
    notify(e?.userMessage || '加载影响预览失败', 'error')
  } finally {
    previewing.value = false
  }
}

// ---------- 审核 ----------
const reviewing = ref(false)
const approveConfirmDialog = ref(false)
const approveConfirmItem = ref<Proposal | null>(null)

const quickApprove = async (item: Proposal) => {
  approveConfirmItem.value = item
  approveConfirmDialog.value = true
}

const doQuickApprove = async () => {
  const item = approveConfirmItem.value
  if (!item) return
  approveConfirmDialog.value = false
  reviewing.value = true
  try {
    await reviewProposal(item.id, { approved: true })
    notify(`提议 #${item.id} 已批准并生效`, 'success')
    await loadList()
  } catch (e: any) {
    notify(e?.userMessage || '审核操作失败', 'error')
  } finally {
    reviewing.value = false
    approveConfirmItem.value = null
  }
}

const reviewCurrent = async (approved: boolean) => {
  if (!detailItem.value) return
  reviewing.value = true
  try {
    await reviewProposal(detailItem.value.id, {
      approved,
      note: approved ? '' : rejectNote.value.trim(),
    })
    notify(
      approved ? `提议 #${detailItem.value.id} 已批准并生效` : `提议 #${detailItem.value.id} 已驳回`,
      approved ? 'success' : 'info',
    )
    // 局部刷新当前条目（保持列表筛选不变）
    try {
      detailItem.value = await getProposal(detailItem.value.id)
    } catch {
      /* ignore */
    }
    await loadList()
    detailDialog.value = false
  } catch (e: any) {
    notify(e?.userMessage || '审核操作失败', 'error')
  } finally {
    reviewing.value = false
  }
}

// ---------- 回滚 ----------
const revertDialog = ref(false)
const revertTarget = ref<Proposal | null>(null)
const reverting = ref(false)

const canRevert = (item: Proposal | null): boolean => {
  if (!item || item.status !== 'applied') return false
  if (!item.revertable_until) return true // 无窗口限制时允许
  return new Date(item.revertable_until) > new Date()
}

const confirmRevert = (item: Proposal) => {
  if (!canRevert(item)) {
    notify('该提议不在可回滚窗口内', 'warning')
    return
  }
  revertTarget.value = item
  revertDialog.value = true
}

const doRevert = async () => {
  if (!revertTarget.value) return
  reverting.value = true
  try {
    const updated = await revertProposal(revertTarget.value.id)
    notify(`提议 #${updated.id} 已回滚`, 'success')
    revertDialog.value = false
    if (detailItem.value?.id === updated.id) detailItem.value = updated
    await loadList()
  } catch (e: any) {
    notify(e?.userMessage || '回滚操作失败', 'error')
  } finally {
    reverting.value = false
  }
}

// ---------- 反垃圾 ----------
const antiSpamDialog = ref(false)
const antiSpamUserId = ref<number | null>(null)
const antiSpamResult = ref<number | null>(null)
const antiSpamLoading = ref(false)

const doAntiSpam = async () => {
  if (!antiSpamUserId.value || antiSpamUserId.value < 1) return
  antiSpamLoading.value = true
  antiSpamResult.value = null
  try {
    const res = await revertByUser(antiSpamUserId.value)
    antiSpamResult.value = res.reverted_count
    notify(`已回退 ${res.reverted_count} 条提议`, 'success')
    await loadList()
  } catch (e: any) {
    notify(e?.userMessage || '反垃圾回退失败', 'error')
  } finally {
    antiSpamLoading.value = false
  }
}

// ---------- 工具：文案/颜色/格式化 ----------
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
function riskColor(r: string): string {
  switch (r) {
    case 'high': return 'error'
    case 'medium': return 'warning'
    case 'low': return 'success'
    default: return 'default'
  }
}
function riskLabel(r: string): string {
  switch (r) {
    case 'high': return '高'
    case 'mid': return '中'
    case 'medium': return '中'
    case 'low': return '低'
    default: return r || '—'
  }
}
function policyLabel(p: string): string {
  switch (p) {
    case 'auto_approve': return '自动生效'
    case 'auto_review': return '自动审核'
    case 'manual': return '人工审核'
    default: return p
  }
}
function entityTypeLabel(t: string): string {
  const map: Record<string, string> = {
    ingredient: '原料',
    nutrition: '营养',
    unit: '单位',
    hierarchy: '食材层级关系',
    merchant: '商家',
    merchant_merge: '商家合并',
    product_split: '商品拆分',
    product_merge: '商品合并',
    product: '商品',
    recipe: '菜谱',
    entity_unit_override: '实体单位覆盖',
    entity_density: '实体密度',
    usda_ingredient_match: 'USDA 原料匹配',
    usda_product_match: 'USDA 商品匹配',
  }
  return map[t] || t
}
function actionLabel(a: string): string {
  const map: Record<string, string> = {
    create: '创建',
    update: '更新',
    delete: '删除',
    merge: '合并',
    publish: '发布',
  }
  return map[a] || a
}
function payloadSummary(item: Proposal): string {
  // 目标实体可读标签前置（如「原料「鸡蛋」单位「盒」」），无则降级
  const label = item.entity_label ? `${item.entity_label}` : ''
  const p = item.payload || {}
  // 常见字段优先：name / source / target
  // 优先字段：常见名称/密度/单位/层级等
  const candidates = [
    'name', 'source_name', 'target_name', 'unit_name', 'density', 'condition',
    'category', 'parent_id', 'child_id', 'relation_type', 'entity_type', 'entity_id',
    'target_id', 'source_id',
  ]
  const parts: string[] = []
  for (const key of candidates) {
    if (p[key] != null) parts.push(`${FIELD_LABELS[key] || key}: ${p[key]}`)
  }
  let detail: string
  if (parts.length) {
    detail = parts.slice(0, 2).join('，')
  } else {
    // 兜底：截断 JSON
    try {
      const s = JSON.stringify(p)
      detail = s.length > 60 ? s.slice(0, 60) + '…' : s
    } catch {
      detail = '—'
    }
  }
  return label ? `${label} · ${detail}` : detail
}
function submitTime(item: Proposal): string {
  // 后端未直接返回 created_at；用 reviewed_at/applied_at 的较前者兜底，仅作"未审核"分支展示占位
  return item.reviewed_at || item.applied_at || new Date().toISOString()
}
interface DiffRow {
  field: string
  before: any
  after: any
  kind: 'added' | 'removed' | 'changed' | 'unchanged'
}

const diffRows = computed<DiffRow[]>(() => {
  const item = detailItem.value
  if (!item) return []
  const before = item.snapshot || {}
  const after = item.payload || {}
  const fields = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
    .filter(f => !f.startsWith('_'))
  return fields.map(f => {
    const b = before[f]
    const a = after[f]
    let kind: DiffRow['kind'] = 'unchanged'
    const hasB = f in before
    const hasA = f in after
    if (hasB && !hasA) kind = 'removed'
    else if (!hasB && hasA) kind = 'added'
    else if (JSON.stringify(b) !== JSON.stringify(a)) kind = 'changed'
    return { field: f, before: hasB ? b : null, after: hasA ? a : null, kind }
  })
})

const detailRenderer = computed(() => {
  const item = detailItem.value
  return item ? resolveProposalRenderer(item) : null
})

/** 级联影响提示：从 snapshot 中提取级联删除信息展示。 */
const cascadeEffectInfo = computed<{ type: string; text: string } | null>(() => {
  const item = detailItem.value
  if (!item || item.action !== 'delete') return null
  const snap = item.snapshot
  if (!snap) return null
  const parts: string[] = []
  const rc = snap.cascade_record_count
  if (rc != null && rc > 0) parts.push(`${rc} 条价格记录`)
  const pc = snap.cascade_product_count
  if (pc != null && pc > 0) parts.push(`${pc} 个关联商品`)
  const hc = snap.cascade_hierarchy_count
  if (hc != null && hc > 0) parts.push(`${hc} 条层级关系`)
  if (!parts.length) return null
  return {
    type: 'warning',
    text: `此操作将同时级联删除 ${parts.join('、')}。`,
  }
})

const FIELD_LABELS: Record<string, string> = {
  name: '名称',
  aliases: '别名',
  brand: '品牌',
  barcode: '条码',
  category: '分类',
  unit_name: '单位名',
  density: '密度',
  confidence: '置信度',
  condition: '条件',
  factor: '换算系数',
  is_standard: '标准单位',
  parent_id: '父食材',
  child_id: '子食材',
  relation_type: '关系类型',
  strength: '关联强度',
  entity_type: '实体类型',
  entity_id: '实体 ID',
  source_id: '源 ID',
  target_id: '目标 ID',
  source_name: '源名称',
  target_name: '目标名称',
  is_optional: '可选',
  quantity: '用量',
  quantity_range: '用量范围',
  unit_id: '单位 ID',
  note: '备注',
  original_quantity: '原始用量',
  cooking_steps: '操作步骤',
  tips: '小贴士',
  description: '描述',
  tags: '标签',
  is_open: '开放状态',
  is_public: '公开',
  serving_weight: '份重(g)',
  review_policy: '审核策略',
  risk_level: '风险等级',
  phone: '电话',
  address: '地址',
  longitude: '经度',
  latitude: '纬度',
  category_id: '分类',
  default_unit: '默认单位',
  updated_by: '修改者',
  cascade_record_count: '级联价格记录',
}
function fieldLabel(f: string): string {
  return FIELD_LABELS[f] || f
}

// ---- ID 字段 → 名称解析（数字 ID 显示为可读名称）----
const ID_FIELDS: Record<string, 'category' | 'unit' | 'user' | 'ingredient'> = {
  category_id: 'category',
  default_unit_id: 'unit',
  unit_id: 'unit',
  weight_unit_id: 'unit',
  updated_by: 'user',
  created_by: 'user',
  proposer_id: 'user',
  reviewer_id: 'user',
  user_id: 'user',
  ingredient_id: 'ingredient',
}
const nameCache = ref<{
  category: Record<number, string>
  unit: Record<number, string>
  user: Record<number, string>
  ingredient: Record<number, string>
}>({ category: {}, unit: {}, user: {}, ingredient: {} })

async function loadNameCache() {
  if (!isAdmin.value) return
  try {
    // 分类可能有多级，递归加载全部，用 display_name（中文名）优先
    const top = await api.get('/ingredients/categories')
    const all: any[] = Array.isArray(top) ? [...top] : []
    async function loadChildren(parentId: number) {
      const children = await api.get('/ingredients/categories', { params: { parent_id: parentId } })
      if (Array.isArray(children)) {
        all.push(...children)
        for (const c of children) {
          if (c.id != null) await loadChildren(c.id)
        }
      }
    }
    for (const c of all.slice()) {
      if (c.id != null) await loadChildren(c.id)
    }
    all.forEach((c: any) => { nameCache.value.category[c.id] = c.display_name || c.name })
  } catch { /* ignore */ }
  try {
    const units = await api.get('/units/', { params: { limit: 500 } })
    const list: any[] = Array.isArray(units) ? units : (units.items || units.data || [])
    list.forEach((u: any) => { nameCache.value.unit[u.id] = u.name })
  } catch { /* ignore */ }
  try {
    const users = await api.get('/auth/users', { params: { limit: 500 } })
    const list: any[] = Array.isArray(users) ? users : (users.items || users.users || users.data || [])
    list.forEach((u: any) => { nameCache.value.user[u.id] = u.username || u.name || `#${u.id}` })
  } catch { /* ignore */ }
  try {
    const ings = await api.get('/ingredients', { params: { limit: 500 } })
    const list2: any[] = Array.isArray(ings) ? ings : (ings.items || ings.data || [])
    list2.forEach((i: any) => { nameCache.value.ingredient[i.id] = i.name })
  } catch { /* ignore */ }
}

function formatFieldValue(field: string, v: any): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  const kind = ID_FIELDS[field]
  if (kind) {
    const id = Number(v)
    const name = nameCache.value[kind][id]
    if (name) return name
    return `#${v}`
  }
  if (typeof v === 'boolean') return v ? '是' : '否'
  return String(v)
}
function formatValue(v: any): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function formatJson(obj: any): string {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

watch(isAdmin, (v) => { if (v) { loadList(); loadNameCache() } })
onMounted(() => {
  if (isAdmin.value) {
    loadList()
    loadNameCache()
  }
})
</script>

<style scoped>
.payload-block {
  background: rgba(var(--v-theme-on-surface), 0.05);
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  max-height: 280px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
code {
  font-family: 'Courier New', monospace;
  padding: 2px 6px;
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 4px;
}
.diff-table .diff-cell { font-size: 0.8rem; word-break: break-all; }
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }
.diff-table .before.removed { color: rgb(244, 67, 54); }
.diff-table .after.added { color: rgb(76, 175, 80); }
</style>
