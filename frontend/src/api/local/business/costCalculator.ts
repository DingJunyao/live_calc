// 菜谱成本计算模块 — 纯函数，不依赖 IndexedDB。
// 基于原料用量、商品加权价格、单位换算和层级回退计算菜谱总成本。

export interface CostCalcIngredient {
  recipe_ingredient_id?: number
  ingredient_id: number
  ingredient_name?: string
  quantity: number | null
  quantity_range: [number, number] | null  // [min, max]
  unit_id: number
  is_optional: boolean
}

export interface CostCalcProduct {
  id: number
  ingredient_id: number
  name?: string
  price_weight: number
}

export interface CostCalcPriceRecord {
  id?: number
  product_id: number
  price: number
  quantity: number
  unit_id?: number
  standard_quantity?: number | null
  standard_unit_id?: number | null
  recorded_at: string
  merchant_id?: number
}

export interface CostCalcUnit {
  id: number
  unit_type: string
  si_factor: number | null
  abbreviation?: string
}

export interface CostCalcHierarchy {
  parent_id: number
  child_id: number
  relation_type: string  // 'FALLBACK' | 'SUBSTITUTABLE' | 'CONTAINS'
  strength: number       // 0-100
}

export interface CostInput {
  recipe_id?: number
  servings?: number
  ingredients: CostCalcIngredient[]
  products: CostCalcProduct[]
  price_records: CostCalcPriceRecord[]
  units: CostCalcUnit[]
  overrides: any[]
  densities: any[]
  hierarchies: CostCalcHierarchy[]
  weight_overrides?: Array<{ product_id: number; weight: number }>
}

export interface CostPerIngredient {
  ingredient_id: number
  ingredient_name?: string
  cost: number
  quantity: string
  unit_price: number
  source: 'direct' | 'fallback' | 'substitute' | 'contains' | 'zero'
  source_ingredient_id?: number
  product_id?: number
}

export interface CostResult {
  total_cost: number
  cost_per_serving: number
  per_ingredient: CostPerIngredient[]
  currency: string
}

/**
 * 计算菜谱总成本。
 *
 * 对每个食材：
 * 1. 查找属于该食材的商品
 * 2. 对每个商品，按 recorded_at 降序查找最新价格记录
 * 3. 按 price_weight 加权平均
 * 4. 将食材用量单位转换为价格单位
 * 5. 若未找到直连价格，沿层级关系回退
 * 6. 处理 quantity_range（用平均值）
 * 7. 可选食材成本为零
 */
