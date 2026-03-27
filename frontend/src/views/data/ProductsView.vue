<template>
  <v-container fluid>
    <!-- 顶部标题栏 -->
    <v-app-bar elevation="0" color="background" density="comfortable" class="mb-4">
      <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
      <v-app-bar-title class="text-h6">商品管理</v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadProducts" />
      </template>
    </v-app-bar>

    <v-text-field
      v-model="search"
      label="搜索商品..."
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
        <v-btn variant="text" @click="loadProducts">重试</v-btn>
      </template>
    </v-alert>

    <!-- 商品列表 -->
    <v-card v-else elevation="0">
      <v-list lines="two">
        <v-list-item
          v-for="item in items"
          :key="item.id"
          :to="`/data/products/${item.id}`"
        >
          <template #prepend>
            <v-avatar color="primary" size="40">
              <span class="text-white">{{ item.name?.charAt(0) }}</span>
            </v-avatar>
          </template>

          <v-list-item-title>{{ item.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ item.category || '未分类' }}</v-list-item-subtitle>

          <template #append>
            <v-btn icon="mdi-chevron-right" size="small" variant="text" />
          </template>
        </v-list-item>

        <v-list-item v-if="items.length === 0">
          <v-list-item-title class="text-center text-medium-emphasis">
            暂无商品
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- 分页器 -->
    <div v-if="total > 0" class="d-flex flex-wrap justify-center align-center ga-2 pa-4">
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

    <!-- FAB 浮动添加按钮 -->
    <v-btn
      icon="mdi-plus"
      color="primary"
      size="large"
      elevation="8"
      class="position-fixed"
      style="bottom: 80px; right: 24px"
      @click="showAddDialog = true"
    />

    <!-- 添加对话框 -->
    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>添加商品</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="form.name"
              label="商品名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-text-field
              v-model="form.category"
              label="分类"
              variant="outlined"
              class="mb-4"
            />
            <v-textarea
              v-model="form.description"
              label="描述"
              variant="outlined"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddDialog = false">取消</v-btn>
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

interface Product {
  id: number
  name: string
  category?: string
  description?: string
  created_at?: string
}

const items = ref<Product[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const showAddDialog = ref(false)
const saving = ref(false)
const form = ref({
  name: '',
  category: '',
  description: '',
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
    loadProducts()
  }, 300)
}

const loadProducts = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = {
      skip,
      limit: pageSize.value,
      sort_by: 'price_records'  // 按价格记录次数排序
    }
    if (search.value) {
      params.search = search.value
    }

    const response = await api.get('/products/entity', { params })
    items.value = response.items || []
    total.value = response.total || 0
  } catch (e: any) {
    console.error('加载商品失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  loadProducts()
}

watch(currentPage, () => {
  loadProducts()
})

const saveItem = async () => {
  if (!form.value.name.trim()) return

  saving.value = true
  try {
    const response = await api.post('/products/entity', form.value)
    items.value.unshift(response)
    total.value++
    showAddDialog.value = false
    form.value = { name: '', category: '', description: '' }
  } catch (e: any) {
    console.error('保存商品失败', e)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadProducts()
  window.addEventListener('app-refresh', loadProducts)
})

onUnmounted(() => {
  window.removeEventListener('app-refresh', loadProducts)
})
</script>
