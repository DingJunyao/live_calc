// stores/meals.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getDailyRecommendations,
  refreshMealRecommendation,
  type DailyRecommendationsResponse,
  type MealRecommendation,
  type DailyTotals,
} from '@/api/meals'

export const useMealsStore = defineStore('meals', () => {
  const date = ref('')
  const recommendations = ref<MealRecommendation[]>([])
  const totals = ref<DailyTotals | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const refreshLoading = ref<Record<string, boolean>>({})

  /** 加载今日推荐 */
  async function loadRecommendations() {
    loading.value = true
    error.value = null
    try {
      const data = await getDailyRecommendations()
      date.value = data.date
      recommendations.value = data.recommendations
      totals.value = data.totals || null
    } catch (e: any) {
      error.value = e.userMessage || '加载推荐失败'
    } finally {
      loading.value = false
    }
  }

  /** 刷新某一餐 */
  async function refreshMeal(mealType: string) {
    refreshLoading.value = { ...refreshLoading.value, [mealType]: true }
    try {
      const data = await refreshMealRecommendation(mealType)
      date.value = data.date
      recommendations.value = data.recommendations
      totals.value = data.totals || null
    } catch (e: any) {
      throw e
    } finally {
      refreshLoading.value = { ...refreshLoading.value, [mealType]: false }
    }
  }

  return {
    date,
    recommendations,
    totals,
    loading,
    error,
    refreshLoading,
    loadRecommendations,
    refreshMeal,
  }
})
