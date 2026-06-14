<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push('/prices')" />
    <v-app-bar-title class="text-h6">快速填写</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-check-all" variant="text" :loading="saving" @click="saveAll" />
    </template>
  </v-app-bar>

  <v-container fluid class="pa-4 list-grid-container" style="margin-top: 56px;">
    <v-autocomplete
      v-model="selectedMerchantId"
      :items="merchants"
      item-title="name"
      item-value="id"
      label="选择商家"
      variant="outlined"
      density="compact"
      hide-details
      class="mb-3"
      @update:model-value="onMerchantChange"
    />

    <template v-if="!selectedMerchantId">
      <div class="text-center py-8 text-medium-emphasis">请先选择商家</div>
    </template>

    <template v-else>
      <div class="text-caption text-medium-emphasis mb-3">
        选商家后自动列出历史所有商品，只保存填了价格的
      </div>
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

interface Merchant {
  id: number
  name: string
}

const merchants = ref<Merchant[]>([])
const selectedMerchantId = ref<number | null>(null)
const saving = ref(false)

// 加载商家列表
const loadMerchants = async () => {
  try {
    const res = await api.get('/merchants', { params: { limit: 100 } })
    merchants.value = res.items || []
  } catch {
    merchants.value = []
  }
}

const onMerchantChange = (val: number | null) => {
  // 将在 Task 3 中实现：加载该商家的历史商品列表
}

const saveAll = async () => {
  // 将在 Task 5 中实现：批量保存所有填写了价格的记录
}

onMounted(() => {
  loadMerchants()
})
</script>
