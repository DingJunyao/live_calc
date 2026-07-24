// Browser Agent 工具定义 — 7 个 IndexedDB 工具。
// 每个工具包含名称、中文描述、JSON Schema 参数和 execute 执行函数。

import { getAll, getById, getByIndex, countAll, getDb } from '../database'

// ============================================================
// 类型定义
// ============================================================

export interface ToolDefinition {
  name: string
  description: string
  parameters: Record<string, any>
  execute: (args: Record<string, any>) => Promise<any>
}

// ============================================================
// 工具 1：read_products
// ============================================================

const read_products: ToolDefinition = {
  name: 'read_products',
  description: '查询商品列表。支持按名称搜索（模糊匹配），可限制返回数量。',
  parameters: {
    type: 'object',
    properties: {
      name: {
        type: 'string',
        description: '商品名称搜索关键字（模糊匹配）',
      },
      limit: {
        type: 'integer',
        description: '最大返回数量，默认 20，最大 100',
        default: 20,
      },
      ingredient_id: {
        type: 'integer',
        description: '按关联食材 ID 过滤',
      },
    },
  },
  async execute(args: Record<string, any>) {
    const all: any[] = await getAll('products')
    const limit = Math.min(args.limit ?? 20, 100)
    const lower = args.name?.toLowerCase()

    let filtered = all.filter((p: any) => {
      if (p.is_active === false) return false
      if (lower && !p.name?.toLowerCase().includes(lower)) return false
      if (args.ingredient_id && p.ingredient_id !== args.ingredient_id) return false
      return true
    })

    return filtered.slice(0, limit)
  },
}

// ============================================================
// 工具 2：read_ingredients
// ============================================================

const read_ingredients: ToolDefinition = {
  name: 'read_ingredients',
  description: '查询食材列表。支持按名称搜索（模糊匹配），可限制返回数量。',
  parameters: {
    type: 'object',
    properties: {
      name: {
        type: 'string',
        description: '食材名称搜索关键字（模糊匹配）',
      },
      limit: {
        type: 'integer',
        description: '最大返回数量，默认 20，最大 100',
        default: 20,
      },
      category_id: {
        type: 'integer',
        description: '按分类 ID 过滤',
      },
    },
  },
  async execute(args: Record<string, any>) {
    const all: any[] = await getAll('ingredients')
    const limit = Math.min(args.limit ?? 20, 100)
    const lower = args.name?.toLowerCase()

    let filtered = all.filter((i: any) => {
      if (i.is_active === false) return false
      if (lower && !i.name?.toLowerCase().includes(lower)) return false
      if (args.category_id && i.category_id !== args.category_id) return false
      return true
    })

    return filtered.slice(0, limit)
  },
}

// ============================================================
// 工具 3：read_recipes
// ============================================================

const read_recipes: ToolDefinition = {
  name: 'read_recipes',
  description: '查询菜谱列表。支持按名称搜索（模糊匹配），可限制返回数量。',
  parameters: {
    type: 'object',
    properties: {
      name: {
        type: 'string',
        description: '菜谱名称搜索关键字（模糊匹配）',
      },
      limit: {
        type: 'integer',
        description: '最大返回数量，默认 20，最大 100',
        default: 20,
      },
    },
  },
  async execute(args: Record<string, any>) {
    const all: any[] = await getAll('recipes')
    const limit = Math.min(args.limit ?? 20, 100)
    const lower = args.name?.toLowerCase()

    let filtered = all.filter((r: any) => {
      if (r.is_active === false) return false
      if (lower && !r.name?.toLowerCase().includes(lower)) return false
      return true
    })

    return filtered.slice(0, limit)
  },
}

// ============================================================
// 工具 4：read_nutrition
// ============================================================

const read_nutrition: ToolDefinition = {
  name: 'read_nutrition',
  description: '查询指定食材的营养数据。返回食材的营养成分列表（每 100g 含量）。',
  parameters: {
    type: 'object',
    properties: {
      ingredient_id: {
        type: 'integer',
        description: '食材 ID',
      },
    },
    required: ['ingredient_id'],
  },
  async execute(args: Record<string, any>) {
    const items = await getByIndex('nutrition_data', 'by_ingredient_id', args.ingredient_id)

    // Also fetch the ingredient name for context
    const ingredient = await getById('ingredients', args.ingredient_id)

    return {
      ingredient_id: args.ingredient_id,
      ingredient_name: ingredient?.name ?? '未知',
      items: items || [],
      total: (items || []).length,
    }
  },
}

// ============================================================
// 工具 5：update_nutrition
// ============================================================