export function calculateCost(input: CostInput): CostResult {
  const perIngredient: CostPerIngredient[] = []
  let totalCost = 0

  for (const ing of input.ingredients) {
    if (ing.is_optional) {
      perIngredient.push({
        ingredient_id: ing.ingredient_id,
        ingredient_name: ing.ingredient_name,
        cost: 0,
        quantity: '0',
        unit_price: 0,
        source: 'zero',
      })
      continue
    }

    // 获取有效用量（quantity_range 取平均值）
    const effectiveQty = ing.quantity ?? (
      ing.quantity_range ? (ing.quantity_range[0] + ing.quantity_range[1]) / 2 : 0
    )

    if (effectiveQty <= 0) {
      perIngredient.push({
        ingredient_id: ing.ingredient_id,
        ingredient_name: ing.ingredient_name,
        cost: 0,
        quantity: '0',
        unit_price: 0,
        source: 'zero',
      })
      continue
    }

    // 查找该食材的商品
    const ingredientProducts = input.products.filter(p => p.ingredient_id === ing.ingredient_id)

    if (ingredientProducts.length > 0) {
      // 加权平均价格
      const weightedPrice = calculateWeightedPrice(ingredientProducts, input.price_records, input.weight_overrides)

      if (weightedPrice != null) {
        // 单位转换：将食材用量从 ing.unit_id 转换为 weightedPrice.unit_id
        let convertedQty = effectiveQty
        const recipeUnit = input.units.find(u => u.id === ing.unit_id)
        const priceUnit = input.units.find(u => u.id === weightedPrice.unit_id)

        if (recipeUnit && priceUnit && ing.unit_id !== weightedPrice.unit_id) {
          if (recipeUnit.unit_type === priceUnit.unit_type && recipeUnit.si_factor != null && priceUnit.si_factor != null) {
            // 同类型：si_factor 比值
            convertedQty = effectiveQty * (recipeUnit.si_factor / priceUnit.si_factor)
          } else {
            // 跨类型：查密度
            const density = findCostDensity(ing.ingredient_id, ing.unit_id, weightedPrice.unit_id, input)
            if (density != null) {
              if (isCostMass(recipeUnit.unit_type) && isCostVolume(priceUnit.unit_type)) {
                // mass→volume: mass / density
                const kg = effectiveQty * (recipeUnit.si_factor ?? 1)
                const liters = kg / density
                convertedQty = liters / (priceUnit.si_factor ?? 1)
              } else if (isCostVolume(recipeUnit.unit_type) && isCostMass(priceUnit.unit_type)) {
                // volume→mass: volume * density
                const liters = effectiveQty * (recipeUnit.si_factor ?? 1)
                const kg = liters * density
                convertedQty = kg / (priceUnit.si_factor ?? 1)
              }
            }
          }
        }

        const ingredientCost = convertedQty * weightedPrice.pricePerUnit
        perIngredient.push({
          ingredient_id: ing.ingredient_id,
          ingredient_name: ing.ingredient_name,
          cost: ingredientCost,
          quantity: String(convertedQty),
          unit_price: weightedPrice.pricePerUnit,
          source: 'direct',
          product_id: weightedPrice.product_id,
        })
        totalCost += ingredientCost
        continue
      }
    }

    // 无直接商品价格，尝试层级回退
    const fallback = findFallbackPrice(ing.ingredient_id, input)
    if (fallback != null) {
      // 单位转换：将食材用量从 ing.unit_id 转换为回退价格的单位
      let convertedQty = effectiveQty
      const recipeUnit = input.units.find(u => u.id === ing.unit_id)
      const priceUnit = input.units.find(u => u.id === fallback.unit_id)

      if (recipeUnit && priceUnit && ing.unit_id !== fallback.unit_id) {
        if (recipeUnit.unit_type === priceUnit.unit_type && recipeUnit.si_factor != null && priceUnit.si_factor != null) {
          // 同类型：si_factor 比值
          convertedQty = effectiveQty * (recipeUnit.si_factor / priceUnit.si_factor)
        } else {
          // 跨类型：查密度
          const density = findCostDensity(ing.ingredient_id, ing.unit_id, fallback.unit_id, input)
          if (density != null) {
            if (isCostMass(recipeUnit.unit_type) && isCostVolume(priceUnit.unit_type)) {
              const kg = effectiveQty * (recipeUnit.si_factor ?? 1)
              const liters = kg / density
              convertedQty = liters / (priceUnit.si_factor ?? 1)
            } else if (isCostVolume(recipeUnit.unit_type) && isCostMass(priceUnit.unit_type)) {
              const liters = effectiveQty * (recipeUnit.si_factor ?? 1)
              const kg = liters * density
              convertedQty = kg / (priceUnit.si_factor ?? 1)
            }
          }
        }
      }

      const fallbackCost = convertedQty * fallback.pricePerUnit
      perIngredient.push({
        ingredient_id: ing.ingredient_id,
        ingredient_name: ing.ingredient_name,
        cost: fallbackCost,
        quantity: String(convertedQty),
        unit_price: fallback.pricePerUnit,
        source: 'fallback',
        source_ingredient_id: fallback.sourceIngredientId,
        product_id: fallback.productId,
      })
      totalCost += fallbackCost
      continue
    }

    // 所有途径均失败，记零
    perIngredient.push({
      ingredient_id: ing.ingredient_id,
      ingredient_name: ing.ingredient_name,
      cost: 0,
      quantity: String(effectiveQty),
      unit_price: 0,
      source: 'zero',
    })
  }

  const servings = input.servings || 1
  return {
    total_cost: Math.round(totalCost * 100) / 100,
    cost_per_serving: Math.round((totalCost / servings) * 100) / 100,
    per_ingredient: perIngredient,
    currency: 'CNY',
  }
}

