/** 菜谱相关类型定义 */

export interface CostHistoryRecord {
  id: number
  recipe_id: number
  recipe_name: string
  total_cost: number
  recorded_at: number  // Unix 时间戳（秒）
  exchange_rate: number
}
