/**
 * 菜谱/原料图片路径解析（统一入口）。
 *
 * 云模式路径有四种形态，按优先级解析：
 * 1. http(s) 绝对 URL（S3 等远端存储）—— 原样返回
 * 2. /static/images/... 旧格式路径 —— 提取 key 后走动态图片端点 /api/v1/images/
 * 3. recipes/xxx.jpg 等 storage key（新格式）—— 同样走动态图片端点
 * 4. 其它（仓库相对路径，如 images/xxx.jpg）—— 拼到数据仓库图片基址（兜底）
 *
 * 本地模式：图片存 IndexedDB Blob，此函数返回空字符串，
 * 调用方应使用 loadLocalImageBlob() 异步加载。
 *
 * 统一抽离自 RecipesView / RecipeDetail / ImageManager / RecipeEditDiff / MealCard
 * 各自重复的实现；同时补齐 MealCard 原本缺失的「仓库兜底」分支，
 * 让残缺路径（如 images/xxx.jpg）也能从远程仓库加载，行为与其余页面一致。
 */
const DEFAULT_REPO_BASE =
  'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out'

/**
 * Local-mode S3 config cache (synchronous read, avoids making resolveImageUrl async).
 * Loaded by preloadStorageConfig() at app startup; null means not loaded yet.
 */
let cachedStorageConfig: any = null

export async function preloadStorageConfig(): Promise<void> {
  if (import.meta.env.VITE_STORAGE_MODE !== 'local') return
  try {
    const { getDb } = await import('@/api/local/database')
    const db = await getDb()
    const val = await db.get('system_config', 'storage_config')
    cachedStorageConfig = val?.value || null
  } catch { /* ignore — fall back to repo */ }
}

/** Build an S3 object URL (mirrors admin.buildS3Url for synchronous use). */
function buildS3UrlLocal(key: string, cfg: any): string {
  const basePath = cfg.s3_base_path || ''
  const suffix = cfg.s3_url_suffix || ''
  const fullKey = (basePath ? `${basePath}/` : '') + key.split('/').map(s => encodeURIComponent(s)).join('/')
  if (cfg.s3_custom_domain) return `${cfg.s3_custom_domain.replace(/\/$/, '')}/${fullKey}${suffix}`
  const endpoint = (cfg.s3_endpoint || '').replace(/\/$/, '')
  const bucket = cfg.s3_bucket || ''
  if (cfg.s3_url_style === 'virtual') {
    try { const u = new URL(endpoint); return `${u.protocol}//${bucket}.${u.host}/${fullKey}${suffix}` }
    catch { /* fall through */ }
  }
  return `${endpoint}/${bucket}/${fullKey}${suffix}`
}

export function resolveImageUrl(path: string | null | undefined): string {
  if (!path) return ''

  if (path.startsWith('http')) return path
  const base = import.meta.env.VITE_API_URL || '/api/v1'
  const isLocal = import.meta.env.VITE_STORAGE_MODE === 'local'

  // 本地模式：没有后端图片服务，直接走仓库远程兜底
  // 图片路径含中文需 URL encode，否则浏览器加载失败
  if (isLocal) {
    // S3 backend active? Build S3 URL from cached config
    if (cachedStorageConfig?.backend === 's3' && cachedStorageConfig.s3_endpoint && cachedStorageConfig.s3_bucket) {
      const key = path.startsWith('/static/images/') ? path.slice('/static/images/'.length) : path
      return buildS3UrlLocal(key, cachedStorageConfig)
    }
    // http(s) 已在上面返回，/static/ 和 recipes/ 等走仓库基址
    if (path.startsWith('/static/images/')) {
      const key = path.slice('/static/images/'.length)
      // 本地模式无法提供图片服务，但仓库可能有
      const repoBase = import.meta.env.VITE_DATA_REPO_IMAGE_BASE || DEFAULT_REPO_BASE
      return `${repoBase}/${key.split('/').map(s => encodeURIComponent(s)).join('/')}`
    }
    const repoBase = import.meta.env.VITE_DATA_REPO_IMAGE_BASE || DEFAULT_REPO_BASE
    return `${repoBase}/${path.split('/').map(s => encodeURIComponent(s)).join('/')}`
  }

  // 旧格式 /static/images/recipes/xxx.jpg → 提取 key → 走动态图片端点
  if (path.startsWith('/static/images/')) {
    const key = path.slice('/static/images/'.length)
    return `${base}/images/${key}`
  }
  // Storage key: "recipes/xxx.jpg", "avatars/yyy.png"（相对路径，无前导 /）
  if (/^(recipes|avatars)\//.test(path)) {
    return `${base}/images/${path}`
  }
  const repoBase = import.meta.env.VITE_DATA_REPO_IMAGE_BASE || DEFAULT_REPO_BASE
  return `${repoBase}/${path}`
}

