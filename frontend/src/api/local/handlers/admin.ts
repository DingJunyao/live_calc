// Admin handler — system configuration and statistics.

import { getDb, countAll } from '../database'

async function getConfigValue(key: string): Promise<any> {
  const db = await getDb()
  const val = await db.get('system_config', key)
  return val?.value
}

async function setConfigValue(key: string, value: any): Promise<void> {
  const db = await getDb()
  // 剥离 Vue 响应式 Proxy（结构化克隆无法克隆 Proxy，会抛 DataCloneError）
  const plain = JSON.parse(JSON.stringify(value))
  await db.put('system_config', { key, value: plain })
}

/** 把网络异常转成可读文案（重点标注 CORS 问题） */
function friendlyErr(e: any): string {
  const name = e?.name || ''
  const msg = e?.message || String(e)
  if (name === 'TypeError' || /Failed to fetch|NetworkError|CORS/i.test(msg)) {
    return `浏览器无法连接该端点（可能是 CORS 被拒、域名不通或证书问题）：${msg}`
  }
  if (name === 'TimeoutError' || /timeout|aborted/i.test(msg)) {
    return `请求超时：${msg}`
  }
  return `${name || 'Error'}: ${msg}`
}

/** 带超时的 fetch：用 AbortController + setTimeout 保证一定中止（AbortSignal.timeout 在某些跨域场景下不触发） */
async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  ms: number,
): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), ms)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

export async function getMapConfig(): Promise<any> {
  const config = await getConfigValue('map_config')
  return config || {
    map_enabled: true,
    default_map: 'amap',
    available_maps: ['amap', 'baidu', 'tencent', 'leaflet'],
    map_api_keys: {},
  }
}

export async function updateMapConfig(_params: Record<string, string>, data?: any): Promise<any> {
  await setConfigValue('map_config', data)
  return data
}

export async function getConfig(_params: Record<string, string>, query?: any): Promise<any> {
  const key = query?.key
  if (key) {
    return { key, value: await getConfigValue(key) }
  }
  const db = await getDb()
  const all = await db.getAll('system_config')
  const map: Record<string, any> = {}
  for (const item of all) {
    map[item.key] = item.value
  }
  return map
}

export async function getStats(): Promise<any> {
  // 与云端 AdminStatsResponse 契约对齐：{ users, products, recipes, merchants }。
  // 注意云端 products 字段数的是 ProductRecord（价格记录）表，而非商品实体表，
  // 否则前端 AdminDashboard 读 stats.products 会拿到 undefined 而恒为 0。
  const [priceRecords, recipes, merchants] = await Promise.all([
    countAll('product_records'),
    countAll('recipes'),
    countAll('merchants'),
  ])
  return {
    users: 1, // 本地模式为单用户实例
    products: priceRecords,
    recipes,
    merchants,
  }
}

export async function getStorageConfig(): Promise<any> {
  const config = await getConfigValue('storage_config')
  return config || {
    provider: 'local',
    base_path: '/static',
    config: {},
  }
}

export async function updateStorageConfig(_params: Record<string, string>, data?: any): Promise<any> {
  await setConfigValue('storage_config', data)
  return data
}

export async function listEmailTemplates(): Promise<any> {
  return { items: [], total: 0 }
}

export async function updateEmailTemplate(params: Record<string, string>, data?: any): Promise<any> {
  return { ...data, key: params.key }
}

export async function getMapApiKeys(): Promise<any> {
  const config = await getConfigValue('map_api_keys')
  return config || {}
}

export async function updateMapApiKeys(_params: Record<string, string>, data?: any): Promise<any> {
  await setConfigValue('map_api_keys', data)
  return data
}

// ============================================================
// Images (unused image scanning/cleanup)
// ============================================================

export async function scanImages(): Promise<any> {
  return {
    stats: { total_images: 0, used_images: 0, unused_images: 0, used_size: 0, unused_size: 0 },
    message: '扫描完成',
  }
}

export async function getUnusedImages(): Promise<any> {
  return {
    stats: { total_images: 0, used_images: 0, unused_images: 0, used_size: 0, unused_size: 0 },
    groups: { never_used: [], '180d': [], '90d': [], '60d': [], '30d': [], recent: [] },
  }
}

// ============================================================
// Email config (SMTP + templates)
// ============================================================

export async function getSmtpConfig(): Promise<any> {
  return {
    host: '',
    port: 587,
    username: '',
    use_tls: true,
    use_ssl: false,
    from_address: '',
    from_name: '',
    enabled: false,
  }
}

export async function updateSmtpConfig(_params: Record<string, string>, data?: any): Promise<any> {
  return data || { enabled: false }
}

export async function listTemplates(): Promise<any> {
  return []
}

export async function getEmailTemplate(params: Record<string, string>): Promise<any> {
  return {
    key: params.key,
    name: '邮件模板',
    subject: '通知',
    body_html: '<p>内容</p>',
    description: '',
  }
}

