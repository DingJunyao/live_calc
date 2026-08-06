// 餐食推荐模块 — 纯函数，不依赖 IndexedDB。
// 基于菜谱成本、营养和多样性评分，为每餐推荐合适的菜谱。

export interface MealRecipe {
  id: number
  name: string
  category?: string
  cost_estimate?: number
  calories_per_serving?: number
  protein_per_serving?: number
}

export interface MealRecommendation {
  meal_type: 'breakfast' | 'lunch' | 'dinner'
  recipe: MealRecipe | null
}

export interface RecommenderInput {
  recipes: MealRecipe[]
  today_recipes: number[]       // 今天已用过的菜谱 ID
  meal_type: 'breakfast' | 'lunch' | 'dinner'
  hierarchies: any[]
  products: Array<{ id: number; ingredient_id: number }>
  price_records: Array<{ product_id: number; price: number; quantity: number; recorded_at: string }>
  blacklisted_ingredient_ids: number[]
}

/**
 * 为指定餐次推荐菜谱。
 *
 * 算法：
 * 1. 排除今天已用过的菜谱
 * 2. 对候选菜谱评分：
 *    - 成本分：越便宜越好
 *    - 营养分：蛋白质含量高的更优
 *    - 基础分：50
 * 3. 加权随机选取（score + 0.05 防零权重）
 * 4. 返回选中的菜谱
 */
export function recommend(input: RecommenderInput): MealRecommendation {
  const { recipes, today_recipes, meal_type, blacklisted_ingredient_ids = [] } = input

  // 排除今天已用过的菜谱
  let candidates = recipes.filter(r => !today_recipes.includes(r.id))

  // 黑名单过滤：因未传入菜谱-原料关联数据，此处仅保留接口
  // （完整实现需检查 recipe_ingredients 以精确过滤含黑名单原料的菜谱）

  if (candidates.length === 0) {
    return { meal_type, recipe: null }
  }

  // 对候选菜谱评分
  const scored = candidates.map(recipe => {
    let score = 50 // 基础分

    // 成本分：便宜的菜谱更适合日常
    if (recipe.cost_estimate != null) {
      const maxCost = Math.max(...candidates.map(c => c.cost_estimate ?? 0), 1)
      score += (1 - (recipe.cost_estimate / maxCost)) * 30
    }

    // 营养分：蛋白质含量高的更均衡
    if (recipe.protein_per_serving != null) {
      score += Math.min(recipe.protein_per_serving / 20, 1) * 20
    }

    return { recipe, score: Math.max(score, 0) }
  })

  // 加权随机选取
  const totalWeight = scored.reduce((s, item) => s + item.score + 0.05, 0)
  let random = Math.random() * totalWeight

  for (const item of scored) {
    random -= (item.score + 0.05)
    if (random <= 0) {
      return { meal_type, recipe: item.recipe }
    }
  }

  // 兜底
  return { meal_type, recipe: scored[0]?.recipe ?? null }
}
