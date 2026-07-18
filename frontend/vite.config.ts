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
                description: "为你的早 / 午 / 晚各选一道菜"
            },
            {
                name: "价格记录",
                url: "/prices"
            },
            {
                name: "菜谱管理",
                url: "/recipes"
            },
            {
                name: "商品管理",
                url: "/data/products"
            },
            {
                name: "原料管理",
                url: "/data/ingredients"
            },
            {
                name: "商家管理",
                url: "/data/merchants"
            },
            {
                name: "个人中心",
                url: "/profile"
            }
        ],
        // 安装弹窗展示应用截图：桌面 wide + 移动 narrow 各一张
        screenshots: [
          {
            src: 'screenshots/desktop-wide.png',
            sizes: '1280x800',
            type: 'image/png',
            form_factor: 'wide',
            label: '桌面端 · 菜谱详情',
          },
          {
            src: 'screenshots/mobile-narrow.png',
            sizes: '590x1280',
            type: 'image/png',
            form_factor: 'narrow',
            label: '移动端 · 菜谱详情',
          },
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
