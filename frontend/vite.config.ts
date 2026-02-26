import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// 读取环境变量来配置允许的主机
const allowedHostsEnv = process.env.VITE_ALLOWED_HOSTS || 'localhost,127.0.0.1,::1'
const allowedHostsArray = allowedHostsEnv.split(',').map(host => host.trim())

console.log('Allowed hosts:', allowedHostsArray) // 调试信息

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icons/*.png'],
      manifest: {
        name: '生计 - 生活成本计算器',
        short_name: '生计',
        description: '记录商品价格，计算烹饪成本，优化生活开支',
        theme_color: '#42b883',
        icons: [
          {
            src: 'icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    host: '0.0.0.0', // 明确绑定到所有接口
    port: 5173,
    strictPort: false,
    allowedHosts: [
      ...allowedHostsArray,
      'route.a4ding.com' // 明确添加内网穿透域名
    ],
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false, // 对于自签名证书或内网穿透可能需要设置为false
        rewrite: (path) => path.replace(/^\/api\/v1/, '/api/v1')
      }
    }
  }
})
