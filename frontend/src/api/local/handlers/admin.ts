// Admin handler — system configuration and statistics.

import { getDb, countAll, addOne } from '../database'
import { fixBlobMime } from '@/utils/image'
import CryptoJS from 'crypto-js'

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
  const raw = await getConfigValue('storage_config')
  if (!raw) {
    return {
      backend: 'local',
      storage_base_url: null,
      s3_endpoint: null,
      s3_bucket: null,
      s3_region: null,
      s3_access_key: null,
      has_access_key: false,
      s3_secret_key: null,
      has_secret_key: false,
      s3_base_path: null,
      s3_custom_domain: null,
      s3_url_suffix: null,
      s3_url_style: 'path',
      sources: {},
    }
  }
  return {
    backend: raw.backend || 'local',
    storage_base_url: raw.storage_base_url || null,
    s3_endpoint: raw.s3_endpoint || null,
    s3_bucket: raw.s3_bucket || null,
    s3_region: raw.s3_region || null,
    s3_access_key: raw.s3_access_key ? '***' : null,
    has_access_key: !!raw.s3_access_key,
    s3_secret_key: raw.s3_secret_key ? '***' : null,
    has_secret_key: !!raw.s3_secret_key,
    s3_base_path: raw.s3_base_path || null,
    s3_custom_domain: raw.s3_custom_domain || null,
    s3_url_suffix: raw.s3_url_suffix || null,
    s3_url_style: raw.s3_url_style || 'path',
    sources: {},
  }
}

export async function updateStorageConfig(_params: Record<string, string>, data?: any): Promise<any> {
  const existing = (await getConfigValue('storage_config')) || {}
  const merged: Record<string, any> = { ...existing }
  const fields = [
    'backend', 'storage_base_url', 's3_endpoint', 's3_bucket', 's3_region',
    's3_base_path', 's3_custom_domain', 's3_url_suffix', 's3_url_style',
  ]
  for (const f of fields) {
    if (data?.[f] !== undefined) merged[f] = data[f] || null
  }
  for (const cred of ['s3_access_key', 's3_secret_key']) {
    if (data?.[cred] && data[cred] !== '***') {
      merged[cred] = data[cred]
    }
  }
  await setConfigValue('storage_config', merged)
  return { ok: true }
}

/** Build an S3 object URL from a storage key and config. */
export function buildS3Url(key: string, cfg: {
  s3_endpoint?: string | null
  s3_bucket?: string | null
  s3_base_path?: string | null
  s3_custom_domain?: string | null
  s3_url_suffix?: string | null
  s3_url_style?: string | null
}): string {
  const basePath = cfg.s3_base_path || ''
  const suffix = cfg.s3_url_suffix || ''
  const fullKey = (basePath ? `${basePath}/` : '') + key.split('/').map(s => encodeURIComponent(s)).join('/')
  if (cfg.s3_custom_domain) {
    return `${cfg.s3_custom_domain.replace(/\/$/, '')}/${fullKey}${suffix}`
  }
  const endpoint = (cfg.s3_endpoint || '').replace(/\/$/, '')
  const bucket = cfg.s3_bucket || ''
  if (cfg.s3_url_style === 'virtual') {
    try {
      const u = new URL(endpoint)
      return `${u.protocol}//${bucket}.${u.host}/${fullKey}${suffix}`
    } catch { /* fall through to path style */ }
  }
  return `${endpoint}/${bucket}/${fullKey}${suffix}`
}

