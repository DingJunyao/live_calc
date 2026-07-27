// Nutrition handler — ingredient/product nutrition data and weighted price lookups.

import { getAll, getById, putOne, getByIndex, getDb, paginate } from '../database'
import { calcNRV } from '../business/nutritionAggregator'

export async function listNutritionIngredients(_params: Record<string, string>, query?: any): Promise<any> {
  const name = query?.name || query?.search
  const lower = name?.toLowerCase()
  return paginate('ingredients', { page: query?.page, page_size: query?.page_size }, (i: any) => {
    if (i.is_active === false) return false
    if (lower && !i.name?.toLowerCase().includes(lower)) return false
    return true
  })
}

export async function getNutritionIngredient(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  if (!Number.isFinite(id)) return { nutrition_data: [], calories: 0 }
  const ingredient = await getById('ingredients', id)
  if (!ingredient) return { nutrition_data: [], calories: 0 }
  const nutrition = await getByIndex('nutrition_data', 'by_ingredient_id', id)
  return { ...ingredient, nutrition_data: nutrition || [] }
}

export async function getIngredientNutrition(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  if (!Number.isFinite(id)) return { items: [], total: 0, nutrition: { core_nutrients: {}, all_nutrients: {} } }
  const all = await getByIndex('nutrition_data', 'by_ingredient_id', id)
  // 构建前端需要的 nutrition 格式
  const coreNames = ['能量', '热量', '蛋白质', '脂肪', '碳水化合物', '钠']
  const allNutrients: Record<string, any> = {}
  const coreNutrients: Record<string, any> = {}
  for (const n of all) {
    let key = n.nutrient_name || ''
    // 统一能量键名：USDA → 能量，HowToCook → 热量
    if (key.includes('热量') || key.includes('能量') || key.includes('calorie') || key.includes('energy')) {
      key = '能量'
    }
    const nrpPct = calcNRV(n.nutrient_name || '', n.amount_per_100g ?? 0)
    const entry = { value: n.amount_per_100g ?? 0, unit: n.unit || 'g', nrp_pct: nrpPct }
    // 只保留第一个匹配的能量值（避免多个热量字段重复）
    if (key === '能量' && allNutrients[key]) continue
    allNutrients[key] = entry
    if (coreNames.includes(key)) coreNutrients[key] = entry
  }
  return {
    items: all,
    total: all.length,
    nutrition: {
      core_nutrients: coreNutrients,
      all_nutrients: allNutrients,
    },
  }
}

export async function getIngredientNutritionBase(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const all = await getByIndex('nutrition_data', 'by_ingredient_id', id)
  // Return per-100g base nutrition
  const result: Record<string, any> = {}
  for (const n of all) {
    result[n.nutrient_name || n.nutrient_id] = {
      value: n.amount_per_100g ?? n.value ?? 0,
      unit: n.unit,
    }
  }
  return result
}

export async function updateIngredientNutrition(params: Record<string, string>, data?: any): Promise<any> {
  const ingredientId = parseInt(params.id)
  const nutrients: any[] = Array.isArray(data?.nutrients) ? data.nutrients : (Array.isArray(data) ? data : [])

  const db = await getDb()

  // 先将前端字段名映射为数据库字段
  const mapped = nutrients.map(n => ({
    nutrient_name: n.nutrient_name || n.name || '',
    amount_per_100g: n.amount_per_100g ?? n.value ?? 0,
    unit: n.unit || 'g',
    source: n.source || 'custom',
    is_verified: true,
    ingredient_id: ingredientId,
  })).filter(n => n.nutrient_name)

  if (mapped.length === 0) return { items: [], message: 'no nutrients' }

  // Delete-all-then-insert：编辑表单加载了全部营养素，发回的是完整列表
  const tx = db.transaction('nutrition_data', 'readwrite')
  const store = tx.store
  const existing = await store.index('by_ingredient_id').getAll(ingredientId)
  for (const item of existing) await store.delete(item.id)
  for (const n of mapped) await store.add({ ...n, created_at: new Date().toISOString() })
  await tx.done

  const created = await getByIndex('nutrition_data', 'by_ingredient_id', ingredientId)
  return { items: created }
}

