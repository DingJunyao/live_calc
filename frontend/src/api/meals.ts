// api/meals.ts
import { api } from './client'

export interface NutritionPerServing {
  calories: number
  protein_g: number
  carbs_g: number
  fat_g: number
}

export interface RecipeBrief {
  id: number
  name: string
  category?: string
  images?: string[]
  servings: number
  cost_estimate?: number
  nutrition_per_serving?: NutritionPerServing | null
}

export interface MealRecommendation {
  meal_type: 'breakfast' | 'lunch' | 'dinner'
  recipe: RecipeBrief | null
  is_current_meal: boolean
}

export interface DailyTotals {
  cost?: number
  calories?: number
  protein_g?: number
  carbs_g?: number
  fat_g?: number
  refresh_counts?: Record<string, number>
}

export interface DailyRecommendationsResponse {
  status: 'ready' | 'not_generated' | 'generating'
  date: string
  recommendations: MealRecommendation[]
  totals?: DailyTotals
  /** 当前正在后台刷新的餐类 */
  refreshing_meals?: string[]
}

/** 获取今日三餐推荐（轻量，不触发计算） */
export async function getDailyRecommendations(): Promise<DailyRecommendationsResponse> {
  return api.get('/meals/recommendations') as any
}

/** 触发后台生成今日推荐 */
export async function triggerRecommendationGeneration(): Promise<DailyRecommendationsResponse> {
  return api.post('/meals/recommendations/generate') as any
}

/** 刷新某一餐推荐 */
export async function refreshMealRecommendation(
  mealType: string
): Promise<DailyRecommendationsResponse> {
  return api.post('/meals/recommendations/refresh', {
    meal_type: mealType,
  }) as any
}
