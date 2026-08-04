// Merchants handler — CRUD, favorites, coordinates, prices.

import { getAll, getById, addOne, putOne, deleteOne, getByIndex, paginate, resolvePagination } from '../database'

export async function listMerchants(_params: Record<string, string>, query?: any): Promise<any> {
  const name = query?.name || query?.search
  const lower = name?.toLowerCase()
  // 默认隐藏已关闭（is_open === false）的商家；仅当 include_closed 为真时才显示。
  const includeClosed = query?.include_closed === true || query?.include_closed === 'true'
  return paginate('merchants', query, (m: any) => {
    if (m.is_active === false) return false
    if (!includeClosed && m.is_open === false) return false
    if (lower && !m.name?.toLowerCase().includes(lower)) return false
    return true
  })
}

export async function getMerchant(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const merchant = await getById('merchants', id)
  if (!merchant) throw { status: 404, message: `Merchant ${id} not found` }
  return merchant
}

export async function createMerchant(_params: Record<string, string>, data?: any): Promise<any> {
  const id = await addOne('merchants', {
    ...data,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })
  return await getById('merchants', id as number)
}

export async function updateMerchant(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('merchants', id)
  if (!existing) throw { status: 404, message: `Merchant ${id} not found` }
  await putOne('merchants', { ...existing, ...data, id, updated_at: new Date().toISOString() })
  return await getById('merchants', id)
}

export async function deleteMerchant(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('merchants', id)
  if (!existing) throw { status: 404, message: `Merchant ${id} not found` }
  await putOne('merchants', { ...existing, id, is_active: false, updated_at: new Date().toISOString() })
  return { ok: true }
}

export async function listFavorites(_params: Record<string, string>): Promise<any> {
  const all = await getAll('merchant_favorites')
  return { items: all, total: all.length }
}

export async function addFavorite(params: Record<string, string>): Promise<any> {
  const merchantId = parseInt(params.id)
  const existing = await getByIndex('merchant_favorites', 'by_merchant_id', merchantId)
  if (existing.length > 0) return existing[0]
  const id = await addOne('merchant_favorites', {
    merchant_id: merchantId,
    created_at: new Date().toISOString(),
  })
  return await getById('merchant_favorites', id as number)
}

export async function removeFavorite(params: Record<string, string>): Promise<any> {
  const merchantId = parseInt(params.id)
  const existing = await getByIndex('merchant_favorites', 'by_merchant_id', merchantId)
  for (const f of existing) {
    await deleteOne('merchant_favorites', f.id)
  }
  return { ok: true }
}

export async function getCoordinates(_params: Record<string, string>, query?: any): Promise<any> {
  const all = await getAll('merchants')
  const coords = all
    .filter((m: any) => {
      if (!m.latitude || !m.longitude || m.is_active === false) return false
      // 默认排除已关闭商家，与列表行为一致；include_closed=true 时显示
      const includeClosed = query?.include_closed === true || query?.include_closed === 'true'
      if (!includeClosed && m.is_open === false) return false
      return true
    })
    .map((m: any) => ({
      id: m.id,
      name: m.name,
      latitude: m.latitude,
      longitude: m.longitude,
    }))
  return coords
}

export async function getMerchantPrices(params: Record<string, string>, query?: any): Promise<any> {
  const merchantId = parseInt(params.id)
  const all = await getByIndex('product_records', 'by_merchant_id', merchantId)
  const { skip, limit: pageSize, page, page_size } = resolvePagination(query)
  return { items: all.slice(skip, skip + pageSize), total: all.length, page, page_size }
}

export async function getMerchantProductPrices(params: Record<string, string>, query?: any): Promise<any> {
  const merchantId = parseInt(params.id)
  const all = await getByIndex('product_records', 'by_merchant_id', merchantId)
  // Return the latest price for each product at this merchant
  const latestByProduct: Record<number, any> = {}
  for (const rec of all) {
    const existing = latestByProduct[rec.product_id]
    if (!existing || rec.recorded_at > existing.recorded_at) {
      latestByProduct[rec.product_id] = rec
    }
  }
  const records = Object.values(latestByProduct)
  const total = records.length
  const { skip, limit, page, page_size } = resolvePagination(query)
  const pagedRecords = records.slice(skip, skip + limit)
  if (total === 0) return { items: [], total: 0, page, page_size }

  // Join products -> ingredients -> ingredient_categories so the Quick Fill
  // page can sort/group exactly like cloud mode (category sort_order, then
  // pinyin). Also compute custom_sort_score from the last 3 days of learned
  // fill-order records (mirrors the cloud backend's weighted logic).
  const [products, ingredients, categories] = await Promise.all([
    getAll('products'),
    getAll('ingredients'),
    getAll('ingredient_categories'),
  ])
  // user_merchant_product_orders was added in DB v3; if the upgrade hasn't
  // applied yet (HMR stale connection, or an old tab holding the v2 DB open),
  // getAll would throw and break the whole list. Degrade to empty instead.
  const orderRecords = await safeGetAll('user_merchant_product_orders')
  const productMap = new Map(products.map((p: any) => [p.id, p]))
  const ingredientMap = new Map(ingredients.map((i: any) => [i.id, i]))
  const categoryMap = new Map(categories.map((c: any) => [c.id, c]))

  const customScores = computeCustomSortScores(orderRecords, merchantId)

  const items = pagedRecords.map((rec: any) => {
    const product = productMap.get(rec.product_id)
    const ingredient = product?.ingredient_id ? ingredientMap.get(product.ingredient_id) : undefined
    const category = ingredient?.category_id != null ? categoryMap.get(ingredient.category_id) : undefined
    return {
      ...rec,
      product_name: product?.name ?? '',
      category_id: category?.id ?? ingredient?.category_id ?? null,
      category_display_name: category?.display_name ?? null,
      category_sort_order: category?.sort_order ?? null,
      custom_sort_score: customScores.get(rec.product_id),
    }
  })

  return { items, total, page, page_size }
}