export async function getLatestPrice(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  // Find all products for this ingredient
  const products = await getByIndex('products', 'by_ingredient_id', id)
  if (products.length === 0) {
    return { price: null, unit: null, records: 0 }
  }

  // Find latest price record across all products
  let latestRec: any = null
  let totalUnitPrice = 0
  let count = 0
  const productIds = products.map((p: any) => p.id)

  for (const pid of productIds) {
    const records = await getByIndex('product_records', 'by_product_id', pid)
    if (records.length === 0) continue
    const sorted = records.sort((a: any, b: any) => (b.recorded_at || '').localeCompare(a.recorded_at || ''))
    // 按标准量计算单价：price / standard_quantity，结果以 standard_unit 为基准
    for (const rec of records) {
      const price = rec.price ?? rec.unit_price ?? 0
      if (price <= 0) continue
      const qty = rec.standard_quantity ?? rec.quantity ?? 1
      if (qty <= 0) continue
      totalUnitPrice += price / qty
      count++
    }
    if (!latestRec || (sorted[0]?.recorded_at || '') > (latestRec.recorded_at || '')) {
      latestRec = sorted[0]
    }
  }

  if (count === 0) return { average_price: null, unit: null, records: 0 }

  // 默认以「斤」显示：若单价单位是「克」，×500 转成元/斤
  let displayUnit = latestRec?.unit_name || '斤'
  let displayPrice = totalUnitPrice / count
  if (displayUnit === '克') {
    displayPrice *= 500
    displayUnit = '斤'
  }

  return {
    average_price: Math.round(displayPrice * 10000) / 10000,
    unit: displayUnit,
    records: count,
    latest_record: latestRec || null,
  }
}

export async function getLatestPriceByMerchant(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const products = await getByIndex('products', 'by_ingredient_id', id)
  const productIds = products.map((p: any) => p.id)

  // Group records by merchant
  const byMerchant: Record<number, any> = {}
  for (const pid of productIds) {
    const records = await getByIndex('product_records', 'by_product_id', pid)
    for (const rec of records) {
      const mid = rec.merchant_id
      if (!mid) continue
      if (!byMerchant[mid]) {
        byMerchant[mid] = { merchant_id: mid, total: 0, count: 0, latest: null }
      }
      byMerchant[mid].total += rec.price || rec.unit_price || 0
      byMerchant[mid].count++
      if (!byMerchant[mid].latest || (rec.recorded_at || '') > (byMerchant[mid].latest.recorded_at || '')) {
        byMerchant[mid].latest = rec
      }
    }
  }

  const result = Object.entries(byMerchant).map(([mid, data]: [string, any]) => ({
    merchant_id: parseInt(mid),
    price: data.total / data.count,
    records: data.count,
    latest_record: data.latest,
  }))

  return { items: result, total: result.length }
}

export async function getProductWeights(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const products = await getByIndex('products', 'by_ingredient_id', id)
  const productIds = products.map((p: any) => p.id)

  const result: any[] = []
  for (const pid of productIds) {
    const overrides = await getByIndex('product_weight_overrides', 'by_product_id', pid)
    const product = products.find((p: any) => p.id === pid)
    result.push({
      product_id: pid,
      product_name: product?.name || '',
      weight: product?.price_weight ?? 50,
      my_weight: overrides.length > 0 ? overrides[0].weight : null,
    })
  }
  return { items: result, total: result.length }
}

