<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">菜谱导入管理</v-app-bar-title>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 简短的错误提示 -->
    <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4" closable
             @click:close="errorMessage = ''">
      {{ errorMessage }}
    </v-alert>

    <v-row>
      <!-- 从仓库导入 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="github">mdi-source-repository</v-icon>
            <span>从 Git 仓库导入</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              从环境变量配置的 Git 仓库导入菜谱数据。
              仓库地址、分支和数据目录由服务器配置（<code>DATA_REPO_URL</code>、
              <code>DATA_REPO_BRANCH</code>、<code>DATA_REPO_DIR</code>）。
            </p>
            <v-alert type="info" variant="tonal" density="compact">
              <div class="text-caption">
                支持格式：HowToCook_json / 系统导出格式（自动检测）
              </div>
            </v-alert>
          </v-card-text>
          <v-divider />
          <v-card-actions class="pa-4">
            <v-spacer />
            <v-btn
              color="github"
              variant="tonal"
              size="large"
              :loading="submitting.repo"
              @click="importFromRepo"
            >
              <v-icon start>mdi-source-repository</v-icon>
              开始导入
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- 从本地路径导入 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="primary">mdi-folder-open</v-icon>
            <span>从本地路径导入</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              从服务器上的本地目录导入数据。目录结构可以是
              HowToCook_json 格式或系统导出格式（自动检测）。
            </p>
            <v-text-field
              v-model="localPath"
              label="本地目录绝对路径"
              variant="outlined"
              placeholder="/data/recipes/out"
              prepend-icon="mdi-folder-path"
              hint="输入服务器上的数据目录路径"
              persistent-hint
              :disabled="submitting.local"
            />
            <v-alert type="info" variant="tonal" class="mt-4" density="compact">
              <div class="text-caption">
                支持格式：HowToCook_json（ingredients.json + 菜谱 JSON）/<br />
                系统导出格式（manifest.json）
              </div>
            </v-alert>
          </v-card-text>
          <v-divider />
          <v-card-actions class="pa-4">
            <v-spacer />
            <v-btn
              color="primary"
              variant="tonal"
              size="large"
              :loading="submitting.local"
              :disabled="!localPath.trim()"
              @click="importFromLocalPath"
            >
              <v-icon start>mdi-folder-open</v-icon>
              开始导入
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- 上传 ZIP 导入 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="success">mdi-upload</v-icon>
            <span>上传压缩包导入</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              上传 ZIP 压缩包导入数据。支持 HowToCook_json 格式的压缩包，
              以及通过系统导出功能生成的压缩包（含价格记录等数据）。
            </p>
            <v-file-input
              v-model="uploadFile"
              label="选择 ZIP 文件"
              accept=".zip"
              variant="outlined"
              prepend-icon="mdi-zip-box"
              :loading="submitting.upload"
              :disabled="submitting.upload"
              hide-details
            />
          </v-card-text>
          <v-divider />
          <v-card-actions class="pa-4">
            <v-spacer />
            <v-btn
              color="success"
              variant="tonal"
              size="large"
              :loading="submitting.upload"
              :disabled="!uploadFile"
              @click="uploadImport"
            >
              <v-icon start>mdi-upload</v-icon>
              上传并导入
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- AI 后处理 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="purple">mdi-robot</v-icon>
            <span>AI 推测处理</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              使用 AI 推测原料的模糊用量（如鸡蛋 1 个 ≈ 55g）和密度值
              （如食用油 ≈ 0.92 g/cm³）。请先在 AI 配置页启用至少一个后端。
            </p>

            <!-- AI 提供方选择 -->
            <v-select
              v-model="aiProvider"
              :items="enabledProviders"
              label="AI 提供方"
              variant="outlined"
              prepend-icon="mdi-robot"
              :hint="enabledProviders.length ? '' : '请先在 AI 配置页启用后端'"
              persistent-hint
              hide-details
              class="mb-3"
            />

            <v-row>
              <v-col cols="6">
                <v-btn
                  block
                  color="purple"
                  variant="tonal"
                  :loading="submitting.aiQuantities"
                  :disabled="!enabledProviders.length"
                  @click="inferQuantities"
                >
                  <v-icon start>mdi-scale</v-icon>
                  推测模糊量
                </v-btn>
              </v-col>
              <v-col cols="6">
                <v-btn
                  block
                  color="purple"
                  variant="tonal"
                  :loading="submitting.aiDensities"
                  :disabled="!enabledProviders.length"
                  @click="inferDensities"
                >
                  <v-icon start>mdi-database</v-icon>
                  推测密度
                </v-btn>
              </v-col>
            </v-row>
            <v-checkbox v-model="aiForce" label="强制重新处理全部" hide-details class="mt-2" />
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 任务列表 -->
      <v-col cols="12">
        <v-card class="rounded-lg">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2">mdi-format-list-bulleted</v-icon>
            <span>任务列表</span>
            <v-spacer />
            <v-btn variant="text" size="small" @click="fetchTasks(10)">刷新</v-btn>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-4">
            <v-alert v-if="mergedTasks.length === 0" type="info" variant="tonal" density="compact">
              暂无任务记录
            </v-alert>
            <v-list v-else>
              <v-list-item
                v-for="t in mergedTasks" :key="t._kind === 'import' ? 'imp-' + t.id : 'agt-' + t.session_id"
                class="mb-2 border rounded"
                :class="t._kind === 'import' ? taskRunningClass(t.status) : ''"
                :style="t._kind === 'agent' ? { cursor: 'pointer' } : {}"
                @click="t._kind === 'agent' ? router.push('/admin/agent-console?session_id=' + t.session_id) : undefined"
              >
                <template #prepend>
                  <v-icon :color="statusColor(t.status)" class="mr-3">
                    {{ statusIcon(t.status) }}
                  </v-icon>
                </template>
                <v-list-item-title class="font-weight-medium">
                  {{ t._kind === 'agent' ? t.label : taskTypeLabel(t.task_type) }}
                  <v-chip :color="statusColor(t.status)" size="x-small" variant="tonal" class="ml-2">
                    {{ statusLabel(t.status) }}
                  </v-chip>
                </v-list-item-title>
                <v-list-item-subtitle>
                  <!-- import 任务：进度条 / 统计 / 错误 -->
                  <template v-if="t._kind === 'import'">
                    <div v-if="t.progress?.stage" class="text-caption mt-1">
                      {{ t.progress.stage }}: {{ t.progress.message }}
                    </div>
                    <div v-if="t.progress?.total > 0" class="mt-1">
                      <v-progress-linear
                        :model-value="Math.round((t.progress.current / t.progress.total) * 100)"
                        height="6" rounded color="primary"
                      />
                      <div class="text-caption text-medium-emphasis mt-1">
                        {{ t.progress.current }} / {{ t.progress.total }}
                        ({{ Math.round((t.progress.current / t.progress.total) * 100) }}%)
                      </div>
                    </div>
                    <div v-if="t.stats && Object.keys(t.stats).length" class="text-caption mt-1">
                      <v-chip v-for="(v, k) in t.stats" :key="k" size="x-small" variant="tonal"
                              class="mr-1 mb-1">{{ k }}: {{ v }}</v-chip>
                    </div>
                    <div v-if="t.error" class="text-caption text-error mt-1">{{ t.error }}</div>
                  </template>
                  <!-- agent 任务：简洁状态 -->
                  <template v-else>
                    <div v-if="agentErrorMap[t.session_id]" class="text-caption text-error mt-1">
                      {{ agentErrorMap[t.session_id] }}
                    </div>
                    <div class="text-caption text-medium-emphasis mt-1">点击查看实时详情</div>
                  </template>
                  <div class="text-caption text-medium-emphasis mt-1">{{ formatTime(t.created_at) }}</div>
                </v-list-item-subtitle>
                <template #append>
                  <v-progress-circular
                    v-if="t.status === 'running' || t.status === 'pending'"
                    indeterminate size="20" width="2" color="primary"
                  />
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useImportTask } from '@/composables/useImportTask'
import { getTranslationConfig } from '@/api/usda'
import { createSession, getSession, listSessions } from '@/api/agent'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { tasks, fetchTasks, startTask, startUploadTask } = useImportTask()
const router = useRouter()

