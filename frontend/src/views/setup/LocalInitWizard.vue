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
            <v-progress-linear v-if="importing" indeterminate class="mt-4" />
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
          </template>

          <!-- Step 3: Complete -->
          <template v-if="step === 3">
            <v-card-text class="text-body-1 text-center">
              <v-icon size="48" color="success" class="mb-4">mdi-check-circle-outline</v-icon>
              <p>初始化完成！</p>
              <p class="text-caption text-medium-emphasis mt-2">{{ importMessage }}</p>
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
import { seedBasicData } from '@/api/local/seed'

const router = useRouter()
const step = ref(1)
const importing = ref(false)
const importMessage = ref('')

async function importFromRepo() {
  importing.value = true
  importMessage.value = '正在导入基础单位和分类...'
  try {
    await seedBasicData()
    importMessage.value = '正在从 HowToCook 数据仓库下载数据...'

    // 下载仓库 ZIP
    const zipUrl = 'https://github.com/DingJunyao/HowToCook_json/archive/refs/heads/main.zip'
    const response = await fetch(zipUrl)
    if (!response.ok) throw new Error(`下载失败: ${response.status}`)
    const blob = await response.blob()

    importMessage.value = '正在解析数据...'
    const { BlobReader, ZipReader, TextWriter } = await import('@zip.js/zip.js')
    const reader = new ZipReader(new BlobReader(blob))
    const entries = await reader.getEntries()

    // 提取 ZIP 中的 out/ 目录文件
    const prefix = 'HowToCook_json-main/out/'
    const dataFiles: Record<string, string> = {}
    const recipeFiles: Array<{ name: string; json: any }> = []

    for (const entry of entries) {
      if (!entry.filename.startsWith(prefix)) continue
      const relPath = entry.filename.slice(prefix.length)
      if (!relPath || entry.dir) continue

      const text = await entry.getData!(new TextWriter())
      if (relPath === 'ingredients.json' || relPath === 'nutritions.json' || relPath === 'units.json' || relPath === 'ingredients_raw.json' || relPath === 'matched_ingredients.json') {
        dataFiles[relPath] = text
      } else if (relPath.endsWith('.json') && relPath.includes('/')) {
        // 分类目录下的菜谱 JSON
        try {
          recipeFiles.push({ name: relPath, json: JSON.parse(text) })
        } catch { /* skip invalid */ }
      }
    }

    await reader.close()

    importMessage.value = `数据解析完成，正在写入数据库（${recipeFiles.length} 个菜谱）...`
    const { getDb } = await import('@/api/local/database')
    const db = await getDb()

    // 导入单位
    if (dataFiles['units.json']) {
      const units = JSON.parse(dataFiles['units.json'])
      if (Array.isArray(units) && units.length > 0) {
        const tx = db.transaction('units', 'readwrite')
        for (const u of units) {
          if (u.id || u.name) await tx.store.put({ id: u.id, name: u.name, abbreviation: u.abbreviation || u.name, unit_type: u.unit_type || 'count', si_factor: u.si_factor, is_si_base: u.is_si_base || false, is_common: true, display_order: u.display_order || 99 })
        }
        await tx.done
      }
    }

    // 导入原料
    let ingredientCount = 0
    if (dataFiles['ingredients.json']) {
      const ingredients = JSON.parse(dataFiles['ingredients.json'])
      if (Array.isArray(ingredients)) {
        const tx = db.transaction('ingredients', 'readwrite')
        for (const ing of ingredients) {
          if (ing.name) {
            await tx.store.put({ id: ing.id, name: ing.name, category_id: ing.category_id || null, aliases: ing.aliases || [], is_active: true, created_at: new Date().toISOString() })
            ingredientCount++
          }
        }
        await tx.done
      }
    }

    // 导入营养数据
    let nutritionCount = 0
    if (dataFiles['nutritions.json']) {
      const nutritions = JSON.parse(dataFiles['nutritions.json'])
      if (Array.isArray(nutritions)) {
        const tx = db.transaction('nutrition_data', 'readwrite')
        for (const n of nutritions) {
          if (n.ingredient_id != null) {
            await tx.store.add({ ingredient_id: n.ingredient_id, nutrient_name: n.nutrient_name, amount_per_100g: n.amount_per_100g, unit: n.unit, source: 'howtocook', is_verified: true })
            nutritionCount++
          }
        }
        await tx.done
      }
    }

    // 导入菜谱
    let recipeCount = 0
    if (recipeFiles.length > 0) {
      const recipeTx = db.transaction(['recipes', 'recipe_ingredients'], 'readwrite')
      for (const { name, json } of recipeFiles) {
        if (!json.name) continue
        const recipeId = json.id || recipeCount + 1
        const ingredients = json.ingredients || []
        delete json.ingredients

        await recipeTx.objectStore('recipes').put({
          id: recipeId,
          name: json.name,
          category: json.category || null,
          difficulty: json.difficulty || null,
          total_time_minutes: json.total_time || json.total_time_minutes || null,
          servings: json.servings || null,
          cooking_steps: json.steps || [],
          tips: json.tips || [],
          description: json.description || '',
          images: json.images || [],
          tags: json.tags || null,
          is_public: true,
          is_active: true,
          source: 'json_repo',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })

        for (let i = 0; i < ingredients.length; i++) {
          const ing = ingredients[i]
          await recipeTx.objectStore('recipe_ingredients').put({
            recipe_id: recipeId,
            ingredient_id: ing.ingredient_id || null,
            ingredient_name: ing.ingredient_name || ing.name || '',
            quantity: ing.quantity || null,
            unit_id: ing.unit_id || null,
            unit: ing.unit || null,
            quantity_range: ing.quantity_range || null,
            is_optional: ing.is_optional || false,
            note: ing.note || null,
            sort_order: i + 1,
          })
        }
        recipeCount++
      }
      await recipeTx.done
    }

    importMessage.value = `导入完成！${ingredientCount} 个原料，${nutritionCount} 条营养数据，${recipeCount} 个菜谱。`
    step.value = 3
  } catch (e: any) {
    importMessage.value = '导入失败：' + (e?.message || '未知错误')
    console.error('[repo-import]', e)
  } finally {
    importing.value = false
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
  importMessage.value = '正在解析 ZIP 数据包...'
  try {
    await seedBasicData()

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
  try {
    await seedBasicData()
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
