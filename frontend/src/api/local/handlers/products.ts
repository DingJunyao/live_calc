// Products handler — product entities, price records, barcodes, weights.

import { getAll, getById, addOne, putOne, deleteOne, getByIndex, paginate, resolvePagination } from '../database'
import { aggregatePrices } from '../business/priceNormalize'
import type { UnitInfo, EntityOverride, DensityInfo } from '../business/unitConverter'
import {
  parseIdList,
  parseStringList,
  isTruthy,
  listIncludes,
  buildProductRecordStats,
} from './_filter'

// ============================================================
// Product Entity CRUD
// ============================================================

export async function listEntity(_params: Record<string, string>, query?: any): Promise<any> {
  const lower = (query?.search || query?.name || query?.q)?.toLowerCase()
  const ingredientIds = parseIdList(query?.ingredient_ids ?? query?.ingredient_id)
  const ingredientCategoryIds = parseIdList(query?.ingredient_category_ids)
  const brandList = parseStringList(query?.brands)
  const brandSet = brandList.length ? new Set(brandList) : null
  const noPrice = isTruthy(query?.no_price)
  const singlePrice = isTruthy(query?.single_price)
  const singleMerchant = isTruthy(query?.single_merchant)
  const sortBy = query?.sort_by

  const needStats = noPrice || singlePrice || singleMerchant || sortBy === 'price_records'
  const needIngredients = !!lower || ingredientCategoryIds.length > 0
  const stats = needStats ? await buildProductRecordStats() : null

  const ingredientById = new Map<number, any>()
  if (needIngredients) {
    const allIngredients = await getAll('ingredients')
    for (const ing of allIngredients) ingredientById.set(ing.id, ing)
  }

  // ingredient_ids filter (direct) and ingredient_category_ids (resolved)
  const directIngredientIds = ingredientIds.length ? new Set(ingredientIds) : null
  let categoryIngredientIds: Set<number> | null = null
  if (ingredientCategoryIds.length) {
    const catSet = new Set(ingredientCategoryIds)
    categoryIngredientIds = new Set(
      [...ingredientById.values()]
        .filter((i) => catSet.has(i.category_id))
        .map((i) => i.id),
    )
  }

  const allProducts = stats ? stats.products : await getAll('products')
  let filtered = allProducts.filter((p: any) => {
    if (p.is_active === false) return false
    if (lower) {
      const selfMatch = p.name?.toLowerCase().includes(lower) || listIncludes(p.aliases, lower)
      if (!selfMatch) {
        const ing = ingredientById.get(p.ingredient_id)
        const ingMatch =
          ing && (ing.name?.toLowerCase().includes(lower) || listIncludes(ing.aliases, lower))
        if (!ingMatch) return false
      }
    }
    if (directIngredientIds && !directIngredientIds.has(p.ingredient_id)) return false
    if (categoryIngredientIds && !categoryIngredientIds.has(p.ingredient_id)) return false
    if (brandSet && !(p.brand && brandSet.has(p.brand))) return false
    if (noPrice && (stats!.recordCountByProduct.get(p.id) ?? 0) > 0) return false
    if (singlePrice && (stats!.recordCountByProduct.get(p.id) ?? 0) !== 1) return false
    if (singleMerchant && (stats!.merchantCountByProduct.get(p.id) ?? 0) !== 1) return false
    return true
  })

  if (sortBy === 'price_records' && stats) {
    filtered.sort(
      (a, b) =>
        (stats.recordCountByProduct.get(b.id) ?? 0) -
          (stats.recordCountByProduct.get(a.id) ?? 0) || a.id - b.id,
    )
  } else if (sortBy === 'updated_at') {
    filtered.sort((a, b) => ((b.updated_at || '') > (a.updated_at || '') ? 1 : -1))
  } else {
    filtered.sort((a, b) => ((b.created_at || '') > (a.created_at || '') ? 1 : -1))
  }

  const { skip, limit: pageSize, page, page_size } = resolvePagination(query)
  return { items: filtered.slice(skip, skip + pageSize), total: filtered.length, page, page_size }
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
      // 按单位类型分组归一化，避免质量/计数混算（鸡蛋类问题的根因）
      const [units, overrides, densities] = await Promise.all([
        getAll('units') as Promise<UnitInfo[]>,
        getAll('entity_unit_overrides') as Promise<EntityOverride[]>,
        getAll('entity_densities') as Promise<DensityInfo[]>,
      ])
      // 覆盖表按 ingredient 维护，用 product.ingredient_id 查找；缺则回退到商品 id
      const entId = product.ingredient_id ?? id
      const agg = aggregatePrices(records, units, overrides, densities, 'ingredient', entId)
      if (agg.average_price != null) {
        latestPrice = agg.average_price
        latestPriceUnit = agg.unit
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
  if (!q) return []

  const lower = q.toLowerCase()
  const result = await paginate('products', query, (p: any) => {
    if (p.is_active === false) return false
    if (!p.name?.toLowerCase().includes(lower) &&
        !(Array.isArray(p.aliases) && p.aliases.some((a: string) => a.toLowerCase().includes(lower)))) {
      return false
    }
    return true
  })
  return result.items
}

// ============================================================
// Price Records CRUD
// ============================================================

export async function listRecords(_params: Record<string, string>, query?: any): Promise<any> {
  const lower = (query?.search || query?.product_name || query?.q)?.toLowerCase()
  const merchantIds = parseIdList(query?.merchant_ids ?? query?.merchant_id)
  const merchantIdSet = merchantIds.length ? new Set(merchantIds) : null
  const recordTypes = parseStringList(query?.record_types ?? query?.record_type)
  const recordTypeSet = recordTypes.length ? new Set(recordTypes) : null
  const categoryIds = parseIdList(query?.ingredient_category_ids)
  const catSet = categoryIds.length ? new Set(categoryIds) : null
  const ingredientId = query?.ingredient_id
  const productId = query?.product_id
  const startDate = query?.start_date || query?.startDate
  const endDate = query?.end_date || query?.endDate

  // Search and category/ingredient joins need product + ingredient lookups;
  // merchants are always needed to attach merchant_name for display.
  const needJoin = !!lower || !!catSet || !!ingredientId
  const products = needJoin ? await getAll('products') : null
  const merchants = await getAll('merchants')
  const ingredients = needJoin ? await getAll('ingredients') : null

  const productMap = new Map<number, any>()
  if (products) for (const p of products) productMap.set(p.id, p)
  const merchantMap = new Map<number, any>()
  for (const m of merchants) merchantMap.set(m.id, m)
  const ingredientMap = new Map<number, any>()
  if (ingredients) for (const i of ingredients) ingredientMap.set(i.id, i)

  // ingredient_id -> product ids (ingredient detail page)
  let ingredientProductIds: Set<number> | null = null
  if (ingredientId) {
    ingredientProductIds = new Set(
      (products || [])
        .filter((p: any) => p.ingredient_id === parseInt(ingredientId))
        .map((p: any) => p.id),
    )
  }
  // ingredient_category_ids -> product ids via product.ingredient.category_id
  let categoryProductIds: Set<number> | null = null
  if (catSet) {
    categoryProductIds = new Set(
      (products || [])
        .filter((p: any) => {
          const ing = ingredientMap.get(p.ingredient_id)
          return ing && catSet.has(ing.category_id)
        })
        .map((p: any) => p.id),
    )
  }

  const all = (await getAll('product_records')).filter((r: any) => {
    if (ingredientProductIds && !ingredientProductIds.has(r.product_id)) return false
    if (productId && r.product_id !== parseInt(productId)) return false
    if (merchantIdSet && !(r.merchant_id != null && merchantIdSet.has(r.merchant_id))) return false
    if (recordTypeSet && !recordTypeSet.has(r.record_type)) return false
    if (categoryProductIds && !categoryProductIds.has(r.product_id)) return false
    if (startDate && (r.recorded_at || '') < startDate) return false
    if (endDate && (r.recorded_at || '') > endDate) return false
    if (lower) {
      const prod = productMap.get(r.product_id)
      const nameMatch =
        r.product_name?.toLowerCase().includes(lower) ||
        (prod && (prod.name?.toLowerCase().includes(lower) || listIncludes(prod.aliases, lower)))
      if (!nameMatch) {
        const ing = ingredientMap.get(prod?.ingredient_id)
        const ingMatch =
          ing && (ing.name?.toLowerCase().includes(lower) || listIncludes(ing.aliases, lower))
        if (!ingMatch) return false
      }
    }
    return true
  })

  // Backfill missing fields (legacy import data) and attach product/merchant
  // names so the list (and its filters) behave like cloud mode.
  for (const r of all) {
    if (r.original_unit == null) r.original_unit = r.original_unit_name || ''
    if (r.unit_name == null) r.unit_name = r.standard_unit_name || ''
    if (r.original_quantity == null) r.original_quantity = r.quantity ?? 1
    if (!r.product_name) {
      const prod = productMap.get(r.product_id)
      if (prod) r.product_name = prod.name
    }
    if (r.merchant_name === undefined && r.merchant_id != null) {
      const m = merchantMap.get(r.merchant_id)
      if (m) r.merchant_name = m.name
    }
  }

  // Sort by recorded_at descending
  all.sort((a: any, b: any) => ((b.recorded_at || '') > (a.recorded_at || '') ? 1 : -1))

  const { skip, limit: pageSize, page, page_size } = resolvePagination(query)
  return { items: all.slice(skip, skip + pageSize), total: all.length, page, page_size }
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

  // 按单位类型分组归一化：质量记录返回 ¥/斤，计数记录单独 ¥/个，不混算
  const product = await getById('products', productId)
  const [units, overrides, densities] = await Promise.all([
    getAll('units') as Promise<UnitInfo[]>,
    getAll('entity_unit_overrides') as Promise<EntityOverride[]>,
    getAll('entity_densities') as Promise<DensityInfo[]>,
  ])
  const entId = product?.ingredient_id ?? productId
  const agg = aggregatePrices(records, units, overrides, densities, 'ingredient', entId)

  return {
    average_price: agg.average_price,
    unit: agg.average_price != null ? agg.unit : null,
    min_price: agg.min_price,
    max_price: agg.max_price,
    records: agg.records,
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