// ============================================================
// Translation / AI config
// ============================================================

export async function getTranslationConfig(): Promise<any> {
  // 默认结构：未保存过时使用；已保存则合并返回（确保 API key 等配置可持久化读回）
  const defaults = {
    ai: {
      providers: {
        claude_code: { enabled: false },
        openai: { enabled: false, base_url: 'https://api.openai.com/v1', api_key: '', model: 'gpt-4o-mini' },
        anthropic: { enabled: false, base_url: 'https://api.anthropic.com', api_key: '', model: 'claude-sonnet-4-6' },
      },
    },
    machine: {
      providers: {
        baidu: { enabled: false, appid: '', secret: '' },
        aliyun: { enabled: false, access_key_id: '', access_key_secret: '' },
        deepl: { enabled: false, auth_key: '' },
      },
    },
  }
  const saved = await getConfigValue('translation_config')
  if (!saved) return defaults
  // 浅合并：保留已保存的 provider key，补齐缺失的默认字段
  const merged = JSON.parse(JSON.stringify(defaults))
  for (const group of ['ai', 'machine']) {
    if (saved?.[group]?.providers) {
      merged[group].providers = { ...merged[group].providers, ...saved[group].providers }
    }
  }
  return merged
}

export async function updateTranslationConfig(_params: Record<string, string>, data?: any): Promise<any> {
  const config = data?.config || data
  await setConfigValue('translation_config', config)
  return config
}

export async function testTranslationConnection(_params: Record<string, string>, data?: any): Promise<any> {
  // 本地模式：对 AI provider 发起一次最小请求验证连通性（浏览器直连，需端点支持 CORS）
  const provider = data?.provider || 'unknown'
  const cfg = await getTranslationConfig()
  const section =
    cfg?.ai?.providers?.[provider] ?? cfg?.machine?.providers?.[provider]

 // 机器翻译 / claude_code：本地无法测试（需服务端签名或 CLI）
  const UNSUPPORTED = ['claude_code', 'baidu', 'aliyun']
  if (UNSUPPORTED.includes(provider)) {
    return {
      provider,
      ok: false,
      detail: '本地模式不支持测试该 provider（需服务端能力）',
    }
  }

  // DeepL：简单的 POST /translate
  if (provider === 'deepl') {
    const authKey = section?.auth_key
    if (!authKey) return { provider, ok: false, detail: '未配置 Auth Key' }
    const isFree = String(authKey).endsWith(':fx')
    const host = isFree ? 'https://api-free.deepl.com' : 'https://api.deepl.com'
    try {
      const res = await fetchWithTimeout(`${host}/v2/translate`, {
        method: 'POST',
        headers: {
          Authorization: `DeepL-Auth-Key ${authKey}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ text: 'Water', target_lang: 'ZH' }).toString(),
      }, 15000)
      if (!res.ok) {
        const t = await res.text().catch(() => '')
        return { provider, ok: false, detail: `DeepL ${res.status}: ${t || res.statusText}` }
      }
      const j = await res.json()
      const out = j?.translations?.[0]?.text
      return {
        provider,
        ok: !!out,
        detail: out ? `连接成功（Water → ${out}）` : '调用成功但无有效译文',
      }
    } catch (e: any) {
      return { provider, ok: false, detail: friendlyErr(e) }
    }
  }

  // OpenAI / Anthropic：发一次最小对话请求
  if (provider === 'openai' || provider === 'anthropic') {
    const apiKey = section?.api_key
    const model = section?.model
    if (!apiKey) return { provider, ok: false, detail: '未配置 API Key' }
    if (!model) return { provider, ok: false, detail: '未配置 Model' }

    try {
      if (provider === 'anthropic') {
        const base = String(section.base_url || 'https://api.anthropic.com').replace(/\/$/, '')
        const res = await fetchWithTimeout(`${base}/v1/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
            'anthropic-dangerous-direct-browser-access': 'true',
          },
          body: JSON.stringify({ model, max_tokens: 8, messages: [{ role: 'user', content: 'ping' }] }),
        }, 20000)
        if (!res.ok) {
          const t = await res.text().catch(() => '')
          return { provider, ok: false, detail: `Anthropic ${res.status}: ${t || res.statusText}` }
        }
        return { provider, ok: true, detail: '连接成功' }
      } else {
        const obase = String(section.base_url || 'https://api.openai.com/v1').replace(/\/$/, '')
        const res = await fetchWithTimeout(`${obase}/chat/completions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({ model, max_tokens: 8, messages: [{ role: 'user', content: 'ping' }] }),
        }, 20000)
        if (!res.ok) {
          const t = await res.text().catch(() => '')
          return { provider, ok: false, detail: `OpenAI ${res.status}: ${t || res.statusText}` }
        }
        return { provider, ok: true, detail: '连接成功' }
      }
    } catch (e: any) {
      return { provider, ok: false, detail: friendlyErr(e) }
    }
  }

  return { provider, ok: false, detail: '未知的 provider' }
}
