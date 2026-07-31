// USDA handler — search, detail, match ingredient/product, admin download.
// Data sourced from IndexedDB stores (usda_foods, usda_food_nutrients).

import { getAll, getById, getByIndex, putOne, getDb } from '../database'
import { parseUsdaDataset } from './usdaData'

export async function searchUsda(_params: Record<string, string>, query?: any): Promise<any> {
  const q = query?.q || ''
  const limit = parseInt(query?.limit) || 50

  if (!q.trim()) return []

  const lower = q.toLowerCase()
  const all = await getAll('usda_foods')
  const matched = all.filter((f: any) => {
    const desc = (f.description || '').toLowerCase()
    const descZh = (f.description_zh || '').toLowerCase()
    return desc.includes(lower) || descZh.includes(lower)
  })

  // Sort by relevance — exact prefix match first
  matched.sort((a: any, b: any) => {
    const aDesc = (a.description || '').toLowerCase()
    const bDesc = (b.description || '').toLowerCase()
    const aPrefix = aDesc.startsWith(lower) ? 1 : 0
    const bPrefix = bDesc.startsWith(lower) ? 1 : 0
    if (aPrefix !== bPrefix) return bPrefix - aPrefix
    return (a.description || '').localeCompare(b.description || '')
  })

  const items = matched.slice(0, limit)

  // Attach nutrient counts
  const result: any[] = []
  for (const food of items) {
    const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', food.fdc_id)
    result.push({
      fdc_id: food.fdc_id,
      description: food.description,
      description_zh: food.description_zh || null,
      data_type: food.data_type || 'Foundation',
      nutrient_count: nutrients.length,
      score: food.description?.toLowerCase() === lower ? 100 : Math.round((lower.length / Math.max(food.description?.length || 1, 1)) * 100),
    })
  }

  return result
}

export async function getUsdaFood(params: Record<string, string>): Promise<any> {
  const fdcId = parseInt(params.fdcId)
  const food = await getById('usda_foods', fdcId)
  if (!food) throw { status: 404, message: `USDA food ${fdcId} not found` }

  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)

  return {
    fdc_id: food.fdc_id,
    description: food.description,
    description_zh: food.description_zh || null,
    data_type: food.data_type || 'Foundation',
    nutrients: nutrients.map((n: any) => ({
      name: n.name,
      name_zh: n.name_zh || null,
      amount: n.amount,
      unit_name: n.unit_name,
    })),
  }
}

export async function previewNutrition(_params: Record<string, string>, query?: any): Promise<any> {
  const fdcId = parseInt(query?.fdc_id)
  if (!fdcId) throw { status: 400, message: 'fdc_id is required' }

  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)

  // Build structured nutrition data matching backend matcher output
  const coreNutrients: Record<string, any> = {}
  const allNutrients: any[] = []
  const nutrientDetails: any[] = []

  for (const n of nutrients) {
    const item = {
      name: n.name,
      name_zh: n.name_zh || n.name,
      amount: n.amount,
      unit: n.unit_name,
    }
    allNutrients.push(item)
    nutrientDetails.push(item)

    const key = (n.name_zh || n.name).toLowerCase()
    if (!coreNutrients[key]) {
      coreNutrients[key] = { value: n.amount, unit: n.unit_name }
    }
  }

  return {
    core_nutrients: coreNutrients,
    all_nutrients: allNutrients,
    nutrient_details: nutrientDetails,
  }
}

