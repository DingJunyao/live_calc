<template>
  <v-container fluid>
    <!-- 顶部标题栏 -->
    <v-app-bar elevation="0" color="background" density="comfortable" class="mb-4">
      <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
      <v-app-bar-title class="text-h6">商家管理</v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadMerchants" />
      </template>
    </v-app-bar>

    <v-text-field
      v-model="search"
      label="搜索商家..."
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      density="compact"
      hide-details
      clearable
      class="mb-4"
      @update:model-value="debouncedSearch"
    />

    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadMerchants">重试</v-btn>
      </template>
    </v-alert>

    <!-- 商家列表 -->
    <v-card v-else elevation="0">
      <v-list lines="two">
        <v-list-item
          v-for="item in items"
          :key="item.id"
          @click="openEditDialog(item)"
        >
          <template #prepend>
            <v-avatar color="tertiary" size="40">
              <v-icon>mdi-store</v-icon>
            </v-avatar>
          </template>

          <v-list-item-title>{{ item.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ item.address || '暂无地址' }}</v-list-item-subtitle>

          <template #append>
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click.stop="deleteItem(item.id)" />
          </template>
        </v-list-item>

        <v-list-item v-if="items.length === 0">
          <v-list-item-title class="text-center text-medium-emphasis">
            暂无商家
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- 分页器 -->
    <div v-if="total > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
      <v-pagination
        v-model="currentPage"
        :length="totalPages"
        :total-visible="3"
        rounded="circle"
        density="comfortable"
      />
      <div class="d-flex align-center ga-2">
        <v-select
          v-model="pageSize"
          :items="[10, 20, 50, 100]"
          label="每页"
          variant="outlined"
          density="compact"
          hide-details
          style="max-width: 90px"
          @update:model-value="handlePageSizeChange"
        />
        <span class="text-caption text-medium-emphasis">共 {{ total }} 条</span>
      </div>
    </div>

    <v-btn
      color="primary"
      class="ma-4"
      prepend-icon="mdi-plus"
      @click="openEditDialog()"
    >
      添加商家
    </v-btn>

    <!-- 添加/编辑对话框 -->
    <v-dialog v-model="addDialog" max-width="500">
      <v-card>
        <v-card-title>{{ editingItem ? '编辑商家' : '添加商家' }}</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="form.name"
              label="商家名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-text-field
              v-model="form.address"
              label="地址"
              variant="outlined"
              class="mb-4"
            />
            <v-text-field
              v-model="form.phone"
              label="电话"
              variant="outlined"
            />
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/api/client'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

interface Merchant {
  id: number
  name: string
  address?: string
  phone?: string
  latitude?: number
  longitude?: number
  created_at?: string
}

const items = ref<Merchant[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const addDialog = ref(false)
const editingItem = ref<Merchant | null>(null)
const saving = ref(false)
const form = ref({
  name: '',
  address: '',
  phone: '',
})

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadMerchants()
  }, 300)
}

const loadMerchants = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = {
      skip,
      limit: pageSize.value
    }
    if (search.value) {
      params.search = search.value
    }

    const response = await api.get('/merchants', { params })
    items.value = response.items || []
    total.value = response.total || 0
  } catch (e: any) {
    console.error('加载商家失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  loadMerchants()
}

watch(currentPage, () => {
  loadMerchants()
})

const openEditDialog = (item?: Merchant) => {
  editingItem.value = item || null
  if (item) {
    form.value = {
      name: item.name,
      address: item.address || '',
      phone: item.phone || '',
    }
  } else {
    form.value = { name: '', address: '', phone: '' }
  }
  addDialog.value = true
}

const saveItem = async () => {
  if (!form.value.name.trim()) return

  saving.value = true
  try {
    if (editingItem.value) {
      const response = await api.put(`/merchants/${editingItem.value.id}`, form.value)
      const index = items.value.findIndex(i => i.id === editingItem.value!.id)
      if (index !== -1) {
        items.value[index] = response
      }
    } else {
      const response = await api.post('/merchants', form.value)
      items.value.unshift(response)
      total.value++
    }
    addDialog.value = false
  } catch (e: any) {
    console.error('保存商家失败', e)
  } finally {
    saving.value = false
  }
}

const deleteItem = async (id: number) => {
  try {
    await api.delete(`/merchants/${id}`)
    const index = items.value.findIndex(i => i.id === id)
    if (index !== -1) {
      items.value.splice(index, 1)
      total.value--
    }
  } catch (e: any) {
    console.error('删除商家失败', e)
  }
}

onMounted(() => {
  loadMerchants()
  window.addEventListener('app-refresh', loadMerchants)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', loadMerchants)
})
</script>
