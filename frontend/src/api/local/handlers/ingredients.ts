// Ingredients handler — CRUD, categories, search, merge, batch product creation.

import { getAll, getById, addOne, putOne, getByIndex, resolvePagination } from '../database'
import {
  parseIdList,
  isTruthy,
  listIncludes,
  buildProductRecordStats,
  ingredientsWithTrustedNutrition,
  recipeIngredientIdSet,
} from './_filter'

export async function listIngredients(_params: Record<string, string>, query?: any): Promise<any> {
  const lower = (query?.q || query?.search || query?.name)?.toLowerCase()
  const categoryIds = parseIdList(query?.category_ids ?? query?.category_id)
  const catSet = categoryIds.length ? new Set(categoryIds) : null

  const noNutrition = isTruthy(query?.no_nutrition)
  const noPrice = isTruthy(query?.no_price)
  const singlePrice = isTruthy(query?.single_price)
  const singleMerchant = isTruthy(query?.single_merchant)
  const noRecipe = isTruthy(query?.no_recipe)
  const noProduct = isTruthy(query?.no_product)
  const sortBy = query?.sort_by

  // Products/records are needed for search-by-product-name, the price-related
  // special conditions, and price_records sort.
  const needProducts =
    !!lower || noPrice || singlePrice || singleMerchant || noProduct || sortBy === 'price_records'
  const stats = needProducts ? await buildProductRecordStats() : null

  // ingredient_id -> active products (and derived price/merchant counts)
  const productsByIngredient = new Map<number, any[]>()
  const recordCountByIngredient = new Map<number, number>()
  const merchantCountByIngredient = new Map<number, number>()
  if (stats) {
    for (const p of stats.products) {
      if (p.is_active === false) continue
      const arr = productsByIngredient.get(p.ingredient_id)
      if (arr) arr.push(p)
      else productsByIngredient.set(p.ingredient_id, [p])
    }
    for (const [ingId, prods] of productsByIngredient) {
      let count = 0
      const merchants = new Set<number>()
      for (const p of prods) {
        const recs = stats.recordsByProduct.get(p.id) || []
        count += recs.length
        for (const r of recs) if (r.merchant_id != null) merchants.add(r.merchant_id)
      }
      recordCountByIngredient.set(ingId, count)
      merchantCountByIngredient.set(ingId, merchants.size)
    }
  }

  const trustedNutrition = noNutrition ? await ingredientsWithTrustedNutrition() : null
  const recipeIngIds = noRecipe ? await recipeIngredientIdSet() : null

  const all = await getAll('ingredients')
  let filtered = all.filter((i: any) => {
    if (i.is_active === false) return false
    if (catSet && !catSet.has(i.category_id)) return false
    if (lower) {
      const selfMatch = i.name?.toLowerCase().includes(lower) || listIncludes(i.aliases, lower)
      if (!selfMatch) {
        const prods = productsByIngredient.get(i.id) || []
        const prodMatch = prods.some(
          (p) => p.name?.toLowerCase().includes(lower) || listIncludes(p.aliases, lower),
        )
        if (!prodMatch) return false
      }
    }
    if (noNutrition && trustedNutrition!.has(i.id)) return false
    if (noProduct && productsByIngredient.has(i.id)) return false
    if (noPrice && (recordCountByIngredient.get(i.id) ?? 0) > 0) return false
    if (singlePrice && (recordCountByIngredient.get(i.id) ?? 0) !== 1) return false
    if (singleMerchant && (merchantCountByIngredient.get(i.id) ?? 0) !== 1) return false
    if (noRecipe && recipeIngIds!.has(i.id)) return false
    return true
  })

  if (sortBy === 'price_records') {
    filtered.sort(
      (a, b) =>
        (recordCountByIngredient.get(b.id) ?? 0) - (recordCountByIngredient.get(a.id) ?? 0) ||
        a.id - b.id,
    )
  } else if (sortBy === 'name') {
    filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
  } else {
    filtered.sort((a, b) => ((b.created_at || '') > (a.created_at || '') ? 1 : -1))
  }

  const { skip, limit: pageSize, page, page_size } = resolvePagination(query)
  const items = filtered.slice(skip, skip + pageSize)
  return { items, total: filtered.length, page, page_size }
}

export async function getIngredient(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const ingredient = await getById('ingredients', id)
  if (!ingredient) throw { status: 404, message: `Ingredient ${id} not found` }
  return ingredient
}

export async function createIngredient(_params: Record<string, string>, data?: any): Promise<any> {
  const id = await addOne('ingredients', {
    ...data,
    is_active: true,
    aliases: data?.aliases || [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })
  return await getById('ingredients', id as number)
}

export async function updateIngredient(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('ingredients', id)
  if (!existing) throw { status: 404, message: `Ingredient ${id} not found` }
  await putOne('ingredients', { ...existing, ...data, id, updated_at: new Date().toISOString() })
  return await getById('ingredients', id)
}

export async function deleteIngredient(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('ingredients', id)
  if (!existing) throw { status: 404, message: `Ingredient ${id} not found` }
  await putOne('ingredients', { ...existing, id, is_active: false, updated_at: new Date().toISOString() })
  return { ok: true }
}

export async function listCategories(): Promise<any> {
  const all = await getAll('ingredient_categories')
  return all
}

export async function searchByName(params: Record<string, string>, query?: any): Promise<any> {
  const name = params.name || query?.name
  if (!name) return { items: [], total: 0 }
  const lower = name.toLowerCase()
  const all = await getAll('ingredients')
  const matched = all.filter(
    (i: any) =>
      i.is_active !== false &&
      (i.name?.toLowerCase().includes(lower) ||
        (Array.isArray(i.aliases) && i.aliases.some((a: string) => a.toLowerCase().includes(lower)))),
  )
  return { items: matched, total: matched.length }
}

export async function mergeIngredients(_params: Record<string, string>, data?: any): Promise<any> {
  // Stub: mark source as inactive, keep target
  const { source_id, target_id } = data || {}
  if (!source_id || !target_id) throw { status: 400, message: 'source_id and target_id are required' }

  const source = await getById('ingredients', parseInt(source_id))
  if (source) {
    await putOne('ingredients', { ...source, id: parseInt(source_id), is_active: false, updated_at: new Date().toISOString() })
  }

  // Move products from source to target
  const sourceProducts = await getByIndex('products', 'by_ingredient_id', parseInt(source_id))
  for (const prod of sourceProducts) {
    await putOne('products', { ...prod, ingredient_id: parseInt(target_id) })
  }

  return await getById('ingredients', parseInt(target_id))
}

export async function batchCreateProducts(_params: Record<string, string>, data?: any): Promise<any> {
  // data = { ingredient_id, names: string[] }
  const ingredientId = parseInt(data?.ingredient_id || data?.ingredientId)
  const names: string[] = data?.names || []
  if (!ingredientId || names.length === 0) throw { status: 400, message: 'ingredient_id and names are required' }

  const created: any[] = []
  for (const name of names) {
    const id = await addOne('products', {
      name,
      ingredient_id: ingredientId,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    created.push(await getById('products', id as number))
  }
  return created
}
