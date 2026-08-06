// Meals handler — 餐食推荐，编排 IndexedDB 数据加载并调用推荐算法。

import { getDb, getAll, getByIndex, addOne, putOne, deleteOne, getById } from '../database'
import { recommend, type MealRecipe, type MealRecommendation } from '../business/mealRecommender'
import { resolveHierarchy } from '../business/hierarchyResolver'
import { resolveImageUrl } from '@/utils/image'
import * as recipes from './recipes'

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
    const cachedResults: MealRecommendation[] = MEAL_TYPES.map(mt => {
      const found = cached.find((c: any) => c.meal_type === mt)
      return {
        meal_type: mt,
        recipe: found?.recipe_id ? { id: found.recipe_id } : null,
      }
    })
    return await buildResponse(cachedResults)
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

  return await buildResponse([result])
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

  return await buildResponse(results)
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

// ============================================================
// Response building: enrich recipe brief with cost + nutrition
// ============================================================

function getCurrentMeal(): 'breakfast' | 'lunch' | 'dinner' | null {
  const h = new Date().getHours()
  if (h >= 5 && h < 10) return 'breakfast'
  if (h >= 10 && h < 14) return 'lunch'
  if (h >= 14 && h < 22) return 'dinner'
  return null
}

function round1(v: number): number { return Math.round(v * 10) / 10 }
function round2(v: number): number { return Math.round(v * 100) / 100 }

/** Compute full RecipeBrief (cost + nutrition + images) for one recipe. */
async function buildRecipeBrief(recipeId: number): Promise<any | null> {
  const recipe = await getById('recipes', recipeId)
  if (!recipe) return null
  const servings = recipe.servings || 1

  let cost_estimate: number | null = null
  let nutrition_per_serving: { calories: number; protein_g: number; carbs_g: number; fat_g: number } | null = null

  try {
    const cost = await recipes.getRecipeCost({ id: String(recipeId) })
    if (cost?.cost_per_serving != null && Number.isFinite(cost.cost_per_serving)) {
      cost_estimate = round2(cost.cost_per_serving)
    }
  } catch { /* no price records — leave null */ }

  try {
    const nutrition = await recipes.getRecipeNutrition({ id: String(recipeId) })
    // getRecipeNutrition returns totals for the whole recipe; divide by servings
    if (servings > 0 && nutrition) {
      nutrition_per_serving = {
        calories: round1((nutrition.calories || 0) / servings),
        protein_g: round1((nutrition.protein || 0) / servings),
        carbs_g: round1((nutrition.carbohydrate || 0) / servings),
        fat_g: round1((nutrition.fat || 0) / servings),
      }
    }
  } catch { /* no nutrition data — leave null */ }

  return {
    id: recipeId,
    name: recipe.name || '',
    category: recipe.category || undefined,
    images: recipe.images || [],
    image_urls: (recipe.images || []).map(resolveImageUrl),
    servings,
    cost_estimate,
    nutrition_per_serving,
  }
}

/** Build the full daily-recommendations response: enrich each recipe with
 *  cost/nutrition/images, add is_current_meal, and compute daily totals. */
async function buildResponse(results: MealRecommendation[]): Promise<any> {
  const today = getTodayDate()
  const currentMeal = getCurrentMeal()
  const recommendations = []
  const totals = { cost: 0, calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }

  for (const r of results) {
    const recipe = r.recipe ? await buildRecipeBrief(r.recipe.id) : null
    recommendations.push({
      meal_type: r.meal_type,
      recipe,
      is_current_meal: r.meal_type === currentMeal,
    })
    if (recipe) {
      if (recipe.cost_estimate != null && Number.isFinite(recipe.cost_estimate)) totals.cost += recipe.cost_estimate
      const n = recipe.nutrition_per_serving
      if (n) {
        totals.calories += Number.isFinite(n.calories) ? n.calories : 0
        totals.protein_g += Number.isFinite(n.protein_g) ? n.protein_g : 0
        totals.carbs_g += Number.isFinite(n.carbs_g) ? n.carbs_g : 0
        totals.fat_g += Number.isFinite(n.fat_g) ? n.fat_g : 0
      }
    }
  }

  return {
    status: 'ready',
    date: today,
    recommendations,
    totals: {
      cost: round2(totals.cost),
      calories: round1(totals.calories),
      protein_g: round1(totals.protein_g),
      carbs_g: round1(totals.carbs_g),
      fat_g: round1(totals.fat_g),
    },
  }
}
