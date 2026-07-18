// main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'
import './assets/css/responsive.css'

// 导入 Leaflet 样式和地图相关库
// 注意：proj4leaflet 必须在 leaflet.chinatmsproviders 之前导入
import 'leaflet/dist/leaflet.css'
import 'proj4leaflet'
import 'leaflet.chinatmsproviders'

// 修复 Edge 浏览器窗口最小化后立即恢复的问题
// 原因：Vue Router 在 visibilitychange 事件中调用 history API，
// Edge 错误地将其识别为页面激活信号，导致窗口强制恢复
const originalReplaceState = window.history.replaceState.bind(window.history)
const originalPushState = window.history.pushState.bind(window.history)

window.history.replaceState = function (...args: Parameters<typeof originalReplaceState>) {
  if (document.visibilityState === 'hidden') return
  return originalReplaceState(...args)
}
window.history.pushState = function (...args: Parameters<typeof originalPushState>) {
  if (document.visibilityState === 'hidden') return
  return originalPushState(...args)
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')

// 兜底：站内 <a href="/..."> 点击统一交给 Vue Router 客户端导航（preventDefault + router.push）。
// 防止 <a> 默认文档导航在 PWA standalone 下被浏览器甩到外部窗口——
// Vuetify v-list-item 等组件在某些环境下只调 router.push、漏了 preventDefault，
// 普通浏览器 tab 里默认导航在当前页无感，PWA standalone 才会被甩到外部浏览器。
document.addEventListener('click', (e) => {
  const a = (e.target as HTMLElement | null)?.closest('a')
  if (!a) return
  const href = a.getAttribute('href')
  if (!href || a.target === '_blank') return
  // 仅站内绝对路径（/xxx），排除外部 URL、协议链接、锚点
  if (!href.startsWith('/') || href.startsWith('//')) return
  e.preventDefault()
  router.push(href)
}, false)
