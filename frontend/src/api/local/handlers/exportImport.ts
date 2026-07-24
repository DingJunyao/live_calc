// Export/Import handler — local mode data export and import.
// GET /export/data — Export all local data as JSON
// POST /import/data/upload — Upload and import data (placeholder)

import { getDb } from '../database'

/** 导出数据类型白名单 (IndexedDB store 名称列表) */
const EXPORT_STORES = [
  'units',
  'unit_conversions',
  'ingredient_categories',
  'ingredients',
  'nutrition_data',
  'products',
  'product_records',
  'recipes',
  'recipe_ingredients',
  'merchants',
  'ingredient_hierarchy',
  'entity_unit_overrides',
  'entity_densities',
  'blacklist_groups',
  'blacklist_group_ingredients',
  'blacklist_subscriptions',
  'user_places',
  'merchant_favorites',
  'meal_recommendations',
  'system_config',
  'recipe_cost_history',
  'product_weight_overrides',
  'product_barcodes',
] as const

/**
 * GET /export/data — 导出全部本地数据为 JSON 对象。
 * 仅包含有数据的 store，空 store 省略。
 */
export async function getExportData(
  _params: Record<string, string>,
  _query?: any,
): Promise<Record<string, any[]>> {
  const db = await getDb()
  const exportData: Record<string, any[]> = {}

  for (const store of EXPORT_STORES) {
    const items: any[] = await db.getAll(store)
    if (items.length > 0) {
      exportData[store] = items
    }
  }

  return exportData
}

/**
 * POST /import/data/upload — 导入数据（占位实现）。
 * 完整实现在后续版本中完成。
 */
export async function uploadImport(
  _params: Record<string, string>,
  _data?: any,
): Promise<{ status: string; message: string }> {
  // Ensure basic data exists before import
  return { status: 'ok', message: 'Import endpoint ready' }
}
