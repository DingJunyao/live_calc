// 食材层级回退解析模块 — 纯函数，不依赖 IndexedDB。
// 沿食材层级关系（FALLBACK > SUBSTITUTABLE > CONTAINS）查找可用的价格来源。

export interface HierarchyRelation {
  id?: number
  parent_id: number
  child_id: number
  relation_type: string  // 'FALLBACK' | 'SUBSTITUTABLE' | 'CONTAINS'
  strength: number
}

export interface ResolveInput {
  ingredient_id: number
  hierarchies: HierarchyRelation[]
  products: Array<{ id: number; ingredient_id: number }>
  price_records: Array<{ product_id: number; price: number; quantity: number; recorded_at: string }>
  max_depth?: number
}

export interface ResolveResult {
  ingredient_id: number
  resolved: boolean
  path: Array<{ ingredient_id: number; relation_type: string }>
  product_id?: number
}

/**
 * 沿食材层级关系查找价格来源。
 *
 * 遍历优先级：FALLBACK > SUBSTITUTABLE > CONTAINS
 * 最大深度：5（默认）
 *
 * 对每个父级食材：
 * 1. 检查是否有带价格记录的商品
 * 2. 有则返回该父级的商品
 * 3. 无则递归进入父级的父级
 */
export function resolveHierarchy(input: ResolveInput): ResolveResult | null {
  const { ingredient_id, hierarchies, products, price_records, max_depth = 5 } = input
  return resolveRecursive(ingredient_id, hierarchies, products, price_records, max_depth, 0, [])
}

function resolveRecursive(
  ingredientId: number,
  hierarchies: HierarchyRelation[],
  products: Array<{ id: number; ingredient_id: number }>,
  priceRecords: Array<{ product_id: number; price: number; quantity: number; recorded_at: string }>,
  maxDepth: number,
  depth: number,
  path: Array<{ ingredient_id: number; relation_type: string }>,
): ResolveResult | null {
  if (depth >= maxDepth) return null

  // 查找该食材的父级，按关系类型优先级排序
  const parents = hierarchies
    .filter(h => h.child_id === ingredientId)
    .sort((a, b) => {
      const order: Record<string, number> = { FALLBACK: 0, SUBSTITUTABLE: 1, CONTAINS: 2 }
      return (order[a.relation_type] ?? 99) - (order[b.relation_type] ?? 99)
    })

  for (const parent of parents) {
    // 检查父级是否有带价格的商品
    const parentProducts = products.filter(p => p.ingredient_id === parent.parent_id)
    for (const pp of parentProducts) {
      const hasPrice = priceRecords.some(r => r.product_id === pp.id)
      if (hasPrice) {
        return {
          ingredient_id: ingredientId,
          resolved: true,
          path: [...path, { ingredient_id: parent.parent_id, relation_type: parent.relation_type }],
          product_id: pp.id,
        }
      }
    }

    // 递归进入该父级
    const result = resolveRecursive(
      parent.parent_id, hierarchies, products, priceRecords,
      maxDepth, depth + 1,
      [...path, { ingredient_id: parent.parent_id, relation_type: parent.relation_type }],
    )
    if (result) return result
  }

  return null
}
