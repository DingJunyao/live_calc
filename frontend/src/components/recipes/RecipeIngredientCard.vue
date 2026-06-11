<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="primary">mdi-food-apple-outline</v-icon>
      原料列表
      <v-chip size="small" class="ml-2" v-if="recipe.ingredients?.length">
        {{ editing ? editRows.length : recipe.ingredients.length }}
      </v-chip>
      <v-spacer />
      <template v-if="!editing">
        <v-btn
          size="small"
          variant="text"
          color="primary"
          prepend-icon="mdi-pencil"
          @click="startEdit"
        >编辑</v-btn>
      </template>
      <template v-else>
        <v-btn
          size="small"
          variant="text"
          color="success"
          prepend-icon="mdi-check"
          :loading="saving"
          @click="handleSave"
        >保存</v-btn>
        <v-btn
          size="small"
          variant="text"
          color="medium-emphasis"
          prepend-icon="mdi-close"
          :disabled="saving"
          @click="cancelEdit"
          class="ml-1"
        >取消</v-btn>
      </template>
    </v-card-title>
    <v-divider />
    <v-alert
      v-if="saveError"
      type="warning"
      variant="tonal"
      density="compact"
      class="ma-3"
      closable
      @click:close="saveError = ''"
    >{{ saveError }}</v-alert>

    <!-- 查看模式 -->
    <template v-if="!editing">
      <v-card-text v-if="recipe.ingredients?.length" class="pa-0">
        <div
          v-for="(ingredient, index) in recipe.ingredients"
          :key="ingredient.id"
          class="ingredient-item"
          :class="{ 'mb-2': index < recipe.ingredients.length - 1 }"
        >
          <div class="d-flex align-center py-2">
            <div
              class="ingredient-name flex-grow-1 text-body-2 ingredient-clickable"
              @click="goToIngredient(ingredient.ingredient_id)"
            >
              {{ ingredient.name }}
              <v-chip v-if="ingredient.is_optional" size="x-small" color="info" variant="flat" class="ml-1">可选</v-chip>
              <v-icon size="x-small" class="ml-1">mdi-chevron-right</v-icon>
            </div>
            <div class="ingredient-quantity text-body-2 text-right mr-4" style="min-width: 80px">
              <template v-if="ingredient.quantity && ingredient.quantity_range">
                {{ ingredient.quantity_range.min }}~{{ ingredient.quantity_range.max }} {{ ingredient.unit }}
                <span class="text-medium-emphasis">（推荐 {{ ingredient.quantity }} {{ ingredient.unit }}）</span>
              </template>
              <span v-else-if="scaleQuantity(ingredient.quantity, servings)">
                {{ scaleQuantity(ingredient.quantity, servings) }} {{ ingredient.unit }}
              </span>
              <span v-else-if="ingredient.quantity_range">
                {{ ingredient.quantity_range.min }}-{{ ingredient.quantity_range.max }} {{ ingredient.unit }}
              </span>
              <span v-else-if="ingredient.original_quantity">{{ ingredient.original_quantity }}</span>
              <span v-else>-</span>
            </div>
            <div class="ingredient-cost text-body-2 text-right d-flex align-center justify-end" style="min-width: 60px">
              <template v-if="getIngredientFallbackChain(ingredient)">
                <v-tooltip location="top">
                  <template #activator="{ props }">
                    <v-icon v-bind="props" size="small" color="info" class="mr-1">mdi-information</v-icon>
                  </template>
                  <div>
                    <div class="text-caption">根据以下食材计算成本：</div>
                    <div class="text-body-2 font-weight-bold">{{ getIngredientFallbackChain(ingredient) }}</div>
                  </div>
                </v-tooltip>
              </template>
              <span>¥{{ formatIngredientCost(ingredient) }}</span>
            </div>
          </div>
          <div v-if="ingredient.note" class="text-caption text-medium-emphasis pl-2 pb-1">
            {{ ingredient.note }}
          </div>
        </div>
      </v-card-text>
      <v-card-text v-else class="text-center py-4 text-medium-emphasis">
        暂无原料数据
      </v-card-text>
    </template>

    <!-- 编辑模式 -->
    <v-card-text v-else class="pa-0">
      <div class="ingredient-edit-table">
        <!-- 表头 -->
        <div class="edit-table-header d-none d-md-flex text-caption text-medium-emphasis px-3 py-2">
          <div style="width: 30px"></div>
          <div class="flex-grow-1" style="min-width: 130px">原料</div>
          <div style="width: 65px" class="text-center">类型</div>
          <div style="width: 70px" class="text-center">推荐值</div>
          <div style="width: 70px" class="text-center">min</div>
          <div style="width: 70px" class="text-center">max</div>
          <div style="width: 70px" class="text-center">单位</div>
          <div style="width: 30px"></div>
        </div>

        <!-- 编辑行 -->
        <div
          v-for="(row, index) in editRows"
          :key="row.tempId"
          class="edit-table-row pa-3 pb-2"
          :class="{ 'border-bottom': index < editRows.length - 1 }"
        >
          <!-- 第1行：原料 + 类型 + 删除 -->
          <div class="d-flex flex-wrap align-start ga-2 mb-1">
            <v-icon size="small" class="drag-handle mt-2" color="medium-emphasis">mdi-drag</v-icon>

            <v-autocomplete
              v-model="row.ingredient_name"
              :items="ingredientSearchResults"
              item-title="name"
              item-value="name"
              label="原料"
              variant="outlined"
              density="compact"
              hide-details
              class="flex-grow-1"
              style="min-width: 140px"
              :loading="searchingIngredient"
              @update:search="onSearchIngredient"
              @update:model-value="(val: string) => onSelectIngredient(row, val)"
              clearable
            />

            <v-select
              v-model="row.quantity_type"
              :items="quantityTypeOptions"
              item-title="label"
              item-value="value"
              label="类型"
              variant="outlined"
              density="compact"
              hide-details
              style="width: 75px"
            />

            <v-btn
              icon="mdi-delete"
              size="x-small"
              color="error"
              variant="text"
              class="mt-1"
              @click="removeRow(index)"
            />
          </div>

          <!-- 第2行：推荐值 min max 单位（仅数值类型时显示） -->
          <div v-if="!row.quantity_type" class="d-flex flex-wrap align-start ga-2 mb-1 pl-7">
            <v-text-field
              v-model="row.quantity_recommended"
              type="number"
              label="推荐"
              variant="outlined"
              density="compact"
              hide-details
              style="width: 80px"
              min="0"
              step="any"
            />
            <v-text-field
              v-model="row.quantity_min"
              type="number"
              label="min"
              variant="outlined"
              density="compact"
              hide-details
              style="width: 70px"
              min="0"
              step="any"
            />
            <v-text-field
              v-model="row.quantity_max"
              type="number"
              label="max"
              variant="outlined"
              density="compact"
              hide-details
              style="width: 70px"
              min="0"
              step="any"
            />
            <v-autocomplete
              v-model="row.unit_name"
              :items="unitOptions"
              item-title="label"
              item-value="value"
              label="单位"
              variant="outlined"
              density="compact"
              hide-details
              style="width: 80px"
              clearable
            />
          </div>

          <!-- 第3行：备注 + 可选（仅数值类型时显示） -->
          <div v-if="!row.quantity_type" class="d-flex flex-wrap align-center ga-2 pl-7">
            <v-text-field
              v-model="row.note"
              label="备注"
              variant="outlined"
              density="compact"
              hide-details
              style="min-width: 160px; max-width: 360px"
              maxlength="200"
              clearable
            />
            <v-checkbox
              v-model="row.is_optional"
              label="可选"
              density="compact"
              hide-details
              class="mt-0 pt-0"
            />
          </div>
        </div>

        <div class="pa-3">
          <v-btn
            variant="text"
            color="primary"
            prepend-icon="mdi-plus"
            size="small"
            @click="addRow"
          >添加原料</v-btn>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { RecipeDetail, RecipeIngredient, IngredientEditRow, IngredientOption, UnitOption } from './types'