/** Normalize an image path to the S3 logical key used by the app. */
function normalizeStorageKey(path: string): string {
  return path.replace(/^\/static\/images\//, '').replace(/^\/+/, '')
}

/** RFC 3986 path-segment encoding used by AWS SigV4. */
function awsUriEncode(value: string): string {
  return encodeURIComponent(value).replace(/[!'()*]/g, (ch) => (
    `%${ch.charCodeAt(0).toString(16).toUpperCase()}`
  ))
}

/** Build the endpoint URL used for S3 API calls (never the read-only CDN domain). */
function buildS3ApiTarget(key: string, cfg: {
  s3_endpoint?: string | null
  s3_bucket?: string | null
  s3_base_path?: string | null
  s3_url_style?: string | null
}): { url: string; host: string; canonicalUri: string } {
  const rawEndpoint = (cfg.s3_endpoint || '').trim()
  const bucket = (cfg.s3_bucket || '').trim()
  if (!rawEndpoint) throw new Error('S3 endpoint 不能为空')
  if (!bucket) throw new Error('S3 bucket 不能为空')
  const endpoint = rawEndpoint.includes('://') ? rawEndpoint : `https://${rawEndpoint}`
  const basePath = (cfg.s3_base_path || '').replace(/^\/+|\/+$/g, '')
  const logicalKey = normalizeStorageKey(key)
  const rawPath = [basePath, ...logicalKey.split('/')].filter(Boolean).join('/')
  const encodedPath = rawPath.split('/').map(awsUriEncode).join('/')

  if (cfg.s3_url_style === 'virtual') {
    const u = new URL(endpoint)
    const canonicalUri = `/${encodedPath}`
    const url = `${u.protocol}//${bucket}.${u.host}${canonicalUri}`
    return { url, host: new URL(url).host, canonicalUri }
  }

  const u = new URL(endpoint)
  const endpointPath = u.pathname === '/' ? '' : u.pathname.replace(/\/$/, '')
  const canonicalUri = `/${awsUriEncode(bucket)}/${encodedPath}`
  const url = `${u.origin}${endpointPath}${canonicalUri}`
  return { url, host: new URL(url).host, canonicalUri }
}

/** SHA-256 of a Blob using crypto-js (works on non-HTTPS LAN hosts too). */
async function sha256Blob(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer())
  const words: number[] = []
  for (let i = 0; i < bytes.length; i++) {
    words[i >>> 2] = (words[i >>> 2] || 0) | (bytes[i] << (24 - (i % 4) * 8))
  }
  return CryptoJS.SHA256(CryptoJS.lib.WordArray.create(words, bytes.length)).toString()
}

/** Build and execute an AWS SigV4-signed S3 request from the browser. */
async function signedS3Fetch(
  method: 'PUT' | 'GET' | 'HEAD',
  key: string,
  cfg: {
    s3_endpoint?: string | null
    s3_bucket?: string | null
    s3_access_key?: string | null
    s3_secret_key?: string | null
    s3_region?: string | null
    s3_base_path?: string | null
    s3_url_style?: string | null
  },
  body?: Blob | null,
  contentType?: string,
): Promise<Response> {
  const { url, host, canonicalUri } = buildS3ApiTarget(key, cfg)
  const accessKey = (cfg.s3_access_key || '').trim()
  const secretKey = (cfg.s3_secret_key || '').trim()
  if (!accessKey || !secretKey) throw new Error('S3 access key / secret key 不能为空')
  const region = (cfg.s3_region || 'us-east-1').trim()
  const payloadHash = body ? await sha256Blob(body) : CryptoJS.SHA256('').toString()
  const now = new Date()
  const amzDate = now.toISOString().replace(/[-:]|\.\d{3}/g, '')
  const dateStamp = amzDate.slice(0, 8)
  const scope = `${dateStamp}/${region}/s3/aws4_request`

  const signedHeaders = contentType
    ? 'content-type;host;x-amz-content-sha256;x-amz-date'
    : 'host;x-amz-content-sha256;x-amz-date'
  const canonicalHeaders = [
    contentType ? `content-type:${contentType}` : '',
    `host:${host}`,
    `x-amz-content-sha256:${payloadHash}`,
    `x-amz-date:${amzDate}`,
  ].filter(Boolean).join('\n') + '\n'

  const canonicalRequest = [
    method,
    canonicalUri,
    '',
    canonicalHeaders,
    signedHeaders,
    payloadHash,
  ].join('\n')
  const stringToSign = [
    'AWS4-HMAC-SHA256',
    amzDate,
    scope,
    CryptoJS.SHA256(canonicalRequest).toString(),
  ].join('\n')

  const kDate = CryptoJS.HmacSHA256(dateStamp, `AWS4${secretKey}`)
  const kRegion = CryptoJS.HmacSHA256(region, kDate)
  const kService = CryptoJS.HmacSHA256('s3', kRegion)
  const kSigning = CryptoJS.HmacSHA256('aws4_request', kService)
  const signature = CryptoJS.HmacSHA256(stringToSign, kSigning).toString()
  const authorization =
    `AWS4-HMAC-SHA256 Credential=${accessKey}/${scope}, ` +
    `SignedHeaders=${signedHeaders}, Signature=${signature}`

  const headers: Record<string, string> = {
    'x-amz-content-sha256': payloadHash,
    'x-amz-date': amzDate,
    Authorization: authorization,
  }
  if (contentType) headers['Content-Type'] = contentType
  return fetchWithTimeout(url, { method, headers, body: body ?? undefined }, 60000)
}

