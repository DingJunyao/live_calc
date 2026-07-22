/**
 * 菜谱/原料图片路径解析（统一入口）。
 *
 * 路径有四种形态，按优先级解析：
 * 1. http(s) 绝对 URL（S3 等远端存储）—— 原样返回
 * 2. /static/images/... 旧格式路径 —— 提取 key 后走动态图片端点 /api/v1/images/
 * 3. recipes/xxx.jpg 等 storage key（新格式）—— 同样走动态图片端点
 * 4. 其它（仓库相对路径，如 images/xxx.jpg）—— 拼到数据仓库图片基址（兜底）
 *
 * 统一抽离自 RecipesView / RecipeDetail / ImageManager / RecipeEditDiff / MealCard
 * 各自重复的实现；同时补齐 MealCard 原本缺失的「仓库兜底」分支，
 * 让残缺路径（如 images/xxx.jpg）也能从远程仓库加载，行为与其余页面一致。
 */
const DEFAULT_REPO_BASE =
  'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out'

export function resolveImageUrl(path: string | null | undefined): string {
  if (!path) return ''
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
