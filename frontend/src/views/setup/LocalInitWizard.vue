<template>
  <v-container fluid class="fill-height" style="background: rgb(var(--v-theme-surface))">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="pa-6">
          <v-card-title class="text-h4 text-center mb-4">生计 — 初始化</v-card-title>

          <!-- Step 1: Welcome + choose method -->
          <template v-if="step === 1">
            <v-card-text class="text-body-1 text-center mb-4">
              欢迎使用本地版本！请选择数据初始化方式：
            </v-card-text>
            <v-list lines="two">
              <v-list-item
                prepend-icon="mdi-database-import-outline"
                title="从 HowToCook 仓库导入"
                subtitle="导入公开菜谱、原料和营养数据（需要网络）"
                @click="importFromRepo"
                :disabled="importing"
              />
              <v-list-item
                prepend-icon="mdi-upload-outline"
                title="上传数据包"
                subtitle="导入之前导出的 ZIP 数据包"
                @click="step = 2"
                :disabled="importing"
              />
              <v-list-item
                prepend-icon="mdi-rocket-launch-outline"
                title="空白起步"
                subtitle="只导入基础单位和分类，后续在数据维护中心导入"
                @click="skipImport"
                :disabled="importing"
              />
            </v-list>
            <!-- 导入进度显示 -->
            <template v-if="importing">
              <v-progress-linear
                :model-value="importProgress"
                :indeterminate="importProgress === 0"
                class="mt-4 mb-2"
                color="primary"
                height="6"
              />
              <div class="text-caption text-center text-medium-emphasis" style="white-space: pre-line;">{{ importMessage }}</div>
              <div v-if="canCancel" class="text-center mt-2">
                <v-btn size="small" variant="tonal" color="error" :disabled="cancelImport" @click="cancelImport = true">
                  <v-icon start>mdi-stop-circle-outline</v-icon>中止导入
                </v-btn>
              </div>
            </template>
          </template>

          <!-- Step 2: Upload ZIP -->
          <template v-if="step === 2">
            <v-card-text class="text-body-1 mb-4">
              选择之前导出的 ZIP 数据包：
            </v-card-text>
            <v-file-input
              label="选择 ZIP 文件"
              accept=".zip"
              @change="handleZipUpload"
              :loading="importing"
            />
            <v-btn variant="text" @click="step = 1" :disabled="importing">返回</v-btn>
            <!-- 导入进度 -->
            <template v-if="importing">
              <v-progress-linear
                :model-value="importProgress"
                :indeterminate="importProgress === 0"
                class="mt-4 mb-2"
                color="primary"
                height="6"
              />
              <div class="text-caption text-center text-medium-emphasis">{{ importMessage }}</div>
            </template>
          </template>

          <!-- Step 3: Complete -->
          <template v-if="step === 3">
            <v-card-text class="text-body-1 text-center">
              <v-icon size="48" color="success" class="mb-4">mdi-check-circle-outline</v-icon>
              <p>初始化完成！</p>
              <p class="text-caption text-medium-emphasis mt-2" style="white-space: pre-line;">{{ importMessage }}</p>
            </v-card-text>
            <v-btn color="primary" block class="mt-4" @click="goToHome">
              开始使用
            </v-btn>
          </template>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { seedBasicData, BASE_UNITS } from '@/api/local/seed'

const router = useRouter()
const step = ref(1)
const importing = ref(false)
const importMessage = ref('')
const importProgress = ref(0) // 0-100，0 表示不确定

const cancelImport = ref(false) // 菜谱阶段用户主动中止
const canCancel = ref(false)   // 是否处于可中止阶段（菜谱导入中）

/**
 * 带「超时 + 重试」的 fetch：每次尝试最多等 timeoutMs，失败后线性退避重试，
 * 重试次数用尽则抛出最后一次错误。onRetry 用于在重试时更新界面提示。
 */
async function fetchWithRetry(
  url: string,
  retries = 3,
  timeoutMs = 30000,
  onRetry?: (attempt: number, reason: string) => void,
): Promise<Response> {
  let lastErr: unknown
  for (let attempt = 1; attempt <= retries; attempt++) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const resp = await fetch(url, { signal: controller.signal })
      clearTimeout(timer)
      if (resp.ok) return resp
      lastErr = new Error(`HTTP ${resp.status}`)
    } catch (e) {
      clearTimeout(timer)
      lastErr = (e instanceof DOMException && e.name === 'AbortError')
        ? new Error('请求超时')
        : e
    }
    if (attempt < retries) {
      onRetry?.(attempt, (lastErr as Error)?.message || '未知错误')
      await new Promise(r => setTimeout(r, 1000 * attempt))
    }
  }
  throw lastErr
}

