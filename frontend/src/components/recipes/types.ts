/** 菜谱详情数据类型 */
export interface RecipeDetail {
  id: number
  name: string
  description?: string
  category?: string
  difficulty?: string
  cooking_steps?: (string | CookingStepContent)[]
  total_time_minutes?: number
  servings?: number
  tips?: string[]
  images?: string[]
  result_ingredient_id?: number
  created_at?: string
  updated_at?: string
  source?: string
  ingredients?: RecipeIngredient[]
}

export interface CookingStepContent {
  content: string
  duration_minutes?: number
  tips?: string
}

export interface RecipeIngredient {
  id: number
  ingredient_id: number
  name: string
  quantity?: number | string
  quantity_range?: { min: number; max: number }
  original_quantity?: string
  unit?: string
  is_optional?: boolean
  note?: string
}

export interface IngredientOption {
  id: number
  name: string
  aliases?: string[]
}

export interface UnitOption {
  id: number
  name: string
  abbreviation: string
}

/** 原料编辑行数据 */
export interface IngredientEditRow {
  tempId: number
  ingredient_name: string
  ingredient_id: number | null
  quantity: string
  quantity_min: string
  quantity_max: string
  unit_id: number | null
  unit_name: string
  is_optional: boolean
  note: string
}

/** 步骤编辑行数据 */
export interface StepEditRow {
  tempId: number
  content: string
  duration_minutes: string
  tips: string
}
