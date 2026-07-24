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

export function resolveImageUrl(path: string | null | undefined): string {
  if (!path) return ''

  // Local mode: images stored in IndexedDB blobs, return empty string.
  // Consumers should use loadLocalImageBlob() for async blob loading.
  if (import.meta.env.VITE_STORAGE_MODE === 'local') {
    return ''
  }

  if (path.startsWith('http')) return path
  const base = import.meta.env.VITE_API_URL || '/api/v1'

  // 旧格式 /static/images/recipes/xxx.jpg → 提取 key → 走动态图片端点
  // 无论本地还是 S3，统一由后端 /api/v1/images/ 按当前存储后端分流
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
    // Try exact key match first
    if (imageKey) {
      const all = await db.getAllFromIndex('images', 'by_entity', [entityType, entityId])
      const matched = all.find((img: any) => img.path === imageKey || img.key === imageKey)
      if (matched?.blob) {
        return URL.createObjectURL(matched.blob)
      }
    }
    // Fall back to the first image for this entity
    const images = await db.getAllFromIndex('images', 'by_entity', [entityType, entityId])
    if (images.length > 0 && images[0].blob) {
      return URL.createObjectURL(images[0].blob)
    }
    return null
  } catch (e) {
    console.error('Failed to load local image blob:', e)
    return null
  }
}