async function importFromRepo() {
  importing.value = true
  importProgress.value = 5
  cancelImport.value = false
  canCancel.value = false
  importMessage.value = '正在从 HowToCook 数据仓库获取文件列表...'
  try {

    const RAW_BASE = 'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out'
    const API_BASE = 'https://api.github.com/repos/DingJunyao/HowToCook_json/contents/out'

    // 获取文件列表（强制：失败重试 3 次，仍失败则中止整个导入）
    const listResp = await fetchWithRetry(API_BASE, 3, 30000, (a, m) => {
      importMessage.value = `获取文件列表第 ${a} 次失败（${m}），重试中...`
    })
    const files: Array<{ name: string; type: string; download_url: string }> = await listResp.json()

    // 分类数据文件
   const dataFiles = ['ingredients.json', 'nutritions.json', 'units.json', 'ingredients_raw.json', 'matched_ingredients.json']
   const allRecipeFiles = files.filter(f => f.type === 'file' && f.name.endsWith('.json') && !dataFiles.includes(f.name))

   // 全量导入所有菜谱
   const recipeFiles = allRecipeFiles

   importMessage.value = `发现 ${recipeFiles.length} 个菜谱文件，准备全量导入`
   importProgress.value = 10

    const { getDb } = await import('@/api/local/database')
    const db = await getDb()

    // 清空旧数据（保留基础单位和分类，它们由 seedBasicData 和仓库数据覆盖）
    for (const store of ['ingredients', 'nutrition_data', 'products', 'product_records',
      'recipes', 'recipe_ingredients', 'merchants', 'ingredient_hierarchy',
      'entity_unit_overrides', 'entity_densities', 'meal_recommendations', 'images',
      'blacklist_groups', 'blacklist_group_ingredients', 'blacklist_subscriptions', 'user_places']) {
      const tx = db.transaction(store, 'readwrite')
      await tx.store.clear()
      await tx.done
    }
    importProgress.value = 12
    await seedBasicData() // 确保基础单位和分类存在

    // 下载并导入单位（强制：失败重试 3 次，仍失败则中止整个导入）
    importProgress.value = 15
    importMessage.value = '(1/4) 正在导入单位...'
    const unitsResp = await fetchWithRetry(`${RAW_BASE}/units.json`, 3, 30000, (a, m) => {
      importMessage.value = `(1/4) 单位导入第 ${a} 次失败（${m}），重试中...`
    })
    const unitsJson = await unitsResp.json()
    const htcUnits = Array.isArray(unitsJson) ? unitsJson : Object.values(unitsJson)
    if (htcUnits.length === 0) throw new Error('单位导入失败：units.json 内容为空')
    // HowToCook 的 units.json 只含 name/aliases，没有 unit_type/si_factor。
    // 若直接 put 会用 HowToCook 的名字覆盖 seed 单位记录（把 mass 单位变成 count、
    // si_factor 清空），导致成本换算全部失效。正确做法：先强制恢复 BASE_UNITS 的
    // 正确定义（顺便修正历史导入造成的损坏），再仅添加 seed 中没有的新单位，绝不覆盖。
    const unitKeyToId = new Map<string, number>()
    let nextUnitId = 0
    {
      const tx = db.transaction('units', 'readwrite')
      // 1. 强制恢复 seed 基础单位（保证 type/si_factor 正确，修复历史损坏）
      for (const su of BASE_UNITS) {
        await tx.store.put(su)
        unitKeyToId.set(su.name, su.id)
        if (su.abbreviation) unitKeyToId.set(su.abbreviation, su.id)
        if (su.id >= nextUnitId) nextUnitId = su.id + 1
      }
      // 2. 把已存在的（含用户自建/历史）单位纳入查找，避免重复添加
      const existing = await tx.store.getAll()
      for (const eu of existing) {
        if (eu.name) unitKeyToId.set(eu.name, eu.id)
        if (eu.abbreviation) unitKeyToId.set(eu.abbreviation, eu.id)
        if (eu.id >= nextUnitId) nextUnitId = eu.id + 1
      }
      // 3. 仅添加 seed 中不存在的新单位（朵/根/瓣/厘米等），绝不覆盖已有单位
      for (const u of htcUnits) {
        const name = u.name || u.abbreviation
        if (!name || unitKeyToId.has(name)) continue
        const aliasHit = (u.aliases || []).find((a: string) => unitKeyToId.has(a))
        if (aliasHit) {
          // 别名命中已有单位，仅补映射，不新增记录
          unitKeyToId.set(name, unitKeyToId.get(aliasHit)!)
          continue
        }
        const newId = nextUnitId++
        unitKeyToId.set(name, newId)
        await tx.store.put({
          id: newId, name,
          abbreviation: u.abbreviation || name,
          unit_type: 'count', si_factor: null,
          is_si_base: false, is_common: false,
          display_order: 99, plural_form: null,
        })
      }
      await tx.done
    }
    importProgress.value = 20
    importMessage.value = '(1/4) 单位已导入，正在导入原料...'

    // 下载并导入原料（ingredients.json 是对象，key=原料名）
    // （强制：失败重试 3 次，仍失败则中止）
    importProgress.value = 22
    importMessage.value = '(2/4) 正在导入原料...'
    let ingredientCount = 0
    const ingredientNameToId: Record<string, number> = {}
    const ingResp = await fetchWithRetry(`${RAW_BASE}/ingredients.json`, 3, 30000, (a, m) => {
      importMessage.value = `(2/4) 原料导入第 ${a} 次失败（${m}），重试中...`
    })
    const ingObj: Record<string, any> = await ingResp.json()
    const entries = Object.entries(ingObj)
    if (entries.length === 0) throw new Error('原料导入失败：ingredients.json 内容为空')
    {
      const tx = db.transaction('ingredients', 'readwrite')
      let idCounter = 1
      for (const [key, ing] of entries) {
        const name = ing.name || key
        const ingId = ing.id || idCounter++
        await tx.store.put({
          id: ingId, name,
          category_id: null,
          aliases: ing.aliases || [],
          is_active: true, created_at: new Date().toISOString(),
        })
        ingredientNameToId[name] = ingId
        ingredientCount++
      }
      await tx.done
    }
    importProgress.value = 40
    importMessage.value = `(2/4) ${ingredientCount} 个原料已导入，正在下载营养数据...`

    // 下载并导入营养数据（可选：失败重试 3 次后跳过，不影响后续导入）
    let nutritionCount = 0
    let nutritionSkipped = false
    try {
      const nutResp = await fetchWithRetry(`${RAW_BASE}/nutritions.json`, 3, 30000)
      const nutritions: any[] = await nutResp.json()
      if (Array.isArray(nutritions)) {
        const tx = db.transaction('nutrition_data', 'readwrite')
        const seen = new Set<string>()
        for (const item of nutritions) {
          const ingName = item.ingredient_name
          const ingId = ingredientNameToId[ingName]
          if (!ingId || !item.nutrients) continue
          for (const n of item.nutrients) {
            if (!n.name || n.value == null) continue
            const key = `${ingId}-${n.name}`
            if (seen.has(key)) continue
            seen.add(key)
            await tx.store.add({
              ingredient_id: ingId,
              nutrient_name: n.name,
              amount_per_100g: n.value,
              unit: n.unit || 'g',
              source: n.name_en ? 'usda' : 'howtocook',
              is_verified: true,
            })
            nutritionCount++
          }
        }
        await tx.done
      }
    } catch (e) {
      console.warn('[repo-import] 营养数据导入失败，已跳过', e)
      nutritionSkipped = true
    }
    importProgress.value = 50
    importMessage.value = `(3/4) ${nutritionCount} 条营养数据已导入，正在为原料创建商品...`

    // 为每个原料创建对应的商品（产品和原料 1:1）
    let productCount = 0
    try {
      const tx = db.transaction('products', 'readwrite')
      for (const [name, ingId] of Object.entries(ingredientNameToId)) {
        await tx.store.put({
          name, ingredient_id: ingId as number,
          is_active: true, price_weight: 50,
          created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
        })
        productCount++
      }
      await tx.done
    } catch { /* optional */ }
    importProgress.value = 55
    importMessage.value = `(3/4) 已为 ${productCount} 个原料创建商品，正在下载菜谱（0/${recipeFiles.length}）...`

    // 构建单位名→ID 映射（供菜谱原料匹配使用）
    const allUnits = await db.getAll('units')
    const unitNameToId: Record<string, number> = {}
    for (const u of allUnits) {
      unitNameToId[u.name] = u.id; if (u.abbreviation) unitNameToId[u.abbreviation] = u.id
    }
    unitNameToId['g'] = unitNameToId['克'] || 2; unitNameToId['ml'] = unitNameToId['mL'] || 5
    unitNameToId['l'] = unitNameToId['升'] || 4; unitNameToId['kg'] = unitNameToId['千克'] || 1
    unitNameToId['片'] = unitNameToId['克'] || 2; unitNameToId['根'] = unitNameToId['个'] || 6
    unitNameToId['瓣'] = unitNameToId['个'] || 6; unitNameToId['颗'] = unitNameToId['个'] || 6
    unitNameToId['只'] = unitNameToId['个'] || 6

    // 逐个下载并导入菜谱（非强制：每条失败重试 3 次后跳过，可随时中止）
    canCancel.value = true
    let recipeCount = 0
    let recipeFailures = 0
    const totalRecipes = recipeFiles.length
    const BATCH_SIZE = 10
    const IMG_BASE = 'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out'
    let totalImages = 0
    let downloadedImages = 0

    for (let i = 0; i < totalRecipes; i += BATCH_SIZE) {
      if (cancelImport.value) break
      const batch = recipeFiles.slice(i, i + BATCH_SIZE)
      const pct = 50 + Math.round((i / totalRecipes) * 40)
      importProgress.value = pct
      const failedNote = recipeFailures > 0 ? `，失败 ${recipeFailures} 个` : ''
      importMessage.value = `(4/4) 正在导入菜谱 ${Math.min(i + BATCH_SIZE, totalRecipes)}/${totalRecipes}${failedNote}...`

      // 每个菜谱文件独立重试 3 次；某条彻底失败只计数，不影响其他
      const results = await Promise.allSettled(batch.map(async (file: any) => {
        const resp = await fetchWithRetry(file.download_url, 3, 20000)
        const json = await resp.json()
        return { name: file.name, json }
      }))

      // 收集本批菜谱中需要下载图片的条目
      const pendingImages: Array<{ recipeId: number; imagePath: string }> = []

      const recipeTx = db.transaction(['recipes', 'recipe_ingredients'], 'readwrite')
      for (let r = 0; r < results.length; r++) {
        const result = results[r]
        if (result.status === 'rejected') {
          recipeFailures++
          console.warn(`[repo-import] 菜谱导入失败: ${batch[r].name}`, result.reason)
          continue
        }
        const { json } = result.value
        if (!json || !json.name) {
          recipeFailures++
          continue
        }

        const recipeId = json.id || recipeCount + 1
        const ingredients = json.ingredients || []
        const images = json.images || []
        delete json.ingredients

        await recipeTx.objectStore('recipes').put({
          id: recipeId, name: json.name,
          category: json.category || null, difficulty: json.difficulty || null,
          total_time_minutes: json.total_time || json.total_time_minutes || null,
          servings: json.servings || null,
          cooking_steps: json.steps || [], tips: json.tips || [],
          description: json.description || '', images,
          tags: json.tags || null,
          is_public: true, is_active: true, source: 'json_repo',
          created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
        })

        for (let j = 0; j < ingredients.length; j++) {
          const ing = ingredients[j]
          // 按名称匹配 ingredient_id
          const matchedId = ing.ingredient_id || ingredientNameToId[ing.ingredient_name || ing.name || '']
          // 按名称匹配 unit_id（unitNameToId 已在循环外预载好）
          const unitStr = ing.unit || ''
          const matchedUnitId = ing.unit_id || unitNameToId[unitStr] || unitNameToId[unitStr.toLowerCase()] || null
          await recipeTx.objectStore('recipe_ingredients').put({
            recipe_id: recipeId, ingredient_id: matchedId || null,
            ingredient_name: ing.ingredient_name || ing.name || '',
            quantity: ing.quantity || null, unit_id: matchedUnitId,
            unit: ing.unit || null, quantity_range: ing.quantity_range || null,
            is_optional: ing.is_optional || false, note: ing.note || null,
            sort_order: j + 1,
          })
        }

        // 记录待下载图片
        for (const imgPath of images) {
          if (imgPath && typeof imgPath === 'string') {
            pendingImages.push({ recipeId, imagePath: imgPath })
          }
        }
        recipeCount++
      }
      await recipeTx.done

      // 下载本批菜谱的图片（每个图片独立事务，一张失败不影响其他）
      if (!cancelImport.value && pendingImages.length > 0) {
        totalImages += pendingImages.length
        for (const { recipeId, imagePath } of pendingImages) {
          if (cancelImport.value) break
          try {
            const encodedPath = imagePath.split('/').map(s => encodeURIComponent(s)).join('/')
            const imgUrl = imagePath.startsWith('http')
              ? imagePath
              : `${IMG_BASE}/${encodedPath}`
            const imgResp = await fetch(imgUrl)
            if (!imgResp.ok) continue
            const blob = await imgResp.blob()
            // 每个图片单独事务
            const singleTx = db.transaction('images', 'readwrite')
            await singleTx.store.add({
              entity_type: 'recipes',
              entity_id: recipeId,
              path: imagePath,
              blob,
              mime_type: blob.type || 'image/jpeg',
              created_at: new Date().toISOString(),
            })
            await singleTx.done
            downloadedImages++
          } catch (e) {
            console.warn(`[img] 图片下载失败: ${imagePath}`, e)
          }
        }
      }
    }
    canCancel.value = false

    importProgress.value = 100
    let summary = `导入完成！${ingredientCount} 个原料，${recipeCount} 个菜谱，${downloadedImages} 张图片。`
    summary += nutritionSkipped
      ? `\n营养数据导入失败已跳过，不影响使用。`
      : `\n${nutritionCount} 条营养数据。`
    if (recipeFailures > 0) {
      summary += `\n⚠ ${recipeFailures} 个菜谱导入失败，已跳过。`
    }
    if (cancelImport.value) {
      const remaining = totalRecipes - recipeCount - recipeFailures
      summary += `\n已中止导入，剩余 ${remaining} 个菜谱未处理。`
    }
    importMessage.value = summary
    step.value = 3
  } catch (e: any) {
    importMessage.value = '导入失败：' + (e?.message || '未知错误')
    console.error('[repo-import]', e)
  } finally {
    importing.value = false
    canCancel.value = false
  }
}

