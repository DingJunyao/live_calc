<template>
  <v-snackbar
    :model-value="needRefresh"
    :timeout="-1"
    color="primary"
    location="top"
    multi-line
  >
    <div class="d-flex align-center">
      <v-icon class="mr-2">mdi-update</v-icon>
      <span>发现新版本，刷新以更新</span>
    </div>
    <template #actions>
      <v-btn variant="text" @click="update">刷新</v-btn>
      <v-btn variant="text" @click="close">稍后</v-btn>
    </template>
  </v-snackbar>
</template>

<script setup lang="ts">
import { useRegisterSW } from 'virtual:pwa-register/vue'

// prompt 模式：检测到新版本 SW 时 needRefresh 置真，弹提示让用户主动刷新，
// 避免 autoUpdate 自动刷新打断用户填价格表单。
// offlineReady（首次 SW 就绪）静默处理——最小集不强调离线，不打扰用户。
const { needRefresh, updateServiceWorker } = useRegisterSW({
  onOfflineReady() {
    // 静默：不做任何提示
  },
})

const update = () => {
  updateServiceWorker(true)
}

const close = () => {
  needRefresh.value = false
}
</script>
