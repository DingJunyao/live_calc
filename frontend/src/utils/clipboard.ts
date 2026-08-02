/**
 * 复制文本到剪贴板，兼容 http / https / file 等非安全上下文。
 *
 * 优先用 Clipboard API（window.isSecureContext 为 true 时可用，含 https 与 localhost）；
 * 不可用或失败时降级到 document.execCommand('copy')（临时 textarea + 选中），
 * 兼容 http 明文部署（如内网 / NAS 直连场景）。
 *
 * @returns 是否复制成功
 */
export async function copyText(text: string): Promise<boolean> {
  // 安全上下文：优先 Clipboard API
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 权限拒绝或其它异常，走降级
    }
  }
  // 降级：临时 textarea + execCommand('copy')
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    // 固定定位 + 透明，避免页面跳动；mobile 需 fontSize ≥ 16px 防缩放
    ta.style.position = 'fixed'
    ta.style.top = '0'
    ta.style.left = '0'
    ta.style.fontSize = '16px'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}
