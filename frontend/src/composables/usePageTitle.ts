// composables/usePageTitle.ts
// 统一管理页面标题（document.title）

const SITE_NAME = '生计 - 生活成本计算器'

/**
 * 页面标题管理 composable
 *
 * 用法：
 * - 列表页/静态页：由路由 meta.title 自动设置
 * - 详情页：const { setDetailTitle } = usePageTitle()
 *           watch(entity, () => setDetailTitle(entity.value?.name, '菜谱'))
 */
export function usePageTitle() {
  /**
   * 设置静态页面标题：`{title} - 生计 - 生活成本计算器`
   */
  const setTitle = (title: string) => {
    document.title = `${title} - ${SITE_NAME}`
  }

  /**
   * 设置详情页标题：`{name}（{type}） - 生计 - 生活成本计算器`
   * @param name 实体名称，为空时使用 fallback
   * @param type 实体类型标签（菜谱/商品/原料/商家）
   * @param fallback name 为空时的默认值
   */
  const setDetailTitle = (name: string | undefined | null, type: string, fallback = '详情') => {
    const displayName = name || fallback
    document.title = `${displayName}（${type}） - ${SITE_NAME}`
  }

  return { setTitle, setDetailTitle }
}
