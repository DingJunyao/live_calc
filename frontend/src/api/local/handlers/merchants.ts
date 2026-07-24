// Merchants handler — CRUD, favorites, coordinates, prices.

import { getDb, getAll, getById, addOne, putOne, deleteOne, getByIndex } from '../database'

function paginate<T>(items: T[], query: any): { items: T[]; total: number; page: number; page_size: number } {
  const page = parseInt(query?.page) || 1
  const pageSize = parseInt(query?.page_size) || 20
  const start = (page - 1) * pageSize
  return { items: items.slice(start, start + pageSize), total: items.length, page, page_size: pageSize }
}

export async function listMerchants(_params: Record<string, string>, query?: any): Promise<any> {
  let all = await getAll('merchants')
  const name = query?.name || query?.search
  if (name) {
    const lower = name.toLowerCase()
    all = all.filter((m: any) => m.name?.toLowerCase().includes(lower))
  }
  return paginate(all.filter((m: any) => m.is_active !== false), query)
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

export async function getCoordinates(): Promise<any> {
  const all = await getAll('merchants')
  const coords = all
    .filter((m: any) => m.latitude && m.longitude && m.is_active !== false)
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
  return paginate(all, query)
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