const update_nutrition: ToolDefinition = {
  name: 'update_nutrition',
  description: '批量更新指定食材的营养数据。先删除该食材所有现有营养记录，再插入新数据。整个过程在单个事务中完成。每次最多 200 条。',
  parameters: {
    type: 'object',
    properties: {
      ingredient_id: {
        type: 'integer',
        description: '食材 ID',
      },
      nutrients: {
        type: 'array',
        description: '营养数据列表，每项包含 nutrient_name（营养素名）、value_per_100g（每 100g 含量）、unit（单位）',
        items: {
          type: 'object',
          properties: {
            nutrient_name: { type: 'string', description: '营养素名称，如 能量、蛋白质、脂肪' },
            value_per_100g: { type: 'number', description: '每 100g 含量数值' },
            unit: { type: 'string', description: '单位，如 kcal、g、mg、μg' },
          },
          required: ['nutrient_name', 'value_per_100g', 'unit'],
        },
      },
    },
    required: ['ingredient_id', 'nutrients'],
  },
  async execute(args: Record<string, any>) {
    const ingredientId = args.ingredient_id
    const nutrients: any[] = args.nutrients || []

    if (nutrients.length > 200) {
      return { error: `营养数据条数 ${nutrients.length} 超过最大限制 200` }
    }

    const db = await getDb()
    const tx = db.transaction('nutrition_data', 'readwrite')
    const store = tx.store

    // Delete existing records for this ingredient
    const index = store.index('by_ingredient_id')
    const existing = await index.getAll(ingredientId)
    for (const item of existing) {
      await store.delete(item.id)
    }

    // Insert new records
    const inserted: number[] = []
    for (const n of nutrients) {
      const key = await store.add({
        ingredient_id: ingredientId,
        nutrient_name: n.nutrient_name,
        value_per_100g: n.value_per_100g,
        unit: n.unit,
        is_verified: true,
        source: 'agent',
        created_at: new Date().toISOString(),
      })
      inserted.push(key as number)
    }

    await tx.done

    return {
      ingredient_id: ingredientId,
      deleted: existing.length,
      inserted: inserted.length,
      nutrients: nutrients,
    }
  },
}

// ============================================================
// 工具 6：read_statistics
// ============================================================

const read_statistics: ToolDefinition = {
  name: 'read_statistics',
  description: '统计各实体表的数据量。返回食材、商品、菜谱、商家、价格记录等核心表的记录数。',
  parameters: {
    type: 'object',
    properties: {},
  },
  async execute() {
    const stores = [
      'ingredients',
      'products',
      'recipes',
      'merchants',
      'product_records',
      'product_barcodes',
      'nutrition_data',
      'recipe_ingredients',
      'ingredient_hierarchy',
      'entity_unit_overrides',
      'entity_densities',
      'blacklist_groups',
      'meal_recommendations',
      'units',
      'unit_conversions',
    ]

    const counts: Record<string, number> = {}
    for (const store of stores) {
      try {
        counts[store] = await countAll(store)
      } catch {
        counts[store] = -1
      }
    }

    return { counts }
  },
}

// ============================================================
// 工具 7：batch_update
// ============================================================

const batch_update: ToolDefinition = {
  name: 'batch_update',
  description: '批量更新指定 store 中多条记录的字段值。每次最多 50 条，整个操作在单个事务中完成。注意：本工具只能更新已有记录，不能新增。',
  parameters: {
    type: 'object',
    properties: {
      store: {
        type: 'string',
        description: '数据表名称，如 ingredients、products、recipes、merchants 等。注意：不能用 nutrition_data（请用 update_nutrition 工具）',
      },
      updates: {
        type: 'array',
        description: '更新列表，每项包含 id（记录主键）和 fields（要更新的字段键值对）',
        items: {
          type: 'object',
          properties: {
            id: { type: 'integer', description: '记录主键 ID' },
            fields: {
              type: 'object',
              description: '要更新的字段键值对',
              additionalProperties: true,
            },
          },
          required: ['id', 'fields'],
        },
      },
    },
    required: ['store', 'updates'],
  },
  async execute(args: Record<string, any>) {
    const storeName = args.store
    const updates: any[] = args.updates || []

    if (updates.length > 50) {
      return { error: `更新条数 ${updates.length} 超过最大限制 50` }
    }

    if (storeName === 'nutrition_data') {
      return { error: '请使用 update_nutrition 工具更新营养数据' }
    }

    const db = await getDb()
    const tx = db.transaction(storeName, 'readwrite')
    const store = tx.store
    const results: any[] = []

    for (const u of updates) {
      const existing = await store.get(u.id)
      if (!existing) {
        results.push({ id: u.id, status: 'not_found' })
        continue
      }
      const updated = {
        ...existing,
        ...u.fields,
        id: u.id,
        updated_at: new Date().toISOString(),
      }
      await store.put(updated)
      results.push({ id: u.id, status: 'updated' })
    }

    await tx.done

    return {
      store: storeName,
      attempted: updates.length,
      updated: results.filter((r) => r.status === 'updated').length,
      not_found: results.filter((r) => r.status === 'not_found').length,
      results,
    }
  },
}

// ============================================================
// 工具注册表
// ============================================================

export const TOOLS: ToolDefinition[] = [
  read_products,
  read_ingredients,
  read_recipes,
  read_nutrition,
  update_nutrition,
  read_statistics,
  batch_update,
]

/** 按名称查找工具定义 */
export function getToolByName(name: string): ToolDefinition | undefined {
  return TOOLS.find((t) => t.name === name)
}
