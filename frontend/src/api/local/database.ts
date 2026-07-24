// IndexedDB 本地存储层 — 所有数据表的 schema 定义与 CRUD 辅助函数。
// 使用 idb 库提供类型安全的事务包装。

import { openDB, type IDBPDatabase, type DBSchema } from 'idb'

// ============================================================
// Schema 定义
// ============================================================

interface LocalDB extends DBSchema {
  'units': {
    key: number
    value: any
    indexes: { 'by_type': string }
  }
  'unit_conversions': {
    key: number
    value: any
    indexes: { 'by_from_unit': number; 'by_to_unit': number }
  }
  'ingredient_categories': {
    key: number
    value: any
  }
  'ingredients': {
    key: number
    value: any
    indexes: { 'by_name': string; 'by_category_id': number }
  }
  'nutrition_data': {
    key: number
    value: any
    indexes: { 'by_ingredient_id': number }
  }
  'products': {
    key: number
    value: any
    indexes: { 'by_name': string; 'by_ingredient_id': number }
  }
  'product_records': {
    key: number
    value: any
    indexes: { 'by_product_id': number; 'by_merchant_id': number; 'by_recorded_at': string }
  }
  'product_weight_overrides': {
    key: number
    value: any
    indexes: { 'by_product_id': number }
  }
  'product_barcodes': {
    key: number
    value: any
    indexes: { 'by_product_id': number; 'by_code': string }
  }
  'recipes': {
    key: number
    value: any
    indexes: { 'by_name': string }
  }
  'recipe_ingredients': {
    key: number
    value: any
    indexes: { 'by_recipe_id': number; 'by_ingredient_id': number }
  }
  'recipe_cost_history': {
    key: number
    value: any
    indexes: { 'by_recipe_id': number; 'by_recorded_at': string }
  }
  'merchants': {
    key: number
    value: any
    indexes: { 'by_name': string }
  }
  'merchant_favorites': {
    key: number
    value: any
    indexes: { 'by_merchant_id': number }
  }
  'user_places': {
    key: number
    value: any
  }
  'ingredient_hierarchy': {
    key: number
    value: any
    indexes: { 'by_parent': number; 'by_child': number }
  }
  'entity_unit_overrides': {
    key: number
    value: any
    indexes: { 'by_entity': [string, number] }
  }
  'entity_densities': {
    key: number
    value: any
    indexes: { 'by_entity': [string, number] }
  }
  'usda_foods': {
    key: number
    value: any
    indexes: { 'by_name': string }
  }
  'usda_food_nutrients': {
    key: number
    value: any
    indexes: { 'by_fdc_id': number }
  }
  'blacklist_groups': {
    key: number
    value: any
    indexes: { 'by_name': string }
  }
  'blacklist_group_ingredients': {
    key: number
    value: any
    indexes: { 'by_group_id': number; 'by_ingredient_id': number }
  }
  'blacklist_subscriptions': {
    key: number
    value: any
    indexes: { 'by_group_id': number }
  }
  'meal_recommendations': {
    key: number
    value: any
    indexes: { 'by_date': string }
  }
  'system_config': {
    key: string
    value: any
  }
  'images': {
    key: number
    value: any
    indexes: { 'by_entity': [string, number] }
  }
  'import_tasks': {
    key: number
    value: any
  }
  'agent_sessions': {
    key: number
    value: any
  }
}

type StoreName = keyof LocalDB

// ============================================================
// 数据库单例
// ============================================================

const DB_NAME = 'livecalc'
const DB_VERSION = 1

let dbInstance: IDBPDatabase<LocalDB> | null = null