/** ZIP 文件名到 IndexedDB store 名的映射 */
const FILE_TO_STORE: Record<string, { store: string; transform?: (item: any) => any }> = {
  'units.json': { store: 'units' },
  'unit_conversions.json': { store: 'unit_conversions' },
  'ingredient_categories.json': { store: 'ingredient_categories' },
  'ingredients.json': { store: 'ingredients' },
  'nutritions.json': { store: 'nutrition_data' },
  'ingredient_hierarchy.json': { store: 'ingredient_hierarchy' },
  'entity_densities.json': { store: 'entity_densities' },
  'entity_unit_overrides.json': { store: 'entity_unit_overrides' },
  'products.json': { store: 'products' },
  'product_barcodes.json': { store: 'product_barcodes' },
  'price_records.json': { store: 'product_records' },
  'merchants.json': { store: 'merchants', transform: (m: any) => ({ ...m, is_active: m.is_active ?? true }) },
  'user_places.json': { store: 'user_places' },
  'blacklist_groups.json': { store: 'blacklist_groups' },
  'user_ingredient_blacklist.json': { store: 'blacklist_group_ingredients' },
  'blacklist_group_subscriptions.json': { store: 'blacklist_subscriptions' },
}

/** 导入顺序（依赖关系：被引用的先导入） */
const IMPORT_ORDER = [
  'units.json', 'unit_conversions.json', 'ingredient_categories.json',
  'ingredients.json', 'nutritions.json', 'merchants.json',
  'products.json', 'product_barcodes.json', 'price_records.json',
  'ingredient_hierarchy.json', 'entity_unit_overrides.json', 'entity_densities.json',
  'user_places.json', 'blacklist_groups.json', 'user_ingredient_blacklist.json',
  'blacklist_group_subscriptions.json',
]

