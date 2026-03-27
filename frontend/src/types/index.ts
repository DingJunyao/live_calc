// types/index.ts

export interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
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
