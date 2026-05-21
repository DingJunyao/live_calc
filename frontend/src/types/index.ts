// types/index.ts

export interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
  is_superuser: boolean
  created_at: string
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
