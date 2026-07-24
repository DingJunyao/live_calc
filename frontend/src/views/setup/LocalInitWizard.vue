<template>
  <v-container fluid class="fill-height" style="background: rgb(var(--v-theme-surface))">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="pa-6">
          <v-card-title class="text-h4 text-center mb-4">生计 — 初始化</v-card-title>

          <!-- Step 1: Welcome + choose method -->
          <template v-if="step === 1">
            <v-card-text class="text-body-1 text-center mb-4">
              欢迎使用本地版本！请选择数据初始化方式：
            </v-card-text>
            <v-list lines="two">
              <v-list-item
                prepend-icon="mdi-database-import-outline"
                title="从 HowToCook 仓库导入"
                subtitle="导入公开菜谱、原料和营养数据（需要网络）"
                @click="importFromRepo"
                :disabled="importing"
              />
              <v-list-item
                prepend-icon="mdi-upload-outline"
                title="上传数据包"
                subtitle="导入之前导出的 ZIP 数据包"
                @click="step = 2"
                :disabled="importing"
              />
              <v-list-item
                prepend-icon="mdi-rocket-launch-outline"
                title="空白起步"
                subtitle="只导入基础单位和分类，后续在数据维护中心导入"
                @click="skipImport"
                :disabled="importing"
              />
            </v-list>
            <v-progress-linear v-if="importing" indeterminate class="mt-4" />
          </template>

          <!-- Step 2: Upload ZIP -->
          <template v-if="step === 2">
            <v-card-text class="text-body-1 mb-4">
              选择之前导出的 ZIP 数据包：
            </v-card-text>
            <v-file-input
              label="选择 ZIP 文件"
              accept=".zip"
              @change="handleZipUpload"
              :loading="importing"
            />
            <v-btn variant="text" @click="step = 1" :disabled="importing">返回</v-btn>
          </template>

          <!-- Step 3: Complete -->
          <template v-if="step === 3">
            <v-card-text class="text-body-1 text-center">
              <v-icon size="48" color="success" class="mb-4">mdi-check-circle-outline</v-icon>
              <p>初始化完成！</p>
              <p class="text-caption text-medium-emphasis mt-2">{{ importMessage }}</p>
            </v-card-text>
            <v-btn color="primary" block class="mt-4" @click="goToHome">
              开始使用
            </v-btn>
          </template>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { seedBasicData } from '@/api/local/seed'

const router = useRouter()
const step = ref(1)
const importing = ref(false)
const importMessage = ref('')

async function importFromRepo() {
  importing.value = true
  importMessage.value = '正在导入基础单位和分类...'
  try {
    await seedBasicData()
    importMessage.value = '基础数据导入完成！正在尝试从 HowToCook 仓库导入菜谱...'
    // Try to fetch from HowToCook repo to validate connectivity
    try {
      const response = await fetch(
        'https://raw.githubusercontent.com/Anduin2017/HowToCook/refs/heads/master/dishes/README.md'
      )
      if (response.ok) {
        importMessage.value = '已连接到数据仓库。完整导入功能将在后续版本中完善。'
      } else {
        importMessage.value = '数据仓库暂时不可用，基础数据已就绪。'
      }
    } catch {
      importMessage.value = '数据仓库连接失败，基础数据已就绪。'
    }
    step.value = 3
  } catch (e: any) {
    importMessage.value = '导入失败：' + (e?.message || '未知错误')
  } finally {
    importing.value = false
  }
}

async function handleZipUpload(event: any) {
  const file = event?.target?.files?.[0] || event?.file
  if (!file) return
  importing.value = true
  importMessage.value = '正在导入数据包...'
  try {
    await seedBasicData() // Ensure basic data first
    // ZIP import will be handled in Phase 8
    importMessage.value = '基础数据已导入。ZIP 导入功能将在后续版本中完善。'
    step.value = 3
  } catch (e: any) {
    importMessage.value = '导入失败：' + (e?.message || '未知错误')
  } finally {
    importing.value = false
  }
}

async function skipImport() {
  importing.value = true
  try {
    await seedBasicData()
    importMessage.value = '基础单位和分类已就绪。'
    step.value = 3
  } catch (e: any) {
    importMessage.value = '导入失败：' + (e?.message || '未知错误')
  } finally {
    importing.value = false
  }
}

function goToHome() {
  router.replace('/')
}
</script>
