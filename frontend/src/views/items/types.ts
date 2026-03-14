/** 商品/原料详情页类型定义 */

export interface Item {
  id: number
  name: string
  brand?: string
  image_url?: string
  tags?: string[]
  ingredient_name?: string
  ingredient_id?: number
  aliases?: string[]
  created_at: string
  updated_at?: string
  barcodes?: ProductBarcode[]
}

export interface ProductBarcode {
  id: number
  product_id: number
  barcode: string
  barcode_type: string
  is_primary: boolean
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface PriceRecord {
  id: number
  product_id: number
  product_name: string
  merchant_id?: number
  merchant_name?: string
  price: number
  currency: string
  original_quantity: number
  original_unit: string
  standard_quantity: number
  standard_unit: string
  record_type: string
  exchange_rate: number
  recorded_at: string
  notes?: string
}

export interface NutritionData {
  ingredient_id?: number
  product_id?: number
  quantity: number
  unit: string
  base_quantity: number
  nutrition: {
    core_nutrients: Record<string, any>
    all_nutrients: Record<string, any>
  }
  source?: string
  reference_amount?: number
  reference_unit?: string
  match_confidence?: number
}

export interface HierarchyRelation {
  id: number
  parent_id: number
  parent_name: string
  child_id: number
  child_name: string
  relation_type: string
  strength: number
  created_at: string
}

export interface HierarchyRelations {
  parent_relations: HierarchyRelation[]
  child_relations: HierarchyRelation[]
}

export interface Association {
  id: number
  name: string
  brand?: string
  type: 'product' | 'ingredient'
  created_at: string
}
