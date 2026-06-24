/**
 * 食材配色工具——同种食材在成本占比、成本趋势、营养溯源三张图表中使用相同颜色
 *
 * 通过 ingredient_id 的 hash 值从共享色板中取色。
 * 放到"其他"分类的食材不需要统一颜色，不在这个逻辑范围内。
 */

// 共享色板（16 色，覆盖常见食材数量）
export const INGREDIENT_COLOR_PALETTE: string[] = [
  '#ff9800', '#4caf50', '#2196f3', '#9c27b0',
  '#f44336', '#00bcd4', '#ff5722', '#607d8b',
  '#e91e63', '#3f51b5', '#009688', '#795548',
  '#cddc39', '#ffc107', '#03a9f4', '#8bc34a',
]

/**
 * 根据 ingredient_id 获取一致的颜色
 */
export function getIngredientColor(ingredientId: number | string | undefined | null): string {
  if (ingredientId == null) return '#e0e0e0'
  const id = typeof ingredientId === 'string' ? parseInt(ingredientId, 10) : ingredientId
  if (isNaN(id)) return '#e0e0e0'
  return INGREDIENT_COLOR_PALETTE[Math.abs(id) % INGREDIENT_COLOR_PALETTE.length]
}