const goBack = () => router.back()

// 各卡片提交中状态
const submitting = reactive({
  repo: false,
  local: false,
  upload: false,
  aiQuantities: false,
  aiDensities: false,
})

// 简短错误提示（仅在启动任务失败时显示）
const errorMessage = ref('')

interface AgentTaskItem {
  session_id: number
  task_type: string
  label: string
  status: 'pending' | 'running' | 'success' | 'failed'
  created_at: string
}

const agentTasks = ref<AgentTaskItem[]>([])
const agentPollingMap = new Map<number, ReturnType<typeof setInterval>>()
const agentErrorMap = ref<Record<number, string>>({})

const localPath = ref('')
const uploadFile = ref<File | null>(null)
const aiForce = ref(false)

// AI 提供方选择（从翻译配置读取）
const aiProvider = ref('')
const translationConfig = ref<any>(null)

function enabledIn(region: string): string[] {
  const cfg = translationConfig.value
  if (!cfg) return []
  const provs = cfg[region]?.providers || {}
  return Object.entries(provs)
    .filter(([, v]: any) => v.enabled !== false)
    .map(([k]) => k)
}

const enabledProviders = computed<string[]>(() => enabledIn('ai'))

onMounted(async () => {
  // 加载近期任务列表，恢复对运行中任务的轮询
  fetchTasks(10)
  // 加载 AI 配置
  try {
    translationConfig.value = await getTranslationConfig()
    if (enabledProviders.value.length) {
      aiProvider.value = enabledProviders.value[0]
    }
  } catch {
    // 忽略错误，用户会看到"请先在 AI 配置页启用后端"
  }

  // 恢复最近的 agent 会话到任务列表（刷新后重建）
  try {
    const recent = await listSessions(20)
    const relevant = recent.filter(
      (s) => s.task_type === 'infer_quantities' || s.task_type === 'infer_densities',
    )
    for (const s of relevant) {
      if (!agentTasks.value.find((t) => t.session_id === s.id)) {
        agentTasks.value.push({
          session_id: s.id,
          task_type: s.task_type,
          label: s.task_type === 'infer_quantities' ? 'Agent 模糊量推测' : 'Agent 密度推测',
          status: s.status === 'completed' ? 'success' : (s.status as any),
          created_at: s.created_at || new Date().toISOString(),
        })
      }
    }
  } catch {
    // 列表加载失败不阻塞
  }

  // 恢复 agent 任务的轮询
  const pendingAgent = agentTasks.value.filter(
    (t) => t.status === 'pending' || t.status === 'running'
  )
  pendingAgent.forEach((t) => startAgentPolling(t.session_id))
})

