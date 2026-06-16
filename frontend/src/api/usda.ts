// frontend/src/api/usda.ts
import api from './client'

// === 用户：搜索 / 详情 / 匹配 ===
export const searchUsdaFoods = (q: string, limit = 50) =>
  api.get('/usda/search', { params: { q, limit } })

export const getUsdaFood = (fdcId: number) =>
  api.get(`/usda/${fdcId}`)

export const matchIngredient = (ingredientId: number, fdcId: number) =>
  api.post(`/usda/match/ingredient/${ingredientId}`, { fdc_id: fdcId })

export const matchProduct = (productId: number, fdcId: number) =>
  api.post(`/usda/match/product/${productId}`, { fdc_id: fdcId })

// === 后台：配置 ===
export const getTranslationConfig = () => api.get('/admin/translation-config')
export const putTranslationConfig = (config: Record<string, any>) =>
  api.put('/admin/translation-config', { config })
export const testTranslationConnection = (provider: string) =>
  api.post('/admin/translation-config/test', { provider })

// === 后台：USDA 数据 ===
export const getUsdaStatistics = () => api.get('/admin/usda/statistics')
export const getUnmappedNutrients = () => api.get('/admin/usda/unmapped-nutrients')
export const downloadUsda = (datasets?: string) =>
  api.post('/admin/usda/download', null, { params: datasets ? { datasets } : {} })
export const uploadUsda = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/admin/usda/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000, // 上传大文件用长超时
  })
}
export const translateUsda = (provider: string) =>
  api.post('/admin/usda/translate', { provider })
export const getUsdaTask = () => api.get('/admin/usda/task')
