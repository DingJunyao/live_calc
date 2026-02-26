<template>
  <div class="login-container">
    <div class="login-card">
      <h1>生计</h1>
      <h2>生活成本计算器</h2>

      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="formData.username"
            type="text"
            required
            placeholder="请输入用户名"
            minlength="3"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            required
            placeholder="请输入密码"
            minlength="6"
          />
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="links">
        <router-link to="/register">注册新账号</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import SHA256 from 'crypto-js/sha256'
import Hex from 'crypto-js/enc-hex'

const router = useRouter()
const userStore = useUserStore()

const formData = ref({
  username: '',
  password: ''
})
const loading = ref(false)
const errorMessage = ref('')

function preparePassword(password: string): string {
  // 使用 crypto-js 进行 SHA256 哈希
  const hash = SHA256(password)
  return hash.toString(Hex)
}

function validateForm(): boolean {
  errorMessage.value = ''

  if (!formData.value.username || formData.value.username.trim().length < 3) {
    errorMessage.value = '用户名至少需要 3 个字符'
    return false
  }

  if (!formData.value.password || formData.value.password.length < 6) {
    errorMessage.value = '密码至少需要 6 个字符'
    return false
  }

  return true
}

async function handleLogin() {
  if (!validateForm()) {
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    // 对密码进行 SHA256 哈希
    const password_hash = preparePassword(formData.value.password)

    await userStore.login(formData.value.username, password_hash)
    router.push('/')
  } catch (error: any) {
    errorMessage.value = error.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.login-card h1 {
  font-size: 2rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.login-card h2 {
  font-size: 1rem;
  color: #666;
  margin-bottom: 2rem;
}

.error-message {
  background-color: #fee;
  color: #c33;
  padding: 0.75rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  border: 1px solid #fcc;
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
