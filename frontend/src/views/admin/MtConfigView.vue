<!-- frontend/src/views/admin/MtConfigView.vue -->
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getTranslationConfig, putTranslationConfig, testTranslationConnection } from '@/api/usda'

const config = ref<any>(null)
const testing = ref('')
const saving = ref(false)
const saveMessage = ref('')
const testResult = reactive<Record<string, { ok: boolean; detail: string }>>({})

onMounted(async () => { config.value = await getTranslationConfig() })
function setField(p: string, f: string, v: any) { config.value.machine.providers[p][f] = v }
async function testProvider(p: string) {
  testing.value = p
  delete testResult[p]
  try {
    await putTranslationConfig(config.value)
    const r: any = await testTranslationConnection(p)
    testResult[p] = { ok: !!r.ok, detail: r.detail || (r.ok ? '连接成功' : '连接失败') }
  } catch (e: any) {
    testResult[p] = { ok: false, detail: e.userMessage || '测试失败' }
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
    <h2>机器翻译配置</h2>
    <v-card class="my-3" variant="outlined">
      <v-card-title>百度翻译</v-card-title>
      <v-card-text>
        <v-switch :model-value="config.machine.providers.baidu.enabled" label="启用" @update:model-value="setField('baidu', 'enabled', $event)" />
        <v-text-field :model-value="config.machine.providers.baidu.appid" label="AppID" @update:model-value="setField('baidu', 'appid', $event)" />
        <v-text-field :model-value="config.machine.providers.baidu.secret" label="Secret" type="password" @update:model-value="setField('baidu', 'secret', $event)" />
        <div class="d-flex align-center">
          <v-btn :loading="testing === 'baidu'" @click="testProvider('baidu')">测试连接</v-btn>
          <span v-if="testResult['baidu']" class="ml-3 text-body-2"
            :class="testResult['baidu'].ok ? 'text-success' : 'text-error'">
            {{ testResult['baidu'].detail }}
          </span>
        </div>
      </v-card-text>
    </v-card>
    <v-card class="my-3" variant="outlined">
      <v-card-title>阿里云机器翻译</v-card-title>
      <v-card-text>
        <v-switch :model-value="config.machine.providers.aliyun.enabled" label="启用" @update:model-value="setField('aliyun', 'enabled', $event)" />
        <v-text-field :model-value="config.machine.providers.aliyun.access_key_id" label="AccessKey ID" @update:model-value="setField('aliyun', 'access_key_id', $event)" />
        <v-text-field :model-value="config.machine.providers.aliyun.access_key_secret" label="AccessKey Secret" type="password" @update:model-value="setField('aliyun', 'access_key_secret', $event)" />
        <div class="d-flex align-center">
          <v-btn :loading="testing === 'aliyun'" @click="testProvider('aliyun')">测试连接</v-btn>
          <span v-if="testResult['aliyun']" class="ml-3 text-body-2"
            :class="testResult['aliyun'].ok ? 'text-success' : 'text-error'">
            {{ testResult['aliyun'].detail }}
          </span>
        </div>
      </v-card-text>
    </v-card>
    <v-card class="my-3" variant="outlined">
      <v-card-title>DeepL</v-card-title>
      <v-card-text>
        <v-switch :model-value="config.machine.providers.deepl.enabled" label="启用" @update:model-value="setField('deepl', 'enabled', $event)" />
        <v-text-field :model-value="config.machine.providers.deepl.auth_key" label="Auth Key（free 以 :fx 结尾）" type="password" @update:model-value="setField('deepl', 'auth_key', $event)" />
        <div class="d-flex align-center">
          <v-btn :loading="testing === 'deepl'" @click="testProvider('deepl')">测试连接</v-btn>
          <span v-if="testResult['deepl']" class="ml-3 text-body-2"
            :class="testResult['deepl'].ok ? 'text-success' : 'text-error'">
            {{ testResult['deepl'].detail }}
          </span>
        </div>
      </v-card-text>
    </v-card>
    <v-btn color="primary" :loading="saving" @click="save">保存配置</v-btn>
    <v-alert v-if="saveMessage" class="mt-3" density="compact" :text="saveMessage" />
  </v-container>
</template>