async function handleZipUpload(event: any) {
  const file = event?.target?.files?.[0] || event?.file
  if (!file) return

  importing.value = true
  importProgress.value = 5
  importMessage.value = '正在解析 ZIP 数据包...'
  try {
    await seedBasicData()
    importProgress.value = 10

    const { BlobReader, ZipReader } = await import('@zip.js/zip.js')
    const reader = new ZipReader(new BlobReader(file))
    const entries = await reader.getEntries()
    importMessage.value = `ZIP 中包含 ${entries.length} 个文件，正在导入...`

    // 收集所有 JSON 数据
    const dataMap: Record<string, any[]> = {}
    const recipeFiles: Array<{ filename: string; data: any }> = []
    let imported = 0

    for (const entry of entries) {
      if (!entry.filename.endsWith('.json')) continue
      if (entry.filename === 'manifest.json') continue

      const text = await (entry.getData as any)(new (await import('@zip.js/zip.js')).TextWriter())
      const json = JSON.parse(text)

      // recipes/ 目录下的文件是独立菜谱
      if (entry.filename.startsWith('recipes/')) {
        recipeFiles.push({ filename: entry.filename, data: json })
        imported++
        continue
      }

      const items = Array.isArray(json) ? json : [json]
      dataMap[entry.filename] = items
      imported += items.length
    }

    importProgress.value = 30
    importMessage.value = `解析完成（${imported} 条记录 + ${recipeFiles.length} 个菜谱），正在写入数据库...`

    // 按依赖顺序导入
    const { getDb } = await import('@/api/local/database')
    const db = await getDb()
    let totalWritten = 0

    for (const filename of IMPORT_ORDER) {
      const items = dataMap[filename]
      if (!items || items.length === 0) continue

      const mapping = FILE_TO_STORE[filename]
      if (!mapping) continue

      const storeName = mapping.store
      const transformed = mapping.transform ? items.map(mapping.transform) : items

      const tx = db.transaction(storeName, 'readwrite')
      for (const item of transformed) {
        await tx.store.put(item)
      }
      await tx.done
      totalWritten += transformed.length
    }

    // 导入菜谱
    if (recipeFiles.length > 0) {
      importMessage.value = `正在导入 ${recipeFiles.length} 个菜谱...`
      const recipeTx = db.transaction(['recipes', 'recipe_ingredients'], 'readwrite')

      for (const { data } of recipeFiles) {
        // 提取 ingredients 字段
        const ingredients = data.ingredients || []
        delete data.ingredients

        // 写入菜谱主体
        const recipeRecord = {
          id: data.id,
          name: data.name,
          category: data.category || null,
          difficulty: data.difficulty || null,
          total_time_minutes: data.total_time_minutes || null,
          servings: data.servings || null,
          cooking_steps: data.steps || [],
          tips: data.tips || [],
          description: data.description || '',
          images: data.images || [],
          tags: data.tags || null,
          result_ingredient_id: data.result_ingredient_id || null,
          is_public: true,
          is_active: true,
          source: 'imported',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        await recipeTx.objectStore('recipes').put(recipeRecord)

        // 写入菜谱原料
        for (let i = 0; i < ingredients.length; i++) {
          const ing = ingredients[i]
          await recipeTx.objectStore('recipe_ingredients').put({
            recipe_id: data.id,
            ingredient_id: ing.ingredient_id || null,
            ingredient_name: ing.ingredient_name,
            quantity: ing.quantity || null,
            unit_id: ing.unit_id || null,
            unit: ing.unit || null,
            quantity_range: ing.quantity_range || null,
            is_optional: ing.is_optional || false,
            note: ing.note || null,
            sort_order: i + 1,
          })
        }
        totalWritten++
      }
      await recipeTx.done
    }

    reader.close()
    importMessage.value = `导入完成！共导入 ${totalWritten} 条数据。`
    step.value = 3
  } catch (e: any) {
    importMessage.value = '导入失败：' + (e?.message || '未知错误')
    console.error('[zip-import]', e)
  } finally {
    importing.value = false
  }
}

async function skipImport() {
  importing.value = true
  importProgress.value = 50
  try {
    await seedBasicData()
    importProgress.value = 100
    importMessage.value = '基础单位和分类已就绪。'
    step.value = 3
  } catch (e: any) {
    importMessage.value = '导入失败：' + (e?.message || '未知错误')
  } finally {
    importing.value = false
  }
}

function goToHome() {
  router.replace('/')
}
</script>
