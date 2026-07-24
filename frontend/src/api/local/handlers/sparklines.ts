// Sparklines handler — 价格趋势迷你图数据聚合。
// 为商品/食材提供近期的价格记录，以日期-价格对形式返回。

import { getAll, getByIndex } from '../database'

/** 获取单个商品的最新 N 条价格记录。 */
async function getProductSparklineData(productId: number, limit: number = 30): Promise<Array<{ date: string; price: number }>> {
  const records = await getByIndex('product_records', 'by_product_id', productId)
  if (records.length === 0) return []

  // 按 recorded_at 降序排序
  records.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  return records.slice(0, limit).map((r: any) => ({
    date: (r.recorded_at || '').split('T')[0],
    price: r.price ?? r.unit_price ?? 0,
  }))
}

/**
 * GET /sparklines/products?ids=1,2,3
 * 为指定的商品 ID 列表返回热门价格数据。
 * 返回: { [product_id]: [{ date, price }] }
 */
export async function getProductSparklines(_params: Record<string, string>, query?: any): Promise<any> {
  const idsStr: string = query?.ids || query?.product_ids || ''
  if (!idsStr) return {}

  const ids = idsStr.split(',').map((s: string) => parseInt(s.trim())).filter(n => !isNaN(n))
  if (ids.length === 0) return {}

  const result: Record<number, Array<{ date: string; price: number }>> = {}

  await Promise.all(ids.map(async (pid) => {
    result[pid] = await getProductSparklineData(pid, 30)
  }))

  return result
}

/**
 * GET /sparklines/ingredients?ids=1,2,3
 * 为指定的食材 ID 列表返回按食材聚合的价格数据。
 * 对每个食材，取其所有商品的最新价格记录汇总。
 * 返回: { [ingredient_id]: [{ date, price }] }
 */
export async function getIngredientSparklines(_params: Record<string, string>, query?: any): Promise<any> {
  const idsStr: string = query?.ids || query?.ingredient_ids || ''
  if (!idsStr) return {}

  const ids = idsStr.split(',').map((s: string) => parseInt(s.trim())).filter(n => !isNaN(n))
  if (ids.length === 0) return {}

  const allProducts = await getAll('products')
  const allRecords = await getAll('product_records')

  // 按 recorded_at 降序排序
  allRecords.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  const result: Record<number, Array<{ date: string; price: number }>> = {}

  for (const ingredientId of ids) {
    // 找出该食材的所有商品
    const ingredientProducts = allProducts.filter(
      (p: any) => p.is_active !== false && p.ingredient_id === ingredientId,
    )
    const productIds = ingredientProducts.map((p: any) => p.id)

    // 找出这些商品的价格记录
    const records = allRecords
      .filter((r: any) => productIds.includes(r.product_id))
      .slice(0, 30)
      .map((r: any) => ({
        date: (r.recorded_at || '').split('T')[0],
        price: r.price ?? r.unit_price ?? 0,
      }))

    result[ingredientId] = records
  }

  return result
}
