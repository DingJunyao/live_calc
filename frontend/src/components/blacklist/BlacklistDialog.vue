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
          <div class="text-caption text-medium-emphasis mb-2">快速选择</div>
          <v-chip-group>
            <v-chip
              v-for="group in allergenGroups"
              :key="group.id"
              :color="isGroupFullyAdded(group) ? 'grey' : 'primary'"
              :variant="isGroupFullyAdded(group) ? 'outlined' : 'tonal'"
              :disabled="isGroupFullyAdded(group)"
              :loading="addingGroupId === group.id"
              size="small"
              @click="addGroup(group)"
            >
              {{ group.name }}
              <template #append v-if="isGroupFullyAdded(group)">
                <v-icon size="small">mdi-check</v-icon>
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
const addingGroupId = ref<number | null>(null)
const snackbar = ref({ show: false, message: '', color: 'error' })

function showError(msg: string) {
  snackbar.value = { show: true, message: msg, color: 'error' }
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

async function addGroup(group: AllergenGroup) {
  addingGroupId.value = group.id
  try {
    await api.post('/blacklist/batch', {
      ingredient_ids: group.ingredient_ids,
      source: 'allergen_group',
      allergen_group_id: group.id,
    })
    await loadBlacklist()
  } catch (e: any) {
    showError('添加失败：' + (e?.userMessage || e?.message || '未知错误'))
  } finally {
    addingGroupId.value = null
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
      const { data } = await api.get(`/ingredients/search-by-name/${encodeURIComponent(search)}`)
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
    loadBlacklist()
    loadAllergenGroups()
  }
})
</script>
