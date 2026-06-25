<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">数据维护中心</v-app-bar-title>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 成功提示 -->
    <v-alert v-if="successMessage" type="success" variant="tonal" class="mb-4" closable
             @click:close="successMessage = ''">
      {{ successMessage }}
    </v-alert>
    <!-- 错误提示 -->
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
              从服务器上的本地目录导入数据。目录路径取自配置文件
              <code>backend/.env</code> 的 <code>DATA_LOCAL_PATH</code>，
              与启动时导入共用同一来源（自动检测 HowToCook_json / 系统导出格式）。
            </p>
            <v-alert
              :type="localPathConfig.configured ? 'info' : 'warning'"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              <div v-if="!localPathConfig.loaded" class="text-caption">
                正在读取配置…
              </div>
              <div v-else-if="localPathConfig.configured" class="text-caption">
                将导入：<code>{{ localPathConfig.path }}</code>
              </div>
              <div v-else class="text-caption">
                未配置 <code>DATA_LOCAL_PATH</code>，请在
                <code>backend/.env</code> 设置后重启服务。
              </div>
            </v-alert>
            <v-alert type="info" variant="tonal" density="compact">
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
              :disabled="!localPathConfig.loaded || !localPathConfig.configured"
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

      <!-- USDA 数据管理 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="deep-orange">mdi-database</v-icon>
            <span>USDA 数据管理</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              管理 USDA 营养数据，包括下载原始数据和上传已处理的数据包。
            </p>
            <!-- Statistics -->
            <div v-if="usdaStats.total != null && usdaStats.total > 0" class="mb-4">
              <v-chip size="small" variant="tonal" class="mr-2 mb-2">
                食材: {{ usdaStats.total }}
              </v-chip>
              <v-chip size="small" variant="tonal" class="mr-2 mb-2">
                营养素: {{ usdaStats.nutrients || 0 }}
              </v-chip>
              <v-chip size="small" variant="tonal" class="mb-2">
                已映射: {{ usdaStats.mapped_pct || 0 }}%
              </v-chip>
            </div>
            <v-alert v-else type="info" variant="tonal" density="compact">
              <div class="text-caption">统计数据暂不可用，请先下载 USDA 数据。</div>
            </v-alert>
          </v-card-text>
          <v-divider />
          <v-card-actions class="pa-4">
            <v-spacer />
            <v-btn
              color="deep-orange"
              variant="tonal"
              size="large"
              :loading="usdaDownloading"
              :disabled="usdaDownloading"
              @click="downloadUsdaData"
            >
              <v-icon start>mdi-download</v-icon>
              下载 USDA
            </v-btn>
            <v-btn
              color="deep-orange"
              variant="tonal"
              size="large"
              :loading="usdaUploading"
              :disabled="usdaUploading"
              @click="triggerUsdaUpload"
              class="ml-2"
            >
              <v-icon start>mdi-upload</v-icon>
              上传 ZIP
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- AI 后处理 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="purple">mdi-robot</v-icon>
            <span>AI 后处理</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              使用 AI 推测原料的模糊用量和密度值，以及翻译 USDA 食材名和营养素名。
              请先在 AI 配置页启用相应的后端。
            </p>

            <!-- AI 推断后端选择 -->
            <v-select
              v-model="aiInferProvider"
              :items="enabledAiProviders"
              label="AI 推断后端"
              variant="outlined"
              prepend-icon="mdi-robot"
              hint="用于模糊量、密度、营养素翻译"
              persistent-hint
              hide-details
              class="mb-3"
            />

            <!-- 翻译后端选择 -->
            <v-select
              v-model="translateProvider"
              :items="enabledTranslateProviders"
              label="翻译后端"
              variant="outlined"
              prepend-icon="mdi-translate"
              hint="用于食材名翻译（AI + 机翻）"
              persistent-hint
              hide-details
              class="mb-3"
            />

            <v-checkbox v-model="aiForce" label="强制重新处理全部" hide-details class="mb-3" />

            <v-row>
              <v-col cols="6">
                <v-btn
                  block
                  color="purple"
                  variant="tonal"
                  :loading="submitting.aiPieceWeight"
                  :disabled="!enabledAiProviders.length"
                  @click="fillPieceWeight"
                >
                  <v-icon start>mdi-weight</v-icon>
                  自定义单位校准
                </v-btn>
              </v-col>
              <v-col cols="6">
                <v-btn
                  block
                  color="purple"
                  variant="tonal"
                  :loading="submitting.aiDensities"
                  :disabled="!enabledAiProviders.length"
                  @click="inferDensities"
                >
                  <v-icon start>mdi-database</v-icon>
                  推测密度
                </v-btn>
              </v-col>
            </v-row>
            <v-row class="mt-1">
              <v-col cols="6">
                <v-btn
                  block
                  color="purple"
                  variant="tonal"
                  :loading="submitting.translateFoods"
                  :disabled="!enabledTranslateProviders.length"
                  @click="onTranslateFoods"
                >
                  <v-icon start>mdi-food-apple</v-icon>
                  食材名翻译
                </v-btn>
              </v-col>
              <v-col cols="6">
                <v-btn
                  block
                  color="purple"
                  variant="tonal"
                  :loading="submitting.translateNutrients"
                  :disabled="!enabledTranslateProviders.length"
                  @click="onTranslateNutrients"
                >
                  <v-icon start>mdi-table</v-icon>
                  营养素翻译
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 未映射营养素 -->
      <v-col cols="12">
        <v-card v-if="unmappedNutrients.length" class="rounded-lg mb-4">
          <v-card-title
            class="d-flex align-center py-3 cursor-pointer"
            style="cursor: pointer;"
            @click="showUnmapped = !showUnmapped"
          >
            <v-icon class="mr-2" color="warning">mdi-alert-outline</v-icon>
            <span>未映射营养素（{{ unmappedNutrients.length }} 个）</span>
            <v-spacer />
            <v-icon>{{ showUnmapped ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
          </v-card-title>
          <v-divider v-if="showUnmapped" />
          <v-card-text v-if="showUnmapped" class="pt-4">
            <v-chip
              v-for="name in unmappedNutrients"
              :key="name"
              size="small"
              variant="tonal"
              color="warning"
              class="mr-2 mb-2"
            >
              {{ name }}
            </v-chip>
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
                v-for="t in mergedTasks"
                :key="t._kind === 'import' ? 'imp-' + t.id : t._kind === 'usda' ? 'usda-' + t.id : 'agt-' + t.session_id"
                class="mb-2 border rounded"
                :class="(t._kind === 'import' || t._kind === 'usda') ? taskRunningClass(t.status) : ''"
                :style="hasAgentLink(t) ? { cursor: 'pointer' } : {}"
                @click="onTaskClick(t)"
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
                  <!-- usda 任务：完成统计 / 错误 / 运行中提示 -->
                  <template v-else-if="t._kind === 'usda'">
                    <div v-if="t.progress?.foods != null" class="text-caption mt-1">
                      食材: {{ t.progress.foods }}
                    </div>
                    <div v-if="t.error" class="text-caption text-error mt-1">{{ t.error }}</div>
                    <div v-else-if="t.status === 'running' || t.status === 'pending'" class="text-caption text-medium-emphasis mt-1">
                      后台处理中…
                    </div>
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
                  <v-btn
                    v-if="(t.status === 'running' || t.status === 'pending') && t._kind !== 'usda'"
                    icon="mdi-close-circle-outline" size="small" variant="text"
                    color="grey"
                    @click.stop="cancelTask(t)"
                  />
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
import {
  getTranslationConfig,
  getUsdaStatistics,
  getUnmappedNutrients,
  downloadUsda,
  uploadUsda,
  getUsdaTasks,
  getUsdaTaskById,
} from '@/api/usda'
import { createSession, getSession, listSessions, cancelSession } from '@/api/agent'
import api from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { tasks, fetchTasks, startTask, startUploadTask } = useImportTask()
const router = useRouter()

const goBack = () => router.back()

// 各卡片提交中状态
const submitting = reactive({ aiPieceWeight: false,
  repo: false,
  local: false,
  upload: false,
  aiQuantities: false,
  aiDensities: false,
  translateFoods: false,
  translateNutrients: false,
})

// 简短错误提示（仅在启动任务失败时显示）
const errorMessage = ref('')
const successMessage = ref('')

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

interface UsdaTaskItem {
  id: number
  task_type: string
  status: 'pending' | 'running' | 'success' | 'failed'
  progress?: Record<string, any> | null
  error?: string | null
  created_at: string
}

const usdaTasks = ref<UsdaTaskItem[]>([])
const usdaPollingMap = new Map<number, ReturnType<typeof setInterval>>()

// 本地导入路径配置（从后端 GET /import/data/local-path-config 读取，只读展示）
const localPathConfig = reactive({
  loaded: false,
  configured: false,
  path: '',
})
const uploadFile = ref<File | null>(null)
const aiForce = ref(false)

// AI 提供方选择（从翻译配置读取）
const aiInferProvider = ref('')
const translateProvider = ref('')
const translationConfig = ref<any>(null)

// USDA 状态
const usdaStats = ref<any>({})
const unmappedNutrients = ref<string[]>([])
const showUnmapped = ref(false)
const usdaDownloading = ref(false)
const usdaUploading = ref(false)

const AGENT_TASK_TYPES = ['fill_piece_weight', 'infer_densities', 'usda_translate', 'unmapped_nutrient_translate']
const TASK_LABELS: Record<string, string> = {
  fill_piece_weight: 'Agent 自定义单位校准',
  infer_densities: 'Agent 密度推测',
  usda_translate: 'Agent 食材名翻译',
  unmapped_nutrient_translate: 'Agent 营养素翻译',
}

function enabledIn(region: string): string[] {
  const cfg = translationConfig.value
  if (!cfg) return []
  const provs = cfg[region]?.providers || {}
  return Object.entries(provs)
    .filter(([, v]: any) => v.enabled !== false)
    .map(([k]) => k)
}

const enabledAiProviders = computed<string[]>(() => enabledIn('ai'))
const enabledTranslateProviders = computed<string[]>(() => [...enabledIn('ai'), ...enabledIn('machine')])

onMounted(async () => {
  // 加载近期任务列表，恢复对运行中任务的轮询
  fetchTasks(10)

  // 加载本地导入路径配置（只读展示用，失败降级为「未配置」）
  api
    .get('/import/data/local-path-config')
    .then((cfg: any) => {
      localPathConfig.configured = !!cfg?.configured
      localPathConfig.path = cfg?.path || ''
    })
    .catch(() => {
      localPathConfig.configured = false
    })
    .finally(() => {
      localPathConfig.loaded = true
    })

  // 加载翻译配置
  try {
    translationConfig.value = await getTranslationConfig()
    if (enabledAiProviders.value.length) {
      aiInferProvider.value = enabledAiProviders.value[0]
    }
    if (enabledTranslateProviders.value.length) {
      translateProvider.value = enabledTranslateProviders.value[0]
    }
  } catch {
    // 忽略错误
  }

  // 加载 USDA 统计
  try {
    const stats = await getUsdaStatistics()
    usdaStats.value = {
      ...stats,
      mapped_pct: stats.total > 0 ? Math.round((stats.translated / stats.total) * 100) : 0,
    }
  } catch {
    // 忽略错误
  }

  // 加载未映射营养素
  try {
    unmappedNutrients.value = await getUnmappedNutrients()
  } catch {
    // 忽略错误
  }

  // 恢复最近的 agent 会话到任务列表（刷新后重建）
  try {
    const recent = await listSessions(20)
    const relevant = recent.filter(
      (s) => AGENT_TASK_TYPES.includes(s.task_type) && !(s.title || '').startsWith('[后台]')
    )
    for (const s of relevant) {
      if (!agentTasks.value.find((t) => t.session_id === s.id)) {
        agentTasks.value.push({
          session_id: s.id,
          task_type: s.task_type,
          label: TASK_LABELS[s.task_type] || s.task_type,
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

  // 恢复最近的 USDA 任务（下载 / 上传）到任务列表（刷新后重建）
  try {
    const usdaRecent: any[] = await getUsdaTasks(20)
    for (const s of usdaRecent || []) {
      // 翻译类 UsdaTask 是内部实现细节，不在任务列表显示（由 ImportTask + AgentSession 承载）。
      if (s.task_type === 'translate' || s.task_type === 'translate_nutrients') continue
      if (!usdaTasks.value.find((t) => t.id === s.id)) {
        usdaTasks.value.push({
          id: s.id,
          task_type: s.task_type,
          status: s.status,
          progress: s.progress,
          error: s.error_log || null,
          created_at: s.created_at || new Date().toISOString(),
        })
      }
    }
  } catch {
    // 列表加载失败不阻塞
  }

  // 恢复 USDA 运行中任务的轮询
  usdaTasks.value
    .filter((t) => t.status === 'running' || t.status === 'pending')
    .forEach((t) => startUsdaPolling(t.id))
})

onUnmounted(() => {
  agentPollingMap.forEach((interval) => clearInterval(interval))
  agentPollingMap.clear()
  usdaPollingMap.forEach((interval) => clearInterval(interval))
  usdaPollingMap.clear()
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
  const taskId = await startTask('/import/data/import-from-local')
  if (!taskId) {
    errorMessage.value = '本地导入任务启动失败，请检查后端状态与 DATA_LOCAL_PATH 配置'
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

async function fillPieceWeight() {
    submitting.aiPieceWeight = true
    try {
      const { session_id } = await createSession('fill_piece_weight', aiForce.value)
      agentTasks.value.unshift({
        session_id,
        task_type: 'fill_piece_weight',
        label: TASK_LABELS.fill_piece_weight + (aiForce.value ? ' (强制)' : ''),
        status: 'pending',
        created_at: new Date().toISOString(),
      })
      await refreshSessions()
    } finally {
      submitting.aiPieceWeight = false
    }
  }

async function inferDensities() {
  submitting.aiDensities = true
  try {
    const provider = aiInferProvider.value || 'claude_code'
    if (provider === 'claude_code') {
      const { session_id } = await createSession('infer_densities', aiForce.value)
      agentTasks.value.unshift({
        session_id,
        task_type: 'infer_densities',
        label: 'Agent 密度推测',
        status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      const taskId = await startTask('/import/ai-infer/densities', {
        params: { force: aiForce.value, provider },
      })
      if (!taskId) {
        errorMessage.value = '密度推测任务启动失败'
      }
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '密度推测任务启动失败'
  }
  submitting.aiDensities = false
}

async function onTranslateFoods() {
  submitting.translateFoods = true
  try {
    const provider = translateProvider.value || 'claude_code'
    if (provider === 'claude_code') {
      const { session_id } = await createSession('usda_translate', aiForce.value)
      agentTasks.value.unshift({
        session_id,
        task_type: 'usda_translate',
        label: 'Agent 食材名翻译',
        status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      const taskId = await startTask('/import/translate/foods', {
        params: { provider, force: aiForce.value },
      })
      if (!taskId) {
        errorMessage.value = '食材名翻译任务启动失败'
      } else {
        successMessage.value = '食材名翻译任务已启动'
      }
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '食材名翻译任务启动失败'
  }
  submitting.translateFoods = false
}

async function onTranslateNutrients() {
  submitting.translateNutrients = true
  try {
    const provider = translateProvider.value || 'claude_code'
    if (provider === 'claude_code') {
      const { session_id } = await createSession('unmapped_nutrient_translate', aiForce.value)
      agentTasks.value.unshift({
        session_id,
        task_type: 'unmapped_nutrient_translate',
        label: 'Agent 营养素翻译',
        status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      const taskId = await startTask('/import/translate/nutrients', {
        params: { provider, force: aiForce.value },
      })
      if (!taskId) {
        errorMessage.value = '营养素翻译任务启动失败'
      } else {
        successMessage.value = '营养素翻译任务已启动'
      }
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '营养素翻译任务启动失败'
  }
  submitting.translateNutrients = false
}

// === USDA 操作 ===

async function loadUsdaStats() {
  try {
    const stats = await getUsdaStatistics()
    usdaStats.value = {
      ...stats,
      mapped_pct: stats.total > 0 ? Math.round((stats.translated / stats.total) * 100) : 0,
    }
  } catch {
    // 忽略
  }
}

async function loadUnmapped() {
  try {
    unmappedNutrients.value = await getUnmappedNutrients()
  } catch {
    // 忽略
  }
}

async function downloadUsdaData() {
  usdaDownloading.value = true
  try {
    const data: any = await downloadUsda()
    if (data?.task_id) {
      addUsdaTask(data.task_id, 'download')
    }
    successMessage.value = 'USDA 数据下载任务已启动'
  } catch (e: any) {
    errorMessage.value = e?.userMessage || 'USDA 数据下载失败'
  } finally {
    usdaDownloading.value = false
  }
}

function triggerUsdaUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.zip'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    usdaUploading.value = true
    try {
      const data: any = await uploadUsda(file)
      if (data?.task_id) {
        addUsdaTask(data.task_id, 'upload')
      }
      successMessage.value = 'USDA 数据上传成功'
      loadUsdaStats()
    } catch (e: any) {
      errorMessage.value = e?.response?.data?.detail || 'USDA 数据上传失败'
    } finally {
      usdaUploading.value = false
    }
  }
  input.click()
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

// === USDA 任务（下载 / 上传）入列 + 轮询 ===

function addUsdaTask(taskId: number, taskType: string) {
  if (usdaTasks.value.find((t) => t.id === taskId)) return
  usdaTasks.value.unshift({
    id: taskId,
    task_type: taskType,
    status: 'running',
    progress: null,
    error: null,
    created_at: new Date().toISOString(),
  })
  startUsdaPolling(taskId)
}

function startUsdaPolling(taskId: number) {
  if (usdaPollingMap.has(taskId)) return
  const interval = setInterval(async () => {
    try {
      const data: any = await getUsdaTaskById(taskId)
      const idx = usdaTasks.value.findIndex((t) => t.id === taskId)
      if (idx >= 0) {
        usdaTasks.value[idx] = {
          ...usdaTasks.value[idx],
          status: data.status,
          progress: data.progress,
          error: data.error_log || null,
        }
      }
      if (data.status === 'success' || data.status === 'failed') {
        stopUsdaPolling(taskId)
        loadUsdaStats()
      }
    } catch {
      stopUsdaPolling(taskId)
    }
  }, 3000)
  usdaPollingMap.set(taskId, interval)
}

function stopUsdaPolling(taskId: number) {
  const interval = usdaPollingMap.get(taskId)
  if (interval) {
    clearInterval(interval)
    usdaPollingMap.delete(taskId)
  }
}

// === 取消任务 ===

async function cancelTask(t: any) {
  try {
    if (t._kind === 'agent') {
      await cancelSession(t.session_id)
      stopAgentPolling(t.session_id)
      const idx = agentTasks.value.findIndex(x => x.session_id === t.session_id)
      if (idx >= 0) agentTasks.value[idx] = { ...agentTasks.value[idx], status: 'cancelled' }
    } else {
      await api.post(`/import/task/${t.id}/cancel`)
      successMessage.value = '任务已取消'
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '取消失败'
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

interface UsdaTaskLike extends UsdaTaskItem {
  _kind: 'usda'
}

type MergedTask = ImportTaskLike | AgentTaskLike | UsdaTaskLike

const mergedTasks = computed<MergedTask[]>(() => {
  const imports: ImportTaskLike[] = tasks.value.map(t => ({ ...t, _kind: 'import' as const }))
  // 排除已被 ImportTask 的 stats.agent_session_id 关联的 Agent（避免同一操作显示两条）。
  const _importAgentIds = new Set(
    imports.filter(t => t.stats?.agent_session_id).map(t => t.stats!.agent_session_id!)
  )
  const agents: AgentTaskLike[] = agentTasks.value
    .filter(t => !_importAgentIds.has(t.session_id))
    .map(t => ({ ...t, _kind: 'agent' as const }))
  const usdas: UsdaTaskLike[] = usdaTasks.value
    .filter(t => t.task_type !== 'translate' && t.task_type !== 'translate_nutrients')
    .map(t => ({ ...t, _kind: 'usda' as const }))
  return [...imports, ...agents, ...usdas].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
})

// 是否可跳转到任务台对话：agent 任务，或带 agent_session_id 的 import 任务（AI 推测
// 走 Agent 路径时，inferrer 把 [后台] AgentSession.id 写进 ImportTask.stats.agent_session_id）。
function hasAgentLink(t: MergedTask): boolean {
  if (t._kind === 'agent') return true
  if (t._kind === 'import') return !!t.stats?.agent_session_id
  return false
}

// 点击任务条目跳转任务台对话。
function onTaskClick(t: MergedTask) {
  if (t._kind === 'agent') {
    router.push('/admin/agent-console?session_id=' + t.session_id)
  } else if (t._kind === 'import' && t.stats?.agent_session_id) {
    router.push('/admin/agent-console?session_id=' + t.stats.agent_session_id)
  }
}

const taskTypeLabels: Record<string, string> = {
  git_import: 'Git 仓库导入',
  local_import: '本地路径导入',
  upload_import: '上传导入',
  ai_quantities: 'AI 模糊量推测',
  ai_densities: 'AI 密度推测',
  usda_translate: '食材名翻译',
  nutrient_translate: '营养素翻译',
  download: 'USDA 数据下载',
  upload: 'USDA 数据上传',
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
