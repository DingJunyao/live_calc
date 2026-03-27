import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'
import '@mdi/font/css/materialdesignicons.css'

// 预先加载地图相关库（解决百度地图 CRS 问题）
import 'proj4leaflet'
import 'leaflet.chinatmsproviders'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 在应用启动时初始化用户状态
const userStore = useUserStore()
userStore.initializeUserFromStorage()

app.mount('#app')
