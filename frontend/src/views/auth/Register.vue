<template>
  <div class="register-container">
    <div class="register-card">
      <h1>注册</h1>

      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="formData.username"
            type="text"
            required
            placeholder="3-50个字符"
            minlength="3"
            maxlength="50"
          />
        </div>

        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="formData.email"
            type="email"
            required
            placeholder="your@email.com"
          />
        </div>

        <div class="form-group">
          <label for="phone">手机号（可选）</label>
          <input
            id="phone"
            v-model="formData.phone"
            type="tel"
            placeholder="请输入手机号"
            pattern="^1[3-9]\d{9}$"
          />
          <small>格式: 11位手机号，如 13812345678</small>
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            required
            placeholder="至少6个字符"
            minlength="6"
          />
        </div>

        <div class="form-group" v-if="requireInviteCode">
          <label for="inviteCode">邀请码</label>
          <input
            id="inviteCode"
            v-model="formData.invite_code"
            type="text"
            required
            placeholder="请输入邀请码"
          />
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <div class="links">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formData = ref({
  username: '',
  email: '',
  phone: '',
  password: '',
  invite_code: ''
})
const loading = ref(false)
const errorMessage = ref('')
const requireInviteCode = ref(false)

// 使用 Web Crypto API 进行 SHA256 哈希
async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message)
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
  return hashHex
}

function validateForm(): boolean {
  errorMessage.value = ''

  if (!formData.value.username || formData.value.username.trim().length < 3) {
    errorMessage.value = '用户名至少需要 3 个字符'
    return false
  }

  if (formData.value.username.length > 50) {
    errorMessage.value = '用户名最多 50 个字符'
    return false
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!formData.value.email || !emailRegex.test(formData.value.email)) {
    errorMessage.value = '请输入有效的邮箱地址'
    return false
  }

  if (formData.value.phone && !/^1[3-9]\d{9}$/.test(formData.value.phone)) {
    errorMessage.value = '请输入有效的手机号'
    return false
  }

  if (!formData.value.password || formData.value.password.length < 6) {
    errorMessage.value = '密码至少需要 6 个字符'
    return false
  }

  return true
}

onMounted(async () => {
  // 检查是否需要邀请码
  // 注意：此端点可能需要在后端实现
  try {
    const config = await fetch('/api/v1/config').then(r => r.json())
    requireInviteCode.value = config.registration_require_invite_code || false
  } catch (error) {
    // 忽略错误，默认不需要邀请码
    requireInviteCode.value = false
  }
})

async function handleRegister() {
  if (!validateForm()) {
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const password_hash = await sha256(formData.value.password)

    await userStore.register({
      ...formData.value,
      password_hash
    })
    router.push('/')
  } catch (error: any) {
    errorMessage.value = error.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.register-card h1 {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 1.5rem;
}

.error-message {
  background-color: #fee;
  color: #c33;
  padding: 0.75rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  border: 1px solid #fcc;
}

.form-group small {
  display: block;
  font-size: 0.75rem;
  color: #999;
  margin-top: 0.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.btn-primary {
  width: 100%;
  padding: 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  cursor: pointer;
  margin-top: 1rem;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.links {
  margin-top: 1.5rem;
  text-align: center;
}

.links a {
  color: #667eea;
  text-decoration: none;
}

.links a:hover {
  text-decoration: underline;
}
</style>
