// Products handler — product entities, price records, barcodes, weights.

import { getAll, getById, addOne, putOne, deleteOne, getByIndex, paginate } from '../database'

// ============================================================
// Product Entity CRUD
// ============================================================

export async function listEntity(_params: Record<string, string>, query?: any): Promise<any> {
  const name = query?.name || query?.search
  const lower = name?.toLowerCase()
  const ingredientId = query?.ingredient_id ? parseInt(query.ingredient_id) : undefined
  return paginate('products', { page: query?.page, page_size: query?.page_size || query?.pageSize }, (p: any) => {
    if (p.is_active === false) return false
    if (lower && !p.name?.toLowerCase().includes(lower)) return false
    if (ingredientId && p.ingredient_id !== ingredientId) return false
    return true
  })
}

export async function getEntity(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const product = await getById('products', id)
  if (!product) throw { status: 404, message: `Product ${id} not found` }
  // Attach barcodes
  const barcodes = await getByIndex('product_barcodes', 'by_product_id', id)
  // Attach ingredient name
  let ingredientName = ''
  if (product.ingredient_id) {
    const ing = await getById('ingredients', product.ingredient_id)
    ingredientName = ing?.name || ''
  }
  // Attach latest price（复用自身的 getLatestPrice 计算逻辑）
  let latestPrice: number | null = null
  let latestPriceUnit: string | null = null
  try {
    const records = await getByIndex('product_records', 'by_product_id', id)
    if (records.length > 0) {
      let total = 0, count = 0
      for (const rec of records) {
        const p = rec.price ?? rec.unit_price ?? 0
        if (p <= 0) continue
        const qty = rec.standard_quantity ?? rec.quantity ?? 1
        if (qty <= 0) continue
        total += p / qty
        count++
      }
      if (count > 0) {
        let up = total / count
        let u = records[0]?.unit_name || '斤'
        if (u === '克') { up *= 500; u = '斤' }
        latestPrice = Math.round(up * 10000) / 10000
        latestPriceUnit = u
      }
    }
  } catch { /* latest price is optional */ }
  return {
    ...product,
    barcodes: barcodes || [],
    ingredient_name: ingredientName,
    latest_price: latestPrice,
    latest_price_unit: latestPriceUnit,
  }
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
  return paginate('products', { page: query?.page, page_size: query?.page_size }, (p: any) => {
    if (p.is_active === false) return false
    if (!p.name?.toLowerCase().includes(lower) &&
        !(Array.isArray(p.aliases) && p.aliases.some((a: string) => a.toLowerCase().includes(lower)))) {
      return false
    }
    return true
  })
}

// ============================================================
// Price Records CRUD
// ============================================================

export async function listRecords(_params: Record<string, string>, query?: any): Promise<any> {
  let all = await getAll('product_records')

  // 按原料过滤：查出该原料下所有商品 id，再筛价格记录（原料详情页用）
  const ingredientId = query?.ingredient_id
  if (ingredientId) {
    const products = await getByIndex('products', 'by_ingredient_id', parseInt(ingredientId))
    const productIds = products.map((p: any) => p.id)
    all = all.filter((r: any) => productIds.includes(r.product_id))
  }

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

  // 运行时空缺字段兜底（兼容旧导入数据）
  for (const r of all) {
    if (r.original_unit == null) r.original_unit = r.original_unit_name || ''
    if (r.unit_name == null) r.unit_name = r.standard_unit_name || ''
    if (r.original_quantity == null) r.original_quantity = r.quantity ?? 1
  }

  // Sort by recorded_at descending
  all.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  const page = parseInt(query?.page) || 1
  const pageSize = parseInt(query?.page_size) || parseInt(query?.pageSize) || 20
  const start = (page - 1) * pageSize
  return { items: all.slice(start, start + pageSize), total: all.length, page, page_size: pageSize }
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
    return { average_price: null, unit: null, records: 0 }
  }

  records.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  // 按标准量计算单价：price / standard_quantity
  let totalUnitPrice = 0
  let count = 0
  for (const rec of records) {
    const p = rec.price ?? rec.unit_price ?? 0
    if (p <= 0) continue
    const qty = rec.standard_quantity ?? rec.quantity ?? 1
    if (qty <= 0) continue
    totalUnitPrice += p / qty
    count++
  }

  // 默认以「斤」显示：若单价单位是「克」，×500 转成元/斤
  let displayUnit = records[0]?.unit_name || '斤'
  let displayPrice = count > 0 ? totalUnitPrice / count : 0
  if (displayUnit === '克') {
    displayPrice *= 500
    displayUnit = '斤'
  }

  return {
    average_price: displayPrice > 0 ? Math.round(displayPrice * 10000) / 10000 : null,
    unit: displayUnit,
    records: count,
    latest_record: records[0],
  }
}

export async function getLatestPriceByMerchant(params: Record<string, string>): Promise<any> {
  // Return per-merchant pricing for a product
  const id = parseInt(params.id)
  if (!Number.isFinite(id)) return { prices: [], unit: null }
  const records = await getByIndex('product_records', 'by_product_id', id)
  // 前端模板期望 { prices: [...], unit: "..." }
  return {
    prices: records.map((r: any) => ({
      unit_name: r.unit_name || r.original_unit_name || '',
      price: r.price ?? 0,
      quantity: r.original_quantity ?? 1,
      merchant_id: r.merchant_id,
      merchant_name: r.merchant_name || '',
      recorded_at: r.recorded_at,
    })),
    unit: records[0]?.unit_name || '斤',
  }
}

export async function getProductHistory(params: Record<string, string>): Promise<any> {
  return { items: [], total: 0 }
}
