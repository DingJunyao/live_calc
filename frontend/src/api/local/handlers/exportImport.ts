// Export/Import handler — local mode data export and import.
// GET /export/data — Export all local data as JSON
// POST /import/data/upload — Upload and import data via ZIP
// GET /import/tasks — List import tasks
// GET /import/task/:id — Get task status

import { getDb, clearStore, batchAdd, addOne, getAll } from '../database'
import JSZip from 'jszip'

/** 导出数据类型白名单 (IndexedDB store 名称列表) */
const EXPORT_STORES = [
  'units',
  'unit_conversions',
  'ingredient_categories',
  'ingredients',
  'nutrition_data',
  'products',
  'product_records',
  'recipes',
  'recipe_ingredients',
  'merchants',
  'ingredient_hierarchy',
  'entity_unit_overrides',
  'entity_densities',
  'blacklist_groups',
  'blacklist_group_ingredients',
  'blacklist_subscriptions',
  'user_places',
  'merchant_favorites',
  'meal_recommendations',
  'system_config',
  'recipe_cost_history',
  'product_weight_overrides',
  'product_barcodes',
] as const

/**
 * 云模式导出 ZIP 中的 JSON 文件 → IndexedDB store 名称 映射。
 * cloud 用 backend 字段名，local 用 IndexedDB 字段名，栏中注明差异。
 * 无差异的（字段名完全对应），只映射即可。
 */
const FILE_STORE_MAP: Record<string, string> = {
  'units.json': 'units',
  'unit_conversions.json': 'unit_conversions',
  'ingredient_categories.json': 'ingredient_categories',
  'ingredients.json': 'ingredients',
  'nutritions.json': 'nutrition_data',
  'products.json': 'products',
  'product_barcodes.json': 'product_barcodes',
  'price_records.json': 'product_records',
  'merchants.json': 'merchants',
  'ingredient_hierarchy.json': 'ingredient_hierarchy',
  'entity_unit_overrides.json': 'entity_unit_overrides',
  'entity_densities.json': 'entity_densities',
  'user_places.json': 'user_places',
  'blacklist_groups.json': 'blacklist_groups',
  'merchant_favorites.json': 'merchant_favorites',
  'product_weight_overrides.json': 'product_weight_overrides',
}

/**
 * 从 recipe JSON（云模式下 recipes/xxx.json 的内容）中分离
 * recipe 本体与 recipe_ingredients，分别写入。
 * 一条 recipe JSON 结构：
 *   { id, name, ingredients: [...], steps, tips, ... }
 *   → recipes store（去掉ingredients顶层字段）
 *   → recipe_ingredients store（从 ingredients 数组提取）
 */
async function importRecipe(
  db: any,
  data: any,
  resolveUnitId?: (cloudId: number | null | undefined, name?: string) => number | null,
): Promise<{ recipeId: number; count: number; images: string[] }> {
  const { ingredients: ingList, ...recipeBody } = data
  // 确保 recipe 有必要字段
  const recipeId = recipeBody.id

  // 纯前端单用户管理员模式：强制已发布
  const rawImages: string[] = recipeBody.images ?? []
  const recipeRecord = {
    ...recipeBody,
    images: rawImages,
    is_public: true,
    tags: recipeBody.tags ?? [],
    cooking_steps: recipeBody.steps ?? recipeBody.cooking_steps ?? [],
    tips: recipeBody.tips ?? [],
    created_at: recipeBody.created_at || new Date().toISOString(),
    updated_at: recipeBody.updated_at || new Date().toISOString(),
  }
  delete recipeRecord.steps  // 用 cooking_steps，steps 是云模式字段名

  // 写入 recipes（先删后加 — 统一用 put 覆盖已有 id）
  const tx1 = db.transaction('recipes', 'readwrite')
  await tx1.store.put(recipeRecord)
  await tx1.done

  // 写入 recipe_ingredients（先删旧的再批量加）
  const tx2 = db.transaction('recipe_ingredients', 'readwrite')
  const existing = await tx2.store.index('by_recipe_id').getAll(recipeId)
  for (const old of existing) {
    await tx2.store.delete(old.id)
  }
  await tx2.done

  let count = 0
  if (Array.isArray(ingList)) {
    for (let i = 0; i < ingList.length; i++) {
      const ing = ingList[i]
      const ri = {
        recipe_id: recipeId,
        ingredient_id: ing.ingredient_id ?? null,
        ingredient_name: ing.ingredient_name || '',
        quantity: ing.quantity ?? null,
        quantity_range: ing.quantity_range ?? null,
        unit_id: resolveUnitId ? resolveUnitId(ing.unit_id, ing.unit) : (ing.unit_id ?? null),
        is_optional: ing.is_optional ?? false,
        note: ing.note ?? '',
        sort_order: i,
      }
      // 用 addOne 让 DB 自增 id
      const id = await addOne('recipe_ingredients', ri)
      if (id) count++
    }
  }

  return { recipeId, count, images: rawImages }
}

