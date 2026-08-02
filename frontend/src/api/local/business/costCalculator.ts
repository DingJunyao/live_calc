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
  original_quantity?: string | null
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
const GRAM_UNIT_ID = 2 // 克 unit ID in local DB

/** 模糊量关键词 → 默认克数映射（与云端 VAGUE_QUANTITY_GRAM_MAP 对齐） */
const VAGUE_QUANTITY_GRAM_MAP: Record<string, number> = {
  '适量': 100,
  '少许': 5,
}

/**
 * 解析 original_quantity 中的模糊量关键词。
 * @returns 克数 或 null（无匹配）
 */
function resolveVagueQuantity(original?: string | null): number | null {
  if (!original) return null
  const text = typeof original === 'string' ? original : String(original)
  for (const [keyword, grams] of Object.entries(VAGUE_QUANTITY_GRAM_MAP)) {
    if (text.includes(keyword)) return grams
  }
  return null
}
export function calculateCost(input: CostInput): CostResult {
  const perIngredient: CostPerIngredient[] = []
  let totalCost = 0

  for (const ing of input.ingredients) {
    if (ing.is_optional) {
      perIngredient.push({
        recipe_ingredient_id: ing.recipe_ingredient_id,
        ingredient_id: ing.ingredient_id,
        ingredient_name: ing.ingredient_name,
        cost: 0,
        quantity: '0',
        unit_price: 0,
        source: 'zero',
      })
      continue
    }

    // 获取有效用量：quantity → quantity_range 平均值 → original_quantity 模糊量回退
    let effectiveQty: number
    let effectiveUnitId = ing.unit_id

    const rawQty = ing.quantity
    if (rawQty != null && Number.isFinite(Number(rawQty)) && Number(rawQty) > 0) {
      effectiveQty = Number(rawQty)
    } else if (ing.quantity_range && ing.quantity_range[0] != null && ing.quantity_range[1] != null) {
      effectiveQty = (ing.quantity_range[0] + ing.quantity_range[1]) / 2
    } else {
      // 模糊量回退：检查 original_quantity 中的关键词（适量→100g, 少许→5g）
      const vague = resolveVagueQuantity(ing.original_quantity)
      if (vague != null) {
        effectiveQty = vague
        effectiveUnitId = GRAM_UNIT_ID
      } else {
        effectiveQty = 0
      }
    }

    if (!Number.isFinite(effectiveQty) || effectiveQty <= 0) {
      perIngredient.push({
        recipe_ingredient_id: ing.recipe_ingredient_id,
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
            const density = findCostDensity(ing.ingredient_id, effectiveUnitId, weightedPrice.unit_id, input)
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
        if (!Number.isFinite(ingredientCost)) continue
        perIngredient.push({
          recipe_ingredient_id: ing.recipe_ingredient_id,
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
      const recipeUnit = input.units.find(u => u.id === effectiveUnitId)
      const priceUnit = input.units.find(u => u.id === fallback.unit_id)

      if (recipeUnit && priceUnit && ing.unit_id !== fallback.unit_id) {
        if (recipeUnit.unit_type === priceUnit.unit_type && recipeUnit.si_factor != null && priceUnit.si_factor != null) {
          // 同类型：si_factor 比值
          convertedQty = effectiveQty * (recipeUnit.si_factor / priceUnit.si_factor)
        } else {
          // 跨类型：查密度
          const density = findCostDensity(ing.ingredient_id, effectiveUnitId, fallback.unit_id, input)
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
      if (!Number.isFinite(fallbackCost)) continue
      perIngredient.push({
        recipe_ingredient_id: ing.recipe_ingredient_id,
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

    // No direct/fallback price — try CONTAINS aggregation (weighted avg from child ingredient prices)
    const containsResult = findContainsPrice(ing.ingredient_id, input)
    if (containsResult != null) {
      // CONTAINS price is per-gram; convert recipe quantity to grams
      const gramUnit = input.units.find(u => u.name === '克')
      let convertedQty = effectiveQty
      const recipeUnit = input.units.find(u => u.id === effectiveUnitId)
      if (recipeUnit && gramUnit && effectiveUnitId !== gramUnit.id) {
        if (recipeUnit.unit_type === 'mass' && recipeUnit.si_factor != null && gramUnit.si_factor != null) {
          convertedQty = effectiveQty * (recipeUnit.si_factor / gramUnit.si_factor)
        }
        // count/volume types can't easily convert to grams without density/piece_weight
      }

      const containsCost = convertedQty * containsResult.pricePerGram
      if (!Number.isFinite(containsCost)) continue
      perIngredient.push({
        recipe_ingredient_id: ing.recipe_ingredient_id,
        ingredient_id: ing.ingredient_id,
        ingredient_name: ing.ingredient_name,
        cost: containsCost,
        quantity: String(convertedQty),
        unit_price: containsResult.pricePerGram,
        source: 'contains',
      })
      totalCost += containsCost
      continue
    }

    // 所有途径均失败，记零
    perIngredient.push({
      recipe_ingredient_id: ing.recipe_ingredient_id,
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
    total_cost: Number.isFinite(totalCost) ? Math.round(totalCost * 100) / 100 : 0,
    cost_per_serving: Number.isFinite(totalCost) ? Math.round((totalCost / servings) * 100) / 100 : 0,
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
  const order: Record<string, number> = { FALLBACK: 0, SUBSTITUTABLE: 1 }
  const hierarchies = input.hierarchies
    .filter(h => h.child_id === ingredientId)
    .sort((a, b) => {
      const oa = order[(a.relation_type || '').toUpperCase()] ?? 99
      const ob = order[(b.relation_type || '').toUpperCase()] ?? 99
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

/**
 * CONTAINS aggregation: compute a weighted-average price-per-gram from child
 * ingredient prices. Mirrors cloud _aggregate_child_prices().
 *
 * For each CONTAINS child, get its direct weighted price (no fallback chain),
 * convert to per-gram, then weight by hierarchy strength.
 */
function findContainsPrice(
  ingredientId: number,
  input: CostInput,
): { pricePerGram: number } | null {
  // Find all CONTAINS children of this ingredient, sorted by strength desc
  const hierarchies = input.hierarchies
    .filter(h => h.parent_id === ingredientId && (h.relation_type || '').toUpperCase() === 'CONTAINS')
    .sort((a, b) => (b.strength ?? 0) - (a.strength ?? 0))

  if (hierarchies.length === 0) return null

  const gramUnit = input.units.find(u => u.name === '\u514B')
  if (!gramUnit || gramUnit.si_factor == null) return null

  const childPrices: { pricePerGram: number; strength: number }[] = []
  let totalStrength = 0

  for (const h of hierarchies) {
    const childProducts = input.products.filter(p => p.ingredient_id === h.child_id)
    if (childProducts.length === 0) continue

    // Child's direct weighted price (no fallback chain — mirrors cloud _get_child_price_per_gram)
    const weighted = calculateWeightedPrice(childProducts, input.price_records, input.weight_overrides)
    if (weighted == null) continue

    // Convert per-unit price to per-gram
    const priceUnit = input.units.find(u => u.id === weighted.unit_id)
    let pricePerGram = weighted.pricePerUnit
    if (priceUnit && priceUnit.si_factor != null && priceUnit.unit_type === 'mass') {
      // gramPrice = pricePerUnit * gramSiFactor / priceSiFactor
      pricePerGram = weighted.pricePerUnit * gramUnit.si_factor / priceUnit.si_factor
    } else if (priceUnit && priceUnit.unit_type !== 'mass') {
      // Non-mass price unit (count/volume) — can't reliably convert to per-gram
      continue
    }

    if (!Number.isFinite(pricePerGram) || pricePerGram <= 0) continue

    const strength = h.strength ?? 50
    childPrices.push({ pricePerGram, strength })
    totalStrength += strength
  }

  if (childPrices.length === 0) return null

  // Weighted average
  let weightedAvg: number
  if (totalStrength > 0) {
    weightedAvg = childPrices.reduce((sum, p) => sum + p.pricePerGram * p.strength, 0) / totalStrength
  } else {
    weightedAvg = childPrices.reduce((sum, p) => sum + p.pricePerGram, 0) / childPrices.length
  }

  return { pricePerGram: weightedAvg }
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
