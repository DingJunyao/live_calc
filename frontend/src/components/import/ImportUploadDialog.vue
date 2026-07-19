<template>
  <v-dialog v-model="visible" max-width="600" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-upload</v-icon>
        数据导入
      </v-card-title>

      <v-card-text>
        <v-alert v-if="result" :type="result.success ? 'success' : 'error'"
                 variant="tonal" class="mb-4" closable>
          <div v-if="result.success">
            导入完成：
            <span v-for="(v, k) in displayStats" :key="k" class="mr-2">
              {{ k }}={{ v }}
            </span>
            <div v-if="skippedItems.length" class="mt-2">
              <div class="text-caption text-medium-emphasis">已跳过（权限或隐私限制）：</div>
              <div v-for="item in skippedItems" :key="item.key" class="text-caption">
                · {{ skippedLabel[item.key] || item.key }}：{{ item.count }} 条
              </div>
            </div>
          </div>
          <div v-else>{{ result.errors?.join('; ') }}</div>
          <div v-if="result.warnings?.length" class="mt-1">
            <div v-for="(w, i) in result.warnings" :key="i" class="text-caption">{{ w }}</div>
          </div>
        </v-alert>

        <v-file-input
          v-model="file"
          label="选择 ZIP 压缩包"
          accept=".zip"
          :loading="uploading"
          :disabled="uploading"
          @update:model-value="result = null"
        />

        <div v-if="uploading" class="text-center py-4">
          <v-progress-circular indeterminate color="primary" />
          <div class="mt-2">
            {{ currentTask?.progress?.message || '正在导入，请稍候…' }}
          </div>
          <div
            v-if="currentTask?.progress?.total"
            class="text-caption text-medium-emphasis mt-1"
          >
            {{ currentTask.progress.stage }}：{{ currentTask.progress.current }}/{{
              currentTask.progress.total
            }}
          </div>
        </div>

        <v-btn block color="primary" :loading="uploading" :disabled="!file"
               class="mt-2" @click="handleUpload">
          <v-icon start>mdi-upload</v-icon>
          开始导入
        </v-btn>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="uploading" @click="close">关闭</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useImportTask } from '@/composables/useImportTask'
import type { ImportTask } from '@/composables/useImportTask'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })

const { tasks, startUploadTask } = useImportTask()

const file = ref<File | null>(null)
const uploading = ref(false)
const result = ref<any>(null)
const currentTaskId = ref<number | null>(null)

const currentTask = computed<ImportTask | undefined>(() => {
  if (!currentTaskId.value) return undefined
  return tasks.value.find((t) => t.id === currentTaskId.value)
})

// 导入统计（排除 skipped 子表，skipped 单独展示）
const displayStats = computed<Record<string, any>>(() => {
  const s = result.value?.stats || {}
  const rest: Record<string, any> = {}
  for (const [k, v] of Object.entries(s)) {
    if (k !== 'skipped') rest[k] = v
  }
  return rest
})

const skippedItems = computed<{ key: string; count: number }[]>(() => {
  const skipped = result.value?.stats?.skipped
  if (!skipped || typeof skipped !== 'object') return []
  return Object.entries(skipped).map(([key, count]) => ({ key, count: count as number }))
})

const skippedLabel: Record<string, string> = {
  blacklist_groups: '管理员专属·黑名单分组',
  unit_conversions: '管理员专属·单位换算',
  product_barcodes: '管理员专属·商品条码',
  user_places: '他人隐私·常用地点',
  price_records: '他人隐私·价格记录',
  user_ingredient_blacklist: '他人隐私·个人黑名单',
  blacklist_group_subscriptions: '他人隐私·分组订阅',
}

// 监听任务状态变化，终态时展示结果
watch(
  () => {
    const t = currentTask.value
    return t ? { status: t.status, stats: t.stats, error: t.error } : null
  },
  (snapshot) => {
    if (!snapshot) return
    if (snapshot.status === 'success') {
      result.value = {
        success: true,
        stats: snapshot.stats,
        warnings: snapshot.error ? [snapshot.error] : [],
      }
      uploading.value = false
      currentTaskId.value = null
    } else if (snapshot.status === 'failed') {
      result.value = {
        success: false,
        errors: [snapshot.error || '导入失败'],
      }
      uploading.value = false
      currentTaskId.value = null
    } else if (snapshot.status === 'cancelled') {
      result.value = {
        success: false,
        errors: ['导入任务已取消'],
      }
      uploading.value = false
      currentTaskId.value = null
    }
  },
)

async function handleUpload() {
  if (!file.value) return
  uploading.value = true
  result.value = null
  const taskId = await startUploadTask(file.value)
  if (taskId) {
    currentTaskId.value = taskId
  } else {
    result.value = {
      success: false,
      errors: ['上传失败，请检查网络后重试'],
    }
    uploading.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}
</script>
