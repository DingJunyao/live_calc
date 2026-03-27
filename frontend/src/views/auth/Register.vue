<template>
  <v-app>
    <v-main class="d-flex align-center justify-center bg-background">
      <v-container class="h-100 d-flex align-center justify-center">
        <v-card class="elevation-8" max-width="400" width="100%">
          <v-card-title class="text-center pa-6">
            <div class="text-h4 font-weight-bold text-primary">注册</div>
            <div class="text-subtitle-2 text-medium-emphasis mt-2">创建您的生计账号</div>
          </v-card-title>

          <v-card-text>
            <v-form @submit.prevent="handleRegister">
              <v-text-field
                v-model="form.username"
                label="用户名"
                prepend-inner-icon="mdi-account"
                variant="outlined"
                required
                :error-messages="errors.username"
                class="mb-4"
              />

              <v-text-field
                v-model="form.email"
                label="邮箱"
                prepend-inner-icon="mdi-email"
                type="email"
                variant="outlined"
                required
                :error-messages="errors.email"
                class="mb-4"
              />

              <v-text-field
                v-model="form.password"
                label="密码"
                prepend-inner-icon="mdi-lock"
                type="password"
                variant="outlined"
                required
                :error-messages="errors.password"
                class="mb-4"
              />

              <v-text-field
                v-model="form.confirmPassword"
                label="确认密码"
                prepend-inner-icon="mdi-lock-check"
                type="password"
                variant="outlined"
                required
                :error-messages="errors.confirmPassword"
                class="mb-4"
              />

              <v-text-field
                v-if="requireInviteCode"
                v-model="form.inviteCode"
                label="邀请码"
                prepend-inner-icon="mdi-ticket"
                variant="outlined"
                required
                :error-messages="errors.inviteCode"
                class="mb-4"
              />

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                variant="elevated"
                :loading="loading"
              >
                注册
              </v-btn>
            </v-form>

            <v-alert v-if="errorMessage" type="error" class="mt-4" closable>
              {{ errorMessage }}
            </v-alert>
          </v-card-text>

          <v-card-actions class="pa-4 pt-0">
            <span class="text-body-2 text-medium-emphasis">已有账号？</span>
            <v-btn variant="text" color="primary" to="/login" class="ml-1">
              立即登录
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/api/client'
import { hashPassword } from '@/utils/crypto'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  inviteCode: '',
})

const errors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  inviteCode: '',
})

const loading = ref(false)
const errorMessage = ref('')
const requireInviteCode = ref(false)

// 获取注册配置
onMounted(async () => {
  try {
    const config: any = await api.get('/auth/config')
    requireInviteCode.value = config.registration_require_invite_code || false
  } catch (error) {
    console.error('Failed to fetch auth config:', error)
  }
})

const handleRegister = async () => {
  // 清空错误
  Object.keys(errors).forEach(key => {
    errors[key as keyof typeof errors] = ''
  })
  errorMessage.value = ''

  // 验证
  let hasError = false
  if (!form.username) {
    errors.username = '请输入用户名'
    hasError = true
  }
  if (!form.email) {
    errors.email = '请输入邮箱'
    hasError = true
  }
  if (!form.password) {
    errors.password = '请输入密码'
    hasError = true
  } else if (form.password.length < 6) {
    errors.password = '密码至少需要6个字符'
    hasError = true
  }
  if (form.password !== form.confirmPassword) {
    errors.confirmPassword = '两次输入的密码不一致'
    hasError = true
  }
  if (requireInviteCode.value && !form.inviteCode) {
    errors.inviteCode = '请输入邀请码'
    hasError = true
  }

  if (hasError) return

  loading.value = true
  try {
    // 在前端加密密码
    const passwordHash = hashPassword(form.password)
    await userStore.register(
      form.username,
      form.email,
      passwordHash,
      requireInviteCode.value ? form.inviteCode : undefined
    )
    router.push('/')
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>
