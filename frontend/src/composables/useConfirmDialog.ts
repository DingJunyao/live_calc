import { ref } from 'vue'

export interface ConfirmOptions {
  /** 对话框标题，默认「请确认」 */
  title?: string
  /** 正文内容 */
  text: string
  /** 确认按钮文字，默认「确认」 */
  confirmText?: string
  /** 取消按钮文字，默认「取消」 */
  cancelText?: string
  /** 确认按钮颜色，默认「primary」；删除场景用「error」 */
  color?: string
}

// 模块级单例状态（全局唯一对话框）
const visible = ref(false)
const options = ref<ConfirmOptions>({ text: '' })
let resolver: ((v: boolean) => void) | null = null

export function useConfirmDialog() {
  /**
   * 弹出确认对话框，返回 Promise<boolean>（true=确认，false=取消）。
   * 用法：`const { ask } = useConfirmDialog(); if (!await ask({ text: '...' })) return`
   */
  function ask(opts: ConfirmOptions): Promise<boolean> {
    options.value = opts
    visible.value = true
    return new Promise<boolean>((resolve) => {
      resolver = resolve
    })
  }

  /** 由对话框组件调用，回传用户选择 */
  function answer(val: boolean) {
    visible.value = false
    resolver?.(val)
    resolver = null
  }

  return { visible, options, ask, answer }
}
