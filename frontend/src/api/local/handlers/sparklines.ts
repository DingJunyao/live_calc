// Sparklines handler — 价格趋势迷你图数据聚合。
// 为商品/食材提供近期的价格记录，以日期-价格对形式返回。

import { getAll, getByIndex } from '../database'
import { normalizeRecordToJin } from '../business/priceNormalize'
import type { UnitInfo, EntityOverride, DensityInfo } from '../business/unitConverter'

/** getById 的安全包装（sparklines 模块未导入 getById，这里局部复用 getAll 查找）。 */
async function getByIdSafe(store: string, id: number): Promise<any> {
  const all = await getAll(store)
  return all.find((x: any) => x.id === id)
}

/** 获取单个商品的最新 N 条价格记录。 */
async function getProductSparklineData(productId: number, limit: number = 30): Promise<number[]> {
  const records = await getByIndex('product_records', 'by_product_id', productId)
  if (records.length === 0) return []

  // 按 recorded_at 降序排序
  records.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  // 预加载归一化所需的辅助表
  const product = await getByIdSafe('products', productId)
  const [units, overrides, densities] = await Promise.all([
    getAll('units') as Promise<UnitInfo[]>,
    getAll('entity_unit_overrides') as Promise<EntityOverride[]>,
    getAll('entity_densities') as Promise<DensityInfo[]>,
  ])
  const entId = product?.ingredient_id ?? productId
  // 每条记录折算到 ¥/斤；无法归一化（纯计数且无覆盖）的记录过滤掉
  return records.slice(0, limit)
    .map((r: any) => {
      const np = normalizeRecordToJin(r, units, overrides, densities, 'ingredient', entId)
      return np.pricePerJin
    })
    .filter((v: number | null): v is number => v != null)
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

  const result: Record<number, number[]> = {}

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
  const [units, overrides, densities] = await Promise.all([
    getAll('units') as Promise<UnitInfo[]>,
    getAll('entity_unit_overrides') as Promise<EntityOverride[]>,
    getAll('entity_densities') as Promise<DensityInfo[]>,
  ])

  // 按 recorded_at 降序排序
  allRecords.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  const result: Record<number, number[]> = {}

  for (const ingredientId of ids) {
    // 找出该食材的所有商品
    const ingredientProducts = allProducts.filter(
      (p: any) => p.is_active !== false && p.ingredient_id === ingredientId,
    )
    const productIds = ingredientProducts.map((p: any) => p.id)

    // 折算到 ¥/斤，避免按个计价的记录拉爆趋势（鸡蛋问题）
    const records = allRecords
      .filter((r: any) => productIds.includes(r.product_id))
      .slice(0, 30)
      .map((r: any) => {
        const np = normalizeRecordToJin(r, units, overrides, densities, 'ingredient', ingredientId)
        return np.pricePerJin
      })
      .filter((v: number | null): v is number => v != null)

    result[ingredientId] = records
  }

  return result
}
