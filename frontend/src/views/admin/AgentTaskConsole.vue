<!--
  Agent 任务台 — 管理员可发起 Agent 任务、查看对话流、审批 SQL、插话。
  复用 useAgentSession（Task 7）。
-->
<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push('/admin')" />
    <v-app-bar-title class="text-h6">Agent 任务台</v-app-bar-title>
    <template #append>
      <v-chip size="small" :color="statusColor" variant="tonal">
        <v-icon start size="small" :color="connected ? 'success' : 'grey'">
          {{ connected ? 'mdi-link-variant' : 'mdi-link-off' }}
        </v-icon>
        {{ statusLabel }}
      </v-chip>
    </template>
  </v-app-bar>

  <v-container fluid class="pa-0 agent-container">
    <v-alert
      v-if="errorMsg"
      type="error"
      variant="tonal"
      density="compact"
      closable
      class="ma-2"
      @click:close="error = ''"
    >
      {{ errorMsg }}
    </v-alert>

    <v-row no-gutters class="agent-row">
      <!-- 左栏：任务按钮 + 历史会话 -->
      <v-col cols="12" md="3" class="agent-sidebar d-none d-md-flex">
        <div class="sidebar-section">
          <div class="text-caption text-medium-emphasis px-3 pt-3 pb-1">任务类型</div>
          <div class="px-3 pb-2">
            <v-select
              v-model="provider"
              :items="providerOptions"
              item-title="label"
              item-value="value"
              label="Provider"
              variant="outlined"
              density="compact"
              hide-details
              :disabled="starting"
            />
          </div>
          <v-list density="compact" nav>
            <v-list-item
              v-for="t in taskTypes"
              :key="t.task_type"
              :disabled="starting"
              @click="onStartTask(t.task_type)"
            >
              <template #prepend>
                <v-icon size="18" color="primary">mdi-rocket-launch</v-icon>
              </template>
              <v-list-item-title class="text-body-2">{{ t.title }}</v-list-item-title>
              <v-list-item-subtitle class="text-caption">{{ t.task_type }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item v-if="!taskTypes.length && !loadingMeta">
              <v-list-item-subtitle class="text-caption">无可用任务</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>

        <v-divider />

        <div class="sidebar-section sidebar-history">
          <div class="d-flex align-center px-3 pt-3 pb-1">
            <span class="text-caption text-medium-emphasis">历史会话</span>
            <v-spacer />
            <v-btn icon="mdi-refresh" size="x-small" variant="text" @click="loadSessions" />
          </div>
          <v-list density="compact" nav class="history-list">
            <v-list-item
              v-for="s in sessions"
              :key="s.id"
              :active="s.id === currentSid"
              @click="onSelectSession(s.id)"
            >
              <template #prepend>
                <v-icon size="16" :color="sessionStatusColor(s.status)">
                  {{ sessionStatusIcon(s.status) }}
                </v-icon>
              </template>
              <v-list-item-title class="text-body-2 text-truncate">
                {{ s.title || `#${s.id} ${s.task_type || ''}` }}
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption">
                {{ s.task_type || '-' }} · {{ formatRelative(s.updated_at || s.created_at) }}
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item v-if="!sessions.length && !loadingMeta">
              <v-list-item-subtitle class="text-caption">暂无历史</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>
      </v-col>

      <!-- 右栏：对话流 + 插话 -->
      <v-col cols="12" md="9" class="agent-main">
        <!-- 移动端：返回侧栏的按钮 -->
        <div v-if="!$vuetify.display.mdAndUp && !currentSid" class="pa-3 text-center">
          <v-btn variant="tonal" color="primary" @click="mobileShowSidebar = true">
            <v-icon start>mdi-menu</v-icon>选择任务或历史会话
          </v-btn>
        </div>

        <template v-else>
          <!-- 顶部状态条 -->
          <div class="status-bar px-3 py-2 d-flex align-center">
            <v-icon size="18" :color="statusColor" class="mr-2">
              {{ sessionStatusIcon(status) }}
            </v-icon>
            <span class="text-body-2 font-weight-medium">{{ statusLabel }}</span>
            <v-spacer />
            <span v-if="costUsd != null" class="text-caption text-medium-emphasis mr-3">
              <v-icon size="12" class="mr-1">mdi-currency-usd</v-icon>${{ costUsd.toFixed(4) }}
            </span>
            <v-progress-circular
              v-if="isRunning"
              indeterminate
              size="14"
              width="2"
              color="primary"
            />
          </div>

          <!-- 对话流 -->
          <div ref="streamEl" class="stream-area">
            <div v-if="!messages.length && !isRunning" class="text-center text-medium-emphasis pa-8">
              <v-icon size="48" class="mb-2">mdi-robot-outline</v-icon>
              <div class="text-body-2">从左侧选择一个任务类型开始，或查看历史会话</div>
            </div>

            <template v-for="m in messages" :key="m.key">
              <AgentMessageBubble :msg="m" />
              <!-- 该消息后挂载的审批卡（composable 用 pendingApprovals 列表） -->
            </template>

            <!-- 待审批卡片区（放在流末尾；pending 的优先展示） -->
            <template v-for="ap in pendingApprovals" :key="`ap-${ap.id}`">
              <AgentApprovalCard :approval="ap" @decide="onDecide" />
            </template>
          </div>

          <!-- 插话框 -->
          <div class="interject-bar pa-3">
            <v-textarea
              v-model="interjectText"
              variant="outlined"
              density="compact"
              rows="1"
              auto-grow
              max-rows="4"
              :placeholder="interjectPlaceholder"
              :disabled="!canInterject"
              hide-details
              @keydown.enter.exact.prevent="onInterject"
              style="font-size: 16px;"
            />
            <v-btn
              color="primary"
              variant="flat"
              class="ml-2"
              :disabled="!canInterject || !interjectText.trim()"
              :loading="sending"
              @click="onInterject"
            >
              <v-icon>mdi-send</v-icon>
              <span class="ml-1 d-none d-sm-inline">发送</span>
            </v-btn>
          </div>
        </template>
      </v-col>
    </v-row>

    <!-- 移动端侧栏抽屉 -->
    <v-navigation-drawer
      v-if="!$vuetify.display.mdAndUp"
      v-model="mobileShowSidebar"
      location="left"
      temporary
      width="300"
    >
      <div class="sidebar-section">
        <div class="text-caption text-medium-emphasis px-3 pt-3 pb-1">任务类型</div>
        <div class="px-3 pb-2">
          <v-select
            v-model="provider"
            :items="providerOptions"
            item-title="label"
            item-value="value"
            label="Provider"
            variant="outlined"
            density="compact"
            hide-details
            :disabled="starting"
          />
        </div>
        <v-list density="compact" nav>
          <v-list-item
            v-for="t in taskTypes"
            :key="t.task_type"
            :disabled="starting"
            @click="onStartTask(t.task_type); mobileShowSidebar = false"
          >
            <template #prepend>
              <v-icon size="18" color="primary">mdi-rocket-launch</v-icon>
            </template>
            <v-list-item-title class="text-body-2">{{ t.title }}</v-list-item-title>
            <v-list-item-subtitle class="text-caption">{{ t.task_type }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </div>
      <v-divider />
      <div class="sidebar-section">
        <div class="text-caption text-medium-emphasis px-3 pt-3 pb-1">历史会话</div>
        <v-list density="compact" nav>
          <v-list-item
            v-for="s in sessions"
            :key="s.id"
            :active="s.id === currentSid"
            @click="onSelectSession(s.id); mobileShowSidebar = false"
          >
            <template #prepend>
              <v-icon size="16" :color="sessionStatusColor(s.status)">
                {{ sessionStatusIcon(s.status) }}
              </v-icon>
            </template>
            <v-list-item-title class="text-body-2 text-truncate">
              {{ s.title || `#${s.id}` }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ s.task_type || '-' }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </div>
    </v-navigation-drawer>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useAgentSession } from '@/composables/useAgentSession'
import { getTaskTypes, listSessions } from '@/api/agent'
import type { AgentProvider } from '@/api/agent'
import type { AgentSession, TaskType } from '@/types/agent'
import AgentMessageBubble from '@/components/agent/AgentMessageBubble.vue'
import AgentApprovalCard from '@/components/agent/AgentApprovalCard.vue'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const route = useRoute()
const router = useRouter()

const {
  messages,
  status,
  pendingApprovals,
  costUsd,
  error,
  connected,
  connect,
  startTask,
  interject,
  approve,
  reset,
} = useAgentSession()

// ---------- 元数据 ----------
const taskTypes = ref<TaskType[]>([])
const sessions = ref<AgentSession[]>([])
const loadingMeta = ref(false)
const starting = ref(false)
const sending = ref(false)

/** Provider 选择（默认 claude_code，保现有行为）。
 * 三选项前端硬编码（YAGNI，不动后端 /task-types）。
 */
const provider = ref<AgentProvider>('claude_code')
const providerOptions: { value: AgentProvider; label: string }[] = [
  { value: 'claude_code', label: 'Claude Code' },
  { value: 'openai', label: 'OpenAI 兼容' },
  { value: 'anthropic', label: 'Anthropic 兼容' },
]

const currentSid = ref<number | null>(null)
const interjectText = ref('')
const mobileShowSidebar = ref(false)
const streamEl = ref<HTMLElement | null>(null)

const errorMsg = computed(() => error.value)

// ---------- 状态展示 ----------
const TERMINAL = new Set(['success', 'completed', 'failed', 'cancelled'])

const isRunning = computed(
  () => status.value === 'running' || status.value === 'pending',
)

const canInterject = computed(() => {
  if (!currentSid.value) return false
  return true // 后端会判 409；运行中也可插话
})

const interjectPlaceholder = computed(() => {
  if (!currentSid.value) return '请先选择/开始会话'
  if (status.value === 'awaiting_approval') return '等待审批中…'
  return '向 Agent 插话（Enter 发送，Shift+Enter 换行）'
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    awaiting_approval: '待审批',
    success: '成功',
    completed: '完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status.value] || status.value
})

const statusColor = computed(() => sessionStatusColor(status.value))

function sessionStatusColor(s: string): string {
  switch (s) {
    case 'running':
    case 'pending':
      return 'primary'
    case 'awaiting_approval':
      return 'warning'
    case 'success':
    case 'completed':
      return 'success'
    case 'failed':
    case 'cancelled':
      return 'error'
    default:
      return 'grey'
  }
}

function sessionStatusIcon(s: string): string {
  switch (s) {
    case 'running':
      return 'mdi-progress-clock'
    case 'pending':
      return 'mdi-clock-outline'
    case 'awaiting_approval':
      return 'mdi-shield-key'
    case 'success':
    case 'completed':
      return 'mdi-check-circle'
    case 'failed':
      return 'mdi-alert-circle'
    case 'cancelled':
      return 'mdi-cancel'
    default:
      return 'mdi-circle-outline'
  }
}

function formatRelative(s: string | null): string {
  if (!s) return ''
  try {
    const d = new Date(s)
    const diff = Date.now() - d.getTime()
    if (diff < 60_000) return '刚刚'
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
    return d.toLocaleDateString('zh-CN')
  } catch {
    return s
  }
}

// ---------- 自动滚动 ----------
async function scrollToBottom() {
  await nextTick()
  const el = streamEl.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(
  () => messages.value.length,
  () => scrollToBottom(),
)
watch(
  () => pendingApprovals.value.length,
  () => scrollToBottom(),
)
// 流式文本变化时也滚动（深 watch content）
watch(
  () => messages.value.map((m) => m.content).join('|'),
  () => scrollToBottom(),
)
// 会话终态时刷新历史会话列表
watch(
  () => status.value,
  (newVal) => {
    if (TERMINAL.has(newVal)) {
      loadSessions()
    }
  },
)

// ---------- 交互 ----------
async function loadMeta() {
  loadingMeta.value = true
  try {
    const [types, sess] = await Promise.all([getTaskTypes(), listSessions(50)])
    taskTypes.value = types
    sessions.value = sess
  } catch (e: any) {
    error.value = e?.message || '加载元数据失败'
  } finally {
    loadingMeta.value = false
  }
}

async function loadSessions() {
  try {
    sessions.value = await listSessions(50)
  } catch (e: any) {
    error.value = e?.message || '加载历史失败'
  }
}

async function onStartTask(taskType: string) {
  starting.value = true
  error.value = ''
  try {
    reset()
    const sid = await startTask(taskType, provider.value)
    currentSid.value = sid
    await router.replace({ query: { ...route.query, session_id: String(sid) } })
    await loadSessions()
    await scrollToBottom()
  } catch (e: any) {
    error.value = e?.message || '启动任务失败'
  } finally {
    starting.value = false
  }
}

async function onSelectSession(sid: number) {
  if (sid === currentSid.value) return
  error.value = ''
  try {
    reset()
    currentSid.value = sid
    await connect(sid)
    await router.replace({ query: { ...route.query, session_id: String(sid) } })
    await scrollToBottom()
  } catch (e: any) {
    error.value = e?.message || '连接会话失败'
  }
}

async function onInterject() {
  if (!currentSid.value) return
  const text = interjectText.value.trim()
  if (!text) return
  sending.value = true
  try {
    await interject(currentSid.value, text)
    interjectText.value = ''
    await scrollToBottom()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '插话失败'
  } finally {
    sending.value = false
  }
}

async function onDecide(aid: number, approved: boolean) {
  try {
    await approve(aid, approved)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '审批失败'
  }
}

// ---------- 生命周期 ----------
onMounted(async () => {
  await loadMeta()
  // URL 带 session_id 时自动回放
  const sidParam = route.query.session_id
  if (sidParam) {
    const sid = Number(sidParam)
    if (Number.isFinite(sid) && sid > 0) {
      await onSelectSession(sid)
    }
  } else {
    // 自动接入进行中会话（若有）
    const live = sessions.value.find(
      (s) => !TERMINAL.has(s.status),
    )
    if (live) {
      await onSelectSession(live.id)
    }
  }
})

onUnmounted(() => {
  // composable 内已 disconnect
})
</script>

<style scoped>
.agent-container {
  height: calc(100vh - 64px);
  overflow: hidden;
}
.agent-row {
  height: 100%;
}
.agent-sidebar {
  border-right: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.sidebar-section {
  flex-shrink: 0;
}
.sidebar-history {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.history-list {
  overflow-y: auto;
  flex: 1;
}
.agent-main {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.status-bar {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  flex-shrink: 0;
}
.stream-area {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}
.interject-bar {
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  display: flex;
  align-items: flex-end;
  flex-shrink: 0;
  background: rgb(var(--v-theme-surface));
}

@media (max-width: 959px) {
  .agent-container {
    height: auto;
    min-height: calc(100vh - 56px);
  }
  .agent-row {
    height: auto;
  }
  .agent-main {
    min-height: calc(100vh - 56px - 220px);
  }
  .stream-area {
    padding: 8px 12px;
  }
}
</style>
