<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  getUsdaStatistics, getUnmappedNutrients, downloadUsda, uploadUsda,
  getUsdaTask, getTranslationConfig,
} from '@/api/usda'

const stats = ref<any>({})
const unmapped = ref<string[]>([])
const task = ref<any>({ status: 'idle' })
const downloading = ref(false); const uploading = ref(false)
const message = ref('')
let timer: any = null

async function refresh() {
  stats.value = await getUsdaStatistics()
  const u: any = await getUnmappedNutrients(); unmapped.value = u.names
  task.value = await getUsdaTask()
}
onMounted(async () => {
  refresh()
  timer = setInterval(async () => { task.value = await getUsdaTask() }, 3000)
})
onUnmounted(() => clearInterval(timer))

async function onDownload() {
  downloading.value = true; message.value = '下载任务已启动'
  try { await downloadUsda('foundation,sr_legacy') } catch (e: any) { message.value = e.userMessage || '失败' }
  finally { downloading.value = false }
}
async function onUpload(file: File | undefined) {
  if (!file) return; uploading.value = true; message.value = ''
  try { const r: any = await uploadUsda(file); message.value = r.message } catch (e: any) { message.value = e.userMessage || '失败' }
  finally { uploading.value = false }
}
</script>

<template>
  <v-container>
    <h2>USDA 数据配置</h2>

    <v-row class="my-2">
      <v-col v-for="(v, k) in stats" :key="k" cols="6" md="2">
        <v-card variant="outlined"><v-card-text>
          <div class="text-caption">{{ k }}</div>
          <div class="text-h6">{{ v }}</div>
        </v-card-text></v-card>
      </v-col>
    </v-row>

    <v-card class="my-3" variant="outlined">
      <v-card-title>数据入库</v-card-title>
      <v-card-text>
        <v-btn color="primary" :loading="downloading" @click="onDownload">下载 Foundation + SR Legacy</v-btn>
        <v-file-input label="或上传 USDA zip" accept=".zip" class="mt-2"
          @update:model-value="onUpload" :disabled="uploading" />
      </v-card-text>
    </v-card>


    <v-card class="my-3" variant="outlined">
      <v-card-title>任务状态</v-card-title>
      <v-card-text>
        <div>类型：{{ task.task_type || '—' }} · 状态：{{ task.status }}</div>
        <pre v-if="task.progress">{{ JSON.stringify(task.progress) }}</pre>
        <div v-if="task.error_log" class="text-error">{{ task.error_log }}</div>
        <v-btn size="small" variant="text" class="mt-2" @click="refresh">刷新统计</v-btn>
      </v-card-text>
    </v-card>

    <v-card class="my-3" variant="outlined">
      <v-card-title>未映射营养素（{{ unmapped.length }} 个）</v-card-title>
      <v-card-text>
        <v-chip v-for="n in unmapped" :key="n" class="ma-1" size="small" variant="tonal">
          {{ n }}
        </v-chip>
        <p v-if="!unmapped.length" class="text-caption text-medium-emphasis">暂无未映射营养素</p>
      </v-card-text>
    </v-card>

    <p class="text-caption text-medium-emphasis mt-2">
      💡 翻译操作已迁移至<router-link to="/admin/data-maintenance">数据维护中心</router-link>
    </p>

    <v-alert v-if="message" density="compact" :text="message" />
  </v-container>
</template>
