// Admin handler — system configuration and statistics.

import { getDb, getAll, getById, countAll } from '../database'

async function getConfigValue(key: string): Promise<any> {
  const db = await getDb()
  const val = await db.get('system_config', key)
  return val?.value
}

async function setConfigValue(key: string, value: any): Promise<void> {
  const db = await getDb()
  await db.put('system_config', { key, value })
}

export async function getMapConfig(): Promise<any> {
  const config = await getConfigValue('map_config')
  return config || {
    map_enabled: true,
    default_map: 'amap',
    available_maps: ['amap', 'baidu', 'tencent', 'leaflet'],
    map_api_keys: {},
  }
}

export async function updateMapConfig(_params: Record<string, string>, data?: any): Promise<any> {
  await setConfigValue('map_config', data)
  return data
}

export async function getConfig(_params: Record<string, string>, query?: any): Promise<any> {
  const key = query?.key
  if (key) {
    return { key, value: await getConfigValue(key) }
  }
  const db = await getDb()
  const all = await db.getAll('system_config')
  const map: Record<string, any> = {}
  for (const item of all) {
    map[item.key] = item.value
  }
  return map
}

export async function getStats(): Promise<any> {
  const [products, records, ingredients, recipes, merchants, units, categories] = await Promise.all([
    countAll('products'),
    countAll('product_records'),
    countAll('ingredients'),
    countAll('recipes'),
    countAll('merchants'),
    countAll('units'),
    countAll('ingredient_categories'),
  ])
  return {
    total_products: products,
    total_price_records: records,
    total_ingredients: ingredients,
    total_recipes: recipes,
    total_merchants: merchants,
    total_units: units,
    total_categories: categories,
  }
}

export async function getStorageConfig(): Promise<any> {
  const config = await getConfigValue('storage_config')
  return config || {
    provider: 'local',
    base_path: '/static',
    config: {},
  }
}

export async function updateStorageConfig(_params: Record<string, string>, data?: any): Promise<any> {
  await setConfigValue('storage_config', data)
  return data
}

export async function listEmailTemplates(): Promise<any> {
  return { items: [], total: 0 }
}

export async function updateEmailTemplate(params: Record<string, string>, data?: any): Promise<any> {
  return { ...data, key: params.key }
}

export async function getMapApiKeys(): Promise<any> {
  const config = await getConfigValue('map_api_keys')
  return config || {}
}

export async function updateMapApiKeys(_params: Record<string, string>, data?: any): Promise<any> {
  await setConfigValue('map_api_keys', data)
  return data
}
