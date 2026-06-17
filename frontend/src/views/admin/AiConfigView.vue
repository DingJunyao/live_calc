<!-- frontend/src/views/admin/AiConfigView.vue -->
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getTranslationConfig, putTranslationConfig, testTranslationConnection } from '@/api/usda'

const config = ref<any>(null)
const testing = ref<string>('')
const saving = ref(false)
const saveMessage = ref('')
// 每个 provider 的测试结果在按钮旁就地显示（成功/失败 + 后端返回的 detail）
const testResult = reactive<Record<string, { ok: boolean; detail: string }>>({})

onMounted(async () => { config.value = await getTranslationConfig() })

function setField(provider: string, field: string, value: any) {
  config.value.ai.providers[provider][field] = value
}
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
async function save() {
  saving.value = true
  try { await putTranslationConfig(config.value); saveMessage.value = '已保存' }
  catch (e: any) { saveMessage.value = e.userMessage || '保存失败' }
  finally { saving.value = false }
}
</script>

<template>
  <v-container v-if="config">
    <h2>AI 翻译配置</h2>
    <p class="text-caption">用于 USDA 食材名称翻译。Anthropic/OpenAI 兼容 base_url 自定义端点。</p>

    <v-card class="my-3" variant="outlined">
      <v-card-title>Claude Code（本机 CLI）</v-card-title>
      <v-card-text>
        <v-switch :model-value="config.ai.providers.claude_code.enabled" label="启用"
          @update:model-value="setField('claude_code', 'enabled', $event)" />
        <p class="text-caption">需服务器 PATH 中有 claude CLI。</p>
        <div class="d-flex align-center">
          <v-btn :loading="testing === 'claude_code'" @click="testProvider('claude_code')">测试连接</v-btn>
          <span v-if="testResult['claude_code']" class="ml-3 text-body-2"
            :class="testResult['claude_code'].ok ? 'text-success' : 'text-error'">
            {{ testResult['claude_code'].detail }}
          </span>
        </div>
      </v-card-text>
    </v-card>

    <v-card class="my-3" variant="outlined">
      <v-card-title>OpenAI 兼容</v-card-title>
      <v-card-text>
        <v-switch :model-value="config.ai.providers.openai.enabled" label="启用"
          @update:model-value="setField('openai', 'enabled', $event)" />
        <v-text-field :model-value="config.ai.providers.openai.base_url" label="Base URL"
          @update:model-value="setField('openai', 'base_url', $event)" />
        <v-text-field :model-value="config.ai.providers.openai.api_key" label="API Key" type="password"
          @update:model-value="setField('openai', 'api_key', $event)" />
        <v-text-field :model-value="config.ai.providers.openai.model" label="Model"
          @update:model-value="setField('openai', 'model', $event)" />
        <div class="d-flex align-center">
          <v-btn :loading="testing === 'openai'" @click="testProvider('openai')">测试连接</v-btn>
          <span v-if="testResult['openai']" class="ml-3 text-body-2"
            :class="testResult['openai'].ok ? 'text-success' : 'text-error'">
            {{ testResult['openai'].detail }}
          </span>
        </div>
      </v-card-text>
    </v-card>

    <v-card class="my-3" variant="outlined">
      <v-card-title>Anthropic 兼容</v-card-title>
      <v-card-text>
        <v-switch :model-value="config.ai.providers.anthropic.enabled" label="启用"
          @update:model-value="setField('anthropic', 'enabled', $event)" />
        <v-text-field :model-value="config.ai.providers.anthropic.base_url" label="Base URL"
          @update:model-value="setField('anthropic', 'base_url', $event)" />
        <v-text-field :model-value="config.ai.providers.anthropic.api_key" label="API Key" type="password"
          @update:model-value="setField('anthropic', 'api_key', $event)" />
        <v-text-field :model-value="config.ai.providers.anthropic.model" label="Model"
          @update:model-value="setField('anthropic', 'model', $event)" />
        <div class="d-flex align-center">
          <v-btn :loading="testing === 'anthropic'" @click="testProvider('anthropic')">测试连接</v-btn>
          <span v-if="testResult['anthropic']" class="ml-3 text-body-2"
            :class="testResult['anthropic'].ok ? 'text-success' : 'text-error'">
            {{ testResult['anthropic'].detail }}
          </span>
        </div>
      </v-card-text>
    </v-card>

    <v-btn color="primary" :loading="saving" @click="save">保存配置</v-btn>
    <v-alert v-if="saveMessage" class="mt-3" density="compact" :text="saveMessage" />
  </v-container>
</template>
