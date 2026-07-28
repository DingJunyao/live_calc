// Merchants handler — CRUD, favorites, coordinates, prices.

import { getAll, getById, addOne, putOne, deleteOne, getByIndex, paginate } from '../database'

export async function listMerchants(_params: Record<string, string>, query?: any): Promise<any> {
  const name = query?.name || query?.search
  const lower = name?.toLowerCase()
  // 默认隐藏已关闭（is_open === false）的商家；仅当 include_closed 为真时才显示。
  const includeClosed = query?.include_closed === true || query?.include_closed === 'true'
  // 前端按 offset/limit 风格传参（skip/limit），兼容 page/page_size。
  const limit = query?.limit != null ? Number(query.limit) : Number(query?.page_size) || 20
  const skip = query?.skip != null ? Number(query.skip) : (Number(query?.page || 1) - 1) * limit
  const page = Math.floor(skip / limit) + 1
  return paginate('merchants', { page, page_size: limit }, (m: any) => {
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
  const page = parseInt(query?.page) || 1
  const pageSize = parseInt(query?.page_size) || 20
  const start = (page - 1) * pageSize
  return { items: all.slice(start, start + pageSize), total: all.length, page, page_size: pageSize }
}

export async function getMerchantProductPrices(params: Record<string, string>): Promise<any> {
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
  return { items: Object.values(latestByProduct), total: Object.keys(latestByProduct).length }
}

export async function getMapConfig(): Promise<any> {
  return {
    map_enabled: true,
    default_map: 'amap',
  }
}

export async function listUserPlaces(): Promise<any> {
  const all = await getAll('user_places')
  return { items: all, total: all.length }
}

export async function createUserPlace(_params: Record<string, string>, data?: any): Promise<any> {
  const id = await addOne('user_places', {
    ...data, created_at: new Date().toISOString(),
  })
  return getById('user_places', id as number)
}
