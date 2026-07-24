// Ingredients handler — CRUD, categories, search, merge, batch product creation.

import { getAll, getById, addOne, putOne, getByIndex, paginate } from '../database'

export async function listIngredients(_params: Record<string, string>, query?: any): Promise<any> {
  const name = query?.name || query?.search
  const lower = name?.toLowerCase()
  const categoryId = query?.category_id ? parseInt(query.category_id) : undefined
  return paginate('ingredients', { page: query?.page, page_size: query?.page_size }, (i: any) => {
    if (i.is_active === false) return false
    if (lower && !i.name?.toLowerCase().includes(lower)) return false
    if (categoryId && i.category_id !== categoryId) return false
    return true
  })
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
  return { items: all, total: all.length }
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
