import { ref } from 'vue'

export type SnackbarColor = 'success' | 'error' | 'info' | 'warning' | undefined

// 模块级单例状态（全局唯一 snackbar）
const show = ref(false)
const message = ref('')
const color = ref<SnackbarColor>('info')

export function useGlobalSnackbar() {
  /** 弹出消息提示，替代浏览器 alert */
  function notify(msg: string, c: SnackbarColor = 'info') {
    message.value = msg
    color.value = c
    show.value = true
  }

  return { show, message, color, notify }
}
