import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'
import '@mdi/font/css/materialdesignicons.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 在应用启动时初始化用户状态
const userStore = useUserStore()
userStore.initializeUserFromStorage()

app.mount('#app')
