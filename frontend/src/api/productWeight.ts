// 商品价格权重的用户覆盖 API client
import api from './client'

export interface EffectiveWeight {
  product_id: number
  effective_weight: number
  global_weight: number
  override_weight: number | null
  source: 'override' | 'global'
}

/** 获取该商品对当前用户的生效权重（覆盖 > 全局） */
export const getProductMyWeight = (productId: number) =>
  api.get(`/products/${productId}/my-weight`)

/** 设置/更新当前用户对该商品的权重覆盖（0-100） */
export const setProductMyWeight = (productId: number, weight: number) =>
  api.put(`/products/${productId}/my-weight`, { weight })

/** 删除当前用户对该商品的权重覆盖（回退到全局） */
export const deleteProductMyWeight = (productId: number) =>
  api.delete(`/products/${productId}/my-weight`)
