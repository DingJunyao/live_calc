<template>
  <v-container class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <h1 class="text-h5">价格记录</h1>
      <v-btn color="primary" prepend-icon="mdi-refresh" :loading="loading" @click="loadRecords">刷新</v-btn>
    </div>

    <v-text-field
      v-model="searchQuery"
      label="搜索商品..."
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      hide-details
      clearable
      class="mb-4"
      @update:model-value="debouncedSearch"
    />

    <v-progress-circular v-if="loading" indeterminate color="primary" class="ma-4" />

    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadRecords">重试</v-btn>
      </template>
    </v-alert>

    <v-card v-else elevation="0" variant="outlined">
      <v-list lines="two">
        <v-list-item v-for="record in records" :key="record.id">
          <template #prepend>
            <v-avatar color="primary" size="40">
              <span class="text-white">{{ record.product_name?.charAt(0) }}</span>
            </v-avatar>
          </template>

          <v-list-item-title>{{ record.product_name }}</v-list-item-title>
          <v-list-item-subtitle>
            ¥{{ formatPrice(record.price) }} / {{ record.original_quantity }}{{ record.original_unit }}
            <template v-if="record.merchant_name">· {{ record.merchant_name }}</template>
          </v-list-item-subtitle>

          <template #append>
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="deleteRecord(record.id)" />
          </template>
        </v-list-item>

        <v-list-item v-if="records.length === 0">
          <v-list-item-title class="text-center">暂无记录</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>

    <div v-if="total > 0" class="d-flex justify-center align-center ga-4 py-4">
      <v-select
        v-model="pageSize"
        :items="[10, 20, 50, 100]"
        label="每页"
        variant="outlined"
        density="compact"
        hide-details
        style="max-width: 100px"
        @update:model-value="handlePageSizeChange"
      />
      <v-pagination
        v-model="currentPage"
        :length="totalPages"
        :total-visible="5"
        rounded="circle"
      />
      <span class="text-caption">共 {{ total }} 条</span>
    </div>

    <v-btn
      icon="mdi-plus"
      color="primary"
      size="large"
      elevation="8"
      class="position-fixed"
      style="bottom: 80px; right: 16px"
      @click="showAddDialog = true"
    />

    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>添加价格记录</v-card-title>
        <v-card-text>
          <v-alert type="info">功能即将推出，请先在「商品管理」中添加商品。</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/api/client'

interface PriceRecord {
  id: number
  product_id: number
  product_name: string
  merchant_name?: string
  price: number | string
  original_quantity: number
  original_unit: string
  recorded_at: string
}

const records = ref<PriceRecord[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref('')
const showAddDialog = ref(false)
const pageSize = ref(20)
const currentPage = ref(1)
const total = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadRecords()
  }, 300)
}

const loadRecords = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = { skip, limit: pageSize.value }
    if (searchQuery.value) params.search = searchQuery.value
    const response = await api.get('/products', { params })
    records.value = response.items || []
    total.value = response.total || 0
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  loadRecords()
}

watch(currentPage, loadRecords)

const formatPrice = (price: any) => (parseFloat(price) || 0).toFixed(2)

const deleteRecord = async (id: number) => {
  if (!confirm('确定删除?')) return
  try {
    await api.delete(`/products/${id}`)
    loadRecords()
  } catch (e: any) {
    console.error('删除失败', e)
  }
}

onMounted(loadRecords)
</script>