/**
 * 计算加权平均价格。
 * 对每个商品，取最新价格记录，按 price_weight（或用户覆盖）加权平均。
 */
function calculateWeightedPrice(
  products: CostCalcProduct[],
  records: CostCalcPriceRecord[],
  weightOverrides?: Array<{ product_id: number; weight: number }>,
): { pricePerUnit: number; unit_id: number; product_id: number } | null {
  const productPrices = products.map(p => {
    const productRecords = records
      .filter(r => r.product_id === p.id)
      .sort((a, b) => (b.recorded_at || '').localeCompare(a.recorded_at || ''))

    if (productRecords.length === 0) return null

    const latest = productRecords[0]
    // 计算单价：price / standard_quantity（或 quantity）
    const qty = latest.standard_quantity ?? latest.quantity
    const pricePerUnit = qty && qty > 0 ? latest.price / qty : latest.price
    const weight = weightOverrides?.find(w => w.product_id === p.id)?.weight ?? p.price_weight ?? 50

    return {
      product_id: p.id,
      pricePerUnit,
      unit_id: latest.standard_unit_id ?? latest.unit_id ?? 0,
      weight,
    }
  }).filter((p): p is NonNullable<typeof p> => p !== null)

  if (productPrices.length === 0) return null

  // 加权平均
  const totalWeight = productPrices.reduce((s, p) => s + p.weight, 0)
  if (totalWeight <= 0) return null

  const weightedSum = productPrices.reduce((s, p) => s + p.pricePerUnit * p.weight, 0)

  return {
    pricePerUnit: weightedSum / totalWeight,
    unit_id: productPrices[0].unit_id,
    product_id: productPrices[0].product_id,
  }
}

/**
 * 沿层级关系查找回退价格。
 * 优先级：FALLBACK → SUBSTITUTABLE → CONTAINS，按 strength 降序。
 */
function findFallbackPrice(
  ingredientId: number,
  input: CostInput,
): { pricePerUnit: number; unit_id: number; sourceIngredientId: number; productId?: number } | null {
  // 按优先级排序：FALLBACK(0) < SUBSTITUTABLE(1) < CONTAINS(2)
  const order: Record<string, number> = { FALLBACK: 0, SUBSTITUTABLE: 1, CONTAINS: 2 }
  const hierarchies = input.hierarchies
    .filter(h => h.child_id === ingredientId)
    .sort((a, b) => {
      const oa = order[a.relation_type] ?? 99
      const ob = order[b.relation_type] ?? 99
      if (oa !== ob) return oa - ob
      return (b.strength ?? 0) - (a.strength ?? 0)
    })

  for (const h of hierarchies) {
    const parentProducts = input.products.filter(p => p.ingredient_id === h.parent_id)
    if (parentProducts.length > 0) {
      const price = calculateWeightedPrice(parentProducts, input.price_records, input.weight_overrides)
      if (price != null) {
        return {
          pricePerUnit: price.pricePerUnit,
          unit_id: price.unit_id,
          sourceIngredientId: h.parent_id,
          productId: price.product_id,
        }
      }
    }
  }

  return null
}

function isCostMass(type: string): boolean {
  return type === 'mass'
}

function isCostVolume(type: string): boolean {
  return type === 'volume'
}

function findCostDensity(
  ingredientId: number,
  fromUnitId: number,
  toUnitId: number,
  input: CostInput,
): number | null {
  const { overrides, densities } = input

  // 查 entity_densities
  const d = densities?.find((d: any) => d.entity_type === 'ingredient' && d.entity_id === ingredientId)
  if (d?.density && d.density > 0) {
    return d.density / 1000 // kg/m³ → kg/L
  }

  return null
}