/** Read a store that may not exist yet; return [] on failure (DB not upgraded). */
async function safeGetAll(storeName: string): Promise<any[]> {
  try {
    return await getAll(storeName as any)
  } catch {
    return []
  }
}

/** Local-date string (YYYY-MM-DD) N days before today, in the user's timezone. */
function localDateDaysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toLocaleDateString('en-CA')
}

/**
 * Weighted sort score per product from the last 3 days of fill-order records.
 * Mirrors the cloud backend: today x3, yesterday x2, day-before x1, averaged
 * by total weight. Products with no recent order get no score (undefined).
 */
function computeCustomSortScores(orderRecords: any[], merchantId: number): Map<number, number> {
  const weights: Record<string, number> = {
    [localDateDaysAgo(0)]: 3,
    [localDateDaysAgo(1)]: 2,
    [localDateDaysAgo(2)]: 1,
  }
  const productWeights: Record<number, number> = {}
  const productCounts: Record<number, number> = {}
  for (const rec of orderRecords) {
    if (rec.merchant_id !== merchantId) continue
    const w = weights[rec.session_date]
    if (!w) continue
    const pid = rec.product_id
    productWeights[pid] = (productWeights[pid] || 0) + rec.sort_order * w
    productCounts[pid] = (productCounts[pid] || 0) + w
  }
  const scores = new Map<number, number>()
  for (const pid of Object.keys(productWeights).map(Number)) {
    scores.set(pid, productWeights[pid] / productCounts[pid])
  }
  return scores
}

export async function saveProductOrders(params: Record<string, string>, data?: any): Promise<any> {
  const merchantId = parseInt(params.id)
  const productIds: number[] = Array.isArray(data?.product_ids) ? data.product_ids : []
  const sessionDate: string = data?.session_date || new Date().toLocaleDateString('en-CA')

  // Load existing records for this (merchant, session_date) to upsert by product_id.
  // Mirrors cloud: duplicate product_ids in one request take the last sort_order.
  const all = await getAll('user_merchant_product_orders')
  const existingByPid = new Map<number, any>()
  for (const rec of all) {
    if (rec.merchant_id === merchantId && rec.session_date === sessionDate) {
      existingByPid.set(rec.product_id, rec)
    }
  }

  const seen = new Map<number, any>()
  for (let idx = 0; idx < productIds.length; idx++) {
    const pid = productIds[idx]
    const record = seen.get(pid) || existingByPid.get(pid)
    if (record) {
      // Last sort_order wins for duplicates; pre-existing record queued below.
      record.sort_order = idx
      seen.set(pid, record)
    } else {
      const id = await addOne('user_merchant_product_orders', {
        merchant_id: merchantId,
        product_id: pid,
        session_date: sessionDate,
        sort_order: idx,
        created_at: new Date().toISOString(),
      })
      seen.set(pid, { id })
    }
  }

  for (const rec of seen.values()) {
    if (rec.id != null && existingByPid.has(rec.product_id)) {
      await putOne('user_merchant_product_orders', { ...rec })
    }
  }

  return { message: 'ok' }
}

export async function getMapConfig(): Promise<any> {
  return {
    map_enabled: true,
    default_map: 'amap',
  }
}

export async function listUserPlaces(): Promise<any> {
  // 与云端 List[UserPlaceResponse] 对齐：返回数组，默认地点优先。
  const all = await getAll('user_places')
  return all.sort(
    (a: any, b: any) =>
      Number(!!b.is_default) - Number(!!a.is_default) ||
      (a.sort_order ?? 0) - (b.sort_order ?? 0) ||
      (a.created_at || '').localeCompare(b.created_at || ''),
  )
}

export async function createUserPlace(_params: Record<string, string>, data?: any): Promise<any> {
  if (data?.is_default) {
    // 设为默认前清除其他默认，保证全局唯一
    const all = await getAll('user_places')
    for (const p of all) {
      if (p.is_default) await putOne('user_places', { ...p, is_default: false })
    }
  }
  const id = await addOne('user_places', {
    ...data,
    is_default: !!data?.is_default,
    sort_order: data?.sort_order ?? 0,
    created_at: new Date().toISOString(),
  })
  return getById('user_places', id as number)
}

export async function updateUserPlace(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('user_places', id)
  if (!existing) throw { status: 404, message: '常用地点不存在' }
  await putOne('user_places', { ...existing, ...data, id })
  return getById('user_places', id)
}

export async function deleteUserPlace(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  await deleteOne('user_places', id)
  return { message: '常用地点已删除' }
}

export async function setDefaultUserPlace(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const target = await getById('user_places', id)
  if (!target) throw { status: 404, message: '常用地点不存在' }
  // 清除其他默认，保证全局唯一
  const all = await getAll('user_places')
  for (const p of all) {
    if (p.id !== id && p.is_default) await putOne('user_places', { ...p, is_default: false })
  }
  await putOne('user_places', { ...target, is_default: true })
  return getById('user_places', id)
}
