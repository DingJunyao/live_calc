// 营养数据聚合模块 — 纯函数，不依赖 IndexedDB。
// 按每 100g 基准缩放营养成分，计算 NRV%，支持 kcal/kJ 转换。

export interface NutritionRecord {
  id?: number
  ingredient_id: number
  nutrient_name: string
  amount_per_100g: number
  unit: string
  source?: string
  is_verified?: boolean
}

export interface NutritionItem {
  nutrient_name: string
  amount: number          // 对于给定用量的实际量
  amount_per_100g: number
  unit: string
  nrv_pct?: number        // 中国 NRV%
}

export interface AggregationInput {
  ingredient_id: number
  quantity_g: number       // 实际用量（克）
  nutrition_data: NutritionRecord[]
}

export interface AggregationInputMulti {
  items: AggregationInput[]
}

/**
 * 聚合单个食材的营养数据。
 * 将每 100g 基准值缩放到实际用量。
 */
export function aggregateIngredient(input: AggregationInput): NutritionItem[] {
  const { quantity_g, nutrition_data } = input
  const factor = quantity_g / 100

  return nutrition_data.map(n => ({
    nutrient_name: n.nutrient_name,
    amount: n.amount_per_100g * factor,
    amount_per_100g: n.amount_per_100g,
    unit: n.unit,
    nrv_pct: calcNRV(n.nutrient_name, n.amount_per_100g),
  }))
}

/**
 * 聚合多个食材的营养数据，合并同名营养素。
 */
export function aggregateIngredients(input: AggregationInputMulti): NutritionItem[] {
  const merged = new Map<string, { amount: number; unit: string }>()

  for (const item of input.items) {
    const factor = item.quantity_g / 100
    for (const n of item.nutrition_data) {
      const existing = merged.get(n.nutrient_name)
      if (existing) {
        existing.amount += n.amount_per_100g * factor
      } else {
        merged.set(n.nutrient_name, {
          amount: n.amount_per_100g * factor,
          unit: n.unit,
        })
      }
    }
  }

  const totalQuantityG = input.items.reduce((s, i) => s + i.quantity_g, 0)

  return Array.from(merged.entries()).map(([name, data]) => ({
    nutrient_name: name,
    amount: Math.round(data.amount * 100) / 100,
    amount_per_100g: totalQuantityG > 0 ? Math.round((data.amount / totalQuantityG) * 100 * 100) / 100 : 0,
    unit: data.unit,
    nrv_pct: totalQuantityG > 0 ? calcNRV(name, (data.amount / totalQuantityG) * 100) : undefined,
  }))
}

/**
 * 中国 NRV% 参考值表（GB 28050-2011）。
 * 键为营养素名的规范化键（小写 + 下划线），值为每日参考摄入量。
 */
const NRV_TABLE: Record<string, number> = {
  energy: 8400,          // kJ（注意不是 kcal）
  protein: 60,           // g
  fat: 60,               // g
  carbohydrate: 300,     // g
  dietary_fiber: 25,     // g
  sodium: 2000,          // mg
  vitamin_a: 800,        // µg RE
  vitamin_d: 5,          // µg
  vitamin_e: 14,         // mg α-TE
  vitamin_k: 80,         // µg
  vitamin_c: 100,        // mg
  thiamin: 1.4,          // mg (B1)
  riboflavin: 1.4,       // mg (B2)
  niacin: 14,            // mg (B3)
  vitamin_b6: 1.4,       // mg
  vitamin_b12: 2.4,      // µg
  folate: 400,           // µg DFE
  pantothenic_acid: 5,   // mg (B5)
  biotin: 30,            // µg (B7)
  calcium: 800,          // mg
  phosphorus: 700,       // mg
  potassium: 2000,       // mg
  magnesium: 300,        // mg
  iron: 12,              // mg
  zinc: 12,              // mg
  iodine: 150,           // µg
  selenium: 60,          // µg
  copper: 1.5,           // mg
  fluoride: 1,           // mg
  manganese: 4.5,        // mg
  chromium: 50,          // µg
  molybdenum: 60,        // µg
  cholesterol: 300,      // mg
}

/**
 * 计算中国 NRV%（营养素参考值百分比）。
 * 基于 GB 28050-2011 标准。
 */
export function calcNRV(nutrientName: string, amountPer100g: number): number | undefined {
  if (amountPer100g == null || amountPer100g === 0) return undefined

  // 对营养素名做规范化匹配
  const key = nutrientName
    .toLowerCase()
    .replace(/[^a-z一-鿿]/g, '_')
    .replace(/_{2,}/g, '_')
    .replace(/^_|_$/g, '')

  const nrv = NRV_TABLE[key]
  if (nrv == null || nrv === 0) return undefined

  return Math.round((amountPer100g / nrv) * 100 * 10) / 10
}

/** kcal 转 kJ */
export function kcalToKj(kcal: number): number {
  return kcal * 4.184
}

/** kJ 转 kcal */
export function kjToKcal(kj: number): number {
  return kj / 4.184
}
