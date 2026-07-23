<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">未使用图片清理</v-app-bar-title>
    <template #append>
      <v-btn
        v-if="selected.length > 0"
        color="error"
        variant="tonal"
        size="small"
        class="mr-2"
        :loading="deleting"
        :disabled="deleting"
        @click="confirmDelete"
      >
        <v-icon start size="small">mdi-delete</v-icon>
        删除选中（{{ selected.length }}）
      </v-btn>
    </template>
  </v-app-bar>

  <v-container class="pa-4" style="margin-top: 48px">
    <v-alert
      v-if="errorMsg"
      type="error"
      closable
      class="mb-4"
      @click:close="errorMsg = ''"
    >{{ errorMsg }}</v-alert>

    <v-alert
      v-if="successMsg"
      type="success"
      closable
      class="mb-4"
      @click:close="successMsg = ''"
    >{{ successMsg }}</v-alert>

    <v-skeleton-loader
      v-if="scanning"
      type="card, list-item-two-line, card"
      class="mx-auto"
      max-width="600"
    />

    <template v-else>
      <!-- 存储概览 -->
      <v-card class="mb-4" elevation="0">
        <v-card-text class="d-flex ga-4 flex-wrap">
          <div class="text-body-2">
            <v-icon class="mr-1" color="success">mdi-check-circle</v-icon>
            已用: <strong>{{ stats.used_images }}</strong> 张
            · {{ formatSize(stats.used_size) }}
          </div>
          <div class="text-body-2">
            <v-icon class="mr-1" color="warning">mdi-alert-circle</v-icon>
            未用: <strong>{{ stats.unused_images }}</strong> 张
            · {{ formatSize(stats.unused_size) }}
          </div>
          <div class="text-body-2">
            <v-icon class="mr-1" color="medium-emphasis">mdi-folder</v-icon>
            总计: <strong>{{ stats.total_images }}</strong> 张
            · {{ formatSize(stats.used_size + stats.unused_size) }}
          </div>
        </v-card-text>
      </v-card>

      <!-- 分组列表 -->
      <v-expansion-panels v-model="expandedPanels" multiple>
        <v-expansion-panel v-for="group in groups" :key="group.key" :value="group.key">
          <v-expansion-panel-title class="text-subtitle-2 font-weight-medium">
            <span>{{ group.label }}</span>
            <v-chip size="x-small" class="ml-2">
              {{ group.count }} 张 · {{ formatSize(group.total_size) }}
            </v-chip>
            <v-spacer />
            <v-btn
              v-if="group.count > 0"
              size="x-small"
              color="error"
              variant="text"
              :loading="deleting"
              @click.stop="deleteGroup(group)"
              class="ml-2"
            >
              <v-icon size="small">mdi-delete</v-icon>
              删除本组
            </v-btn>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row>
              <v-col
                v-for="img in group.images"
                :key="img.key"
                cols="6"
                sm="4"
                md="3"
                lg="2"
              >
                <v-card
                  elevation="1"
                  :color="selected.includes(img.key) ? 'primary' : undefined"
                  @click="toggleSelect(img.key)"
                  style="cursor: pointer"
                >
                  <v-img
                    :src="img.url"
                    height="100"
                    cover
                    class="bg-grey-lighten-3"
                  >
                    <template #placeholder>
                      <div class="d-flex align-center justify-center fill-height">
                        <v-icon color="grey">mdi-image-off</v-icon>
                      </div>
                    </template>
                  </v-img>
                  <v-card-text class="pa-1 text-caption text-center">
                    <div class="text-truncate">{{ img.filename }}</div>
                    <div class="text-medium-emphasis">{{ formatSize(img.file_size) }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <div v-if="group.images.length === 0" class="text-center py-4 text-body-2 text-medium-emphasis">
              无
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-card-text
        v-if="!scanning && groups.length === 0"
        class="text-center py-8"
      >
        <v-icon size="64" color="success">mdi-check-circle-outline</v-icon>
        <div class="text-body-1 mt-2">没有未使用的图片</div>
      </v-card-text>
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDisplay } from 'vuetify'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => { router.back() }

const scanning = ref(false)
const deleting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const expandedPanels = ref<string[]>([])

interface ImageItem {
  key: string
  filename: string
  url: string
  file_size: number
  last_used_at: string | null
}

interface ImageGroup {
  key: string
  label: string
  images: ImageItem[]
  count: number
  total_size: number
}

interface Stats {
  total_images: number
  used_images: number
  unused_images: number
  used_size: number
  unused_size: number
}

const stats = ref<Stats>({ total_images: 0, used_images: 0, unused_images: 0, used_size: 0, unused_size: 0 })
const groups = ref<ImageGroup[]>([])
const selected = ref<string[]>([])

const formatSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const idx = Math.min(i, units.length - 1)
  return `${(bytes / Math.pow(1024, idx)).toFixed(1)} ${units[idx]}`
}

const isGroupAllSelected = (groupKey: string): boolean => {
  const group = groups.value.find(g => g.key === groupKey)
  if (!group || group.images.length === 0) return false
  return group.images.every(img => selected.value.includes(img.key))
}

const toggleGroup = (groupKey: string): void => {
  const group = groups.value.find(g => g.key === groupKey)
  if (!group) return
  const allSelected = isGroupAllSelected(groupKey)
  const groupKeys = group.images.map(img => img.key)
  if (allSelected) {
    selected.value = selected.value.filter(k => !groupKeys.includes(k))
  } else {
    const existing = new Set(selected.value)
    for (const k of groupKeys) existing.add(k)
    selected.value = [...existing]
  }
}

const toggleSelect = (key: string): void => {
  const idx = selected.value.indexOf(key)
  if (idx >= 0) {
    selected.value.splice(idx, 1)
  } else {
    selected.value.push(key)
  }
}

const deleteGroup = async (group: ImageGroup) => {
  if (!group.images.length) return
  selected.value = group.images.map(img => img.key)
  await confirmDelete()
}

const loadData = async () => {
  scanning.value = true
  errorMsg.value = ''
  selected.value = []

  try {
    // 先扫描
    await api.post('/admin/images/scan')
    // 获取分组数据
    const resp = await api.get('/admin/images/unused')
    stats.value = resp.stats || { total_images: 0, used_images: 0, unused_images: 0, used_size: 0, unused_size: 0 }
    groups.value = resp.groups || []
    // 默认展开所有组
    expandedPanels.value = (resp.groups || []).map((g: ImageGroup) => g.key)
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    scanning.value = false
  }
}

const confirmDelete = async () => {
  if (!selected.value.length) return
  deleting.value = true
  errorMsg.value = ''
  successMsg.value = ''
  try {
    const resp = await api.post('/admin/images/unused/delete', {
      keys: selected.value,
    })
    successMsg.value = `已删除 ${resp.deleted?.length || 0} 张图片`
    if (resp.errors?.length) {
      errorMsg.value = `删除失败：${resp.errors.join('；')}`
    }
    await loadData()
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || e.message || '删除失败'
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