/**
 * 本地模式：从 IndexedDB 加载图片 Blob 并创建对象 URL。
 * 调用方应在组件 onUnmounted 中调用 URL.revokeObjectURL() 清理。
 *
 * 查询方式：先按 entityType + entityId 精确匹配，再按 imageKey 回退。
 *
 * @param entityType - 实体类型，如 'recipes'、'products'、'avatars'
 * @param entityId   - 实体 ID
 * @param imageKey   - （可选）图片 key，用于精确匹配
 * @returns          - 对象 URL 或 null
 */
export async function loadLocalImageBlob(
  entityType: string,
  entityId: number,
  imageKey?: string | null,
): Promise<string | null> {
  if (import.meta.env.VITE_STORAGE_MODE !== 'local') return null
  try {
    const { getDb } = await import('@/api/local/database')
    const db = await getDb()
    // S3 backend 下不再从 IndexedDB 读 blob，交给 resolveImageUrl / image_urls 走远端。
    const cfg = (await db.get('system_config', 'storage_config'))?.value
    if (cfg?.backend === 's3') return null
    // Try exact key match first
    if (imageKey) {
      const all = await db.getAllFromIndex('images', 'by_entity', [entityType, entityId])
      const matched = all.find((img: any) => img.path === imageKey || img.key === imageKey)
      if (matched?.blob) {
        const fixed = await fixBlobMime(matched.blob, imageKey || undefined)
        return URL.createObjectURL(fixed)
      }
    }
    // Fall back to the first image for this entity
    const images = await db.getAllFromIndex('images', 'by_entity', [entityType, entityId])
    if (images.length > 0 && images[0].blob) {
      const fixed = await fixBlobMime(images[0].blob, images[0].path || undefined)
      return URL.createObjectURL(fixed)
    }
    return null
  } catch (e) {
    console.error('Failed to load local image blob:', e)
    return null
  }
}

/**
 * Sniff an image's MIME type from magic bytes, falling back to file extension.
 * Needed because blobs fetched from GitHub raw often arrive with an empty or
 * generic Content-Type, which makes blob: URLs render as raw bytes in the browser.
 */
export async function detectImageMime(blob: Blob, filename?: string): Promise<string> {
  if (blob.size > 0) {
    try {
      const buf = await blob.slice(0, 12).arrayBuffer()
      const b = new Uint8Array(buf)
      if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg'
      if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'image/png'
      if (b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46) return 'image/gif'
      if (b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46
        && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return 'image/webp'
    } catch { /* fall through to extension guess */ }
  }
  const ext = (filename || '').toLowerCase().match(/\.(\w+)$/)?.[1]
  const extMap: Record<string, string> = {
    jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
    gif: 'image/gif', webp: 'image/webp', bmp: 'image/bmp',
    svg: 'image/svg+xml', ico: 'image/x-icon',
  }
  return (ext && extMap[ext]) || 'image/jpeg'
}

/**
 * Return a Blob whose .type is a real image MIME type.
 * If the blob already has a usable type it is returned unchanged; otherwise a
 * new Blob is created with the detected type. Fixes blob: URLs that would
 * otherwise display as garbled bytes when opened directly in the browser.
 */
export async function fixBlobMime(blob: Blob, filename?: string): Promise<Blob> {
  if (blob.type && blob.type !== 'application/octet-stream') return blob
  const mime = await detectImageMime(blob, filename)
  return new Blob([await blob.arrayBuffer()], { type: mime })
}

/**
 * One-time migration: rewrite every image Blob whose .type is empty/generic so
 * that blob: URLs display correctly when opened directly (not just in <img>).
 * Guarded by a system_config flag so it only runs once per database.
 */
export async function migrateImageMimes(): Promise<void> {
  if (import.meta.env.VITE_STORAGE_MODE !== 'local') return
  try {
    const { getDb } = await import('@/api/local/database')
    const db = await getDb()
    if ((await db.get('system_config', 'images_mime_fixed'))?.value) return
    const all = await db.getAll('images')
    const updates: any[] = []
    for (const img of all) {
      if (img.blob && (!img.blob.type || img.blob.type === 'application/octet-stream')) {
        const fixedBlob = await fixBlobMime(img.blob, img.path || undefined)
        updates.push({ ...img, blob: fixedBlob, mime_type: fixedBlob.type })
      }
    }
    if (updates.length > 0) {
      const tx = db.transaction('images', 'readwrite')
      for (const u of updates) await tx.store.put(u)
      await tx.done
      console.log(`[mime-migration] fixed ${updates.length} images`)
    }
    await db.put('system_config', { key: 'images_mime_fixed', value: true })
  } catch (e) {
    console.error('[mime-migration] failed:', e)
  }
}
