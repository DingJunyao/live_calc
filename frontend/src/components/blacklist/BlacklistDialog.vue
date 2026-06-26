<template>
  <v-dialog :model-value="modelValue" @update:model-value="$emit('update:model-value', $event)" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        原料黑名单
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="$emit('update:model-value', false)" />
      </v-card-title>
      <v-card-text>
        <!-- 快速选择：原料黑名单分组（订阅/取消订阅） -->
        <div v-if="blacklistGroups.length > 0" class="mb-4">
          <div class="text-caption text-medium-emphasis mb-2">快速选择</div>
          <v-chip-group>
            <v-chip
              v-for="group in blacklistGroups"
              :key="group.id"
              :color="isGroupSubscribed(group.id) ? 'primary' : undefined"
              :variant="isGroupSubscribed(group.id) ? 'tonal' : 'outlined'"
              size="small"
              filter
              @click="toggleGroup(group.id)"
            >
              {{ group.name }}
              <template #append v-if="isGroupSubscribed(group.id)">
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

        <!-- 已订阅的分组 -->
        <div v-if="subscribedGroups.length > 0" class="mb-4">
          <div class="text-caption text-medium-emphasis mb-2">已订阅的分组</div>
          <v-expansion-panels variant="accordion">
            <v-expansion-panel
              v-for="sg in subscribedGroups"
              :key="'sg-' + sg.id"
              :title="sg.name + '（' + sg.ingredient_count + ' 种原料）'"
            >
              <v-expansion-panel-text>
                <v-chip
                  v-for="ing in sg.ingredients"
                  :key="'sgi-' + ing.id"
                  size="small"
                  class="mr-1 mb-1"
                  label
                >
                  {{ ing.name }}
                </v-chip>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- 手动黑名单列表 -->
        <div class="text-caption text-medium-emphasis mb-2">手动添加</div>
        <div v-if="loading" class="text-center pa-4">
          <v-progress-circular indeterminate />
        </div>
        <div v-else-if="manualBlacklistItems.length === 0" class="text-center pa-4 text-medium-emphasis">
          暂无手动添加的原料
        </div>
        <v-list v-else density="compact">
          <v-list-item
            v-for="item in manualBlacklistItems"
            :key="item.id"
            :title="item.ingredient_name"
            :subtitle="item.reason || ''"
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

    <!-- 提示 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="4000" location="top">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '@/api/client'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:model-value': [value: boolean] }>()

interface BlacklistItem {
  id: number
  ingredient_id: number
  ingredient_name: string | null
  reason: string | null
  source: string
}

interface BlacklistGroupPublic {
  id: number
  name: string
  ingredient_ids: number[]
}

interface SubscribedGroup {
  id: number
  name: string
  ingredient_count: number
  ingredients: { id: number; name: string }[]
}

const manualBlacklistItems = ref<BlacklistItem[]>([])
const blacklistGroups = ref<BlacklistGroupPublic[]>([])
const subscribedGroups = ref<SubscribedGroup[]>([])
const subscribedGroupIds = ref<Set<number>>(new Set())
const loading = ref(false)
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

function isGroupSubscribed(gid: number): boolean {
  return subscribedGroupIds.value.has(gid)
}

async function loadData() {
  loading.value = true
  try {
    const [manualData, groupsData, subGroupsData] = await Promise.all([
      api.get('/blacklist', { params: { limit: 1000 } }),
      api.get('/blacklist-groups'),
      api.get('/blacklist/groups'),
    ])
    manualBlacklistItems.value = Array.isArray(manualData) ? manualData : []
    blacklistGroups.value = Array.isArray(groupsData) ? groupsData : []
    subscribedGroups.value = Array.isArray(subGroupsData) ? subGroupsData : []
    subscribedGroupIds.value = new Set(subscribedGroups.value.map((g: SubscribedGroup) => g.id))
  } catch (e) {
    console.error('加载黑名单数据失败', e)
  } finally {
    loading.value = false
  }
}

async function toggleGroup(gid: number) {
  try {
    if (subscribedGroupIds.value.has(gid)) {
      await api.delete(`/blacklist/groups/${gid}`)
      subscribedGroupIds.value.delete(gid)
      subscribedGroupIds.value = new Set(subscribedGroupIds.value)
      showSuccess('已取消订阅')
    } else {
      await api.post('/blacklist/groups', { group_ids: [gid] })
      subscribedGroupIds.value.add(gid)
      subscribedGroupIds.value = new Set(subscribedGroupIds.value)
      showSuccess('已订阅分组')
    }
    // 重新加载分组详情
    const subGroupsData = await api.get('/blacklist/groups')
    subscribedGroups.value = Array.isArray(subGroupsData) ? subGroupsData : []
  } catch (e: any) {
    showError('操作失败：' + (e?.userMessage || e?.message || '未知错误'))
  }
}

async function removeItem(item: BlacklistItem) {
  try {
    await api.delete(`/blacklist/${item.ingredient_id}`)
    manualBlacklistItems.value = manualBlacklistItems.value.filter(i => i.id !== item.id)
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
    // 重新加载手动列表
    const manualData = await api.get('/blacklist', { params: { limit: 1000 } })
    manualBlacklistItems.value = Array.isArray(manualData) ? manualData : []
  } catch (e: any) {
    showError('添加失败：' + (e?.userMessage || e?.message || '未知错误'))
  }
}

watch(() => props.modelValue, (val) => {
  if (val) {
    loadData()
  }
})
</script>
