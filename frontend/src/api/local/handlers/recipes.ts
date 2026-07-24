// Recipes handler — CRUD, cost calculation, nutrition aggregation, trends, merchant costs.

import { getAll, getById, addOne, putOne, deleteOne, getByIndex, paginate } from '../database'
import { calculateCost, type CostInput, type CostCalcIngredient, type CostCalcProduct, type CostCalcPriceRecord, type CostCalcUnit, type CostCalcHierarchy } from '../business/costCalculator'
import { aggregateIngredients, type AggregationInput, type AggregationInputMulti } from '../business/nutritionAggregator'
import { convert, type UnitInfo, type EntityOverride, type DensityInfo } from '../business/unitConverter'

// ============================================================
// 辅助函数
// ============================================================

const GRAM_UNIT_ID = 3 // 标准克单位 ID

/** 将食材名解析为 ingredient_id。按名称精确匹配，再按别名匹配。 */
async function resolveIngredientId(name: string): Promise<number | null> {
  const all = await getAll('ingredients')
  const lower = name.toLowerCase()
  const match = all.find((i: any) =>
    i.is_active !== false &&
    (i.name?.toLowerCase() === lower ||
      (Array.isArray(i.aliases) && i.aliases.some((a: string) => a.toLowerCase() === lower))),
  )
  return match ? match.id : null
}