export async function matchIngredient(params: Record<string, string>, data?: any): Promise<any> {
  const ingredientId = parseInt(params.ingredientId)
  const fdcId = data?.fdc_id
  if (!fdcId) throw { status: 400, message: 'fdc_id is required' }

  // 先读 USDA 营养素（独立读事务）：在写事务内部跨事务 await 会导致写事务被浏览器自动提交，
  // 后续 store.add 抛 TransactionInactiveError。因此读取必须在写事务开启之前完成。
  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)

  const db = await getDb()
  const tx = db.transaction('nutrition_data', 'readwrite')
  const store = tx.store

  // 删除该食材已有的营养数据，并在同一事务内连续写入新数据，保持事务活跃
  const index = store.index('by_ingredient_id')
  const existing = await index.getAll(ingredientId)
  for (const item of existing) {
    await store.delete(item.id)
  }

  // 写入 USDA 营养数据
  for (const n of nutrients) {
    await store.add({
      ingredient_id: ingredientId,
      nutrient_name: n.name_zh || n.name,
      nutrient_id: n.nutrient_id || null,
      // 字段名须与 updateIngredientNutrition 及读端 getIngredientNutrition 一致（amount_per_100g），
      // 否则读端取不到值，UI 显示为 0。
      amount_per_100g: n.amount,
      unit: n.unit_name,
      source: 'usda_manual_match',
      is_verified: true,
      created_at: new Date().toISOString(),
    })
  }
  await tx.done

  return { ingredient_id: ingredientId, fdc_id: fdcId, message: 'USDA 匹配成功（本地模式）' }
}

export async function matchProduct(params: Record<string, string>, data?: any): Promise<any> {
  const productId = parseInt(params.productId)
  const fdcId = data?.fdc_id
  if (!fdcId) throw { status: 400, message: 'fdc_id is required' }

  // Load USDA nutrients
  const nutrients = await getByIndex('usda_food_nutrients', 'by_fdc_id', fdcId)
  const nutritionData = nutrients.map((n: any) => ({
    name: n.name_zh || n.name,
    value: n.amount,
    unit: n.unit_name,
  }))

  // Update product's custom_nutrition_data
  const product = await getById('products', productId)
  if (!product) throw { status: 404, message: `Product ${productId} not found` }

  await putOne('products', {
    ...product,
    id: productId,
    custom_nutrition_data: {
      nutrients: nutritionData,
      source: 'usda_manual_match',
    },
    updated_at: new Date().toISOString(),
  })

  return { product_id: productId, fdc_id: fdcId, message: 'USDA 匹配成功（本地模式）' }
}

export async function downloadUsda(_params: Record<string, string>, _data?: any): Promise<any> {
  // 本地模式无后端，无法联网拉取并处理 USDA 数据集。
  // 不返回 task_id（前端据此判断是否轮询），同步给出说明，避免触发对不存在任务的轮询。
  return { message: '本地模式使用预置 USDA 数据，如需更新请通过「上传 ZIP」导入已处理的 USDA 数据包' }
}

// ---- Admin: USDA statistics / tasks（数据维护中心只读展示） ----
// 本地模式下从 IndexedDB 真实统计，避免数据维护中心控制台刷 404。
export async function getStatistics(): Promise<any> {
  const [foods, nutrients] = await Promise.all([
    getAll('usda_foods'),
    getAll('usda_food_nutrients'),
  ])
  const translated = foods.filter((f: any) => f.description_zh).length
  return {
    total: foods.length,
    nutrients: nutrients.length,
    translated,
  }
}

export async function getUnmappedNutrients(): Promise<any> {
  // 本地模式不维护营养素映射表，直接返回空列表
  return []
}

export async function listTasks(_params: Record<string, string>, query?: any): Promise<any> {
  // 本地模式无 USDA 异步任务记录（下载/上传为同步占位），返回空
  void query
  return []
}

export async function getTask(): Promise<any> {
  return null
}

// ---- Admin: USDA upload / translate（数据维护中心写入与 AI 操作） ----
// 本地模式无真实 USDA 处理管线，这些端点降级为不报错的友好响应。

/**
 * POST /admin/usda/upload — 上传 USDA 数据包（ZIP）。
 * 兼容两种格式：
 *  1) 原始 USDA zip（含 FoundationFoods / SRLegacyFoods 的 JSON）— 与云端一致，用解析器转换；
 *  2) 预处理 zip（含 usda_foods.json / usda_food_nutrients.json）— 直接写入。
 */