/**
 * 获取本地模式的所有导入任务。
 */
export async function listTasks(_params: Record<string, string>, _query?: any): Promise<any> {
  const all = await getAll('import_tasks')
  return all.sort((a: any, b: any) => (b.created_at || '').localeCompare(a.created_at || ''))
}

/**
 * 获取单个导入任务详情。
 */
export async function getTask(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  if (!Number.isFinite(id)) throw { status: 400, message: 'Invalid task id' }
  const db = await getDb()
  const task = await db.get('import_tasks', id)
  if (!task) throw { status: 404, message: `Task ${id} not found` }
  return task
}

// ============================================================
// 导出
// ============================================================

/**
 * GET /export/data — 导出全部本地数据为 JSON 对象。
 * 仅包含有数据的 store，空 store 省略。
 */
export async function getExportData(
  _params: Record<string, string>,
  _query?: any,
): Promise<Record<string, any[]>> {
  const db = await getDb()
  const exportData: Record<string, any[]> = {}

  for (const store of EXPORT_STORES) {
    const items: any[] = await db.getAll(store)
    if (items.length > 0) {
      exportData[store] = items
    }
  }

  return exportData
}

// ============================================================
// 导入
// ============================================================

/** 临时内存中的任务跟踪，用于 post→poll 过渡 */
const taskCache = new Map<number, any>()

/**
 * POST /import/data/upload — 上传 ZIP 并导入数据。
 *
 * 流程：
 *  1. 用 JSZip 读取 ZIP
 *  2. 读 manifest.json 获取文件清单
 *  3. 各 JSON 文件按 FILE_STORE_MAP 写入对应 IndexedDB store
 *  4. recipes/xxx.json 拆分为 recipes + recipe_ingredients
 *  5. 营养数据做字段归一化
 *  6. 创建 import_tasks 记录供前端轮询
 */
