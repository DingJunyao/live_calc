<!-- frontend/src/views/admin/AiConfigView.vue -->
<!-- AI 与机翻合并配置页：两个折叠面板（默认全展开），统一保存 -->
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { getTranslationConfig, putTranslationConfig, testTranslationConnection } from '@/api/usda'
import ProviderCard from '@/components/admin/ProviderCard.vue'

const router = useRouter()
const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const goBack = () => router.back()

type FieldType = 'text' | 'password' | 'switch'
interface ProviderField { key: string; label: string; type?: FieldType }
interface ProviderDef { key: string; title: string; hint?: string; fields: ProviderField[] }

// AI 翻译 provider 字段配置（Claude Code / OpenAI 兼容 / Anthropic 兼容）
const AI_PROVIDERS: ProviderDef[] = [
  {
    key: 'claude_code',
    title: 'Claude Code（本机 CLI）',
    hint: '需服务器 PATH 中有 claude CLI。',
    fields: [{ key: 'enabled', label: '启用', type: 'switch' }],
  },
  {
    key: 'openai',
    title: 'OpenAI 兼容',
    fields: [
      { key: 'enabled', label: '启用', type: 'switch' },
      { key: 'base_url', label: 'Base URL' },
      { key: 'api_key', label: 'API Key', type: 'password' },
      { key: 'model', label: 'Model' },
    ],
  },
  {
    key: 'anthropic',
    title: 'Anthropic 兼容',
    fields: [
      { key: 'enabled', label: '启用', type: 'switch' },
      { key: 'base_url', label: 'Base URL' },
      { key: 'api_key', label: 'API Key', type: 'password' },
      { key: 'model', label: 'Model' },
    ],
  },
]

// 机器翻译 provider 字段配置（百度 / 阿里云 / DeepL）
const MT_PROVIDERS: ProviderDef[] = [
  {
    key: 'baidu',
    title: '百度翻译',
    fields: [
      { key: 'enabled', label: '启用', type: 'switch' },
      { key: 'appid', label: 'AppID' },
      { key: 'secret', label: 'Secret', type: 'password' },
    ],
  },
  {
    key: 'aliyun',
    title: '阿里云机器翻译',
    fields: [
      { key: 'enabled', label: '启用', type: 'switch' },
      { key: 'access_key_id', label: 'AccessKey ID' },
      { key: 'access_key_secret', label: 'AccessKey Secret', type: 'password' },
    ],
  },
  {
    key: 'deepl',
    title: 'DeepL',
    fields: [
      { key: 'enabled', label: '启用', type: 'switch' },
      { key: 'auth_key', label: 'Auth Key（free 以 :fx 结尾）', type: 'password' },
    ],
  },
]

const config = ref<any>(null)
const testing = ref('')
const saving = ref(false)
const saveMessage = ref('')
// 每个 provider 的测试结果在按钮旁就地显示（成功/失败 + 后端返回的 detail）
const testResult = reactive<Record<string, { ok: boolean; detail: string }>>({})
// 两个折叠面板默认全展开
const openPanels = ref<number[]>([0, 1])

onMounted(async () => { config.value = await getTranslationConfig() })

// 写入某分组下某 provider 的某字段
function setField(group: 'ai' | 'machine', provider: string, field: string, value: any) {
  config.value[group].providers[provider][field] = value
}

// 测试某 provider 连接（先保存当前配置，再触发后端测试）
async function testProvider(provider: string) {
  testing.value = provider
  delete testResult[provider]
  try {
    await putTranslationConfig(config.value)
    const r: any = await testTranslationConnection(provider)
    testResult[provider] = { ok: !!r.ok, detail: r.detail || (r.ok ? '连接成功' : '连接失败') }
  } catch (e: any) {
    testResult[provider] = { ok: false, detail: e.userMessage || '测试失败' }
  } finally {
    testing.value = ''
  }
}

// 统一保存 AI + 机翻配置
async function save() {
  saving.value = true
  try {
    await putTranslationConfig(config.value)
    saveMessage.value = '已保存'
  } catch (e: any) {
    saveMessage.value = e.userMessage || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <!-- 顶部导航栏 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">AI 与机翻配置</v-app-bar-title>
  </v-app-bar>

  <v-container v-if="config" class="pa-4">
    <p class="text-caption mb-2">
      用于 USDA 食材名翻译。AI 走 Claude Code / OpenAI 兼容 / Anthropic 兼容；机翻走 百度 / 阿里云 / DeepL。
    </p>

    <v-expansion-panels multiple v-model="openPanels" class="my-3">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-robot</v-icon>AI 翻译
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <ProviderCard
            v-for="p in AI_PROVIDERS"
            :key="p.key"
            :title="p.title"
            :hint="p.hint"
            :fields="p.fields"
            :values="config.ai.providers[p.key]"
            :testing="testing === p.key"
            :test-result="testResult[p.key]"
            @update:field="setField('ai', p.key, $event.field, $event.value)"
            @test="testProvider(p.key)"
          />
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-translate</v-icon>机器翻译
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <ProviderCard
            v-for="p in MT_PROVIDERS"
            :key="p.key"
            :title="p.title"
            :fields="p.fields"
            :values="config.machine.providers[p.key]"
            :testing="testing === p.key"
            :test-result="testResult[p.key]"
            @update:field="setField('machine', p.key, $event.field, $event.value)"
            @test="testProvider(p.key)"
          />
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-btn color="primary" :loading="saving" @click="save">保存配置</v-btn>
    <v-alert v-if="saveMessage" class="mt-3" density="compact" :text="saveMessage" />
  </v-container>
</template>
