// 加权价格计算模块 — 纯函数，不依赖 IndexedDB。
// 对多个商品的 price_weight 加权平均，支持用户级权重覆盖。

export interface WeightedPriceInput {
  products: Array<{ id: number; price_weight: number; ingredient_id: number }>
  price_records: Array<{ product_id: number; price: number; quantity: number; unit_id: number; recorded_at: string }>
  weight_overrides?: Array<{ product_id: number; weight: number }>
}

export interface WeightedPriceResult {
  weighted_avg: number
  unit_id: number
  participants: number
  source: 'override' | 'global'
}

/**
 * 计算多个商品的加权平均价格。
 *
 * 对每个商品：
 * 1. 按 recorded_at 降序取最新价格记录
 * 2. 计算单价（price / quantity）
 * 3. 取有效权重：用户覆盖 > product.price_weight > 默认 50
 * 4. 加权平均 = sum(单价 * 权重) / sum(权重)
 *
 * 权重为 0 的商品被排除（可用于"静音"某个商品）。
 * 无价格记录的商品被排除。
 */
export function calculateWeightedPrice(input: WeightedPriceInput): WeightedPriceResult | null {
  const { products, price_records, weight_overrides } = input

  const weighted: Array<{ pricePerUnit: number; weight: number; unitId: number }> = []

  for (const product of products) {
    const productRecords = price_records
      .filter(r => r.product_id === product.id)
      .sort((a, b) => (b.recorded_at || '').localeCompare(a.recorded_at || ''))

    if (productRecords.length === 0) continue

    const latest = productRecords[0]
    const pricePerUnit = latest.price / (latest.quantity || 1)

    const override = weight_overrides?.find(w => w.product_id === product.id)
    const weight = override?.weight ?? product.price_weight ?? 50

    if (weight <= 0) continue // weight 0 = exclude

    weighted.push({ pricePerUnit, weight, unitId: latest.unit_id })
  }

  if (weighted.length === 0) return null

  const totalWeight = weighted.reduce((s, w) => s + w.weight, 0)
  const weightedSum = weighted.reduce((s, w) => s + w.pricePerUnit * w.weight, 0)

  return {
    weighted_avg: weightedSum / totalWeight,
    unit_id: weighted[0].unitId,
    participants: weighted.length,
    source: weight_overrides?.some(w => products.some(p => p.id === w.product_id)) ? 'override' : 'global',
  }
}
