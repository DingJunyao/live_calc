<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">菜谱导入</v-app-bar-title>
  </v-app-bar>

  <v-container class="pa-4">
    <v-row>
      <!-- 从 GitHub 导入 -->
      <v-col cols="12" md="6">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="github">mdi-github</v-icon>
            <span>从 GitHub 仓库导入</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              从指定的 GitHub 仓库导入菜谱数据。支持 howtocook 菜谱仓库格式。
            </p>
            <v-text-field
              v-model="githubUrl"
              label="仓库 URL"
              variant="outlined"
              placeholder="https://github.com/username/repo"
              prepend-icon="mdi-github"
              hint="输入 GitHub 仓库地址"
              persistent-hint
              :disabled="importing"
            />
            <v-alert type="info" variant="tonal" class="mt-4" density="compact">
              <div class="text-caption">
                <strong>支持格式：</strong><br />
                • Anduin2017/howtocook<br />
                • 其他兼容的菜谱仓库
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
              :loading="importing"
              @click="importFromGitHub"
            >
              <v-icon start>mdi-github</v-icon>
              开始导入
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- 初始数据导入 -->
      <v-col cols="12" md="6">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="warning">mdi-database-import</v-icon>
            <span>导入初始菜谱</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              导入预配置的初始菜谱数据。这是第一次设置应用时推荐的操作。
            </p>
            <v-list>
              <v-list-item prepend-icon="mdi-check-circle" title="包含常用菜谱" />
              <v-list-item prepend-icon="mdi-check-circle" title="已验证的营养数据" />
              <v-list-item prepend-icon="mdi-check-circle" title="标准化的格式" />
            </v-list>
            <v-alert type="warning" variant="tonal" class="mt-4" density="compact">
              <div class="text-caption">
                <strong>注意：</strong>导入初始菜谱可能会添加重复数据。请确保在首次设置时使用。
              </div>
            </v-alert>
          </v-card-text>
          <v-divider />
          <v-card-actions class="pa-4">
            <v-spacer />
            <v-btn
              color="warning"
              variant="tonal"
              size="large"
              :loading="importingInitial"
              @click="importInitialRecipes"
            >
              <v-icon start>mdi-database-import</v-icon>
              导入初始数据
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- 导入历史 -->
      <v-col cols="12">
        <v-card class="rounded-lg">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2">mdi-history</v-icon>
            <span>导入记录</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-4">
            <v-alert v-if="importHistory.length === 0" type="info" variant="tonal">
              暂无导入记录
            </v-alert>
            <v-timeline v-else side="end" density="compact">
              <v-timeline-item
                v-for="(record, index) in importHistory"
                :key="index"
                :dot-color="record.success ? 'success' : 'error'"
                size="small"
              >
                <template #icon>
                  <v-icon size="20">
                    {{ record.success ? 'mdi-check' : 'mdi-alert-circle' }}
                  </v-icon>
                </template>
                <div class="d-flex align-center">
                  <strong>{{ record.source }}</strong>
                  <v-chip
                    :color="record.success ? 'success' : 'error'"
                    size="x-small"
                    class="ml-2"
                    variant="tonal"
                  >
                    {{ record.success ? '成功' : '失败' }}
                  </v-chip>
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ record.timestamp }}
                </div>
                <div v-if="record.message" class="text-body-2 mt-1">
                  {{ record.message }}
                </div>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 导入结果对话框 -->
    <v-dialog v-model="resultDialog" max-width="600px" persistent>
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center py-4">
          <v-icon class="mr-2" :color="importResult.success ? 'success' : 'error'">
            {{ importResult.success ? 'mdi-check-circle' : 'mdi-alert-circle' }}
          </v-icon>
          <span>{{ importResult.success ? '导入成功' : '导入失败' }}</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-6">
          <div v-if="importResult.success">
            <p class="text-body-1 mb-4">菜谱导入完成！</p>
            <v-list>
              <v-list-item v-if="importResult.imported">
                <template #prepend>
                  <v-icon color="success">mdi-check-circle</v-icon>
                </template>
                <v-list-item-title>导入菜谱：{{ importResult.imported }} 个</v-list-item-title>
              </v-list-item>
              <v-list-item v-if="importResult.updated">
                <template #prepend>
                  <v-icon color="info">mdi-update</v-icon>
                </template>
                <v-list-item-title>更新菜谱：{{ importResult.updated }} 个</v-list-item-title>
              </v-list-item>
              <v-list-item v-if="importResult.failed">
                <template #prepend>
                  <v-icon color="error">mdi-alert-circle</v-icon>
                </template>
                <v-list-item-title>失败菜谱：{{ importResult.failed }} 个</v-list-item-title>
              </v-list-item>
            </v-list>
          </div>
          <div v-else>
            <p class="text-body-1 mb-4">导入过程中出现错误：</p>
            <v-alert type="error" variant="tonal">
              {{ importResult.error || '未知错误' }}
            </v-alert>
          </div>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn color="primary" @click="resultDialog = false">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import api from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => {
  router.back()
}

interface ImportResult {
  success: boolean
  imported?: number
  updated?: number
  failed?: number
  error?: string
}

interface ImportRecord {
  source: string
  success: boolean
  timestamp: string
  message?: string
}

const githubUrl = ref('')
const importing = ref(false)
const importingInitial = ref(false)

const resultDialog = ref(false)
const importResult = reactive<ImportResult>({
  success: false,
})

const importHistory = ref<ImportRecord[]>([])

const importFromGitHub = async () => {
  if (!githubUrl.value.trim()) {
    alert('请输入 GitHub 仓库地址')
    return
  }

  importing.value = true
  try {
    const response = await api.post('/admin/import-recipes-from-url', null, {
      params: { url: githubUrl.value },
    })
    Object.assign(importResult, {
      success: true,
      imported: response.imported || 0,
      updated: response.updated || 0,
      failed: response.failed || 0,
    })
    addImportHistory({
      source: `GitHub: ${githubUrl.value}`,
      success: true,
      timestamp: new Date().toLocaleString('zh-CN'),
      message: `导入 ${response.imported || 0} 个菜谱`,
    })
  } catch (error: any) {
    Object.assign(importResult, {
      success: false,
      error: error.response?.data?.detail || error.message || '导入失败',
    })
    addImportHistory({
      source: `GitHub: ${githubUrl.value}`,
      success: false,
      timestamp: new Date().toLocaleString('zh-CN'),
      message: error.response?.data?.detail || error.message,
    })
  } finally {
    importing.value = false
    resultDialog.value = true
  }
}

const importInitialRecipes = async () => {
  importingInitial.value = true
  try {
    const response = await api.post('/admin/import-recipes-initial')
    Object.assign(importResult, {
      success: true,
      imported: response.imported || 0,
      updated: response.updated || 0,
    })
    addImportHistory({
      source: '初始菜谱数据',
      success: true,
      timestamp: new Date().toLocaleString('zh-CN'),
      message: `导入 ${response.imported || 0} 个初始菜谱`,
    })
  } catch (error: any) {
    Object.assign(importResult, {
      success: false,
      error: error.response?.data?.detail || error.message || '导入失败',
    })
    addImportHistory({
      source: '初始菜谱数据',
      success: false,
      timestamp: new Date().toLocaleString('zh-CN'),
      message: error.response?.data?.detail || error.message,
    })
  } finally {
    importingInitial.value = false
    resultDialog.value = true
  }
}

const addImportHistory = (record: ImportRecord) => {
  importHistory.value.unshift(record)
  // 只保留最近 10 条记录
  if (importHistory.value.length > 10) {
    importHistory.value = importHistory.value.slice(0, 10)
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
