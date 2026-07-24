// Products handler — product entities, price records, barcodes, weights.

import { getDb, getAll, getById, addOne, putOne, deleteOne, getByIndex } from '../database'

function paginate<T>(items: T[], query: any): { items: T[]; total: number; page: number; page_size: number } {
  const page = parseInt(query?.page) || 1
  const pageSize = parseInt(query?.page_size) || parseInt(query?.pageSize) || 20
  const start = (page - 1) * pageSize
  return { items: items.slice(start, start + pageSize), total: items.length, page, page_size: pageSize }
}

// ============================================================
// Product Entity CRUD
// ============================================================

export async function listEntity(_params: Record<string, string>, query?: any): Promise<any> {
  let all = await getAll('products')
  all = all.filter((p: any) => p.is_active !== false)

  const name = query?.name || query?.search
  if (name) {
    const lower = name.toLowerCase()
    all = all.filter((p: any) => p.name?.toLowerCase().includes(lower))
  }
  const ingredientId = query?.ingredient_id
  if (ingredientId) {
    all = all.filter((p: any) => p.ingredient_id === parseInt(ingredientId))
  }
  return paginate(all, query)
}

export async function getEntity(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const product = await getById('products', id)
  if (!product) throw { status: 404, message: `Product ${id} not found` }
  // Attach barcodes
  const barcodes = await getByIndex('product_barcodes', 'by_product_id', id)
  return { ...product, barcodes: barcodes || [] }
}

export async function createEntity(_params: Record<string, string>, data?: any): Promise<any> {
  const id = await addOne('products', {
    ...data,
    is_active: true,
    aliases: data?.aliases || [],
    tags: data?.tags || [],
    price_weight: data?.price_weight ?? 50,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })
  return await getById('products', id as number)
}

export async function updateEntity(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('products', id)
  if (!existing) throw { status: 404, message: `Product ${id} not found` }
  await putOne('products', { ...existing, ...data, id, updated_at: new Date().toISOString() })
  return await getById('products', id)
}

export async function deleteEntity(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('products', id)
  if (!existing) throw { status: 404, message: `Product ${id} not found` }
  await putOne('products', { ...existing, id, is_active: false, updated_at: new Date().toISOString() })
  return { ok: true }
}

// ============================================================
// Autocomplete
// ============================================================

export async function autocomplete(_params: Record<string, string>, query?: any): Promise<any> {
  const q = query?.q || query?.name || ''
  if (!q) return { items: [], total: 0 }

  const lower = q.toLowerCase()
  const all = await getAll('products')
  const matched = all.filter(
    (p: any) =>
      p.is_active !== false &&
      (p.name?.toLowerCase().includes(lower) ||
        (Array.isArray(p.aliases) && p.aliases.some((a: string) => a.toLowerCase().includes(lower)))),
  )
  return paginate(matched, query)
}

// ============================================================
// Price Records CRUD
// ============================================================

export async function listRecords(_params: Record<string, string>, query?: any): Promise<any> {
  let all = await getAll('product_records')

  const productId = query?.product_id
  if (productId) {
    all = all.filter((r: any) => r.product_id === parseInt(productId))
  }
  const merchantId = query?.merchant_id
  if (merchantId) {
    all = all.filter((r: any) => r.merchant_id === parseInt(merchantId))
  }
  const startDate = query?.start_date || query?.startDate
  if (startDate) {
    all = all.filter((r: any) => (r.recorded_at || '') >= startDate)
  }
  const endDate = query?.end_date || query?.endDate
  if (endDate) {
    all = all.filter((r: any) => (r.recorded_at || '') <= endDate)
  }

  // Sort by recorded_at descending
  all.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  return paginate(all, query)
}

export async function createRecord(_params: Record<string, string>, data?: any): Promise<any> {
  const id = await addOne('product_records', {
    ...data,
    created_at: new Date().toISOString(),
    recorded_at: data?.recorded_at || new Date().toISOString(),
  })
  return await getById('product_records', id as number)
}

export async function updateRecord(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('product_records', id)
  if (!existing) throw { status: 404, message: `Price record ${id} not found` }
  await putOne('product_records', { ...existing, ...data, id, updated_at: new Date().toISOString() })
  return await getById('product_records', id)
}

export async function deleteRecord(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('product_records', id)
  if (!existing) throw { status: 404, message: `Price record ${id} not found` }
  await deleteOne('product_records', id)
  return { ok: true }
}

// ============================================================
// Product Weights
// ============================================================

export async function getWeight(params: Record<string, string>): Promise<any> {
  const productId = parseInt(params.id)
  const overrides = await getByIndex('product_weight_overrides', 'by_product_id', productId)
  const product = await getById('products', productId)
  return {
    product_id: productId,
    global_weight: product?.price_weight ?? 50,
    my_weight: overrides.length > 0 ? overrides[0].weight : null,
    override_id: overrides.length > 0 ? overrides[0].id : null,
  }
}

export async function setWeight(params: Record<string, string>, data?: any): Promise<any> {
  const productId = parseInt(params.id)
  const weight = data?.weight ?? 50
  const existing = await getByIndex('product_weight_overrides', 'by_product_id', productId)

  if (existing.length > 0) {
    await putOne('product_weight_overrides', { ...existing[0], weight, updated_at: new Date().toISOString() })
    return await getById('product_weight_overrides', existing[0].id)
  }
  const id = await addOne('product_weight_overrides', {
    product_id: productId,
    weight,
    created_at: new Date().toISOString(),
  })
  return await getById('product_weight_overrides', id as number)
}

export async function deleteWeight(params: Record<string, string>): Promise<any> {
  const productId = parseInt(params.id)
  const existing = await getByIndex('product_weight_overrides', 'by_product_id', productId)
  for (const item of existing) {
    await deleteOne('product_weight_overrides', item.id)
  }
  return { ok: true }
}

// ============================================================
// Barcodes
// ============================================================

export async function listBarcodes(params: Record<string, string>): Promise<any> {
  const productId = parseInt(params.id)
  const barcodes = await getByIndex('product_barcodes', 'by_product_id', productId)
  return { items: barcodes, total: barcodes.length }
}

export async function addBarcode(params: Record<string, string>, data?: any): Promise<any> {
  const productId = parseInt(params.id)
  const id = await addOne('product_barcodes', {
    product_id: productId,
    code: data?.code,
    standard: data?.standard || 'ean13',
    created_at: new Date().toISOString(),
  })
  return await getById('product_barcodes', id as number)
}

// ============================================================
// Latest Price
// ============================================================

export async function getLatestPrice(params: Record<string, string>): Promise<any> {
  const productId = parseInt(params.id)
  const records = await getByIndex('product_records', 'by_product_id', productId)

  if (records.length === 0) {
    return { price: null, unit: null, records: 0 }
  }

  const sorted = records.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  // Simple average of all records
  let total = 0
  let count = 0
  for (const rec of records) {
    const p = rec.price || rec.unit_price
    if (p && p > 0) {
      total += p
      count++
    }
  }

  return {
    price: count > 0 ? total / count : null,
    unit: sorted[0]?.unit_name || sorted[0]?.unit || '斤',
    records: count,
    latest_record: sorted[0],
  }
}