export async function uploadUsda(_params: Record<string, string>, data?: any): Promise<any> {
  const file: File | null = data?.get?.('file') ?? null
  if (!file) throw { status: 400, message: '缺少上传文件' }

  const db = await getDb()
  let foods = 0
  let nutrients = 0
  try {
    const { default: JSZip } = await import('jszip')
    const zip = await JSZip.loadAsync(await file.arrayBuffer())

    const foodsFile = zip.file('usda_foods.json')
    const nutFile = zip.file('usda_food_nutrients.json')
    if (foodsFile || nutFile) {
      // 预处理格式：ZIP 内含已拆分的 usda_foods.json / usda_food_nutrients.json，直接写入
      if (foodsFile) {
        const arr = JSON.parse(await foodsFile.async('string'))
        const items: any[] = Array.isArray(arr) ? arr : Object.values(arr)
        const tx = db.transaction('usda_foods', 'readwrite')
        for (const it of items) await tx.store.put(it)
        await tx.done
        foods = items.length
      }
      if (nutFile) {
        const arr = JSON.parse(await nutFile.async('string'))
        const items: any[] = Array.isArray(arr) ? arr : Object.values(arr)
        const tx = db.transaction('usda_food_nutrients', 'readwrite')
        for (const it of items) await tx.store.put(it)
        await tx.done
        nutrients = items.length
      }
    } else {
      // 原始 USDA 格式：取首个 .json，用解析器转成内部结构后批量写入
      const jsonFiles = zip.file(/\.json$/) || []
      if (!jsonFiles.length) throw { status: 400, message: 'ZIP 内未找到 JSON 文件' }
      const raw = JSON.parse(await jsonFiles[0].async('string'))
      const parsed = parseUsdaDataset(raw)
      const BATCH = 200
      for (let i = 0; i < parsed.length; i += BATCH) {
        const batch = parsed.slice(i, i + BATCH)
        const tx = db.transaction(['usda_foods', 'usda_food_nutrients'], 'readwrite')
        const foodStore = tx.objectStore('usda_foods')
        const nutStore = tx.objectStore('usda_food_nutrients')
        const nutIndex = nutStore.index('by_fdc_id')
        for (const f of batch) {
          const fdcId = f.fdc_id
          if (fdcId == null) continue
          foodStore.put({
            fdc_id: fdcId,
            data_type: f.data_type,
            description: f.description,
            description_zh: null,
            publication_date: f.publication_date,
            translate_status: 'pending',
          })
          // 该 fdc_id 的旧营养素（autoIncrement 主键，无法 upsert），先清再写
          let cursor = await nutIndex.openCursor(fdcId)
          while (cursor) {
            await cursor.delete()
            cursor = await cursor.continue()
          }
          for (const n of f.nutrients) {
            nutStore.add({
              fdc_id: fdcId,
              nutrient_no: n.nutrient_no,
              name: n.name,
              name_zh: n.name_zh,
              amount: n.amount,
              unit_name: n.unit_name,
            })
          }
          foods += 1
          nutrients += f.nutrients.length
        }
        await tx.done
        // 批间让出主线程，避免长事务阻塞 UI
        await new Promise((r) => setTimeout(r, 0))
      }
    }
  } catch (e: any) {
    if (e?.status) throw e
    throw { status: 400, message: `解析 USDA 数据包失败：${e?.message || e}` }
  }

  // 不返回 task_id（本地同步完成），避免前端轮询不存在的任务
  return {
    message: `USDA 数据导入完成：食材 ${foods} 条，营养素 ${nutrients} 条`,
    foods,
    nutrients,
  }
}

export async function translateUsda(): Promise<any> {
  // 本地模式无 AI 翻译管线，降级提示（前端 AI 后处理已通过 Agent 会话承载翻译）
  return { message: '本地模式请在「AI 后处理」中通过已启用的 AI 后端翻译食材名' }
}

export async function translateNutrients(): Promise<any> {
  return { message: '本地模式请在「AI 后处理」中通过已启用的 AI 后端翻译营养素名' }
}

export async function getTaskById(_params: Record<string, string>): Promise<any> {
  // 本地模式无 USDA 异步任务，轮询某个 id 时返回 null（前端会停止轮询）
  return null
}
