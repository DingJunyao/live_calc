// Shared filter / search helpers for local-mode list handlers.
//
// The cloud backend applies a consistent set of query params (comma-separated
// ID lists, special-condition booleans, sort modes). These helpers let the
// local handlers mirror that logic without duplicating the bookkeeping.

import { getAll } from '../database'

/** Parse a comma-separated list (or array) of numeric IDs into number[]. */
export function parseIdList(value: any): number[] {
  if (value == null) return []
  if (Array.isArray(value)) {
    return value.map((v) => Number(v)).filter((n) => Number.isFinite(n) && n > 0)
  }
  return String(value)
    .split(',')
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isFinite(n) && n > 0)
}

/** Parse a comma-separated list (or array) of strings into a trimmed string[]. */
export function parseStringList(value: any): string[] {
  if (value == null) return []
  if (Array.isArray(value)) return value.map((v) => String(v).trim()).filter(Boolean)
  return String(value)
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

/** Truthy check tolerant of boolean / 'true' / '1' / 1 query values. */
export function isTruthy(value: any): boolean {
  return value === true || value === 'true' || value === '1' || value === 1
}

/** Case-insensitive substring match against a list of strings. */
export function listIncludes(list: any[] | undefined | null, lower: string): boolean {
  return Array.isArray(list) && list.some((a) => String(a).toLowerCase().includes(lower))
}

export interface ProductRecordStats {
  products: any[]
  records: any[]
  /** ids of active products */
  activeProductIds: Set<number>
  /** price records grouped by product_id */
  recordsByProduct: Map<number, any[]>
  /** number of price records per product_id */
  recordCountByProduct: Map<number, number>
  /** distinct merchant count per product_id */
  merchantCountByProduct: Map<number, number>
}

/**
 * Precompute per-product price-record statistics from the products /
 * product_records stores. Powers `sort_by=price_records` ordering and the
 * special-condition filters used by both the ingredient and product lists.
 */
export async function buildProductRecordStats(): Promise<ProductRecordStats> {
  const [products, records] = await Promise.all([getAll('products'), getAll('product_records')])
  const activeProductIds = new Set<number>(
    products.filter((p: any) => p.is_active !== false).map((p: any) => p.id),
  )

  const recordsByProduct = new Map<number, any[]>()
  const merchantSets = new Map<number, Set<number>>()
  for (const r of records) {
    if (!activeProductIds.has(r.product_id)) continue
    const arr = recordsByProduct.get(r.product_id)
    if (arr) arr.push(r)
    else recordsByProduct.set(r.product_id, [r])
    if (r.merchant_id != null) {
      const mset = merchantSets.get(r.product_id)
      if (mset) mset.add(r.merchant_id)
      else merchantSets.set(r.product_id, new Set([r.merchant_id]))
    }
  }

  const recordCountByProduct = new Map<number, number>()
  for (const [pid, arr] of recordsByProduct) recordCountByProduct.set(pid, arr.length)

  const merchantCountByProduct = new Map<number, number>()
  for (const [pid, mset] of merchantSets) merchantCountByProduct.set(pid, mset.size)

  return { products, records, activeProductIds, recordsByProduct, recordCountByProduct, merchantCountByProduct }
}

/**
 * Ingredient ids that have at least one "trusted" nutrition row. In local mode
 * the cloud->local import strips source/is_verified provenance, and the local
 * nutrition editor only ever writes trusted rows (source=custom, is_verified=true),
 * so any present nutrition_data row counts as "maintained". An ingredient with
 * zero rows is considered unnourished — powers no_nutrition / has_unnourished_ingredient.
 */
export async function ingredientsWithTrustedNutrition(): Promise<Set<number>> {
  const all = await getAll('nutrition_data')
  const set = new Set<number>()
  for (const n of all) {
    if (n.ingredient_id == null) continue
    set.add(n.ingredient_id)
  }
  return set
}

/** Ingredient ids referenced by any recipe ingredient row. */
export async function recipeIngredientIdSet(): Promise<Set<number>> {
  const all = await getAll('recipe_ingredients')
  return new Set(all.map((ri: any) => ri.ingredient_id).filter((id: any) => id != null))
}

/**
 * Ingredient ids that have at least one active product but no price records on
 * any of them. Used by the recipe special condition for unpriced ingredients.
 */
export async function unpricedIngredientIds(stats: ProductRecordStats): Promise<Set<number>> {
  const productsByIngredient = new Map<number, any[]>()
  for (const p of stats.products) {
    if (p.is_active === false) continue
    const arr = productsByIngredient.get(p.ingredient_id)
    if (arr) arr.push(p)
    else productsByIngredient.set(p.ingredient_id, [p])
  }
  const result = new Set<number>()
  for (const [ingId, prods] of productsByIngredient) {
    const hasRecord = prods.some((p: any) => (stats.recordCountByProduct.get(p.id) ?? 0) > 0)
    if (!hasRecord) result.add(ingId)
  }
  return result
}