/** Merge blank wizard credentials with the saved raw config (secret sentinel support). */
async function mergeSavedS3Config(data: any): Promise<any> {
  const saved = (await getConfigValue('storage_config')) || {}
  const merged: Record<string, any> = { ...saved }
  for (const [key, value] of Object.entries(data || {})) {
    if (value && value !== '***') merged[key] = value
  }
  return merged
}

export async function testStorageConfig(_params: Record<string, string>, data?: any): Promise<any> {
  if (data?.backend !== 's3') return { ok: true, error: null }
  const cfg = await mergeSavedS3Config(data)
  if (!cfg.s3_endpoint || !cfg.s3_bucket) return { ok: false, error: 'endpoint 和 bucket 不能为空' }
  if (!cfg.s3_access_key || !cfg.s3_secret_key) return { ok: false, error: 'access key / secret key 不能为空' }
  try {
    const resp = await signedS3Fetch('HEAD', '_storage_probe_test', cfg)
    // 200 = object exists, 404 = credentials valid but probe key missing. Both mean the config works.
    if (resp.status === 200 || resp.status === 404) return { ok: true, error: null }
    return { ok: false, error: `S3 返回 ${resp.status}，请检查密钥/权限/CORS 配置` }
  } catch (e: any) {
    return { ok: false, error: friendlyErr(e) }
  }
}

export async function migrateStorage(_params: Record<string, string>, data?: any): Promise<any> {
  const direction = data?.direction
  if (direction !== 'to_s3' && direction !== 'to_local') {
    throw { status: 400, message: '无效的迁移方向' }
  }
  const db = await getDb()
  const total = await db.count('images')
  const taskId = await addOne('import_tasks', {
    task_type: 'storage_migrate',
    status: 'running',
    progress: { stage: '准备中', current: 0, total, uploaded: 0, skipped: 0, failed: 0 },
    stats: { uploaded: 0, skipped: 0, failed: 0 },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })

  // 本地模式没有后台线程：把迁移循环放到独立异步任务里，先返回 task_id，
  // 前端轮询 import/task/:id 才能看到实时进度。
  setTimeout(() => {
    void runStorageMigration(db, taskId, direction, data?.s3_config, total)
  }, 0)
  return { task_id: taskId }
}

async function updateMigrationTask(
  db: any,
  taskId: number | string,
  stage: string,
  current: number,
  total: number,
  stats: { uploaded: number; skipped: number; failed: number },
  status?: string,
  error?: string | null,
): Promise<void> {
  const task = await db.get('import_tasks', taskId)
  if (!task || task.status === 'cancelled') return
  await db.put('import_tasks', {
    ...task,
    ...(status ? { status } : {}),
    ...(error !== undefined ? { error } : {}),
    progress: { stage, current, total, ...stats },
    stats,
    updated_at: new Date().toISOString(),
  })
}