const props = defineProps<{
  recipe: RecipeDetail
  costBreakdown?: any[]
  displayServings?: number
  servings?: number
  onFormatIngredientCost?: (ingredient: RecipeIngredient) => string
  onGetIngredientFallbackChain?: (ingredient: RecipeIngredient) => string | null
}>()

const emit = defineEmits<{
  (e: 'saved', ingredients: any[]): void
}>()

const router = useRouter()
const editing = ref(false)
const saving = ref(false)
const editRows = ref<IngredientEditRow[]>([])
const ingredientSearchResults = ref<IngredientOption[]>([])
const unitOptions = ref<{ label: string; value: string }[]>([])
const unitMap = ref<Record<string, number>>({})
const searchingIngredient = ref(false)

const quantityTypeOptions = [
  { label: '数值', value: '' },
  { label: '适量', value: '适量' },
  { label: '少许', value: '少许' },
]

// 份数计算
const servings = computed(() => props.recipe.servings || 1)

// 缩放原料数量
const scaleQuantity = (quantity: string | number | undefined, origServings: number): string => {
  if (quantity === undefined || quantity === null || quantity === '') return ''
  const num = typeof quantity === 'string' ? parseFloat(quantity) : quantity
  if (isNaN(num) || num === 0) return ''
  const ratio = (props.displayServings || 1) / (origServings || 1)
  const scaled = num * ratio
  if (Number.isInteger(scaled)) return scaled.toString()
  return scaled.toFixed(1).replace(/\.0$/, '')
}

