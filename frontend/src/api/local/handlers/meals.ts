// Meals handler — 餐食推荐，编排 IndexedDB 数据加载并调用推荐算法。

import { getDb, getAll, getByIndex, addOne, putOne, deleteOne } from '../database'
import { recommend, type MealRecipe, type MealRecommendation } from '../business/mealRecommender'
import { resolveHierarchy } from '../business/hierarchyResolver'

// ============================================================
// 内部辅助
// ============================================================

function getTodayDate(): string {
  return new Date().toISOString().split('T')[0]
}

async function getTodayRecommendationsFromDb(): Promise<any[]> {
  const all = await getAll('meal_recommendations')
  const today = getTodayDate()
  return all.filter((r: any) => r.date === today)
}

/** 获取被禁用的食材 ID 列表（通过黑名单分组订阅）。 */
async function getBlacklistedIngredientIds(): Promise<number[]> {
  const db = await getDb()
  const subscriptions = await getAll('blacklist_subscriptions')
  const groupIds = subscriptions.map((s: any) => s.group_id)
  if (groupIds.length === 0) return []

  const allGroupIngredients = await getAll('blacklist_group_ingredients')
  const ids = allGroupIngredients
    .filter((gi: any) => groupIds.includes(gi.group_id))
    .map((gi: any) => gi.ingredient_id)
  return [...new Set(ids)]
}

/** 加载所有菜谱并转换为 MealRecipe 格式。 */
async function loadRecipes(): Promise<MealRecipe[]> {
  const all = await getAll('recipes')
  return all
    .filter((r: any) => r.is_active !== false)
    .map((r: any) => ({
      id: r.id,
      name: r.name || '',
      category: r.category || undefined,
      cost_estimate: r.cost_estimate != null ? Number(r.cost_estimate) : undefined,
      calories_per_serving: r.calories_per_serving != null ? Number(r.calories_per_serving) : undefined,
      protein_per_serving: r.protein_per_serving != null ? Number(r.protein_per_serving) : undefined,
    }))
}

// ============================================================
// 推荐生成
// ============================================================

const MEAL_TYPES: Array<'breakfast' | 'lunch' | 'dinner'> = ['breakfast', 'lunch', 'dinner']

async function loadSupportingData() {
  const [
    products,
    priceRecords,
    hierarchies,
    blacklistedIngredientIds,
  ] = await Promise.all([
    getAll('products'),
    getAll('product_records'),
    getAll('ingredient_hierarchy'),
    getBlacklistedIngredientIds(),
  ])

  return {
    products: products
      .filter((p: any) => p.is_active !== false)
      .map((p: any) => ({ id: p.id, ingredient_id: p.ingredient_id })),
    price_records: priceRecords.map((r: any) => ({
      product_id: r.product_id,
      price: r.price ?? r.unit_price ?? 0,
      quantity: r.quantity ?? 1,
      recorded_at: r.recorded_at || '',
    })),
    hierarchies,
    blacklisted_ingredient_ids: blacklistedIngredientIds,
  }
}

// ============================================================
// Handlers
// ============================================================

/**
 * GET /meals/recommendations
 * 获取今日推荐（从缓存读取，无缓存则自动生成）。
 */
export async function getRecommendations(_params: Record<string, string>, _query?: any): Promise<any> {
  const today = getTodayDate()
  const cached = await getTodayRecommendationsFromDb()

  if (cached.length > 0) {
    return {
      date: today,
      recommendations: MEAL_TYPES.map(mt => {
        const found = cached.find((c: any) => c.meal_type === mt)
        return found
          ? {
              meal_type: mt,
              recipe: found.recipe_id
                ? {
                    id: found.recipe_id,
                    name: found.recipe_name,
                    category: found.recipe_category,
                    cost_estimate: found.cost_estimate,
                    calories_per_serving: found.calories_per_serving,
                    protein_per_serving: found.protein_per_serving,
                  }
                : null,
            }
          : { meal_type: mt, recipe: null }
      }),
    }
  }

  // 无缓存，自动生成
  return (await generateAll()) as any
}

/**
 * POST /meals/recommendations/generate
 * 生成今日三餐推荐。
 */
export async function generate(_params: Record<string, string>, _data?: any): Promise<any> {
  return await generateAll()
}

/**
 * POST /meals/recommendations/refresh
 * 刷新单餐推荐。请求体: { meal_type: 'breakfast' | 'lunch' | 'dinner' }
 */
export async function refresh(_params: Record<string, string>, data?: any): Promise<any> {
  const mealType: string = data?.meal_type
  if (!mealType || !MEAL_TYPES.includes(mealType as any)) {
    throw { status: 400, message: '无效的餐次类型，请指定 breakfast、lunch 或 dinner' }
  }

  const recipes = await loadRecipes()
  const support = await loadSupportingData()
  const todayRecs = await getTodayRecommendationsFromDb()
  // 排除今天其它餐已用的菜谱（不排除当前正在刷新的餐次）
  const todayRecipeIds = todayRecs
    .filter((r: any) => r.meal_type !== mealType && r.recipe_id != null)
    .map((r: any) => r.recipe_id)

  const result = recommend({
    recipes,
    today_recipes: todayRecipeIds,
    meal_type: mealType as 'breakfast' | 'lunch' | 'dinner',
    hierarchies: support.hierarchies,
    products: support.products,
    price_records: support.price_records,
    blacklisted_ingredient_ids: support.blacklisted_ingredient_ids,
  })

  // 删除旧的该餐推荐并写入新的
  const today = getTodayDate()
  const existing = todayRecs.find((r: any) => r.meal_type === mealType)
  if (existing) {
    await deleteOne('meal_recommendations', existing.id)
  }

  await saveRecommendation(today, result)

  return {
    date: today,
    recommendations: [result],
  }
}

// ============================================================
// 内部函数
// ============================================================

async function generateAll(): Promise<any> {
  const today = getTodayDate()
  const recipes = await loadRecipes()
  const support = await loadSupportingData()

  // 删除今日旧推荐
  const existing = await getTodayRecommendationsFromDb()
  for (const rec of existing) {
    await deleteOne('meal_recommendations', rec.id)
  }

  const todayRecipeIds: number[] = []
  const results: MealRecommendation[] = []

  for (const mealType of MEAL_TYPES) {
    const result = recommend({
      recipes,
      today_recipes: todayRecipeIds,
      meal_type: mealType,
      hierarchies: support.hierarchies,
      products: support.products,
      price_records: support.price_records,
      blacklisted_ingredient_ids: support.blacklisted_ingredient_ids,
    })

    if (result.recipe) {
      todayRecipeIds.push(result.recipe.id)
    }

    await saveRecommendation(today, result)
    results.push(result)
  }

  return {
    date: today,
    recommendations: results,
  }
}

async function saveRecommendation(date: string, rec: MealRecommendation): Promise<void> {
  await addOne('meal_recommendations', {
    date,
    meal_type: rec.meal_type,
    recipe_id: rec.recipe?.id ?? null,
    recipe_name: rec.recipe?.name ?? null,
    recipe_category: rec.recipe?.category ?? null,
    cost_estimate: rec.recipe?.cost_estimate ?? null,
    calories_per_serving: rec.recipe?.calories_per_serving ?? null,
    protein_per_serving: rec.recipe?.protein_per_serving ?? null,
    created_at: new Date().toISOString(),
  })
}
