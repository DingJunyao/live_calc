<template>
  <!-- 顶部导航栏 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">图片存储配置</v-app-bar-title>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 当前配置展示卡 -->
    <v-card class="rounded-lg mb-4">
      <v-card-title class="d-flex align-center py-4">
        <v-icon class="mr-2">mdi-cloud-outline</v-icon>
        <span>当前配置</span>
      </v-card-title>
      <v-divider />
      <v-card-text class="pt-4">
        <v-row v-if="config">
          <v-col cols="12" sm="6">
            <div class="text-caption text-medium-emphasis mb-1">存储后端</div>
            <div class="text-h6">{{ config.backend === 'local' ? '本地存储' : 'S3 对象存储' }}</div>
          </v-col>

          <v-col cols="12" sm="6" v-if="config.backend === 'local'">
            <div class="text-caption text-medium-emphasis mb-1">
              storage_base_url
              <v-chip size="x-small" :color="sourceColor(config.sources?.storage_base_url)" class="ml-2">
                {{ sourceLabel(config.sources?.storage_base_url) }}
              </v-chip>
            </div>
            <div class="text-body-2">{{ config.storage_base_url || '(未设置)' }}</div>
          </v-col>

          <template v-if="config.backend === 's3'">
            <v-col cols="12" sm="6">
              <div class="text-caption text-medium-emphasis mb-1">
                endpoint
                <v-chip size="x-small" :color="sourceColor(config.sources?.s3_endpoint)" class="ml-2">
                  {{ sourceLabel(config.sources?.s3_endpoint) }}
                </v-chip>
              </div>
              <div class="text-body-2">{{ config.s3_endpoint || '(未设置)' }}</div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-caption text-medium-emphasis mb-1">
                bucket
                <v-chip size="x-small" :color="sourceColor(config.sources?.s3_bucket)" class="ml-2">
                  {{ sourceLabel(config.sources?.s3_bucket) }}
                </v-chip>
              </div>
              <div class="text-body-2">{{ config.s3_bucket || '(未设置)' }}</div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-caption text-medium-emphasis mb-1">
                region
                <v-chip size="x-small" :color="sourceColor(config.sources?.s3_region)" class="ml-2">
                  {{ sourceLabel(config.sources?.s3_region) }}
                </v-chip>
              </div>
              <div class="text-body-2">{{ config.s3_region || '(未设置)' }}</div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-caption text-medium-emphasis mb-1">
                url_style
                <v-chip size="x-small" :color="sourceColor(config.sources?.s3_url_style)" class="ml-2">
                  {{ sourceLabel(config.sources?.s3_url_style) }}
                </v-chip>
              </div>
              <div class="text-body-2">{{ config.s3_url_style === 'path' ? 'Path' : 'Virtual-hosted' }}</div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-caption text-medium-emphasis mb-1">
                access_key
                <v-chip size="x-small" :color="sourceColor(config.sources?.s3_access_key)" class="ml-2">
                  {{ sourceLabel(config.sources?.s3_access_key) }}
                </v-chip>
              </div>
              <div class="text-body-2">
                {{ config.has_access_key ? '*** 已设置 ***' : '未设置' }}
              </div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-caption text-medium-emphasis mb-1">
                secret_key
                <v-chip size="x-small" :color="sourceColor(config.sources?.s3_secret_key)" class="ml-2">
                  {{ sourceLabel(config.sources?.s3_secret_key) }}
                </v-chip>
              </div>
              <div class="text-body-2">
                {{ config.has_secret_key ? '*** 已设置 ***' : '未设置' }}
              </div>
            </v-col>
          </template>
        </v-row>

        <v-alert v-if="!config" type="info" text="正在加载配置..." class="mt-4" />
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" variant="tonal" @click="openWizard">
          <v-icon start>mdi-swap-horizontal</v-icon>
          切换存储后端
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- 向导弹窗 -->
    <v-dialog v-model="wizardDialog" max-width="800px" persistent>
      <v-card>
        <v-card-title class="d-flex align-center py-4">
          <v-icon class="mr-2">mdi-cloud-sync</v-icon>
          <span>切换存储后端向导</span>
        </v-card-title>
        <v-divider />

        <v-card-text class="pa-4">
          <!-- 步骤指示器 -->
          <v-stepper v-model="wizardStep" :items="wizardItems" class="elevation-0" />

          <!-- 步骤 1: 选目标 backend -->
          <div v-if="wizardStep === 1" class="mt-4">
            <div class="text-h6 mb-4">选择目标存储后端</div>
            <v-radio-group v-model="wizardConfig.targetBackend">
              <v-radio label="本地存储" value="local">
                <template #label>
                  <div class="d-flex align-center">
                    <v-icon class="mr-2">mdi-harddisk</v-icon>
                    <span>本地存储</span>
                  </div>
                </template>
              </v-radio>
              <v-radio label="S3 对象存储" value="s3">
                <template #label>
                  <div class="d-flex align-center">
                    <v-icon class="mr-2">mdi-cloud</v-icon>
                    <span>S3 对象存储</span>
                  </div>
                </template>
              </v-radio>
            </v-radio-group>
          </div>

          <!-- 步骤 2: 填目标配置 -->
          <div v-if="wizardStep === 2" class="mt-4">
            <div class="text-h6 mb-4">填写目标配置</div>

            <!-- S3 配置 -->
            <template v-if="wizardConfig.targetBackend === 's3'">
              <v-text-field
                v-model="wizardConfig.s3_endpoint"
                label="endpoint"
                variant="outlined"
                hint="S3 服务端点（如 https://s3.amazonaws.com）"
                persistent-hint
                class="mb-2"
              />
              <v-text-field
                v-model="wizardConfig.s3_bucket"
                label="bucket"
                variant="outlined"
                hint="存储桶名称"
                persistent-hint
                class="mb-2"
              />
              <v-text-field
                v-model="wizardConfig.s3_region"
                label="region"
                variant="outlined"
                hint="区域（如 us-east-1）"
                persistent-hint
                class="mb-2"
              />
              <v-text-field
                v-model="wizardConfig.s3_access_key"
                label="access_key"
                variant="outlined"
                hint="访问密钥 ID"
                persistent-hint
                class="mb-2"
              />
              <v-text-field
                v-model="wizardConfig.s3_secret_key"
                label="secret_key"
                variant="outlined"
                type="password"
                hint="密钥（未修改时留空保持不变）"
                persistent-hint
                placeholder="未修改时留空"
                class="mb-2"
              />
              <v-radio-group v-model="wizardConfig.s3_url_style" label="url_style">
                <v-radio label="Path（路径风格）" value="path" />
                <v-radio label="Virtual-hosted（虚拟主机风格）" value="virtual" />
              </v-radio-group>
            </template>

            <!-- local 配置 -->
            <template v-if="wizardConfig.targetBackend === 'local'">
              <v-text-field
                v-model="wizardConfig.storage_base_url"
                label="storage_base_url"
                variant="outlined"
                hint="本地存储 URL 基础路径（如 /static/uploads/）"
                persistent-hint
              />
            </template>
          </div>

          <!-- 步骤 3: 测试连接（强制） -->
          <div v-if="wizardStep === 3" class="mt-4">
            <div class="text-h6 mb-4">测试连接</div>
            <v-alert v-if="wizardConfig.targetBackend === 'local'" type="info" text="本地存储无需测试连接" class="mb-4" />
            <div v-else>
              <v-btn
                color="primary"
                variant="tonal"
                :loading="testingConnection"
                @click="testConnection"
                block
              >
                <v-icon start>mdi-network-outline</v-icon>
                测试 S3 连接
              </v-btn>
              <v-alert v-if="testResult" :type="testResult.ok ? 'success' : 'error'" class="mt-4" :text="testResult.error || '连接成功'" />
            </div>
          </div>

          <!-- 步骤 4: 迁移现有图片（可选） -->
          <div v-if="wizardStep === 4" class="mt-4">
            <div class="text-h6 mb-4">迁移现有图片</div>
            <v-alert v-if="!needsMigration" type="info" text="目标后端与当前相同，无需迁移" class="mb-4" />
            <template v-else>
              <v-alert type="warning" class="mb-4">
                <template #prepend>
                  <v-icon>mdi-alert</v-icon>
                </template>
                <div>
                  <div class="font-weight-bold">迁移说明</div>
                  <div class="text-caption">
                    {{ migrationDirectionText }}
                  </div>
                </div>
              </v-alert>

              <!-- 迁移进度 -->
              <div v-if="migrationTaskId">
                <v-progress-linear :model-value="migrationProgress" color="primary" class="mb-2" />
                <div class="text-caption text-medium-emphasis mb-2">
                  {{ migrationStage || '准备中...' }} ({{ migrationCurrent || 0 }}/{{ migrationTotal || 0 }})
                </div>
                <div v-if="migrationStats" class="text-caption">
                  已上传: {{ migrationStats.uploaded }} | 跳过: {{ migrationStats.skipped }} | 失败: {{ migrationStats.failed }}
                </div>
              </div>

              <!-- 迁移控制 -->
              <div v-else class="d-flex flex-column gap-2">
                <v-btn
                  color="primary"
                  variant="tonal"
                  :loading="startingMigration"
                  @click="startMigration"
                  block
                >
                  <v-icon start>mdi-cloud-upload</v-icon>
                  开始迁移
                </v-btn>
                <v-btn
                  color="warning"
                  variant="outlined"
                  @click="skipMigration"
                  block
                >
                  <v-icon start>mdi-skip-next</v-icon>
                  跳过迁移（源端独有图片将无法访问）
                </v-btn>
              </div>
            </template>
          </div>

          <!-- 步骤 5: 确认切换 -->
          <div v-if="wizardStep === 5" class="mt-4">
            <div class="text-h6 mb-4">确认切换</div>
            <v-alert type="info" class="mb-4">
              <div>即将切换到：{{ wizardConfig.targetBackend === 'local' ? '本地存储' : 'S3 对象存储' }}</div>
              <div class="text-caption mt-2" v-if="needsMigration">
                迁移状态：{{ migrationTaskId ? (migrationComplete ? '已完成' : '进行中') : '已跳过' }}
              </div>
            </v-alert>
            <v-btn
              color="error"
              variant="tonal"
              :loading="applyingConfig"
              @click="applyConfig"
              block
            >
              <v-icon start>mdi-check-circle</v-icon>
              确认切换
            </v-btn>
          </div>
        </v-card-text>

        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn v-if="wizardStep > 1" variant="text" @click="prevStep" :disabled="applyingConfig">
            上一步
          </v-btn>
          <v-spacer />
          <v-btn v-if="wizardStep < 5" variant="text" @click="nextStep" :disabled="!canNextStep">
            下一步
          </v-btn>
          <v-btn v-else variant="text" color="error" @click="wizardDialog = false" :disabled="applyingConfig">
            关闭
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 成功提示 -->
    <v-snackbar v-model="showSuccess" color="success" timeout="3000">
      <v-icon start>mdi-check-circle</v-icon>
      {{ successMessage }}
    </v-snackbar>

    <!-- 错误提示 -->
    <v-snackbar v-model="showError" color="error" timeout="5000">
      <v-icon start>mdi-alert-circle</v-icon>
      {{ errorMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import api from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => {
  router.back()
}

interface StorageConfig {
  backend: 'local' | 's3'
  storage_base_url: string | null
  s3_endpoint: string | null
  s3_bucket: string | null
  s3_region: string | null
  s3_access_key: string | null
  s3_secret_key: string | null
  s3_url_style: 'path' | 'virtual'
  has_access_key: boolean
  has_secret_key: boolean
  sources: {
    backend?: string
    storage_base_url?: string
    s3_endpoint?: string
    s3_bucket?: string
    s3_region?: string
    s3_url_style?: string
    s3_access_key?: string
    s3_secret_key?: string
  }
}

const config = ref<StorageConfig | null>(null)
const loading = ref(false)

// 向导状态
const wizardDialog = ref(false)
const wizardStep = ref(1)
const wizardItems = ['选择后端', '填写配置', '测试连接', '迁移图片', '确认切换']

const wizardConfig = reactive({
  targetBackend: 'local' as 'local' | 's3',
  storage_base_url: '',
  s3_endpoint: '',
  s3_bucket: '',
  s3_region: '',
  s3_access_key: '',
  s3_secret_key: '',
  s3_url_style: 'path' as 'path' | 'virtual',
})

// 测试连接
const testingConnection = ref(false)
const testResult = ref<{ ok: boolean; error?: string } | null>(null)

// 迁移
const migrationTaskId = ref<string | null>(null)
const migrationProgress = ref(0)
const migrationStage = ref('')
const migrationCurrent = ref(0)
const migrationTotal = ref(0)
const migrationStats = ref<{ uploaded: number; skipped: number; failed: number } | null>(null)
const migrationComplete = ref(false)
const startingMigration = ref(false)
let migrationPoller: ReturnType<typeof setInterval> | null = null

// 应用配置
const applyingConfig = ref(false)

// 提示
const showSuccess = ref(false)
const successMessage = ref('')
const showError = ref(false)
const errorMessage = ref('')

// source chip 辅助
const sourceColor = (source?: string) => {
  if (!source) return 'default'
  if (source === 'DB') return 'primary'
  if (source === '.env') return 'success'
  return 'info'
}

const sourceLabel = (source?: string) => {
  if (!source) return '默认'
  return source
}

// 是否需要迁移
const needsMigration = computed(() => {
  if (!config.value) return false
  return config.value.backend !== wizardConfig.targetBackend
})

// 迁移方向说明
const migrationDirectionText = computed(() => {
  if (!config.value) return ''
  if (config.value.backend === 'local' && wizardConfig.targetBackend === 's3') {
    return '从本地存储迁移到 S3 对象存储'
  }
  if (config.value.backend === 's3' && wizardConfig.targetBackend === 'local') {
    return '从 S3 对象存储迁移到本地存储'
  }
  return ''
})

// 能否下一步
const canNextStep = computed(() => {
  if (wizardStep.value === 1) {
    return !!wizardConfig.targetBackend
  }
  if (wizardStep.value === 2) {
    if (wizardConfig.targetBackend === 's3') {
      return !!(wizardConfig.s3_endpoint && wizardConfig.s3_bucket)
    }
    return true
  }
  if (wizardStep.value === 3) {
    if (wizardConfig.targetBackend === 'local') {
      return true
    }
    return testResult.value?.ok === true
  }
  if (wizardStep.value === 4) {
    if (!needsMigration.value) return true
    return migrationComplete.value
  }
  return true
})

const nextStep = () => {
  if (wizardStep.value < 5) {
    wizardStep.value++
  }
}

const prevStep = () => {
  if (wizardStep.value > 1) {
    wizardStep.value--
  }
}

const openWizard = () => {
  wizardStep.value = 1
  wizardConfig.targetBackend = config.value?.backend === 's3' ? 'local' : 's3'
  wizardConfig.storage_base_url = config.value?.storage_base_url || ''
  wizardConfig.s3_endpoint = config.value?.s3_endpoint || ''
  wizardConfig.s3_bucket = config.value?.s3_bucket || ''
  wizardConfig.s3_region = config.value?.s3_region || ''
  wizardConfig.s3_access_key = ''
  wizardConfig.s3_secret_key = ''
  wizardConfig.s3_url_style = config.value?.s3_url_style || 'path'
  testResult.value = null
  migrationTaskId.value = null
  migrationProgress.value = 0
  migrationStage.value = ''
  migrationCurrent.value = 0
  migrationTotal.value = 0
  migrationStats.value = null
  migrationComplete.value = false
  wizardDialog.value = true
}

const testConnection = async () => {
  testingConnection.value = true
  testResult.value = null
  try {
    const result = await api.post('/admin/storage-config/test', {
      backend: 's3',
      s3_endpoint: wizardConfig.s3_endpoint,
      s3_bucket: wizardConfig.s3_bucket,
      s3_region: wizardConfig.s3_region,
      s3_access_key: wizardConfig.s3_access_key,
      s3_secret_key: wizardConfig.s3_secret_key,
      s3_url_style: wizardConfig.s3_url_style,
    })
    testResult.value = { ok: result.ok, error: result.error }
  } catch (error: any) {
    testResult.value = { ok: false, error: error.userMessage || '测试失败' }
  } finally {
    testingConnection.value = false
  }
}

const startMigration = async () => {
  startingMigration.value = true
  try {
    const direction = config.value?.backend === 'local' ? 'to_s3' : 'to_local'
    const payload: any = { direction }
    if (direction === 'to_s3') {
      payload.s3_config = {
        s3_endpoint: wizardConfig.s3_endpoint,
        s3_bucket: wizardConfig.s3_bucket,
        s3_region: wizardConfig.s3_region,
        s3_access_key: wizardConfig.s3_access_key,
        s3_secret_key: wizardConfig.s3_secret_key,
        s3_url_style: wizardConfig.s3_url_style,
      }
    }
    const result = await api.post('/admin/storage-config/migrate', payload)
    migrationTaskId.value = result.task_id
    startMigrationPolling()
  } catch (error: any) {
    showError.value = true
    errorMessage.value = error.userMessage || '启动迁移失败'
  } finally {
    startingMigration.value = false
  }
}

const startMigrationPolling = () => {
  if (migrationPoller) clearInterval(migrationPoller)
  migrationPoller = setInterval(async () => {
    if (!migrationTaskId.value) return
    try {
      const result = await api.get(`/import/tasks/${migrationTaskId.value}`)
      const status = result.status
      const progress = result.progress || {}
      migrationProgress.value = progress.current && progress.total
        ? (progress.current / progress.total) * 100
        : 0
      migrationStage.value = progress.stage || ''
      migrationCurrent.value = progress.current || 0
      migrationTotal.value = progress.total || 0
      migrationStats.value = result.stats || null

      if (status === 'success' || status === 'failed') {
        if (migrationPoller) clearInterval(migrationPoller)
        migrationPoller = null
        migrationComplete.value = true
        if (status === 'failed') {
          showError.value = true
          errorMessage.value = result.error || '迁移失败'
        }
      }
    } catch (error) {
      // 忽略轮询错误，继续下一轮
    }
  }, 2000)
}

const skipMigration = () => {
  migrationComplete.value = true
}

const applyConfig = async () => {
  applyingConfig.value = true
  try {
    const payload: any = {
      backend: wizardConfig.targetBackend,
    }
    if (wizardConfig.targetBackend === 'local') {
      payload.storage_base_url = wizardConfig.storage_base_url || null
    } else {
      payload.s3_endpoint = wizardConfig.s3_endpoint || null
      payload.s3_bucket = wizardConfig.s3_bucket || null
      payload.s3_region = wizardConfig.s3_region || null
      payload.s3_access_key = wizardConfig.s3_access_key || null
      // secret_key: 哨兵，空字符串表示未修改，传 null 让后端保持旧值
      payload.s3_secret_key = wizardConfig.s3_secret_key || null
      payload.s3_url_style = wizardConfig.s3_url_style
    }
    await api.put('/admin/storage-config', payload)
    successMessage.value = '存储配置切换成功'
    showSuccess.value = true
    wizardDialog.value = false
    await fetchConfig()
  } catch (error: any) {
    showError.value = true
    errorMessage.value = error.userMessage || '切换失败'
  } finally {
    applyingConfig.value = false
  }
}

const fetchConfig = async () => {
  loading.value = true
  try {
    config.value = await api.get('/admin/storage-config')
  } catch (error) {
    console.error('获取存储配置失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchConfig()
})

onUnmounted(() => {
  if (migrationPoller) clearInterval(migrationPoller)
})
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