onUnmounted(() => {
  agentPollingMap.forEach((interval) => clearInterval(interval))
  agentPollingMap.clear()
})

// === 任务操作 ===

async function importFromRepo() {
  submitting.repo = true
  const taskId = await startTask('/import/data/import-from-repo')
  if (!taskId) {
    errorMessage.value = '仓库导入任务启动失败，请检查后端状态'
  }
  submitting.repo = false
}

async function importFromLocalPath() {
  submitting.local = true
  const taskId = await startTask('/import/data/import-from-local', {
    params: { local_path: localPath.value.trim() },
  })
  if (!taskId) {
    errorMessage.value = '本地导入任务启动失败，请检查路径和后端状态'
  }
  submitting.local = false
}

async function uploadImport() {
  if (!uploadFile.value) return
  submitting.upload = true
  const taskId = await startUploadTask(uploadFile.value)
  if (taskId) {
    uploadFile.value = null
  } else {
    errorMessage.value = '上传导入任务启动失败，请检查文件和后端状态'
  }
  submitting.upload = false
}

async function inferQuantities() {
  submitting.aiQuantities = true
  try {
    const provider = aiProvider.value || 'claude_code'
    if (provider === 'claude_code') {
      // Agent 路径：使用 Claude Code CLI 批量推测
      const { session_id } = await createSession('infer_quantities', aiForce.value)
      agentTasks.value.unshift({
        session_id,
        task_type: 'infer_quantities',
        label: 'Agent 模糊量推测',
        status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      // 旧 AIInferrer 路径：串行逐组推测（适用于 OpenAI 等非 claude_code 提供方）
      const taskId = await startTask('/import/ai-infer/quantities', {
        params: { force: aiForce.value, provider },
      })
      if (!taskId) {
        errorMessage.value = 'AI 模糊量推测任务启动失败，请检查后端状态'
      }
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '模糊量推测任务启动失败'
  }
  submitting.aiQuantities = false
}

async function inferDensities() {
  submitting.aiDensities = true
  const taskId = await startTask('/import/ai-infer/densities', {
    params: { force: aiForce.value, provider: aiProvider.value || 'claude_code' },
  })
  if (!taskId) {
    errorMessage.value = 'AI 密度推测任务启动失败，请检查后端状态'
  }
  submitting.aiDensities = false
}

// === Agent 轮询 ===

function startAgentPolling(sessionId: number) {
  if (agentPollingMap.has(sessionId)) return
  const interval = setInterval(async () => {
    try {
      const data = await getSession(sessionId) as any
      const idx = agentTasks.value.findIndex(t => t.session_id === sessionId)
      if (idx >= 0) {
        const status = data.status === 'completed' ? 'success' : data.status
        if (status !== agentTasks.value[idx].status) {
          agentTasks.value[idx] = { ...agentTasks.value[idx], status }
        }
        if (data.error) {
          agentErrorMap.value[sessionId] = data.error
        }
      }
      if (data.status === 'success' || data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
        stopAgentPolling(sessionId)
      }
    } catch {
      // On polling failure, mark as failed so it doesn't stay pending forever
      const idx = agentTasks.value.findIndex(t => t.session_id === sessionId)
      if (idx >= 0) {
        agentTasks.value[idx] = { ...agentTasks.value[idx], status: 'failed' }
      }
      stopAgentPolling(sessionId)
    }
  }, 3000)
  agentPollingMap.set(sessionId, interval)
}

function stopAgentPolling(sessionId: number) {
  const interval = agentPollingMap.get(sessionId)
  if (interval) {
    clearInterval(interval)
    agentPollingMap.delete(sessionId)
  }
}

// === 辅助函数 ===

interface ImportTaskLike {
  id: number
  task_type: string
  status: string
  progress?: { stage: string; current: number; total: number; message: string }
  stats?: Record<string, number>
  error?: string | null
  created_at: string
  _kind: 'import'
}

interface AgentTaskLike extends AgentTaskItem {
  _kind: 'agent'
}

type MergedTask = ImportTaskLike | AgentTaskLike

const mergedTasks = computed<MergedTask[]>(() => {
  const imports: ImportTaskLike[] = tasks.value.map(t => ({ ...t, _kind: 'import' as const }))
  const agents: AgentTaskLike[] = agentTasks.value.map(t => ({ ...t, _kind: 'agent' as const }))
  return [...imports, ...agents].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
})

const taskTypeLabels: Record<string, string> = {
  git_import: 'Git 仓库导入',
  local_import: '本地路径导入',
  upload_import: '上传导入',
  ai_quantities: 'AI 模糊量推测',
  ai_densities: 'AI 密度推测',
}

function taskTypeLabel(type: string): string {
  return taskTypeLabels[type] || type
}

const statusConfig: Record<string, { color: string; icon: string; label: string }> = {
  pending: { color: 'grey', icon: 'mdi-clock-outline', label: '等待中' },
  running: { color: 'primary', icon: 'mdi-loading', label: '运行中' },
  success: { color: 'success', icon: 'mdi-check-circle', label: '完成' },
  failed: { color: 'error', icon: 'mdi-alert-circle', label: '失败' },
  cancelled: { color: 'warning', icon: 'mdi-cancel', label: '已取消' },
}

function statusColor(status: string): string {
  return statusConfig[status]?.color || 'grey'
}

function statusIcon(status: string): string {
  return statusConfig[status]?.icon || 'mdi-help-circle'
}

function statusLabel(status: string): string {
  return statusConfig[status]?.label || status
}

function taskRunningClass(status: string): string {
  return status === 'running' ? 'status-running' : ''
}

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return iso
  }
}
</script>

<style scoped>
.v-theme--light .v-btn.color-github {
  color: rgb(31, 31, 31);
}
.v-theme--dark .v-btn.color-github {
  color: rgb(220, 220, 220);
}
.v-theme--light .v-btn.color-github.v-btn--variant-tonal {
  background-color: rgb(31, 31, 31);
  color: white;
}
.v-theme--dark .v-btn.color-github.v-btn--variant-tonal {
  background-color: rgb(220, 220, 220);
  color: black;
}

/* 运行中任务脉冲动画 */
:deep(.v-list-item.status-running) {
  animation: pulse-bg 2s ease-in-out infinite;
}

@keyframes pulse-bg {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.65; }
}
</style>
