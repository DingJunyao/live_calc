<!-- frontend/src/views/admin/AiConfigView.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getTranslationConfig, putTranslationConfig, testTranslationConnection } from '@/api/usda'

const config = ref<any>(null)
const testing = ref<string>('')
const saving = ref(false)
const message = ref('')

onMounted(async () => { config.value = await getTranslationConfig() })

function setField(provider: string, field: string, value: any) {
  config.value.ai.providers[provider][field] = value
}
async function testProvider(provider: string) {
  testing.value = provider
  message.value = ''
  try {
    await putTranslationConfig(config.value)
    const r: any = await testTranslationConnection(provider)
    message.value = r.ok ? `${provider} 连接成功` : `${provider} 连接失败`
  } catch (e: any) { message.value = e.userMessage || '测试失败' } finally { testing.value = '' }
}
async function save() {
  saving.value = true
  try { await putTranslationConfig(config.value); message.value = '已保存' }
  catch (e: any) { message.value = e.userMessage || '保存失败' }
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
        <v-btn :loading="testing === 'claude_code'" @click="testProvider('claude_code')">测试连接</v-btn>
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
        <v-btn :loading="testing === 'openai'" @click="testProvider('openai')">测试连接</v-btn>
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
        <v-btn :loading="testing === 'anthropic'" @click="testProvider('anthropic')">测试连接</v-btn>
      </v-card-text>
    </v-card>

    <v-btn color="primary" :loading="saving" @click="save">保存配置</v-btn>
    <v-alert v-if="message" class="mt-3" density="compact" :text="message" />
  </v-container>
</template>