// 获取原料成本
const formatIngredientCost = (ingredient: RecipeIngredient) => {
  if (!props.costBreakdown) return '-'
  const item = props.costBreakdown.find((b: any) => b.recipe_ingredient_id === ingredient.id)
  if (!item) return '-'
  const ratio = (props.displayServings || 1) / (props.recipe.servings || 1)
  const cost = (item.cost || 0) * ratio
  return cost.toFixed(2)
}

const getIngredientFallbackChain = (ingredient: RecipeIngredient): string | null => {
  if (!props.costBreakdown) return null
  const item = props.costBreakdown.find((b: any) => b.recipe_ingredient_id === ingredient.id)
  if (item?.aggregation_chain) return item.aggregation_chain
  return item?.fallback_chain || null
}

const goToIngredient = (ingredientId: number) => {
  router.push(`/data/ingredients/${ingredientId}`)
}

// 搜索原料
const onSearchIngredient = async (query: string) => {
  if (!query || query.length < 1) {
    ingredientSearchResults.value = []
    return
  }
  searchingIngredient.value = true
  try {
    const res = await api.get('/ingredients', { params: { q: query, limit: 20 } })
    ingredientSearchResults.value = (res.items || []).map((i: any) => ({
      id: i.id,
      name: i.name,
      aliases: i.aliases || [],
    }))
  } catch (e) {
    console.error('搜索原料失败', e)
  } finally {
    searchingIngredient.value = false
  }
}

const onSelectIngredient = (row: IngredientEditRow, name: string) => {
  const match = ingredientSearchResults.value.find(i => i.name === name)
  if (match) {
    row.ingredient_id = match.id
  }
}

// 加载单位列表
const loadUnits = async () => {
  try {
    const res = await api.get('/units/', { params: { is_common: true } })
    const items: any[] = Array.isArray(res) ? res : (res?.items || [])
    const map: Record<string, number> = {}
    unitOptions.value = items.map((u: any) => {
      const key = u.abbreviation || u.name
      if (key && u.id) map[key] = u.id
      return { label: key, value: key }
    })
    unitMap.value = map
  } catch (e) {
    console.error('加载单位列表失败', e)
  }
}

// 从现有数据初始化编辑行
const startEdit = () => {
  editRows.value = (props.recipe.ingredients || []).map(ing => {
    let qType = ''
    if (ing.original_quantity === '适量' || ing.original_quantity === '少许') {
      qType = ing.original_quantity
    }

    // quantity、quantity_range.min、quantity_range.max 三者可独立存在
    let qRec = ''
    let qMin = ''
    let qMax = ''
    if (!qType) {
      qRec = ing.quantity ? String(ing.quantity) : ''
      if (ing.quantity_range && typeof ing.quantity_range === 'object') {
        const r = ing.quantity_range as { min?: number; max?: number }
        qMin = r.min ? String(r.min) : ''
        qMax = r.max ? String(r.max) : ''
      }
    }

    return {
      tempId: Date.now() + Math.random(),
      ingredient_name: ing.name || '',
      ingredient_id: ing.ingredient_id,
      quantity_type: qType,
      quantity_recommended: qRec,
      quantity_min: qMin,
      quantity_max: qMax,
      unit_id: null,
      unit_name: ing.unit || '',
      is_optional: ing.is_optional || false,
      note: ing.note || '',
    }
  })
  if (editRows.value.length === 0) {
    addRow()
  }
  editing.value = true
}

