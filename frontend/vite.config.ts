import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { VitePWA } from 'vite-plugin-pwa'
// import eruda from 'vite-plugin-eruda'

export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')

  // 读取环境变量来配置允许的主机
  const allowedHostsEnv = env.VITE_ALLOWED_HOSTS || 'localhost,127.0.0.1,::1'
  const allowedHostsArray = allowedHostsEnv.split(',').map(host => host.trim())

  console.log('Allowed hosts:', allowedHostsArray) // 调试信息

  // 开发服务器端口与后端地址走环境变量，便于自定义（见 .env：VITE_DEV_PORT / VITE_DEV_BACKEND_URL）
  const devPort = Number(env.VITE_DEV_PORT) || 5173
  const devBackendUrl = env.VITE_DEV_BACKEND_URL || 'http://localhost:8000'

  return {
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
    // eruda(),
    VitePWA({
      registerType: 'prompt',          // 新版本弹提示，用户主动刷新；不用 autoUpdate 防丢表单
      injectRegister: 'auto',          // 自动注入 SW 注册脚本
      devOptions: { enabled: true },   // vite dev 下 localhost 可测安装
      includeAssets: ['favicon.ico', 'logo.svg', 'apple-touch-icon-180x180.png'],
      manifest: {
        name: '生计 - 生活成本计算器',
        short_name: '生计',
        description: '记录商品价格、计算烹饪与生活成本',
        lang: 'zh-CN',
        dir: 'ltr',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/',
        start_url: '/',
        theme_color: '#558B2F',
        background_color: '#FDFCF8',
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'maskable-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,png,ico,svg,webmanifest,woff2}'],
        navigateFallback: 'index.html',
        // navigateFallbackDenylist 不必配：Workbox navigateFallback 仅拦截
        // Request.mode === 'navigate'（文档导航）；/api/* 是 fetch/cors，不受影响
      },
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: devPort,
    proxy: {
      '/api': {
        target: devBackendUrl,
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
