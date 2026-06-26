<template>
  <v-dialog :model-value="modelValue" @update:model-value="$emit('update:model-value', $event)" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        原料黑名单
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="$emit('update:model-value', false)" />
      </v-card-title>
      <v-card-text>
        <!-- 快速选择：过敏原分组 -->
        <div v-if="allergenGroups.length > 0" class="mb-4">
          <div class="d-flex align-center mb-2">
            <span class="text-caption text-medium-emphasis">快速选择</span>
            <v-spacer />
            <v-btn
              v-if="selectedGroupIds.size > 0"
              color="primary"
              size="small"
              variant="tonal"
              :loading="saving"
              @click="saveSelectedGroups"
            >
              <v-icon start size="small">mdi-check</v-icon>
              保存 ({{ selectedGroupIds.size }} 组)
            </v-btn>
          </div>
          <v-chip-group>
            <v-chip
              v-for="group in allergenGroups"
              :key="group.id"
              :color="isGroupFullyAdded(group) ? 'grey' : selectedGroupIds.has(group.id) ? 'primary' : undefined"
              :variant="isGroupFullyAdded(group) ? 'outlined' : selectedGroupIds.has(group.id) ? 'tonal' : 'outlined'"
              :disabled="isGroupFullyAdded(group)"
              size="small"
              filter
              @click="toggleGroup(group)"
            >
              {{ group.name }}
              <template #append v-if="isGroupFullyAdded(group)">
                <v-icon size="small">mdi-check</v-icon>
              </template>
              <template #append v-else-if="selectedGroupIds.has(group.id)">
                <v-icon size="small">mdi-plus</v-icon>
              </template>
            </v-chip>
          </v-chip-group>
        </div>

        <v-divider class="mb-4" />

        <!-- 手动添加 -->
        <div class="mb-4">
          <v-autocomplete
            v-model="selectedIngredient"
            :items="searchResults"
            item-title="name"
            item-value="id"
            label="搜索原料添加到黑名单"
            variant="outlined"
            density="compact"
            hide-details="auto"
            clearable
            @update:search="searchIngredients"
            @update:model-value="onSelectIngredient"
          >
            <template #no-data>
              <v-list-item>
                <v-list-item-title>未找到原料，请尝试其他关键词</v-list-item-title>
              </v-list-item>
            </template>
          </v-autocomplete>
        </div>

        <!-- 黑名单列表 -->
        <div v-if="loading" class="text-center pa-4">
          <v-progress-circular indeterminate />
        </div>
        <div v-else-if="blacklistItems.length === 0" class="text-center pa-4 text-medium-emphasis">
          暂无屏蔽的原料
        </div>
        <v-list v-else density="compact">
          <v-list-item
            v-for="item in blacklistItems"
            :key="item.id"
            :title="item.ingredient_name"
            :subtitle="getSubtitle(item)"
          >
            <template #append>
              <v-btn
                icon="mdi-close"
                variant="text"
                size="small"
                color="error"
                @click="removeItem(item)"
              />
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- 错误提示 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="4000" location="top">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:model-value': [value: boolean] }>()

interface BlacklistItem {
  id: number
  ingredient_id: number
  ingredient_name: string | null
  reason: string | null
  source: string
  allergen_group_name: string | null
}

interface AllergenGroup {
  id: number
  name: string
  ingredient_ids: number[]
}

const blacklistItems = ref<BlacklistItem[]>([])
const allergenGroups = ref<AllergenGroup[]>([])
const loading = ref(false)
const saving = ref(false)
const selectedGroupIds = ref<Set<number>>(new Set())
const snackbar = ref({ show: false, message: '', color: 'error' })

function showError(msg: string) {
  snackbar.value = { show: true, message: msg, color: 'error' }
}

function showSuccess(msg: string) {
  snackbar.value = { show: true, message: msg, color: 'success' }
}

// 搜索
const selectedIngredient = ref<any>(null)
const searchResults = ref<any[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null

async function loadBlacklist() {
  loading.value = true
  try {
    const data = await api.get('/blacklist', { params: { limit: 1000 } })
    blacklistItems.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error('加载黑名单失败', e)
  } finally {
    loading.value = false
  }
}

async function loadAllergenGroups() {
  try {
    const data = await api.get('/allergen-groups')
    allergenGroups.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error('加载过敏原分组失败', e)
  }
}

function isGroupFullyAdded(group: AllergenGroup): boolean {
  const blacklistedIds = new Set(blacklistItems.value.map(i => i.ingredient_id))
  return group.ingredient_ids.every(id => blacklistedIds.has(id))
}

function toggleGroup(group: AllergenGroup) {
  if (selectedGroupIds.value.has(group.id)) {
    selectedGroupIds.value.delete(group.id)
  } else {
    selectedGroupIds.value.add(group.id)
  }
  // 触发响应式更新
  selectedGroupIds.value = new Set(selectedGroupIds.value)
}

async function saveSelectedGroups() {
  saving.value = true
  try {
    const allIds: number[] = []
    for (const gid of selectedGroupIds.value) {
      const group = allergenGroups.value.find(g => g.id === gid)
      if (group) {
        for (const id of group.ingredient_ids) {
          if (!allIds.includes(id)) allIds.push(id)
        }
      }
    }
    if (allIds.length > 0) {
      await api.post('/blacklist/batch', { ingredient_ids: allIds })
      showSuccess(`已添加 ${allIds.length} 种原料到黑名单`)
    }
    selectedGroupIds.value = new Set()
    await loadBlacklist()
  } catch (e: any) {
    showError('保存失败：' + (e?.userMessage || e?.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

async function removeItem(item: BlacklistItem) {
  try {
    await api.delete(`/blacklist/${item.ingredient_id}`)
    blacklistItems.value = blacklistItems.value.filter(i => i.id !== item.id)
  } catch (e: any) {
    showError('移除失败：' + (e?.userMessage || e?.message || '未知错误'))
  }
}

function searchIngredients(search: string | null) {
  if (!search || search.length < 1) {
    searchResults.value = []
    return
  }
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    try {
      const data = await api.get(`/ingredients/search-by-name/${encodeURIComponent(search)}`)
      searchResults.value = Array.isArray(data) ? data : []
    } catch {
      searchResults.value = []
    }
  }, 300)
}

async function onSelectIngredient(ingredientId: number | null) {
  if (!ingredientId) return
  try {
    await api.post('/blacklist', { ingredient_id: ingredientId })
    selectedIngredient.value = null
    await loadBlacklist()
  } catch (e: any) {
    showError('添加失败：' + (e?.userMessage || e?.message || '未知错误'))
  }
}

function getSubtitle(item: BlacklistItem): string {
  const parts: string[] = []
  if (item.source === 'allergen_group' && item.allergen_group_name) {
    parts.push(`来自 ${item.allergen_group_name}`)
  } else {
    parts.push('手动添加')
  }
  if (item.reason) parts.push(item.reason)
  return parts.join(' · ')
}

watch(() => props.modelValue, (val) => {
  if (val) {
    selectedGroupIds.value = new Set()
    loadBlacklist()
    loadAllergenGroups()
  }
})
</script>