const cancelEdit = () => {
  editing.value = false
}

const addRow = () => {
  editRows.value.push({
    tempId: Date.now() + Math.random(),
    ingredient_name: '',
    ingredient_id: null,
    quantity_type: '',
    quantity_recommended: '',
    quantity_min: '',
    quantity_max: '',
    unit_id: null,
    unit_name: '',
    is_optional: false,
    note: '',
  })
}

const removeRow = (index: number) => {
  editRows.value.splice(index, 1)
}

const saveError = ref('')

const handleSave = async () => {
  saveError.value = ''

  // 先验证所有行的用量组合
  const invalidRows: number[] = []
  editRows.value.forEach((row, idx) => {
    if (!row.ingredient_name) return  // 空行跳过
    if (row.quantity_type) return     // 适量/少许跳过

    const recVal = row.quantity_recommended ? parseFloat(row.quantity_recommended) : NaN
    const minVal = row.quantity_min ? parseFloat(row.quantity_min) : NaN
    const maxVal = row.quantity_max ? parseFloat(row.quantity_max) : NaN

    const hasRec = !isNaN(recVal)
    const hasMin = !isNaN(minVal)
    const hasMax = !isNaN(maxVal)

    const valid = (hasRec && hasMin && hasMax)   // 推荐+min+max
      || (hasRec && !hasMin && !hasMax)          // 仅推荐值
      || (!hasRec && hasMin && hasMax)           // 仅min+max
      || (!hasRec && !hasMin && !hasMax)          // 全空
    if (!valid) {
      invalidRows.push(idx + 1)
    }
  })

  if (invalidRows.length > 0) {
    saveError.value = `第 ${invalidRows.join('、')} 行的用量组合不完整。用量字段仅支持：①仅推荐值 ②推荐值+min+max ③仅min+max`
    saving.value = false
    return
  }

  saving.value = true
  try {
    const ingredients = editRows.value
      .filter(row => row.ingredient_name)
      .map(row => {
        const data: any = {
          ingredient_name: row.ingredient_name,
          is_optional: row.is_optional,
        }

        if (row.quantity_type) {
          data.original_quantity = row.quantity_type
        } else {
          const recVal = row.quantity_recommended ? parseFloat(row.quantity_recommended) : NaN
          const minVal = row.quantity_min ? parseFloat(row.quantity_min) : NaN
          const maxVal = row.quantity_max ? parseFloat(row.quantity_max) : NaN

          const hasRec = !isNaN(recVal)
          const hasMin = !isNaN(minVal)
          const hasMax = !isNaN(maxVal)

          if (hasRec && hasMin && hasMax) {
            data.quantity = String(recVal)
            data.quantity_range = { min: minVal, max: Math.max(minVal, maxVal) }
          } else if (hasRec && !hasMin && !hasMax) {
            data.quantity = String(recVal)
          } else if (!hasRec && hasMin && hasMax) {
            data.quantity_range = { min: minVal, max: Math.max(minVal, maxVal) }
          }

          if (row.unit_name && (hasRec || hasMin || hasMax)) {
            const uid = unitMap.value[row.unit_name]
            if (uid) data.unit_id = uid
          }
        }

        if (row.note) data.note = row.note
        return data
      })

    const result = await api.put(`/recipes/${props.recipe.id}`, { ingredients })
    emit('saved', result)
    editing.value = false
  } catch (e: any) {
    console.error('保存原料失败', e)
    saveError.value = e.response?.data?.detail || '保存失败，请重试'
  } finally {
    saving.value = false
  }
}

// 加载单位列表
loadUnits()
</script>

<style scoped>
.ingredient-item {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
}

.ingredient-item:last-child {
  border-bottom: none;
}

.ingredient-clickable {
  cursor: pointer;
  transition: background-color 0.2s;
  padding: 4px 8px;
  margin: -4px -8px;
  border-radius: 4px;
}

.ingredient-clickable:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.drag-handle {
  cursor: grab;
}

.edit-table-header {
  background: rgb(var(--v-theme-surface-variant));
  font-weight: 500;
}

.edit-table-row {
  transition: background-color 0.15s;
}

.edit-table-row:hover {
  background: rgba(var(--v-theme-primary), 0.02);
}

.border-bottom {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
}
</style>