export async function getDb(): Promise<IDBPDatabase<LocalDB>> {
  if (dbInstance) return dbInstance

  dbInstance = await openDB<LocalDB>(DB_NAME, DB_VERSION, {
    upgrade(db, _oldVersion, _newVersion, _transaction) {
      // ---- 单位 ----
      const unitsStore = db.createObjectStore('units', { keyPath: 'id', autoIncrement: true })
      unitsStore.createIndex('by_type', 'unit_type')

      // ---- 单位换算 ----
      const unitConvStore = db.createObjectStore('unit_conversions', { keyPath: 'id', autoIncrement: true })
      unitConvStore.createIndex('by_from_unit', 'from_unit_id')
      unitConvStore.createIndex('by_to_unit', 'to_unit_id')

      // ---- 食材分类 ----
      db.createObjectStore('ingredient_categories', { keyPath: 'id', autoIncrement: true })

      // ---- 食材 ----
      const ingredientsStore = db.createObjectStore('ingredients', { keyPath: 'id', autoIncrement: true })
      ingredientsStore.createIndex('by_name', 'name')
      ingredientsStore.createIndex('by_category_id', 'category_id')

      // ---- 营养数据 ----
      const nutritionStore = db.createObjectStore('nutrition_data', { keyPath: 'id', autoIncrement: true })
      nutritionStore.createIndex('by_ingredient_id', 'ingredient_id')

      // ---- 商品 ----
      const productsStore = db.createObjectStore('products', { keyPath: 'id', autoIncrement: true })
      productsStore.createIndex('by_name', 'name')
      productsStore.createIndex('by_ingredient_id', 'ingredient_id')

      // ---- 价格记录 ----
      const recordStore = db.createObjectStore('product_records', { keyPath: 'id', autoIncrement: true })
      recordStore.createIndex('by_product_id', 'product_id')
      recordStore.createIndex('by_merchant_id', 'merchant_id')
      recordStore.createIndex('by_recorded_at', 'recorded_at')

      // ---- 商品权重覆盖 ----
      const weightStore = db.createObjectStore('product_weight_overrides', { keyPath: 'id', autoIncrement: true })
      weightStore.createIndex('by_product_id', 'product_id')

      // ---- 商品条码 ----
      const barcodeStore = db.createObjectStore('product_barcodes', { keyPath: 'id', autoIncrement: true })
      barcodeStore.createIndex('by_product_id', 'product_id')
      barcodeStore.createIndex('by_code', 'code', { unique: true })

      // ---- 菜谱 ----
      const recipesStore = db.createObjectStore('recipes', { keyPath: 'id', autoIncrement: true })
      recipesStore.createIndex('by_name', 'name')

      // ---- 菜谱原料 ----
      const recipeIngStore = db.createObjectStore('recipe_ingredients', { keyPath: 'id', autoIncrement: true })
      recipeIngStore.createIndex('by_recipe_id', 'recipe_id')
      recipeIngStore.createIndex('by_ingredient_id', 'ingredient_id')

      // ---- 菜谱成本历史 ----
      const costHistStore = db.createObjectStore('recipe_cost_history', { keyPath: 'id', autoIncrement: true })
      costHistStore.createIndex('by_recipe_id', 'recipe_id')
      costHistStore.createIndex('by_recorded_at', 'recorded_at')

      // ---- 商家 ----
      const merchantsStore = db.createObjectStore('merchants', { keyPath: 'id', autoIncrement: true })
      merchantsStore.createIndex('by_name', 'name')

      // ---- 商家收藏 ----
      const favStore = db.createObjectStore('merchant_favorites', { keyPath: 'id', autoIncrement: true })
      favStore.createIndex('by_merchant_id', 'merchant_id')

      // ---- 用户地点 ----
      db.createObjectStore('user_places', { keyPath: 'id', autoIncrement: true })

      // ---- 食材层级关系 ----
      const hierStore = db.createObjectStore('ingredient_hierarchy', { keyPath: 'id', autoIncrement: true })
      hierStore.createIndex('by_parent', 'parent_id')
      hierStore.createIndex('by_child', 'child_id')

      // ---- 实体单位覆盖 ----
      const euOverrideStore = db.createObjectStore('entity_unit_overrides', { keyPath: 'id', autoIncrement: true })
      euOverrideStore.createIndex('by_entity', ['entity_type', 'entity_id'])

      // ---- 实体密度 ----
      const densityStore = db.createObjectStore('entity_densities', { keyPath: 'id', autoIncrement: true })
      densityStore.createIndex('by_entity', ['entity_type', 'entity_id'])

      // ---- USDA 食品 ----
      const usdaStore = db.createObjectStore('usda_foods', { keyPath: 'fdc_id' })
      usdaStore.createIndex('by_name', 'description')

      // ---- USDA 食品营养素 ----
      const usdaNutStore = db.createObjectStore('usda_food_nutrients', { keyPath: 'id', autoIncrement: true })
      usdaNutStore.createIndex('by_fdc_id', 'fdc_id')

      // ---- 黑名单分组 ----
      const blGroupStore = db.createObjectStore('blacklist_groups', { keyPath: 'id', autoIncrement: true })
      blGroupStore.createIndex('by_name', 'name')

      // ---- 黑名单分组食材 ----
      const blIngStore = db.createObjectStore('blacklist_group_ingredients', { keyPath: 'id', autoIncrement: true })
      blIngStore.createIndex('by_group_id', 'group_id')
      blIngStore.createIndex('by_ingredient_id', 'ingredient_id')

      // ---- 黑名单订阅 ----
      const blSubStore = db.createObjectStore('blacklist_subscriptions', { keyPath: 'id', autoIncrement: true })
      blSubStore.createIndex('by_group_id', 'group_id')

      // ---- 餐食推荐 ----
      const mealStore = db.createObjectStore('meal_recommendations', { keyPath: 'id', autoIncrement: true })
      mealStore.createIndex('by_date', 'date')

      // ---- 系统配置 ----
      db.createObjectStore('system_config', { keyPath: 'key' })

      // ---- 图片 ----
      const imagesStore = db.createObjectStore('images', { keyPath: 'id', autoIncrement: true })
      imagesStore.createIndex('by_entity', ['entity_type', 'entity_id'])

      // ---- 导入任务 ----
      db.createObjectStore('import_tasks', { keyPath: 'id', autoIncrement: true })

      // ---- Agent 会话 ----
      db.createObjectStore('agent_sessions', { keyPath: 'id', autoIncrement: true })
    },
  })

  return dbInstance
}

