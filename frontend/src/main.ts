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
