<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">菜谱导入管理</v-app-bar-title>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 结果提示 -->
    <v-alert v-if="resultMessage" :type="resultSuccess ? 'success' : 'error'"
             variant="tonal" class="mb-4" closable @click:close="resultMessage = ''">
      <div class="d-flex align-center">
        <v-icon start :color="resultSuccess ? 'success' : 'error'" class="mr-2">
          {{ resultSuccess ? 'mdi-check-circle' : 'mdi-alert-circle' }}
        </v-icon>
        <div>
          <div class="font-weight-medium">{{ resultSuccess ? '操作成功' : '操作失败' }}</div>
          <div v-if="resultDetail" class="text-caption mt-1">{{ resultDetail }}</div>
        </div>
      </div>
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
              :loading="loading.repo"
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
              :disabled="loading.local"
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
              :loading="loading.local"
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
              :loading="loading.upload"
              :disabled="loading.upload"
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
              :loading="loading.upload"
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
                  :loading="loading.aiQuantities"
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
                  :loading="loading.aiDensities"
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

      <!-- 上次导入结果 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="info">mdi-chart-box</v-icon>
            <span>上次导入结果</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <div v-if="lastImportStats">
              <div v-for="(v, k) in lastImportStats" :key="k" class="d-flex align-center mb-2">
                <v-chip size="small" variant="tonal" color="info" class="mr-2 text-caption font-weight-medium">
                  {{ k }}
                </v-chip>
                <span class="text-body-1 font-weight-bold">{{ v }}</span>
              </div>
              <v-divider class="my-2" />
              <div v-if="lastImportWarnings.length" class="mt-2">
                <div class="text-caption font-weight-medium mb-1">警告：</div>
                <div v-for="(w, i) in lastImportWarnings" :key="i" class="text-caption text-warning">
                  • {{ w }}
                </div>
              </div>
            </div>
            <v-alert v-else type="info" variant="tonal" density="compact" class="mt-2">
              暂无导入记录
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import axios from 'axios'
import { getTranslationConfig } from '@/api/usda'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => router.back()

// 状态
const loading = reactive({
  repo: false,
  local: false,
  upload: false,
  aiQuantities: false,
  aiDensities: false,
})

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
  try {
    translationConfig.value = await getTranslationConfig()
    if (enabledProviders.value.length) {
      aiProvider.value = enabledProviders.value[0]
    }
  } catch {
    // 忽略错误，用户会看到"请先在 AI 配置页启用后端"
  }
})

const resultMessage = ref('')
const resultSuccess = ref(false)
const resultDetail = ref('')

const lastImportStats = ref<Record<string, number> | null>(null)
const lastImportWarnings = ref<string[]>([])

// API 基础路径
const baseURL = import.meta.env.VITE_API_URL || '/api/v1'

function getHeaders() {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function showResult(success: boolean, message: string, detail?: string) {
  resultSuccess.value = success
  resultMessage.value = message
  resultDetail.value = detail || ''
  setTimeout(() => { resultMessage.value = '' }, 8000)
}

function handleApiResponse(data: any, actionName: string) {
  const success = data.success !== false
  if (data.stats) {
    lastImportStats.value = data.stats
  }
  lastImportWarnings.value = data.warnings || []

  const total = data.stats ? Object.values(data.stats).reduce((a: any, b: any) => a + b, 0) : 0
  const errors = data.errors?.length || 0

  if (success) {
    showResult(true, `${actionName}成功`, errors > 0
      ? `完成 ${total} 项（${errors} 项失败）`
      : `完成 ${total} 项`)
  } else {
    showResult(false, `${actionName}失败`, data.errors?.join('; ') || '未知错误')
  }
}

// 从仓库导入
async function importFromRepo() {
  loading.repo = true
  try {
    const resp = await axios.post(`${baseURL}/import/data/import-from-repo`, {}, {
      headers: getHeaders(),
    })
    handleApiResponse(resp.data, '仓库导入')
  } catch (e: any) {
    showResult(false, '仓库导入失败', e.response?.data?.detail || e.message)
  } finally {
    loading.repo = false
  }
}

// 从本地路径导入
async function importFromLocalPath() {
  loading.local = true
  try {
    const resp = await axios.post(`${baseURL}/import/data/import-from-local`, {}, {
      params: { local_path: localPath.value.trim() },
      headers: getHeaders(),
    })
    handleApiResponse(resp.data, '本地导入')
  } catch (e: any) {
    showResult(false, '本地导入失败', e.response?.data?.detail || e.message)
  } finally {
    loading.local = false
  }
}

// 上传 ZIP 导入
async function uploadImport() {
  if (!uploadFile.value) return
  loading.upload = true
  try {
    const form = new FormData()
    form.append('file', uploadFile.value)
    const resp = await axios.post(`${baseURL}/import/data/upload`, form, {
      headers: { ...getHeaders(), 'Content-Type': 'multipart/form-data' },
    })
    handleApiResponse(resp.data, '上传导入')
    uploadFile.value = null
  } catch (e: any) {
    showResult(false, '上传导入失败', e.response?.data?.detail || e.message)
  } finally {
    loading.upload = false
  }
}

// AI 推测
async function inferQuantities() {
  loading.aiQuantities = true
  try {
    const resp = await axios.post(`${baseURL}/import/ai-infer/quantities`, {}, {
      params: { force: aiForce.value, provider: aiProvider.value || 'claude_code' },
      headers: getHeaders(),
    })
    handleApiResponse(resp.data, '模糊量推测')
  } catch (e: any) {
    showResult(false, '模糊量推测失败', e.response?.data?.detail || e.message)
  } finally {
    loading.aiQuantities = false
  }
}

async function inferDensities() {
  loading.aiDensities = true
  try {
    const resp = await axios.post(`${baseURL}/import/ai-infer/densities`, {}, {
      params: { force: aiForce.value, provider: aiProvider.value || 'claude_code' },
      headers: getHeaders(),
    })
    handleApiResponse(resp.data, '密度推测')
  } catch (e: any) {
    showResult(false, '密度推测失败', e.response?.data?.detail || e.message)
  } finally {
    loading.aiDensities = false
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
</style>
