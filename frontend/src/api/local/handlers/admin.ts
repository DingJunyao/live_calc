// Admin handler — system configuration and statistics.

import { getDb, countAll } from '../database'

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

// ============================================================
// Images (unused image scanning/cleanup)
// ============================================================

export async function scanImages(): Promise<any> {
  return {
    stats: { total_images: 0, used_images: 0, unused_images: 0, used_size: 0, unused_size: 0 },
    message: '扫描完成',
  }
}

export async function getUnusedImages(): Promise<any> {
  return {
    stats: { total_images: 0, used_images: 0, unused_images: 0, used_size: 0, unused_size: 0 },
    groups: { never_used: [], '180d': [], '90d': [], '60d': [], '30d': [], recent: [] },
  }
}

// ============================================================
// Email config (SMTP + templates)
// ============================================================

export async function getSmtpConfig(): Promise<any> {
  return {
    host: '',
    port: 587,
    username: '',
    use_tls: true,
    use_ssl: false,
    from_address: '',
    from_name: '',
    enabled: false,
  }
}

export async function updateSmtpConfig(_params: Record<string, string>, data?: any): Promise<any> {
  return data || { enabled: false }
}

export async function listTemplates(): Promise<any> {
  return []
}

export async function getEmailTemplate(params: Record<string, string>): Promise<any> {
  return {
    key: params.key,
    name: '邮件模板',
    subject: '通知',
    body_html: '<p>内容</p>',
    description: '',
  }
}

// ============================================================
// Translation / AI config
// ============================================================

export async function getTranslationConfig(): Promise<any> {
  return {
    ai: {
      providers: {
        claude_code: { enabled: false },
        openai: { enabled: false, base_url: 'https://api.openai.com/v1', api_key: '', model: 'gpt-4o-mini' },
        anthropic: { enabled: false, base_url: 'https://api.anthropic.com', api_key: '', model: 'claude-sonnet-4-6' },
      },
    },
    machine: {
      providers: {
        baidu: { enabled: false, appid: '', secret: '' },
        aliyun: { enabled: false, access_key_id: '', access_key_secret: '' },
        deepl: { enabled: false, auth_key: '' },
      },
    },
  }
}

export async function updateTranslationConfig(_params: Record<string, string>, data?: any): Promise<any> {
  const config = data?.config || data
  await setConfigValue('translation_config', config)
  return config
}

export async function testTranslationConnection(_params: Record<string, string>, data?: any): Promise<any> {
  // Local mode: no real provider to test, always return success
  return { provider: data?.provider || 'unknown', ok: true, detail: '本地模式跳过连接测试' }
}
