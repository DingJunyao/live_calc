<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  getUsdaStatistics, getUnmappedNutrients, downloadUsda, uploadUsda,
  translateUsda, translateNutrients, getUsdaTask, getTranslationConfig,
} from '@/api/usda'

const stats = ref<any>({})
const unmapped = ref<string[]>([])
const task = ref<any>({ status: 'idle' })
const transConfig = ref<any>(null)
const translateProvider = ref('openai')
const nutrientProvider = ref('')
const downloading = ref(false); const uploading = ref(false); const translating = ref(false)
const translatingNutrients = ref(false)
const message = ref('')
let timer: any = null

// 某区域已启用的后端
function enabledIn(region: string): string[] {
  const cfg = transConfig.value
  if (!cfg) return []
  const provs = cfg[region]?.providers || {}
  return Object.entries(provs).filter(([, c]) => (c as any)?.enabled).map(([n]) => n)
}
// 食材翻译：AI + 机翻都可用
const enabledProviders = computed<string[]>(() => [...enabledIn('ai'), ...enabledIn('machine')])
// 营养素翻译：只用 AI（缩写/记号需营养学知识，机翻不准）
const enabledAiProviders = computed<string[]>(() => enabledIn('ai'))
// 选中后端若不在启用列表，自动切到第一个
watch(enabledProviders, (list) => {
  if (list.length && !list.includes(translateProvider.value)) {
    translateProvider.value = list[0]
  }
})
watch(enabledAiProviders, (list) => {
  if (list.length && !list.includes(nutrientProvider.value)) {
    nutrientProvider.value = list[0]
  }
})

async function refresh() {
  stats.value = await getUsdaStatistics()
  const u: any = await getUnmappedNutrients(); unmapped.value = u.names
  task.value = await getUsdaTask()
}
onMounted(async () => {
  refresh()
  transConfig.value = await getTranslationConfig()
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
async function onTranslate() {
  if (!enabledProviders.value.length) { message.value = '请先在 AI/机翻配置页启用至少一个翻译后端'; return }
  translating.value = true; message.value = `翻译任务已启动（${translateProvider.value}）`
  try { await translateUsda(translateProvider.value) } catch (e: any) { message.value = e.userMessage || '失败' }
  finally { translating.value = false }
}
async function onTranslateNutrients() {
  if (!enabledAiProviders.value.length) { message.value = '请先在 AI 配置页启用至少一个 AI 后端'; return }
  if (!unmapped.value.length) { message.value = '没有未映射的营养素'; return }
  translatingNutrients.value = true; message.value = `营养素翻译任务已启动（${nutrientProvider.value}）`
  try { await translateNutrients(nutrientProvider.value) } catch (e: any) { message.value = e.userMessage || '失败' }
  finally { translatingNutrients.value = false }
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
      <v-card-title>翻译食材名称</v-card-title>
      <v-card-text>
        <v-select v-model="translateProvider" :items="enabledProviders" label="翻译后端"
          :hint="enabledProviders.length ? '' : '请先在 AI/机翻配置页启用至少一个后端'" persistent-hint />
        <v-btn color="primary" :loading="translating" :disabled="!enabledProviders.length" class="mt-2" @click="onTranslate">开始翻译</v-btn>
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
      <v-card-title>未映射营养素（{{ unmapped.length }}）</v-card-title>
      <v-card-text>
        <v-chip v-for="n in unmapped" :key="n" class="ma-1" size="small">{{ n }}</v-chip>
        <v-divider class="my-3" />
        <div class="d-flex align-center">
          <v-select v-model="nutrientProvider" :items="enabledAiProviders" label="AI 翻译后端"
            density="compact" hide-details style="max-width: 220px" class="mr-2"
            :hint="enabledAiProviders.length ? '' : '请先在 AI 配置页启用至少一个 AI 后端'" persistent-hint />
          <v-btn color="primary" :loading="translatingNutrients"
            :disabled="!unmapped.length || !enabledAiProviders.length" @click="onTranslateNutrients">
            AI 翻译未映射营养素
          </v-btn>
        </div>
        <p class="text-caption mt-2">营养素名多为缩写/脂肪酸记号（如 MUFA、12:1），需 AI 用营养学知识翻译，必要时可查 USDA；译完写回中文名。</p>
      </v-card-text>
    </v-card>

    <v-alert v-if="message" density="compact" :text="message" />
  </v-container>
</template>
