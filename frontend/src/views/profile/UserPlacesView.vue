<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">我的常用地点</v-app-bar-title>
  </v-app-bar>

  <v-container fluid>
    <v-alert v-if="error" type="error" class="ma-4" closable @click:close="error = null">
      {{ error }}
    </v-alert>

    <v-card elevation="0" class="mb-4">
      <v-list v-if="places.length > 0" lines="two">
        <v-list-item v-for="item in places" :key="item.id">
          <template #prepend>
            <v-icon
              :icon="kindIcon(item.kind)"
              :color="item.is_default ? 'primary' : undefined"
            />
          </template>
          <v-list-item-title>
            {{ item.name }}
            <v-icon v-if="item.is_default" size="small" color="primary" class="ms-1">mdi-star</v-icon>
          </v-list-item-title>
          <v-list-item-subtitle v-if="item.address">{{ item.address }}</v-list-item-subtitle>
          <v-list-item-subtitle class="text-caption">
            {{ kindLabel(item.kind) }} · 视野 {{ item.view_radius_km ?? 5 }} km · {{ item.latitude.toFixed(4) }}, {{ item.longitude.toFixed(4) }}
          </v-list-item-subtitle>
          <template #append>
            <div class="d-flex ga-1">
              <v-btn
                icon="mdi-star-outline"
                size="small"
                variant="text"
                :color="item.is_default ? 'primary' : undefined"
                :disabled="item.is_default"
                :title="item.is_default ? '已是默认' : '设为默认'"
                @click="setDefault(item)"
              />
              <v-btn icon="mdi-pencil" size="small" variant="text" color="primary" @click="openEditDialog(item)" />
              <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="deleteItem(item)" />
            </div>
          </template>
        </v-list-item>
      </v-list>
      <v-list v-else>
        <v-list-item>
          <v-list-item-title class="text-center text-medium-emphasis">
            还没有常用地点，点右下角 + 添加（家、公司等）
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>

    <p class="text-caption text-medium-emphasis px-2">
      常用地点用于商家管理地图默认聚焦。设为默认的地点会在每次进入地图时作为中心（约 5km 视野）。
    </p>

    <v-btn
      icon="mdi-plus"
      color="primary"
      size="large"
      elevation="6"
      class="fab-button"
      @click="openEditDialog()"
    />

    <!-- 添加/编辑对话框 -->
    <v-dialog v-model="addDialog" max-width="500" :fullscreen="!isDesktop">
      <v-card>
        <v-card-title>{{ editingItem ? '编辑地点' : '添加地点' }}</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="form.name"
              label="名称（如：家、公司）"
              variant="outlined"
              required
              class="mb-4"
            />

            <v-select
              v-model="form.kind"
              :items="kindItems"
              item-title="label"
              item-value="value"
              label="类型"
              variant="outlined"
              class="mb-4"
            />

            <v-select
              v-model="form.viewRadius"
              :items="radiusItems"
              item-title="label"
              item-value="value"
              label="地图视野范围（聚焦时缩放）"
              variant="outlined"
              class="mb-4"
            />

            <v-text-field v-model="form.address" label="地址（可选）" variant="outlined" class="mb-4" />

            <div class="text-subtitle-2 mb-2">位置</div>
            <MapPicker v-model="pickerCoords" :show-switcher="true" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="addDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveItem">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { getErrorMessage } from '@/utils/errorHandler'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import MapPicker from '@/components/map/MapPicker.vue'
import type { Coordinate } from '@/utils/map/mapTypes'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()
const goBack = () => router.back()

interface PlaceOption {
  id: number
  name: string
  kind: string
  latitude: number
  longitude: number
  address?: string | null
  is_default?: boolean
  view_radius_km?: number
}

const places = ref<PlaceOption[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const addDialog = ref(false)
const editingItem = ref<PlaceOption | null>(null)
const saving = ref(false)
const pickerCoords = ref<Coordinate | undefined>()
const form = ref({ name: '', kind: 'custom', address: '', viewRadius: 5 })

const kindItems = [
  { label: '家', value: 'home' },
  { label: '公司', value: 'work' },
  { label: '其他', value: 'custom' },
]

const radiusItems = [
  { label: '1 km', value: 1 },
  { label: '2 km', value: 2 },
  { label: '5 km', value: 5 },
  { label: '10 km', value: 10 },
  { label: '20 km', value: 20 },
  { label: '50 km', value: 50 },
]

const kindLabel = (k: string) => kindItems.find(i => i.value === k)?.label || '其他'

const kindIcon = (k: string) => {
  if (k === 'home') return 'mdi-home'
  if (k === 'work') return 'mdi-office-building'
  return 'mdi-map-marker'
}

const loadPlaces = async () => {
  loading.value = true
  error.value = null
  try {
    const data = await api.get('/places')
    places.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    error.value = getErrorMessage(e, '加载失败')
  } finally {
    loading.value = false
  }
}

const openEditDialog = (item?: PlaceOption) => {
  editingItem.value = item || null
  if (item) {
    form.value = {
      name: item.name,
      kind: item.kind,
      address: item.address || '',
      viewRadius: item.view_radius_km ?? 5,
    }
    pickerCoords.value = { lat: item.latitude, lng: item.longitude }
  } else {
    form.value = { name: '', kind: 'custom', address: '', viewRadius: 5 }
    pickerCoords.value = undefined
  }
  addDialog.value = true
}

const saveItem = async () => {
  if (!form.value.name.trim()) return
  if (!pickerCoords.value) {
    error.value = '请在地图上选择一个位置'
    return
  }
  saving.value = true
  try {
    const data: any = {
      name: form.value.name,
      kind: form.value.kind,
      latitude: pickerCoords.value.lat,
      longitude: pickerCoords.value.lng,
      address: form.value.address || undefined,
      view_radius_km: form.value.viewRadius,
    }
    if (editingItem.value) {
      await api.put(`/places/${editingItem.value.id}`, data)
    } else {
      await api.post('/places', data)
    }
    addDialog.value = false
    await loadPlaces()
  } catch (e: any) {
    error.value = getErrorMessage(e, '保存失败')
  } finally {
    saving.value = false
  }
}

const setDefault = async (item: PlaceOption) => {
  try {
    await api.put(`/places/${item.id}/default`)
    await loadPlaces()
  } catch (e: any) {
    error.value = getErrorMessage(e, '设置默认失败')
  }
}

const deleteItem = async (item: PlaceOption) => {
  try {
    await api.delete(`/places/${item.id}`)
    await loadPlaces()
  } catch (e: any) {
    error.value = getErrorMessage(e, '删除失败')
  }
}

onMounted(() => {
  loadPlaces()
})
</script>

<style scoped>
.fab-button {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 10;
}
</style>
