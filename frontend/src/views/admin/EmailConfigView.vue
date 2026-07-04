<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">邮件配置</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" @click="loadAll" />
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <v-expansion-panels variant="accordion" multiple>
      <!-- 面板一：SMTP 配置 -->
      <v-expansion-panel :value="0">
        <v-expansion-panel-title>
          <v-icon start class="mr-2">mdi-email-cog</v-icon>
          SMTP 配置
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row dense>
            <v-col cols="12" sm="6">
              <v-text-field v-model="smtp.host" label="SMTP 服务器" placeholder="smtp.example.com"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="6" sm="3">
              <v-text-field v-model.number="smtp.port" label="端口" type="number"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="6" sm="3" class="d-flex align-center">
              <v-switch v-model="smtp.use_tls" label="TLS" density="compact" hide-details />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="smtp.username" label="用户名"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="passwordField" label="密码" type="password"
                variant="outlined" density="compact" hide-details="auto"
                placeholder="留空则不修改" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="smtp.from_address" label="发件人地址" placeholder="noreply@example.com"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="12" sm="3">
              <v-text-field v-model="smtp.from_name" label="发件人名称"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="12" sm="3" class="d-flex align-center">
              <v-switch v-model="smtp.enabled" label="启用" density="compact" hide-details />
            </v-col>
          </v-row>

          <v-row class="mt-4">
            <v-col cols="12" class="d-flex ga-2 flex-wrap">
              <v-btn color="primary" :loading="savingSmtp" @click="saveSmtp">
                保存 SMTP 配置
              </v-btn>
              <v-spacer />
              <v-text-field v-model="testEmail" label="测试邮箱" variant="outlined"
                density="compact" hide-details style="max-width: 250px" />
              <v-btn variant="tonal" :loading="testing" :disabled="!testEmail || !smtp.enabled"
                @click="sendTest">
                发送测试邮件
              </v-btn>
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- 面板二：邮件模板 -->
      <v-expansion-panel :value="1">
        <v-expansion-panel-title>
          <v-icon start class="mr-2">mdi-email-edit-outline</v-icon>
          邮件模板
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-alert type="info" variant="tonal" density="comfortable" class="mb-4">
            可用变量：<code>${proposal_id}</code> <code>${entity_type_label}</code>
            <code>${action_label}</code> <code>${entity_label}</code>
            <code>${proposer_name}</code> <code>${review_note}</code>
          </v-alert>

          <v-card
            v-for="tpl in templates"
            :key="tpl.key"
            variant="outlined"
            class="mb-4 rounded-lg"
          >
            <v-card-text>
              <div class="text-subtitle-2 mb-2">
                {{ tpl.name }}
                <v-chip size="x-small" variant="tonal" class="ml-2">{{ tpl.key }}</v-chip>
              </div>
              <div class="text-caption text-medium-emphasis mb-2">{{ tpl.description }}</div>

              <v-text-field v-model="tpl.subject" label="邮件主题"
                variant="outlined" density="compact" hide-details="auto" class="mb-3" />

              <v-textarea v-model="tpl.body_html" label="HTML 正文"
                variant="outlined" density="compact" hide-details="auto"
                rows="8" class="font-mono" />

              <v-btn
                color="primary"
                variant="tonal"
                size="small"
                class="mt-2"
                :loading="savingTemplate === tpl.key"
                @click="saveTemplate(tpl)"
              >
                保存模板
              </v-btn>
            </v-card-text>
          </v-card>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useGlobalSnackbar } from '@/composables/useGlobalSnackbar'
import {
  getSmtpConfig,
  updateSmtpConfig,
  testSmtpConfig,
  listTemplates,
  updateTemplate,
  type SmtpConfig,
  type EmailTemplate,
} from '@/api/emailConfig'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()
const { notify } = useGlobalSnackbar()
const goBack = () => router.back()

const smtp = reactive<SmtpConfig>({
  host: '', port: 587, username: '', use_tls: true,
  from_address: '', from_name: 'LiveCalc', enabled: false,
})
const passwordField = ref('')
const savingSmtp = ref(false)

const saveSmtp = async () => {
  savingSmtp.value = true
  try {
    const body: Record<string, any> = { ...smtp }
    if (passwordField.value) body.password = passwordField.value
    await updateSmtpConfig(body)
    notify('SMTP 配置已保存', 'success')
  } catch (e: any) {
    notify(e?.userMessage || '保存失败', 'error')
  } finally {
    savingSmtp.value = false
  }
}

const testEmail = ref('')
const testing = ref(false)

const sendTest = async () => {
  if (!testEmail.value) return
  testing.value = true
  try {
    const res = await testSmtpConfig(testEmail.value)
    notify(res.message || '测试邮件已发送', 'success')
  } catch (e: any) {
    notify(e?.userMessage || '发送失败', 'error')
  } finally {
    testing.value = false
  }
}

const templates = ref<EmailTemplate[]>([])
const savingTemplate = ref('')

const saveTemplate = async (tpl: EmailTemplate) => {
  savingTemplate.value = tpl.key
  try {
    await updateTemplate(tpl.key, {
      subject: tpl.subject,
      body_html: tpl.body_html,
    })
    notify(`模板「${tpl.name}」已保存`, 'success')
  } catch (e: any) {
    notify(e?.userMessage || '保存失败', 'error')
  } finally {
    savingTemplate.value = ''
  }
}

const loadAll = async () => {
  try {
    const config = await getSmtpConfig()
    Object.assign(smtp, config)
  } catch { /* ignore */ }
  try {
    templates.value = await listTemplates()
  } catch { /* ignore */ }
}

onMounted(() => { loadAll() })
</script>

<style scoped>
.font-mono :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}
</style>