async function runStorageMigration(
  db: any,
  taskId: number | string,
  direction: string,
  s3Config: any,
  total: number,
): Promise<void> {
  let uploaded = 0
  let skipped = 0
  let failed = 0
  try {
    const allImages = await db.getAll('images')
    const targetS3Config = direction === 'to_s3'
      ? await mergeSavedS3Config(s3Config)
      : await mergeSavedS3Config(null)
    if (direction === 'to_s3' && !targetS3Config.s3_endpoint) {
      throw new Error('S3 endpoint 不能为空')
    }
    if (direction === 'to_local' && (!targetS3Config.s3_endpoint || !targetS3Config.s3_bucket)) {
      throw new Error('当前存储不是有效的 S3 配置')
    }

    const CHUNK_SIZE = 5
    for (let i = 0; i < allImages.length; i += CHUNK_SIZE) {
      const current = await db.get('import_tasks', taskId)
      if (current?.status === 'cancelled') return

      const chunk = allImages.slice(i, i + CHUNK_SIZE)
      for (const img of chunk) {
        const key = normalizeStorageKey(img.path || `images/${img.id}`)
        try {
          if (direction === 'to_s3' && img.blob) {
            const resp = await signedS3Fetch(
              'PUT',
              key,
              targetS3Config,
              img.blob,
              img.mime_type || 'application/octet-stream',
            )
            if (resp.ok) uploaded++
            else {
              failed++
              console.warn(`[migrate] PUT ${img.path} -> ${resp.status}`)
            }
          } else if (direction === 'to_local') {
            const resp = await signedS3Fetch('GET', key, targetS3Config)
            if (!resp.ok) {
              skipped++
              console.warn(`[migrate] GET ${img.path} -> ${resp.status}`)
              continue
            }
            const blob = await resp.blob()
            await db.put('images', { ...img, blob, mime_type: blob.type || img.mime_type })
            uploaded++
          } else {
            skipped++
          }
        } catch (e: any) {
          failed++
          console.warn(`[migrate] ${img.path}: ${e?.message || e}`)
        }
      }
      await updateMigrationTask(
        db,
        taskId,
        `迁移中 ${Math.min(i + CHUNK_SIZE, allImages.length)}/${allImages.length}`,
        Math.min(i + CHUNK_SIZE, allImages.length),
        allImages.length,
        { uploaded, skipped, failed },
      )
      await new Promise((resolve) => setTimeout(resolve, 0))
    }

    await updateMigrationTask(
      db,
      taskId,
      '完成',
      total,
      total,
      { uploaded, skipped, failed },
      'success',
      failed > 0 ? `${failed} 张图片迁移失败` : null,
    )
  } catch (e: any) {
    console.error('[migrate] 迁移任务失败:', e)
    const current = await db.get('import_tasks', taskId).catch(() => null)
    if (current && current.status !== 'cancelled') {
      await updateMigrationTask(
        db,
        taskId,
        '失败',
        total,
        total,
        { uploaded, skipped, failed },
        'failed',
        e?.message || String(e),
      )
    }
  }
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
  const stats = await computeImageStats()
  return { stats, message: '扫描完成' }
}

export async function getUnusedImages(): Promise<any> {
  return computeUnusedImages()
}

