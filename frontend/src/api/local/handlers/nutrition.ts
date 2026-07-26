// Nutrition handler — ingredient/product nutrition data and weighted price lookups.

import { getAll, getById, putOne, getByIndex, getDb, paginate } from '../database'

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
  // 构建前端需要的 nutrition 格式：{ core_nutrients: { "能量": { value, unit }, ... }, all_nutrients: { "铁": { value, unit }, ... } }
  const coreNames = ['能量', '蛋白质', '脂肪', '碳水化合物', '钠']
  const allNutrients: Record<string, any> = {}
  const coreNutrients: Record<string, any> = {}
  for (const n of all) {
    const key = n.nutrient_name || ''
    const entry = { value: n.amount_per_100g ?? 0, unit: n.unit || 'g' }
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
  const nutrients = data?.nutrients || data

  // Use a single readwrite transaction for both delete and insert
  const db = await getDb()
  const tx = db.transaction('nutrition_data', 'readwrite')
  const store = tx.store

  // Delete existing records for this ingredient
  const index = store.index('by_ingredient_id')
  const existing = await index.getAll(ingredientId)
  for (const item of existing) {
    await store.delete(item.id)
  }

  // Insert new records
  for (const n of (Array.isArray(nutrients) ? nutrients : [nutrients])) {
    await store.add({
      ...n,
      ingredient_id: ingredientId,
      is_verified: true,
      source: 'custom',
      created_at: new Date().toISOString(),
    })
  }

  await tx.done

  // Read back the inserted data
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
  let total = 0
  let count = 0
  const productIds = products.map((p: any) => p.id)

  for (const pid of productIds) {
    const records = await getByIndex('product_records', 'by_product_id', pid)
    if (records.length === 0) continue
    const sorted = records.sort((a: any, b: any) => (b.recorded_at || '').localeCompare(a.recorded_at || ''))
    // Simple average
    for (const rec of records) {
      const price = rec.price || rec.unit_price || 0
      if (price > 0) {
        total += price
        count++
      }
    }
    if (!latestRec || (sorted[0]?.recorded_at || '') > (latestRec.recorded_at || '')) {
      latestRec = sorted[0]
    }
  }

  if (count === 0) return { price: null, unit: null, records: 0 }

  return {
    price: total / count,
    unit: latestRec?.unit_name || latestRec?.unit || '斤',
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
  const coreNames = ['能量', '蛋白质', '脂肪', '碳水化合物', '钠']
  const allNutrients: Record<string, any> = {}
  const coreNutrients: Record<string, any> = {}
  for (const n of baseNutrients) {
    const key = n.nutrient_name || ''
    const entry = { value: n.amount_per_100g ?? 0, unit: n.unit || 'g' }
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
      const entry = { value: n.amount_per_100g ?? n.value ?? 0, unit: n.unit || n.unit_name || 'g' }
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
      const entry = { value: n.amount_per_100g ?? n.value ?? 0, unit: n.unit || n.unit_name || 'g' }
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

  await putOne('products', {
    ...product,
    id,
    custom_nutrition_data: data?.nutrients || data,
    updated_at: new Date().toISOString(),
  })
  return data?.nutrients || data
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

export async function getIngredientRecipes(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  if (!Number.isFinite(id)) return []
  return getByIndex('recipe_ingredients', 'by_ingredient_id', id)
}