/** 获取菜谱的原料列表，附带食材名。 */
async function getRecipeIngredients(recipeId: number): Promise<any[]> {
  const ingredients = await getByIndex('recipe_ingredients', 'by_recipe_id', recipeId)
  // 附加食材名
  for (const ri of ingredients) {
    const ing = await getById('ingredients', ri.ingredient_id)
    ri.ingredient_name = ing?.name || `#${ri.ingredient_id}`
    ri.ingredient = ing || null
  }
  return ingredients.sort((a: any, b: any) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
}

// ============================================================
// Recipe CRUD
// ============================================================

export async function listRecipes(_params: Record<string, string>, query?: any): Promise<any> {
  const search = query?.search || query?.name
  const lower = search?.toLowerCase()
  const category = query?.category || query?.categories
  const difficulty = query?.difficulty || query?.difficulties

  return paginate('recipes', { page: query?.page, page_size: query?.page_size || query?.limit || 20 }, (r: any) => {
    if (r.is_active === false) return false
    if (lower && !r.name?.toLowerCase().includes(lower)) return false
    if (category && r.category !== category) return false
    if (difficulty && r.difficulty !== difficulty) return false
    return true
  })
}

export async function createRecipe(_params: Record<string, string>, data?: any): Promise<any> {
  const { ingredients, ...recipeData } = data || {}

  // 创建菜谱
  const recipeId = await addOne('recipes', {
    ...recipeData,
    is_active: true,
    is_public: false,
    tags: recipeData.tags || [],
    cooking_steps: recipeData.cooking_steps || [],
    images: recipeData.images || [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })

  // 创建菜谱原料
  if (Array.isArray(ingredients)) {
    for (let i = 0; i < ingredients.length; i++) {
      const ing = ingredients[i]
      const ingredientId = ing.ingredient_id || (await resolveIngredientId(ing.ingredient_name))
      if (!ingredientId) continue

      await addOne('recipe_ingredients', {
        recipe_id: recipeId,
        ingredient_id: ingredientId,
        quantity: ing.quantity ?? null,
        quantity_range: ing.quantity_range ?? null,
        unit_id: ing.unit_id,
        is_optional: ing.is_optional ?? false,
        note: ing.note ?? null,
        original_quantity: ing.original_quantity ?? null,
        sort_order: i,
        created_at: new Date().toISOString(),
      })
    }
  }

  return await getRecipe({ id: String(recipeId) } as any)
}

export async function getRecipe(params: Record<string, string>, _query?: any): Promise<any> {
  const id = parseInt(params.id)
  const recipe = await getById('recipes', id)
  if (!recipe || recipe.is_active === false) {
    throw { status: 404, message: `菜谱 ${id} 未找到` }
  }

  const ingredients = await getRecipeIngredients(id)
  return { ...recipe, ingredients }
}

export async function updateRecipe(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('recipes', id)
  if (!existing) throw { status: 404, message: `菜谱 ${id} 未找到` }

  const { ingredients, ...recipeData } = data || {}

  // 更新菜谱基本信息
  await putOne('recipes', {
    ...existing,
    ...recipeData,
    id,
    tags: recipeData.tags ?? existing.tags ?? [],
    cooking_steps: recipeData.cooking_steps ?? existing.cooking_steps ?? [],
    images: recipeData.images ?? existing.images ?? [],
    updated_at: new Date().toISOString(),
  })

  // 更新原料列表（若传了 ingredients）
  if (Array.isArray(ingredients)) {
    // 删除旧原料
    const oldIngredients = await getByIndex('recipe_ingredients', 'by_recipe_id', id)
    for (const old of oldIngredients) {
      await deleteOne('recipe_ingredients', old.id)
    }

    // 插入新原料
    for (let i = 0; i < ingredients.length; i++) {
      const ing = ingredients[i]
      const ingredientId = ing.ingredient_id || (await resolveIngredientId(ing.ingredient_name))
      if (!ingredientId) continue

      await addOne('recipe_ingredients', {
        recipe_id: id,
        ingredient_id: ingredientId,
        quantity: ing.quantity ?? null,
        quantity_range: ing.quantity_range ?? null,
        unit_id: ing.unit_id,
        is_optional: ing.is_optional ?? false,
        note: ing.note ?? null,
        original_quantity: ing.original_quantity ?? null,
        sort_order: i,
        created_at: new Date().toISOString(),
      })
    }
  }

  return await getRecipe({ id: String(id) } as any)
}

export async function deleteRecipe(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('recipes', id)
  if (!existing) throw { status: 404, message: `菜谱 ${id} 未找到` }
  await putOne('recipes', { ...existing, id, is_active: false, updated_at: new Date().toISOString() })
  return { ok: true }
}

// ============================================================
// Cost Calculation
// ============================================================

export async function getRecipeCost(params: Record<string, string>, _query?: any): Promise<any> {
  const id = parseInt(params.id)
  const recipe = await getById('recipes', id)
  if (!recipe) throw { status: 404, message: `菜谱 ${id} 未找到` }

  const input = await buildCostInput(id, recipe)
  const result = calculateCost(input)

  return {
    total_cost: result.total_cost,
    currency: result.currency,
    cost_per_serving: result.cost_per_serving,
    cost_breakdown: result.per_ingredient.map(pi => ({
      ingredient_id: pi.ingredient_id,
      ingredient_name: pi.ingredient_name,
      quantity: pi.quantity,
      unit_price: pi.unit_price,
      cost: pi.cost,
      cost_source: pi.source,
      fallback_chain: pi.source_ingredient_id ? [{ source_ingredient_id: pi.source_ingredient_id, relation: 'fallback' }] : null,
    })),
  }
}

export async function batchCost(_params: Record<string, string>, data?: any): Promise<any> {
  const recipeIds: number[] = data?.recipe_ids || data?.recipeIds || []
  if (recipeIds.length === 0) throw { status: 400, message: 'recipe_ids 不能为空' }

  // 预加载所有相关数据
  const allRecipes = await getAll('recipes')
  const allIngredients = await getAll('ingredients')
  const allRecipeIngredients = await getAll('recipe_ingredients')
  const allProducts = await getAll('products')
  const allRecords = await getAll('product_records')
  const allUnits = await getAll('units')
  const allOverrides = await getAll('entity_unit_overrides')
  const allDensities = await getAll('entity_densities')
  const allHierarchies = await getAll('ingredient_hierarchy')

  const results: any[] = []
  for (const rid of recipeIds) {
    const recipe = allRecipes.find((r: any) => r.id === rid)
    if (!recipe || recipe.is_active === false) continue

    const recipeIngredients = allRecipeIngredients.filter((ri: any) => ri.recipe_id === rid)
    const ries = recipeIngredients.map((ri: any) => ({
      recipe_ingredient_id: ri.id,
      ingredient_id: ri.ingredient_id,
      ingredient_name: '',
      quantity: ri.quantity,
      quantity_range: ri.quantity_range,
      unit_id: ri.unit_id,
      is_optional: ri.is_optional,
    }))

    // 填充食材名
    for (const ri of ries) {
      const ing = allIngredients.find((i: any) => i.id === ri.ingredient_id) || await getById('ingredients', ri.ingredient_id)
      ri.ingredient_name = ing?.name || `#${ri.ingredient_id}`
    }

    const ingredientIds = [...new Set(ries.map((ri: any) => ri.ingredient_id))]
    const products = allProducts.filter((p: any) => p.is_active !== false && ingredientIds.includes(p.ingredient_id))
    const productIds = products.map((p: any) => p.id)
    const records = allRecords.filter((r: any) => productIds.includes(r.product_id))

    const input: CostInput = {
      recipe_id: rid,
      servings: recipe.servings || 1,
      ingredients: ries.map((ri: any) => ({
        recipe_ingredient_id: ri.recipe_ingredient_id,
        ingredient_id: ri.ingredient_id,
        ingredient_name: ri.ingredient_name,
        quantity: ri.quantity,
        quantity_range: ri.quantity_range,
        unit_id: ri.unit_id,
        is_optional: ri.is_optional,
      })),
      products: products.map((p: any) => ({
        id: p.id,
        ingredient_id: p.ingredient_id,
        name: p.name,
        price_weight: p.price_weight ?? 50,
      })),
      price_records: records.map((r: any) => ({
        product_id: r.product_id,
        price: r.price,
        quantity: r.quantity,
        unit_id: r.unit_id,
        standard_quantity: r.standard_quantity,
        standard_unit_id: r.standard_unit_id,
        recorded_at: r.recorded_at,
      })),
      units: allUnits,
      overrides: allOverrides,
      densities: allDensities,
      hierarchies: allHierarchies,
    }

    const result = calculateCost(input)
    results.push({
      recipe_id: rid,
      total_cost: result.total_cost,
      cost_per_serving: result.cost_per_serving,
      currency: result.currency,
    })
  }

  return { items: results, total: results.length }
}

// ============================================================
// Nutrition
// ============================================================

export async function getRecipeNutrition(params: Record<string, string>, _query?: any): Promise<any> {
  const id = parseInt(params.id)
  const recipe = await getById('recipes', id)
  if (!recipe) throw { status: 404, message: `菜谱 ${id} 未找到` }

  const recipeIngredients = await getByIndex('recipe_ingredients', 'by_recipe_id', id)
  const aggregationInputs: AggregationInput[] = []

  for (const ri of recipeIngredients) {
    if (ri.is_optional) continue

    // 获取食材的营养数据
    const nutritionData = await getByIndex('nutrition_data', 'by_ingredient_id', ri.ingredient_id)
    if (!nutritionData || nutritionData.length === 0) continue

    // 将食材用量转换为克
    const quantityG = await convertToGrams(ri.quantity, ri.unit_id, ri.ingredient_id)
    if (quantityG == null || quantityG <= 0) continue

    aggregationInputs.push({
      ingredient_id: ri.ingredient_id,
      quantity_g: quantityG,
      nutrition_data: nutritionData.map((n: any) => ({
        ingredient_id: n.ingredient_id,
        nutrient_name: n.nutrient_name || n.name || '',
        amount_per_100g: n.value_per_100g ?? n.amount_per_100g ?? n.value ?? 0,
        unit: n.unit || 'g',
      })),
    })
  }

  const items = aggregateIngredients({ items: aggregationInputs })

  // 按营养素分类：核心营养素 vs 全部
  const coreNames = ['能量', '蛋白质', '脂肪', '碳水化合物', '膳食纤维', '钠', '钙', '铁', '钾', '维生素A', '维生素C', '维生素B1', '维生素B2', '维生素B12', '维生素D', '维生素E', '维生素K']
  const coreNutrients = items.filter(item => coreNames.includes(item.nutrient_name))
  const allNutrients = items

  return {
    items,
    core_nutrients: coreNutrients,
    all_nutrients: allNutrients,
  }
}

/** 将食材用量转换为克。使用共享单位转换模块。 */
async function convertToGrams(quantity: number | null, unitId: number | null, ingredientId: number): Promise<number | null> {
  if (quantity == null || quantity <= 0 || unitId == null) return null
  if (unitId === GRAM_UNIT_ID) return quantity

  try {
    const units = await getAll('units') as UnitInfo[]
    const overrides = await getAll('entity_unit_overrides') as EntityOverride[]
    const densities = await getAll('entity_densities') as DensityInfo[]

    const result = convert({
      value: quantity,
      from_unit_id: unitId,
      to_unit_id: GRAM_UNIT_ID,
      entity_type: 'ingredient',
      entity_id: ingredientId,
      units,
      overrides,
      densities,
    })
    return result.value
  } catch {
    return null
  }
}

// ============================================================
// Cost History
// ============================================================

export async function getCostHistory(params: Record<string, string>, query?: any): Promise<any> {
  const id = parseInt(params.id)
  const recipe = await getById('recipes', id)
  if (!recipe) throw { status: 404, message: `菜谱 ${id} 未找到` }

  const days = parseInt(query?.days) || 90
  const input = await buildCostInput(id, recipe)
  if (!input) return { items: [] }

  // 获取所有价格记录中最早的日期
  const allDates = input.price_records
    .map(r => r.recorded_at?.split('T')[0])
    .filter(Boolean)
    .sort()

  if (allDates.length === 0) return { items: [] }

  const earliestDate = new Date(allDates[0])
  const endDate = new Date()
  const startDate = new Date(Math.max(earliestDate.getTime(), endDate.getTime() - days * 86400000))

  // 生成日期列表（从 start 到 end，每天一条）
  const dateList: Date[] = []
  const current = new Date(startDate)
  while (current <= endDate) {
    dateList.push(new Date(current))
    current.setDate(current.getDate() + 1)
  }

  // 预排序价格记录按 product_id 分组 + 按日期排序
  const recordsByProduct: Record<number, CostCalcPriceRecord[]> = {}
  for (const rec of input.price_records) {
    if (!recordsByProduct[rec.product_id]) recordsByProduct[rec.product_id] = []
    recordsByProduct[rec.product_id].push(rec)
  }
  for (const pid of Object.keys(recordsByProduct)) {
    recordsByProduct[Number(pid)].sort((a, b) => (a.recorded_at || '').localeCompare(b.recorded_at || ''))
  }

  const items: any[] = []
  for (const date of dateList) {
    const dateStr = date.toISOString().split('T')[0]
    const asOfEnd = new Date(date)
    asOfEnd.setHours(23, 59, 59, 999)
    const cutoff = asOfEnd.toISOString()

    // 用截至该日的最新记录构建 input
    const recordsUpToDate = input.price_records.filter(r => (r.recorded_at || '') <= cutoff)

    if (recordsUpToDate.length === 0) continue

    const dayInput: CostInput = {
      ...input,
      price_records: recordsUpToDate,
    }

    const result = calculateCost(dayInput)
    const recordedAt = Math.floor(date.getTime() / 1000)

    items.push({
      date: dateStr,
      recorded_at: recordedAt,
      total_cost: Math.round(result.total_cost * 100),
      avg_cost: result.total_cost,
    })
  }

  return { items }
}

export async function getCostHistoryRange(params: Record<string, string>, query?: any): Promise<any> {
  const id = parseInt(params.id)
  const recipe = await getById('recipes', id)
  if (!recipe) throw { status: 404, message: `菜谱 ${id} 未找到` }

  const days = parseInt(query?.days) || 90
  const offsetDays = parseInt(query?.offset_days) || 0

  const input = await buildCostInput(id, recipe)
  if (!input) return { items: [] }

  const allDates = input.price_records
    .map(r => r.recorded_at?.split('T')[0])
    .filter(Boolean)
    .sort()

  if (allDates.length === 0) return { items: [] }

  const earliestDate = new Date(allDates[0])
  const endDate = new Date()
  endDate.setDate(endDate.getDate() - offsetDays)
  const startDate = new Date(Math.max(earliestDate.getTime(), endDate.getTime() - days * 86400000))

  const dateList: Date[] = []
  const current = new Date(startDate)
  while (current <= endDate) {
    dateList.push(new Date(current))
    current.setDate(current.getDate() + 1)
  }

  // 预排序价格记录
  const recordsByProduct: Record<number, CostCalcPriceRecord[]> = {}
  for (const rec of input.price_records) {
    if (!recordsByProduct[rec.product_id]) recordsByProduct[rec.product_id] = []
    recordsByProduct[rec.product_id].push(rec)
  }
  for (const pid of Object.keys(recordsByProduct)) {
    recordsByProduct[Number(pid)].sort((a, b) => (a.recorded_at || '').localeCompare(b.recorded_at || ''))
  }

  // 收集所有商品的每日有效记录来计算 min/max
  const items: any[] = []
  for (const date of dateList) {
    const dateStr = date.toISOString().split('T')[0]
    const asOfEnd = new Date(date)
    asOfEnd.setHours(23, 59, 59, 999)
    const cutoff = asOfEnd.toISOString()

    // 该日期有效的记录
    const dayRecords = input.price_records.filter(r => (r.recorded_at || '') <= cutoff)
    if (dayRecords.length === 0) continue

    // 计算在同一日期可用的所有价格组合
    // 对每个食材，找出所有商品在该日期的单价范围
    let totalMin = 0
    let totalMax = 0
    let totalAvg = 0
    let validCount = 0

    for (const ing of input.ingredients) {
      if (ing.is_optional || (ing.quantity == null && ing.quantity_range == null)) continue
      const effQty = ing.quantity ?? (ing.quantity_range ? (ing.quantity_range[0] + ing.quantity_range[1]) / 2 : 0)
      if (effQty <= 0) continue

      const ingProducts = input.products.filter(p => p.ingredient_id === ing.ingredient_id)
      if (ingProducts.length === 0) continue

      // 每个商品的最新单价
      const prices: number[] = []
      for (const prod of ingProducts) {
        const recs = dayRecords.filter(r => r.product_id === prod.id)
        if (recs.length === 0) continue
        // 取最新记录
        recs.sort((a, b) => (b.recorded_at || '').localeCompare(a.recorded_at || ''))
        const latest = recs[0]
        const qty = latest.standard_quantity ?? latest.quantity
        if (qty && qty > 0) {
          prices.push(latest.price / qty)
        }
      }

      if (prices.length > 0) {
        totalMin += Math.min(...prices) * effQty
        totalMax += Math.max(...prices) * effQty
        totalAvg += (prices.reduce((s, p) => s + p, 0) / prices.length) * effQty
        validCount++
      }
    }

    if (validCount === 0) continue

    const recordedAt = Math.floor(date.getTime() / 1000)
    items.push({
      date: dateStr,
      recorded_at: recordedAt,
      min_cost: Math.round(totalMin * 100) / 100,
      max_cost: Math.round(totalMax * 100) / 100,
      avg_cost: Math.round(totalAvg * 100) / 100,
    })
  }

  return { items }
}

// ============================================================
// Merchant Costs
// ============================================================

export async function getMerchantCosts(params: Record<string, string>, _query?: any): Promise<any> {
  const id = parseInt(params.id)
  const recipe = await getById('recipes', id)
  if (!recipe) throw { status: 404, message: `菜谱 ${id} 未找到` }

  const recipeIngredients = await getByIndex('recipe_ingredients', 'by_recipe_id', id)
  const units = await getAll('units')
  const allProducts = await getAll('products')
  const allRecords = await getAll('product_records')
  const allMerchants = await getAll('merchants')

  // merchant_id → { merchant_id, merchant_name, items, total_cost }
  const merchantMap: Record<number, any> = {}
  const noMerchantItems: any[] = []

  for (const ri of recipeIngredients) {
    if (ri.is_optional) continue
    const effQty = ri.quantity ?? (ri.quantity_range ? (ri.quantity_range[0] + ri.quantity_range[1]) / 2 : 0)
    if (!effQty || effQty <= 0) continue

    const ingProducts = allProducts.filter((p: any) => p.is_active !== false && p.ingredient_id === ri.ingredient_id)
    if (ingProducts.length === 0) continue

    // 对每个商品，按商家分组取最新价格
    interface MerchantPrice {
      merchantId: number
      merchantName: string
      pricePerUnit: number
      unitId: number
      productId: number
      productName: string
    }
    const prices: MerchantPrice[] = []

    for (const prod of ingProducts) {
      const productRecords = allRecords
        .filter((r: any) => r.product_id === prod.id && r.merchant_id != null)
        .sort((a: any, b: any) => (b.recorded_at || '').localeCompare(a.recorded_at || ''))

      if (productRecords.length === 0) continue

      // 按商家取最新记录
      const merchantLatest: Record<number, any> = {}
      for (const rec of productRecords) {
        if (!merchantLatest[rec.merchant_id]) {
          merchantLatest[rec.merchant_id] = rec
        }
      }

      for (const [mid, rec] of Object.entries(merchantLatest)) {
        const merchantId = Number(mid)
        const merchant = allMerchants.find((m: any) => m.id === merchantId)
        const qty = (rec as any).standard_quantity ?? (rec as any).quantity
        const pricePerUnit = qty && qty > 0 ? (rec as any).price / qty : (rec as any).price
        prices.push({
          merchantId,
          merchantName: merchant?.name || `商家${merchantId}`,
          pricePerUnit,
          unitId: (rec as any).standard_unit_id ?? (rec as any).unit_id,
          productId: prod.id,
          productName: prod.name || '',
        })
      }
    }

    // 将价格分配到各商家
    const ingredientName = (await getById('ingredients', ri.ingredient_id))?.name || `#${ri.ingredient_id}`

    if (prices.length === 0) {
      noMerchantItems.push({
        ingredient_id: ri.ingredient_id,
        ingredient_name: ingredientName,
        cost: 0,
      })
      continue
    }

    // 按商家分组：取该食材在每家商家的最低价
    const byMerchant: Record<number, { pricePerUnit: number; productId: number }> = {}
    for (const p of prices) {
      if (!byMerchant[p.merchantId] || p.pricePerUnit < byMerchant[p.merchantId].pricePerUnit) {
        byMerchant[p.merchantId] = { pricePerUnit: p.pricePerUnit, productId: p.productId }
      }
    }

    for (const [mid, mp] of Object.entries(byMerchant)) {
      const merchantId = Number(mid)
      if (!merchantMap[merchantId]) {
        const merchant = allMerchants.find((m: any) => m.id === merchantId)
        merchantMap[merchantId] = {
          merchant_id: merchantId,
          merchant_name: merchant?.name || `商家${merchantId}`,
          items: [],
          total_cost: 0,
        }
      }

      // 单位转换
      let convertedQty = effQty
      const recipeUnit = units.find((u: any) => u.id === ri.unit_id)
      const priceUnit = units.find((u: any) => u.id === mp.pricePerUnit)
      // simplified: if same type use si_factor
      if (recipeUnit && priceUnit && recipeUnit.unit_type === priceUnit.unit_type && recipeUnit.si_factor && priceUnit.si_factor) {
        convertedQty = effQty * (recipeUnit.si_factor / priceUnit.si_factor)
      }

      const cost = Math.round(convertedQty * mp.pricePerUnit * 100) / 100
      merchantMap[merchantId].items.push({
        ingredient_id: ri.ingredient_id,
        ingredient_name: ingredientName,
        quantity: String(convertedQty),
        unit_price: mp.pricePerUnit,
        cost,
        product_id: mp.productId,
      })
      merchantMap[merchantId].total_cost += cost
    }
  }

  const merchants = Object.values(merchantMap).sort((a: any, b: any) => b.total_cost - a.total_cost)

  return {
    merchants,
    no_merchant_items: noMerchantItems,
  }
}

// ============================================================
// Publish (no-op in single-user local mode)
// ============================================================

export async function publishRecipe(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('recipes', id)
  if (!existing) throw { status: 404, message: `菜谱 ${id} 未找到` }
  // 本地模式：直接标记为已发布
  await putOne('recipes', { ...existing, id, is_public: true, updated_at: new Date().toISOString() })
  return { ok: true, message: '菜谱已发布' }
}

// ============================================================
// Image Upload/Delete (Mock)
// ============================================================

export async function uploadImage(params: Record<string, string>, _data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('recipes', id)
  if (!existing) throw { status: 404, message: `菜谱 ${id} 未找到` }
  // 本地模式：仅返回 mock 图片 URL
  const mockUrl = `/static/images/recipes/${id}_${Date.now()}.jpg`
  return { url: mockUrl, filename: `${id}_${Date.now()}.jpg` }
}

export async function deleteImage(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const filename = params.filename
  const existing = await getById('recipes', id)
  if (!existing) throw { status: 404, message: `菜谱 ${id} 未找到` }
  // 本地模式：仅从 images 数组中去掉该文件名
  const images = (existing.images || []).filter((img: string) => !img.includes(filename))
  await putOne('recipes', { ...existing, id, images, updated_at: new Date().toISOString() })
  return { ok: true }
}

// ============================================================
// 内部辅助：构建 CostInput
// ============================================================

async function buildCostInput(recipeId: number, recipe: any): Promise<CostInput> {
  const recipeIngredients = await getByIndex('recipe_ingredients', 'by_recipe_id', recipeId)
  if (!recipeIngredients || recipeIngredients.length === 0) {
    return {
      recipe_id: recipeId,
      servings: recipe.servings || 1,
      ingredients: [],
      products: [],
      price_records: [],
      units: [],
      overrides: [],
      densities: [],
      hierarchies: [],
    }
  }

  const allUnits = await getAll('units')
  const allOverrides = await getAll('entity_unit_overrides')
  const allDensities = await getAll('entity_densities')
  const allHierarchies = await getAll('ingredient_hierarchy')

  // 收集食材 ID
  const ingredientIds = [...new Set(recipeIngredients.map((ri: any) => ri.ingredient_id))]

  // 加载食材名
  const ingredientNames: Record<number, string> = {}
  for (const iid of ingredientIds) {
    const ing = await getById('ingredients', iid)
    ingredientNames[iid] = ing?.name || `#${iid}`
  }

  // 加载商品
  const allProducts = await getAll('products')
  const products = allProducts.filter((p: any) => p.is_active !== false && ingredientIds.includes(p.ingredient_id))

  // 加载价格记录
  const productIds = products.map((p: any) => p.id)
  const allRecords = await getAll('product_records')
  const records = allRecords.filter((r: any) => productIds.includes(r.product_id))

  // 构建 ingredients 数组
  const ingredients: CostCalcIngredient[] = recipeIngredients.map((ri: any) => ({
    recipe_ingredient_id: ri.id,
    ingredient_id: ri.ingredient_id,
    ingredient_name: ingredientNames[ri.ingredient_id] || '',
    quantity: ri.quantity,
    quantity_range: ri.quantity_range,
    unit_id: ri.unit_id,
    is_optional: ri.is_optional,
  }))

  return {
    recipe_id: recipeId,
    servings: recipe.servings || 1,
    ingredients,
    products: products.map((p: any) => ({
      id: p.id,
      ingredient_id: p.ingredient_id,
      name: p.name,
      price_weight: p.price_weight ?? 50,
    })),
    price_records: records.map((r: any) => ({
      product_id: r.product_id,
      price: r.price ?? r.unit_price ?? 0,
      quantity: r.quantity ?? 1,
      unit_id: r.unit_id,
      standard_quantity: r.standard_quantity,
      standard_unit_id: r.standard_unit_id,
      recorded_at: r.recorded_at,
    })),
    units: allUnits,
    overrides: allOverrides,
    densities: allDensities,
    hierarchies: allHierarchies,
  }
}
