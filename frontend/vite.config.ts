import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import eruda from 'vite-plugin-eruda'

export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')

  // 读取环境变量来配置允许的主机
  const allowedHostsEnv = env.VITE_ALLOWED_HOSTS || 'localhost,127.0.0.1,::1'
  const allowedHostsArray = allowedHostsEnv.split(',').map(host => host.trim())

  console.log('Allowed hosts:', allowedHostsArray) // 调试信息

  return {
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
    eruda(),
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
    allowedHosts: [
      ...allowedHostsArray
    ]
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  }
})