// ============================================================
// 辅助函数
// ============================================================

/** 获取指定 store 的全部记录 */
export async function getAll<T = any>(storeName: any): Promise<T[]> {
  const db = await getDb()
  return (db as any).getAll(storeName)
}

/** 按主键获取单条记录 */
export async function getById<T = any>(storeName: any, id: number | string): Promise<T | undefined> {
  const db = await getDb()
  return (db as any).get(storeName, id)
}

/** 新增记录，返回新主键 */
export async function addOne(storeName: any, value: any): Promise<number | string> {
  const db = await getDb()
  return (db as any).add(storeName, value)
}

/** 写入/覆盖记录（upsert） */
export async function putOne(storeName: any, value: any): Promise<number | string> {
  const db = await getDb()
  return (db as any).put(storeName, value)
}

/** 按主键删除记录 */
export async function deleteOne(storeName: any, id: number | string): Promise<void> {
  const db = await getDb()
  return (db as any).delete(storeName, id)
}

/** 统计 store 记录数 */
export async function countAll(storeName: any): Promise<number> {
  const db = await getDb()
  return (db as any).count(storeName)
}

/** 按索引查询记录 */
export async function getByIndex<T = any>(
  storeName: any,
  indexName: string,
  value: any,
): Promise<T[]> {
  const db = await getDb()
  return (db as any).getAllFromIndex(storeName, indexName, value)
}

/** 清空 store */
export async function clearStore(storeName: any): Promise<void> {
  const db = await getDb()
  return (db as any).clear(storeName)
}

/** 检查 store 是否包含数据 */
export async function hasData(storeName: any): Promise<boolean> {
  const db = await getDb()
  const count = await (db as any).count(storeName)
  return count > 0
}

/** 批量插入，全部在同一读写事务中完成。返回插入记录的主键列表。 */
export async function batchAdd(storeName: any, items: any[]): Promise<any[]> {
  if (items.length === 0) return []
  const db = await getDb()
  const tx = (db as any).transaction(storeName, 'readwrite')
  const store = tx.objectStore(storeName)
  const keys: any[] = []
  for (const item of items) {
    keys.push(await store.add(item))
  }
  await tx.done
  return keys
}

// ============================================================
// 分页辅助
// ============================================================

export interface PaginationParams {
  page?: number
  page_size?: number
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export async function paginate<T>(
  storeName: any,
  options: PaginationParams = {},
  filter?: (item: T) => boolean,
): Promise<PaginatedResult<T>> {
  const db = await getDb()
  const page = options.page || 1
  const pageSize = options.page_size || 20
  let all: T[] = await (db as any).getAll(storeName)
  if (filter) all = all.filter(filter)
  const total = all.length
  const start = (page - 1) * pageSize
  const items = all.slice(start, start + pageSize)
  return { items, total, page, page_size: pageSize }
}

/** 关闭数据库连接（主要用于测试/重置） */
export async function closeDb(): Promise<void> {
  if (dbInstance) {
    dbInstance.close()
    dbInstance = null
  }
}
