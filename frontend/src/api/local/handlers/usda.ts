// USDA handler — search, detail, match ingredient/product, admin download.
// Data sourced from IndexedDB stores (usda_foods, usda_food_nutrients).

import { getAll, getById, getByIndex, putOne, getDb } from '../database'

export async function searchUsda(_params: Record<string, string>, query?: any): Promise<any> {
  const q = query?.q || ''
  const limit = parseInt(query?.limit) || 50

  if (!q.trim()) return []

  const lower = q.toLowerCase()
  const all = await getAll('usda_foods')
  const matched = all.filter((f: any) => {
    const desc = (f.description || '').toLowerCase()
    const descZh = (f.description_zh || '').toLowerCase()
    return desc.includes(lower) || descZh.includes(lower)
  })

  // Sort by relevance — exact prefix match first
  matched.sort((a: any, b: any) => {
    const aDesc = (a.description || '').toLowerCase()
    const bDesc = (b.description || '').toLowerCase()
    const aPrefix = aDesc.startsWith(lower) ? 1 : 0
    const bPrefix = bDesc.startsWith(lower) ? 1 : 0
    if (aPrefix !== bPrefix) return bPrefix - aPrefix
    return (a.description || '').localeCompare(b.description || '')
  })

  const items = matched.slice(0, limit)

  // Attach nutrient counts
  const result: any[] = []
  for (const food of items) {
    const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', food.fdc_id)
    result.push({
      fdc_id: food.fdc_id,
      description: food.description,
      description_zh: food.description_zh || null,
      data_type: food.data_type || 'Foundation',
      nutrient_count: nutrients.length,
      score: food.description?.toLowerCase() === lower ? 100 : Math.round((lower.length / Math.max(food.description?.length || 1, 1)) * 100),
    })
  }

  return result
}

export async function getUsdaFood(params: Record<string, string>): Promise<any> {
  const fdcId = parseInt(params.fdcId)
  const food = await getById('usda_foods', fdcId)
  if (!food) throw { status: 404, message: `USDA food ${fdcId} not found` }

  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)

  return {
    fdc_id: food.fdc_id,
    description: food.description,
    description_zh: food.description_zh || null,
    data_type: food.data_type || 'Foundation',
    nutrients: nutrients.map((n: any) => ({
      name: n.name,
      name_zh: n.name_zh || null,
      amount: n.amount,
      unit_name: n.unit_name,
    })),
  }
}

export async function previewNutrition(_params: Record<string, string>, query?: any): Promise<any> {
  const fdcId = parseInt(query?.fdc_id)
  if (!fdcId) throw { status: 400, message: 'fdc_id is required' }

  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)

  // Build structured nutrition data matching backend matcher output
  const coreNutrients: Record<string, any> = {}
  const allNutrients: any[] = []
  const nutrientDetails: any[] = []

  for (const n of nutrients) {
    const item = {
      name: n.name,
      name_zh: n.name_zh || n.name,
      amount: n.amount,
      unit: n.unit_name,
    }
    allNutrients.push(item)
    nutrientDetails.push(item)

    const key = (n.name_zh || n.name).toLowerCase()
    if (!coreNutrients[key]) {
      coreNutrients[key] = { value: n.amount, unit: n.unit_name }
    }
  }

  return {
    core_nutrients: coreNutrients,
    all_nutrients: allNutrients,
    nutrient_details: nutrientDetails,
  }
}

export async function matchIngredient(params: Record<string, string>, data?: any): Promise<any> {
  const ingredientId = parseInt(params.ingredientId)
  const fdcId = data?.fdc_id
  if (!fdcId) throw { status: 400, message: 'fdc_id is required' }

  const db = await getDb()
  const tx = db.transaction('nutrition_data', 'readwrite')
  const store = tx.store

  // Delete existing nutrition data for this ingredient
  const index = store.index('by_ingredient_id')
  const existing = await index.getAll(ingredientId)
  for (const item of existing) {
    await store.delete(item.id)
  }

  // Load USDA nutrients and create nutrition_data entries
  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)
  for (const n of nutrients) {
    await store.add({
      ingredient_id: ingredientId,
      nutrient_name: n.name_zh || n.name,
      nutrient_id: n.nutrient_id || null,
      value_per_100g: n.amount,
      value: n.amount,
      unit: n.unit_name,
      source: 'usda_manual_match',
      is_verified: true,
      created_at: new Date().toISOString(),
    })
  }
  await tx.done

  return { ingredient_id: ingredientId, fdc_id: fdcId, message: 'USDA 匹配成功（本地模式）' }
}

export async function matchProduct(params: Record<string, string>, data?: any): Promise<any> {
  const productId = parseInt(params.productId)
  const fdcId = data?.fdc_id
  if (!fdcId) throw { status: 400, message: 'fdc_id is required' }

  // Load USDA nutrients
  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)
  const nutritionData = nutrients.map((n: any) => ({
    name: n.name_zh || n.name,
    value: n.amount,
    unit: n.unit_name,
  }))

  // Update product's custom_nutrition_data
  const product = await getById('products', productId)
  if (!product) throw { status: 404, message: `Product ${productId} not found` }

  await putOne('products', {
    ...product,
    id: productId,
    custom_nutrition_data: {
      nutrients: nutritionData,
      source: 'usda_manual_match',
    },
    updated_at: new Date().toISOString(),
  })

  return { product_id: productId, fdc_id: fdcId, message: 'USDA 匹配成功（本地模式）' }
}

export async function downloadUsda(_params: Record<string, string>, _data?: any): Promise<any> {
  // Local mode: mock task — actual USDA data must be pre-loaded into IndexedDB
  return { task_id: 1, message: 'USDA 下载任务已完成（本地模式使用预置数据）' }
}
