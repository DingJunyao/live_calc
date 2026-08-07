import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { VitePWA } from 'vite-plugin-pwa'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
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

  // 应用身份与版本统一来自仓库根目录的 app-info.json
  const appInfo = JSON.parse(
    readFileSync(fileURLToPath(new URL('../app-info.json', import.meta.url)), 'utf-8'),
  ) as {
    name: string
    shortName: string
    version: string
    description: string
    copyright: string
    repository: string
    homepage: string
    authorHomepage: string
  }

  return {
  define: {
    __APP_INFO__: JSON.stringify(appInfo),
  },
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
    // eruda(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',          // 自动注入 SW 注册脚本
     devOptions: {
       enabled: true,
       type: 'module',
       // dev 模式 dev-dist 仅含 sw.js / workbox-*.js（均被默认 globIgnores 排除），
       // workbox 的 globPatterns（为 build 扫 dist 设计）套用到 dev-dist 必然空匹配 → 控制台警告。
       // 官方开关：dev-dist 补一个空 suppress-warnings.js，并把 dev 用 globPatterns 临时指向它。
       // 仅作用于 dev 分支，build 模式的 globPatterns 与 dist precache 清单不受影响。
       suppressWarnings: true,
     },
      includeAssets: ['favicon.ico', 'logo.svg', 'apple-touch-icon-180x180.png'],
      manifest: {
        name: appInfo.name,
        short_name: appInfo.shortName,
        description: appInfo.description,
        lang: 'zh-CN',
        dir: 'ltr',
        // 显式应用身份，避免依赖 start_url 推导（与当前 '/' 一致，无破坏性）
        id: '/',
        display: 'standalone',
        // 桌面安装版优先用窗口控件覆盖（内容铺到顶部、自定义标题栏），回退 standalone
        display_override: ['window-controls-overlay', 'standalone'],
        orientation: 'portrait',
        scope: '/',
        start_url: '/',
        theme_color: '#558B2F',
        background_color: '#FDFCF8',
        shortcuts : [
            {
                name: "今日推荐",
                url: "/",
                description: "为你的早 / 午 / 晚各选一道菜",
                icons: [{ src: "shortcuts/today.png", sizes: "96x96", type: "image/png" }]
            },
            {
                name: "价格记录",
                url: "/prices",
                icons: [{ src: "shortcuts/prices.png", sizes: "96x96", type: "image/png" }]
            },
            {
                name: "菜谱管理",
                url: "/recipes",
                icons: [{ src: "shortcuts/recipes.png", sizes: "96x96", type: "image/png" }]
            },
            {
                name: "商品管理",
                url: "/data/products",
                icons: [{ src: "shortcuts/products.png", sizes: "96x96", type: "image/png" }]
            },
            {
                name: "原料管理",
                url: "/data/ingredients",
                icons: [{ src: "shortcuts/ingredients.png", sizes: "96x96", type: "image/png" }]
            },
            {
                name: "商家管理",
                url: "/data/merchants",
                icons: [{ src: "shortcuts/merchants.png", sizes: "96x96", type: "image/png" }]
            },
            {
                name: env.VITE_STORAGE_MODE === 'local' ? "设置" : "个人中心",
                url: "/profile",
                icons: [{ src: "shortcuts/profile.png", sizes: "96x96", type: "image/png" }]
            }
        ],
        // 安装弹窗展示应用截图
        screenshots: [
          {
            src: 'screenshots/wide/01.png',
            sizes: '1280x960',
            type: 'image/png',
            form_factor: 'wide',
            label: '桌面端 · 原料详情',
          },
          {
            src: 'screenshots/wide/02.png',
            sizes: '1280x960',
            type: 'image/png',
            form_factor: 'wide',
            label: '桌面端 · 菜谱管理',
          },
          {
            src: 'screenshots/wide/03.png',
            sizes: '1280x960',
            type: 'image/png',
            form_factor: 'wide',
            label: '桌面端 · 菜谱详情',
          },
          {
            src: 'screenshots/wide/04.png',
            sizes: '1280x960',
            type: 'image/png',
            form_factor: 'wide',
            label: '桌面端 · 菜谱分析',
          },
          {
            src: 'screenshots/wide/05.png',
            sizes: '1280x960',
            type: 'image/png',
            form_factor: 'wide',
            label: '桌面端 · 原料管理',
          },
          {
            src: 'screenshots/wide/06.png',
            sizes: '1280x960',
            type: 'image/png',
            form_factor: 'wide',
            label: '桌面端 · 商家管理',
          },
          {
            src: 'screenshots/narrow/01.png',
            sizes: '591x1280',
            type: 'image/png',
            form_factor: 'narrow',
            label: '移动端 · 今日推荐',
          },
          {
            src: 'screenshots/narrow/02.png',
            sizes: '591x1280',
            type: 'image/png',
            form_factor: 'narrow',
            label: '移动端 · 价格记录',
          },
          {
            src: 'screenshots/narrow/03.png',
            sizes: '591x1280',
            type: 'image/png',
            form_factor: 'narrow',
            label: '移动端 · 菜谱管理',
          },
          {
            src: 'screenshots/narrow/04.png',
            sizes: '591x1280',
            type: 'image/png',
            form_factor: 'narrow',
            label: '移动端 · 商家管理',
          },
          {
            src: 'screenshots/narrow/05.png',
            sizes: '591x1280',
            type: 'image/png',
            form_factor: 'narrow',
            label: '移动端 · 商品详情',
          },
          {
            src: 'screenshots/narrow/06.png',
            sizes: '591x1280',
            type: 'image/png',
            form_factor: 'narrow',
            label: '移动端 · 菜谱分析',
          }
        ],
        // 注册自定义协议 web+livecalc://type/id，支持菜谱/商品/原料/商家深链接
        // 浏览器以 /?protocol-uri=web+livecalc://recipe/123 形式唤起应用，前端解析后跳转
        protocol_handlers: [
          {
            protocol: 'web+livecalc',
            url: '/?protocol-uri=%s',
          },
        ],
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
