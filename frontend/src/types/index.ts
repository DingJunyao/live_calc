// types/index.ts

export interface UnitPreference {
  id: number
  name: string
  abbreviation: string
}

export interface UnitPreferences {
  energy_unit: string | null
  mass_unit: UnitPreference | null
  volume_unit: UnitPreference | null
  price_unit: UnitPreference | null
}

export interface User {
  id: number
  username: string
  email: string
  phone: string | null
  is_admin: boolean
  is_active: boolean
  email_verified: boolean
  avatar: string | null
  nickname: string | null
  created_at: string | null
  nutrition_goals: Record<string, number> | null
  daily_budget: number | null
  unit_preferences: UnitPreferences | null
  region_id: number | null
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  invite_code?: string
}

export interface PriceRecord {
  id: number
  product_name: string
  price: number
  quantity: number
  unit: string
  merchant_name?: string
  record_date: string
  created_at: string
}

export interface Recipe {
  id: number
  name: string
  description?: string
  category?: string
  difficulty?: string
  cooking_time?: number
  servings?: number
  estimated_cost?: number
  calories?: number
  image_url?: string
  created_at?: string
}

export interface RecipeIngredient {
  id: number
  ingredient_name: string
  quantity: number
  unit: string
}

// 管理员相关类型
export interface AdminStats {
  users: number
  products: number
  recipes: number
  merchants: number
}

export interface InviteCode {
  id: number
  code: string
  created_by: number
  used: boolean
  created_at: string
  expires_at: string | null
}

export interface Unit {
  id: number
  name: string
  abbreviation: string
  plural_form: string | null
  unit_type: string
  unit_system: string | null // metric/market/imperial/count/vague
  si_factor: number | null
  is_si_base: boolean
  is_common: boolean
  display_order: number
  default_estimate: number | null
  base_unit_id: number | null
}

export interface UnitConversion {
  id: number
  from_unit_id: number
  to_unit_id: number
  conversion_factor: number
  formula: string | null
  is_bidirectional: boolean
  precision: number
  from_unit: Unit
  to_unit: Unit
}

export interface EntityUnitOverride {
  id: number
  entity_type: string
  entity_id: number
  unit_name: string
  base_unit_id: number | null
  conversion_factor: number | null
  weight_per_unit: number | null
  weight_unit_id: number | null
  is_default: boolean
  source: string | null
}

export interface UnmappedUnitItem {
  unit_id: number
  unit_name: string
  usage_count: number
}

export interface EntityDensity {
  id: number
  entity_type: string
  entity_id: number
  density: number // kg/m³
  temperature: number | null
  condition: string | null
  source: string | null
  confidence: number
}
