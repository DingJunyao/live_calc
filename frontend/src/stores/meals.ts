// stores/meals.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getDailyRecommendations,
  triggerRecommendationGeneration,
  refreshMealRecommendation,
  type DailyRecommendationsResponse,
  type MealRecommendation,
  type DailyTotals,
} from '@/api/meals'

/** 轮询间隔（毫秒） */
const POLL_INTERVAL = 2000
/** 最大轮询次数（约 60 秒） */
const MAX_POLLS = 30

export const useMealsStore = defineStore('meals', () => {
  const date = ref('')
  const recommendations = ref<MealRecommendation[]>([])
  const totals = ref<DailyTotals | null>(null)
  const loading = ref(false)
  const generating = ref(false)
  const error = ref<string | null>(null)
  const refreshLoading = ref<Record<string, boolean>>({})

  let _pollTimer: ReturnType<typeof setTimeout> | null = null
  let _pollCount = 0

  /** 清理轮询定时器 */
  function _clearPoll() {
    if (_pollTimer != null) {
      clearTimeout(_pollTimer)
      _pollTimer = null
    }
    _pollCount = 0
  }

  /** 轮询等待推荐就绪（初始生成用） */
  async function _pollUntilReady() {
    _clearPoll()
    generating.value = true
    _pollCount = 0

    return new Promise<void>((resolve, reject) => {
      const poll = async () => {
        try {
          _pollCount++
          const data = await getDailyRecommendations()

          if (data.status === 'ready') {
            _clearPoll()
            generating.value = false
            date.value = data.date
            recommendations.value = data.recommendations
            totals.value = data.totals || null

            // 兜底：初始生成完成后检查是否有残留的后台刷新任务
            const refreshing = data.refreshing_meals || []
            if (refreshing.length > 0) {
              for (const mt of refreshing) {
                refreshLoading.value = { ...refreshLoading.value, [mt]: true }
              }
              await Promise.allSettled(
                refreshing.map((mt) =>
                  _pollRefreshMeal(mt).finally(() => {
                    refreshLoading.value = { ...refreshLoading.value, [mt]: false }
                  })
                )
              )
            }
            resolve()
            return
          }

          if (data.status === 'not_generated') {
            // 生成可能失败了，重新触发
            await triggerRecommendationGeneration()
          }

          // status === 'generating' 或重新触发后继续轮询
          if (_pollCount >= MAX_POLLS) {
            _clearPoll()
            generating.value = false
            error.value = '推荐计算超时，请稍后刷新重试'
            reject(new Error('poll timeout'))
            return
          }

          _pollTimer = setTimeout(poll, POLL_INTERVAL)
        } catch (e: any) {
          _clearPoll()
          generating.value = false
          error.value = e.userMessage || '加载推荐失败'
          reject(e)
        }
      }

      poll()
    })
  }

  /** 轮询等待某一餐刷新完成（不更新 refreshLoading，由调用方管理） */
  function _pollRefreshMeal(mealType: string): Promise<void> {
    const maxPolls = 30
    let count = 0

    return new Promise<void>((resolve, reject) => {
      const poll = async () => {
        try {
          count++
          const data = await getDailyRecommendations()

          if (data.status === 'ready') {
            const stillRefreshing = data.refreshing_meals?.includes(mealType)
            if (!stillRefreshing) {
              // 刷新完成，更新数据
              date.value = data.date
              recommendations.value = data.recommendations
              totals.value = data.totals || null
              resolve()
              return
            }
          }

          if (count >= maxPolls) {
            reject(new Error('刷新超时，请稍后重试'))
            return
          }

          setTimeout(poll, POLL_INTERVAL)
        } catch (e) {
          reject(e)
        }
      }

      poll()
    })
  }

  /** 加载今日推荐（智能路由：有缓存立即返回，无缓存触发后台生成+轮询） */
  async function loadRecommendations() {
    loading.value = true
    error.value = null
    _clearPoll()

    try {
      const data = await getDailyRecommendations()

      if (data.status === 'ready') {
        // 先渲染数据
        date.value = data.date
        recommendations.value = data.recommendations
        totals.value = data.totals || null
        loading.value = false

        // 检查是否有后台刷新任务（页面刷新后恢复状态）
        const refreshing = data.refreshing_meals || []
        if (refreshing.length > 0) {
          for (const mt of refreshing) {
            refreshLoading.value = { ...refreshLoading.value, [mt]: true }
          }
          // 为每个在刷新的餐启动轮询（并行等待）
          await Promise.allSettled(
            refreshing.map((mt) =>
              _pollRefreshMeal(mt).finally(() => {
                refreshLoading.value = { ...refreshLoading.value, [mt]: false }
              })
            )
          )
        }
        return
      }

      // 未生成 → 触发后台生成 + 轮询
      if (data.status === 'not_generated') {
        await triggerRecommendationGeneration()
      }

      loading.value = false
      await _pollUntilReady()
    } catch (e: any) {
      if (error.value) return // poll 已设 error
      error.value = e.userMessage || '加载推荐失败'
      loading.value = false
    }
  }

  /** 刷新某一餐（后台异步模式） */
  async function refreshMeal(mealType: string) {
    refreshLoading.value = { ...refreshLoading.value, [mealType]: true }
    try {
      // 触发后台刷新
      await refreshMealRecommendation(mealType)
      // 轮询等待完成
      await _pollRefreshMeal(mealType)
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
    generating,
    error,
    refreshLoading,
    loadRecommendations,
    refreshMeal,
  }
})