export async function getProductNutrition(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const product = await getById('products', id)
  if (!product) throw { status: 404, message: `Product ${id} not found` }

  // Mixin 机制：从原料营养数据为基础，用 custom_nutrition_data 覆盖
  let baseNutrients: any[] = []
  if (product.ingredient_id) {
    baseNutrients = await getByIndex('nutrition_data', 'by_ingredient_id', product.ingredient_id)
  }

  // 构建基础营养映射
  const coreNames = ['能量', '热量', '蛋白质', '脂肪', '碳水化合物', '钠']
  const allNutrients: Record<string, any> = {}
  const coreNutrients: Record<string, any> = {}
  for (const n of baseNutrients) {
    let key = n.nutrient_name || ''
    // 统一能量键名
    if (key.includes('热量') || key.includes('能量') || key.includes('calorie') || key.includes('energy')) {
      key = '能量'
    }
    if (key === '能量' && allNutrients[key]) continue
    const nrpPct = calcNRV(n.nutrient_name || '', n.amount_per_100g ?? 0)
    const entry = { value: n.amount_per_100g ?? 0, unit: n.unit || 'g', nrp_pct: nrpPct }
    allNutrients[key] = entry
    if (coreNames.includes(key)) coreNutrients[key] = entry
  }

  // 用 custom_nutrition_data 覆盖（mixin）
  let source = 'ingredient'
  if (product.custom_nutrition_data) {
    source = 'custom'
    const cnd = product.custom_nutrition_data
    let customItems: any[] = []
    if (Array.isArray(cnd)) customItems = cnd
    else if (cnd?.items) customItems = cnd.items
    else if (cnd?.nutrients) customItems = cnd.nutrients

    for (const n of customItems) {
      const key = n.nutrient_name || n.name || ''
      if (!key) continue
      const val = n.amount_per_100g ?? n.value ?? 0
      const nrpPct = calcNRV(key, val)
      const entry = { value: val, unit: n.unit || n.unit_name || 'g', nrp_pct: nrpPct }
      allNutrients[key] = entry
      if (coreNames.includes(key)) coreNutrients[key] = entry
    }
  }

  // 构建 custom_nutrition_data（前端编辑表单需要区分哪些是用户自定义的）
  const customAll: Record<string, any> = {}
  const customCore: Record<string, any> = {}
  if (product.custom_nutrition_data) {
    const cnd = product.custom_nutrition_data
    let customItems: any[] = []
    if (Array.isArray(cnd)) customItems = cnd
    else if (cnd?.items) customItems = cnd.items
    else if (cnd?.nutrients) customItems = cnd.nutrients
    for (const n of customItems) {
      const key = n.nutrient_name || n.name || ''
      if (!key) continue
      const val = n.amount_per_100g ?? n.value ?? 0
      const entry = { value: val, unit: n.unit || n.unit_name || 'g' }
      customAll[key] = entry
      if (coreNames.includes(key)) customCore[key] = entry
    }
  }

  return {
    items: Object.entries(allNutrients).map(([k, v]) => ({ nutrient_name: k, ...v })),
    total: Object.keys(allNutrients).length,
    source,
    nutrition: { core_nutrients: coreNutrients, all_nutrients: allNutrients },
    custom_nutrition_data: { core_nutrients: customCore, all_nutrients: customAll },
  }
}

export async function updateProductNutrition(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const product = await getById('products', id)
  if (!product) throw { status: 404, message: `Product ${id} not found` }

  // 提取自定义营养素数据
  let customData: any = null
  if (data === null || data === undefined) {
    // 显式 null = 清除自定义覆盖，完全回退到原料营养
    customData = null
  } else {
    const nutrients = data?.nutrients || data
    if (Array.isArray(nutrients) && nutrients.length > 0) {
      customData = nutrients
    }
    // 空数组 = 清除覆盖，回退到原料
  }

  await putOne('products', {
    ...product,
    id,
    custom_nutrition_data: customData,
    updated_at: new Date().toISOString(),
  })
  return { ok: true }
}

export async function searchNutrition(_params: Record<string, string>, query?: any): Promise<any> {
  const q = query?.q || query?.name || ''
  if (!q) return { items: [], total: 0 }

  const lower = q.toLowerCase()
  const ingredients = await getAll('ingredients')
  const matched = ingredients.filter(
    (i: any) =>
      i.is_active !== false &&
      (i.name?.toLowerCase().includes(lower) ||
        (Array.isArray(i.aliases) && i.aliases.some((a: string) => a.toLowerCase().includes(lower)))),
  )
  return { items: matched, total: matched.length }
}

export async function getIngredientRecipes(params: Record<string, string>, query?: any): Promise<any> {
  const id = parseInt(params.id)
  if (!Number.isFinite(id)) return { items: [], total: 0 }

  const skip = parseInt(query?.skip) || 0
  const limit = parseInt(query?.limit) || 50

  // 查含该原料的菜谱关联，按 recipe_id 去重后取菜谱详情
  const ris = await getByIndex('recipe_ingredients', 'by_ingredient_id', id)
  const recipeIds = [...new Set(ris.map((r: any) => r.recipe_id))]

  const items: any[] = []
  for (const rid of recipeIds) {
    const rec = await getById('recipes', rid)
    if (!rec || rec.is_active === false) continue
    items.push({
      id: rec.id,
      name: rec.name,
      images: rec.images || [],
      category: rec.category,
      difficulty: rec.difficulty,
      servings: rec.servings,
      // local 模式单用户，菜谱可见性与发布无关；缺字段时按公开处理，避免误标「未发布」
      is_public: rec.is_public ?? true,
    })
  }
  return { items: items.slice(skip, skip + limit), total: items.length }
}