export async function deleteUnusedImages(_params: Record<string, string>, data?: any): Promise<any> {
  const keys: string[] = data?.keys || []
  if (!keys.length) throw { status: 400, message: '缺少 keys' }
  const db = await getDb()
  const allImages = await db.getAll('images')
  const deleted: string[] = []
  const errors: string[] = []
  for (const img of allImages) {
    const imgKey = img.path || String(img.id)
    if (keys.includes(imgKey)) {
      try {
        await db.delete('images', img.id)
        deleted.push(imgKey)
      } catch (e: any) {
        errors.push(`${imgKey}: ${e?.message || e}`)
      }
    }
  }
  return { deleted, errors }
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

// ============================================================
// Image scanning helpers (IndexedDB-based unused image detection)
// ============================================================

/** Collect all image keys referenced by entities (recipes, products, etc.). */
async function collectUsedImageKeys(): Promise<Set<string>> {
  const db = await getDb()
  const used = new Set<string>()
  const recipes = await db.getAll('recipes')
  for (const recipe of recipes) {
    if (Array.isArray(recipe.images)) {
      for (const img of recipe.images) {
        if (typeof img === 'string' && img) used.add(normalizeStorageKey(img))
      }
    }
  }
  const products = await db.getAll('products')
  for (const p of products) {
    if (typeof p.image_url === 'string' && p.image_url && !p.image_url.startsWith('http')) {
      used.add(normalizeStorageKey(p.image_url))
    }
  }
  return used
}

async function computeImageStats(): Promise<{
  total_images: number; used_images: number; unused_images: number
  used_size: number; unused_size: number
}> {
  const db = await getDb()
  const allImages = await db.getAll('images')
  const usedKeys = await collectUsedImageKeys()
  let usedCount = 0, unusedCount = 0, usedSize = 0, unusedSize = 0
  for (const img of allImages) {
    const key = normalizeStorageKey(img.path || String(img.id))
    const size = img.blob?.size || 0
    if (usedKeys.has(key)) { usedCount++; usedSize += size }
    else { unusedCount++; unusedSize += size }
  }
  return {
    total_images: allImages.length, used_images: usedCount,
    unused_images: unusedCount, used_size: usedSize, unused_size: unusedSize,
  }
}

async function computeUnusedImages(): Promise<{
  stats: any; groups: any[]
}> {
  const db = await getDb()
  const allImages = await db.getAll('images')
  const usedKeys = await collectUsedImageKeys()
  const now = Date.now()
  const DAY_MS = 86400000
  const groupDefs = [
    { key: 'never_used', label: '从未引用', test: () => true },
    { key: '180d', label: '创建超过 180 天', test: (t: number) => (now - t) / DAY_MS >= 180 },
    { key: '90d', label: '创建 90~180 天', test: (t: number) => { const d = (now - t) / DAY_MS; return d >= 90 && d < 180 } },
    { key: '60d', label: '创建 60~90 天', test: (t: number) => { const d = (now - t) / DAY_MS; return d >= 60 && d < 90 } },
    { key: '30d', label: '创建 30~60 天', test: (t: number) => { const d = (now - t) / DAY_MS; return d >= 30 && d < 60 } },
    { key: 'recent', label: '创建 30 天内', test: (t: number) => (now - t) / DAY_MS < 30 },
  ]
  const groups = groupDefs.map(g => ({ ...g, images: [] as any[], count: 0, total_size: 0 }))
  let totalImages = 0, usedImages = 0, unusedImages = 0
  let usedSize = 0, unusedSize = 0
  for (const img of allImages) {
    const key = normalizeStorageKey(img.path || String(img.id))
    const size = img.blob?.size || 0
    totalImages++
    if (usedKeys.has(key)) { usedImages++; usedSize += size; continue }
    unusedImages++; unusedSize += size
    let url = ''
    try { if (img.blob) url = URL.createObjectURL(await fixBlobMime(img.blob, img.path)) } catch { /* ignore */ }
    const item = {
      key, filename: key.split('/').pop() || key, url,
      file_size: size,
      last_used_at: img.created_at || null,
    }
    const created = img.created_at ? new Date(img.created_at).getTime() : 0
    for (const g of groups) {
      if (g.test(created)) {
        g.images.push(item); g.count++; g.total_size += size; break
      }
    }
  }
  const cleanGroups = groups.map(({ key, label, images, count, total_size }) =>
    ({ key, label, images, count, total_size }))
  return {
    stats: {
      total_images: totalImages, used_images: usedImages, unused_images: unusedImages,
      used_size: usedSize, unused_size: unusedSize,
    },
    groups: cleanGroups,
  }
}