export async function uploadImport(
  _params: Record<string, string>,
  data?: any,
): Promise<{ task_id: number }> {
  const file: File | null = data?.get?.('file') ?? null
  if (!file) {
    throw { status: 400, message: '缺少文件：未上传 ZIP 包' }
  }

  const db = await getDb()
  const arrayBuffer = await file.arrayBuffer()
  const zip = await JSZip.loadAsync(arrayBuffer)

  // 读 manifest（兼容无 manifest 的情况）
  let manifest: any = {}
  const manifestFile = zip.file('manifest.json')
  if (manifestFile) {
    const text = await manifestFile.async('string')
    manifest = JSON.parse(text)
  }

  const stats: Record<string, number> = {}
  const errors: string[] = []

  // ---- 预加载本地单位映射（云导出 ID ≠ 本地 seed ID，须按名称匹配）----
  const localUnits = await db.getAll('units')
  const unitNameToId: Record<string, number> = {}
  const unitAbbrToId: Record<string, number> = {}
  for (const u of localUnits) {
    if (u.name) unitNameToId[u.name] = u.id
    if (u.abbreviation) unitAbbrToId[u.abbreviation] = u.id
  }
  function resolveLocalUnitId(cloudId: number | null | undefined, name?: string): number | null {
    if (name) {
      // 优先按名称匹配（本地 seed 有固定名称）
      const byName = unitNameToId[name] || unitAbbrToId[name]
      if (byName) return byName
    }
    // 如果 cloudId 落在本地 seed 范围内（1-15），保持原样（可能碰巧一致）
    if (cloudId != null && cloudId >= 1 && cloudId <= 15) return cloudId
    // 否则无法映射，置 null（后续由消费方兜底）
    return null
  }

  // 这些「参考数据表」的 ID 与本地 seed 固定值耦合（如 千克=1, 克=2, 斤=3），
  // 云导出 ID 不同（千克=2），导入会破坏引用完整性 → 跳过，保留本地 seed。
  const SKIP_REFERENCE_STORES = new Set(['units', 'unit_conversions', 'ingredient_categories'])

  // ---- 第 1 步：按 FILE_STORE_MAP 导入 flat JSON 文件 ----
  for (const [fileName, storeName] of Object.entries(FILE_STORE_MAP)) {
    if (SKIP_REFERENCE_STORES.has(storeName)) continue  // 保留本地 seed 数据
    const fileEntry = zip.file(fileName)
    if (!fileEntry) continue

    try {
      const text = await fileEntry.async('string')
      const parsed = JSON.parse(text)

      // 归一化为数组。云导出 ingredients.json 是 {name: item} 字典，
      // 其余文件是标准数组或 { items: [...], total: N } 包裹。
      let items: any[]
      if (Array.isArray(parsed)) {
        items = parsed
      } else if (parsed.items && Array.isArray(parsed.items)) {
        items = parsed.items
      } else if (parsed.data && Array.isArray(parsed.data)) {
        items = parsed.data
      } else {
        // ingredients.json 字典 → 提取所有 value 为数组
        items = Object.values(parsed)
      }

      if (items.length === 0) continue

      // 字段归一化
      let normalized: any[] = []

      if (storeName === 'nutrition_data') {
        // 云导出 nutritions.json 是 { nutrients: [{name, value, unit}, ...], ingredient_id } 结构，
        // 需要「爆炸」为本地 flat 记录 { nutrient_name, amount_per_100g, unit, ingredient_id }
        for (const item of items) {
          const ingredientId = item.ingredient_id
          const nutList = item.nutrients || item.raw_nutrients || []
          if (Array.isArray(nutList)) {
            for (const nut of nutList) {
              normalized.push({
                ingredient_id: ingredientId,
                nutrient_name: nut.name || nut.nutrient_name || '',
                amount_per_100g: nut.value ?? nut.amount_per_100g ?? 0,
                unit: nut.unit || 'g',
              })
            }
          } else if (typeof nutList === 'object') {
            // raw_nutrients 可能是 { all_nutrients: { "蛋白质": { value, unit }, ... } } 嵌套结构
            const allNuts = nutList.all_nutrients || nutList
            for (const [key, val] of Object.entries(allNuts)) {
              if (val && typeof val === 'object') {
                normalized.push({
                  ingredient_id: ingredientId,
                  nutrient_name: key,
                  amount_per_100g: (val as any).value ?? (val as any).amount_per_100g ?? 0,
                  unit: (val as any).unit || 'g',
                })
              }
            }
          }
        }
      } else {
        normalized = items.map((item: any) => {
          const n = { ...item }

          // 软删字段：云导出不包含 is_active，补 true
          if (['merchants', 'ingredients', 'products', 'entity_unit_overrides', 'entity_densities'].includes(storeName)) {
            if (n.is_active === undefined || n.is_active === null) {
              n.is_active = true
            }
          }

          // 价格记录：云导出字段名与本地不一致，做映射
          if (storeName === 'product_records') {
            // 前端模板读 unit_name 作单价单位、original_unit 作原价单位
            n.unit_name = n.unit_name || n.standard_unit_name || n.original_unit_name || n.unit
            n.unit = n.unit_name
            n.original_unit = n.original_unit || n.original_unit_name
            n.original_quantity = n.original_quantity ?? n.quantity ?? 1
            // unit_id 按名称重映射为本地 ID
            n.unit_id = resolveLocalUnitId(n.unit_id, n.unit_name) ?? resolveLocalUnitId(n.standard_unit_id, n.unit_name)
            n.standard_unit_id = resolveLocalUnitId(n.standard_unit_id, n.standard_unit_name)
            n.original_unit_id = resolveLocalUnitId(n.original_unit_id, n.original_unit_name)
          }

          return n
        })
      }

      // 清空 store 再批量写入
      await clearStore(storeName as any)

      // 用事务写入（避免 batchAdd 的逐条事务开销）
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.store
      for (const item of normalized) {
        await store.put(item)
      }
      await tx.done

      stats[storeName] = normalized.length
    } catch (e: any) {
      errors.push(`${fileName}: ${e.message || e}`)
    }
  }

  // ---- 第 2 步：导入 recipes/xxx.json（拆分 recipes + recipe_ingredients）----
  let recipeCount = 0
  let ingredientCount = 0
  const allRecipeImages: Array<{ recipeId: number; imagePaths: string[] }> = []

  const recipeFiles: string[] = []
  zip.forEach((relPath) => {
    if (relPath.startsWith('recipes/') && relPath.endsWith('.json') && relPath !== 'recipes/.json') {
      recipeFiles.push(relPath)
    }
  })

  for (const fname of recipeFiles) {
    try {
      const entry = zip.file(fname)
      if (!entry) continue
      const text = await entry.async('string')
      const data = JSON.parse(text)

      if (Array.isArray(data)) {
        // 菜谱列表（部分导出格式）
        for (const recipeData of data) {
          const result = await importRecipe(db, recipeData, resolveLocalUnitId)
          recipeCount++
          ingredientCount += result.count
          if (result.images.length > 0) {
            allRecipeImages.push({ recipeId: result.recipeId, imagePaths: result.images })
          }
        }
      } else {
        // 单菜谱
        const result = await importRecipe(db, data)
        recipeCount++
        ingredientCount += result.count
        if (result.images.length > 0) {
          allRecipeImages.push({ recipeId: result.recipeId, imagePaths: result.images })
        }
      }
    } catch (e: any) {
      errors.push(`${fname}: ${e.message || e}`)
    }
  }

  // ---- 第 3 步：导入图片文件（从 ZIP images/ 目录提取并写入 IndexedDB）----
  // 先构建 ZIP 内所有图片文件的索引（key: 路径）
  const zipImageFiles = new Map<string, JSZip.JSZipObject>()
  zip.forEach((relPath) => {
    if (relPath.startsWith('images/') && !relPath.endsWith('/')) {
      zipImageFiles.set(relPath, zip.file(relPath)!)
    }
  })

  if (zipImageFiles.size > 0) {
    let imageCount = 0
    // 逐菜谱匹配图片
    for (const { recipeId, imagePaths } of allRecipeImages) {
      for (const imgPath of imagePaths) {
        if (!imgPath) continue
        // 云导出格式：images/recipes/xxx.jpg（convert_image_path 已去 /static/）
        // 远程 http(s) URL 不处理（浏览器直访）
        if (imgPath.startsWith('http')) continue

        // 尝试直接匹配（imgPath 可能是 images/recipes/xxx.jpg）
        // 也尝试匹配去掉 /static/ 前缀的变体
        const entry = zipImageFiles.get(imgPath) || zipImageFiles.get(imgPath.replace(/^\/?static\//, ''))

        if (!entry) continue

        try {
          const blob = await entry.async('blob')
          const tx = db.transaction('images', 'readwrite')
          await tx.store.put({
            entity_type: 'recipes',
            entity_id: recipeId,
            path: imgPath,
            blob,
            created_at: new Date().toISOString(),
          })
          await tx.done
          imageCount++
        } catch (e: any) {
          errors.push(`图片 ${imgPath}: ${e.message || e}`)
        }
      }
    }
    if (imageCount > 0) stats.images = imageCount
  }

  if (recipeCount > 0) {
    stats.recipes = recipeCount
    stats.recipe_ingredients = ingredientCount
  }

  // ---- 写入导入任务记录 ----
  const taskRecord = {
    task_type: 'upload_import',
    status: 'success',
    progress: { stage: '完成', current: 0, total: 0, message: '导入完成' },
    stats,
    error: errors.length > 0 ? errors.join('; ') : null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
  const taskId = await addOne('import_tasks', taskRecord)

  // 也放内存缓存，供 getTask 立即返回
  taskCache.set(taskId, { id: taskId, ...taskRecord })

  return { task_id: taskId }
}
