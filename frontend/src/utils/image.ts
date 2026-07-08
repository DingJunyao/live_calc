/**
 * 菜谱/原料图片路径解析（统一入口）。
 *
 * 路径有三种形态，按优先级解析：
 * 1. http(s) 绝对 URL —— 原样返回
 * 2. /static/images/... 本地静态路径 —— 补 API 前缀，走后端 /api/v1/static
 * 3. 其它（仓库相对路径，如 images/xxx.jpg）—— 拼到数据仓库图片基址（兜底）
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
  if (path.startsWith('/static/images/')) {
    const base = import.meta.env.VITE_API_URL || '/api/v1'
    return `${base}${path}`
  }
  const repoBase = import.meta.env.VITE_DATA_REPO_IMAGE_BASE || DEFAULT_REPO_BASE
  return `${repoBase}/${path}`
}
