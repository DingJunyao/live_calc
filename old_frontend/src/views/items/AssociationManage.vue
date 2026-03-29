<template>
  <PageHeader :title="pageTitle" :show-back="true" />

  <div class="association-manage">
    <div class="association-section">
      <h3 class="section-title">可添加的{{ targetTypeName }}</h3>
      <div class="search-box">
        <input
          v-model="searchTerm"
          type="text"
          placeholder="搜索..."
          class="search-input"
        />
      </div>
      <div class="items-list">
        <div
          v-for="item in filteredAvailableItems"
          :key="item.id"
          class="item-card"
          @click="addAssociation(item)"
        >
          <div class="item-name">{{ item.name }}</div>
          <div v-if="item.brand" class="item-brand">{{ item.brand }}</div>
          <i class="mdi mdi-plus"></i>
        </div>
        <div v-if="filteredAvailableItems.length === 0" class="no-data">
          <p>暂无数据</p>
        </div>
      </div>
    </div>

    <div class="association-section">
      <h3 class="section-title">已关联的{{ targetTypeName }}</h3>
      <div class="items-list">
        <div
          v-for="assoc in associations"
          :key="assoc.id"
          class="item-card associated"
          @click="removeAssociation(assoc)"
        >
          <div class="item-name">{{ assoc.name }}</div>
          <div v-if="assoc.brand" class="item-brand">{{ assoc.brand }}</div>
          <i class="mdi mdi-minus"></i>
        </div>
        <div v-if="associations.length === 0" class="no-data">
          <p>暂无关联</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { api } from '@/api/client'
import type { Association } from './types'

const route = useRoute()
const router = useRouter()

const type = computed(() => route.params.type as 'product' | 'ingredient')
const itemId = computed(() => parseInt(route.params.id as string))

const searchTerm = ref('')
const availableItems = ref<Association[]>([])
const associations = ref<Association[]>([])

const pageTitle = computed(() => {
  const typeName = type.value === 'product' ? '商品' : '原料'
  return `管理${typeName}关联`
})

const targetTypeName = computed(() => {
  return type.value === 'product' ? '原料' : '商品'
})

const filteredAvailableItems = computed(() => {
  if (!searchTerm.value) return availableItems.value
  const term = searchTerm.value.toLowerCase()
  return availableItems.value.filter(
    item =>
      item.name.toLowerCase().includes(term) ||
      (item.brand && item.brand.toLowerCase().includes(term))
  )
})

async function loadAvailableItems() {
  if (type.value === 'product') {
    // 商品详情页：加载所有原料
    const response = await api.get('/nutrition/ingredients', {
      params: { limit: 100 }
    })
    availableItems.value = response.data.map((ing: any) => ({
      id: ing.id,
      name: ing.name,
      type: 'ingredient' as const,
      created_at: ing.created_at
    }))
  } else {
    // 原料详情页：加载所有商品
    const response = await api.get('/products/entity', {
      params: { limit: 100 }
    })
    availableItems.value = response.data.items.map((prod: any) => ({
      id: prod.id,
      name: prod.name,
      brand: prod.brand,
      type: 'product' as const,
      created_at: prod.created_at
    }))
  }
}

async function loadAssociations() {
  // 已在 ItemDetail 中加载，这里简化处理
  associations.value = []
}

async function addAssociation(item: Association) {
  if (type.value === 'product') {
    // 为商品添加原料关联
    await api.put(`/products/entity/${itemId.value}`, {
      ingredient_id: item.id
    })
  } else {
    // TODO: 实现为商品添加原料关联
    alert('功能待实现')
  }

  await loadAssociations()
}

async function removeAssociation(assoc: Association) {
  if (type.value === 'product') {
    // 移除商品的原料关联
    await api.put(`/products/entity/${itemId.value}`, {
      ingredient_id: null
    })
  } else {
    // TODO: 实现移除关联
    alert('功能待实现')
  }

  await loadAssociations()
}

onMounted(() => {
  loadAvailableItems()
  loadAssociations()
})
</script>

<style scoped>
.association-manage {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.association-section {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 24px;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.search-box {
  margin-bottom: 16px;
}

.search-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #42b883;
}

.items-list {
  max-height: 400px;
  overflow-y: auto;
}

.item-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.item-card:hover {
  border-color: #42b883;
  background-color: #f9f9f9;
}

.item-card.associated {
  background-color: #e8f5e9;
  border-color: #c8e6c9;
}

.item-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.item-brand {
  font-size: 13px;
  color: #666;
}

.item-card i {
  font-size: 18px;
  color: #42b883;
}

.item-card.associated i {
  color: #c33;
}

.no-data {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.no-data p {
  margin: 0;
  font-size: 14px;
}

@media (max-width: 768px) {
  .association-manage {
    padding: 12px;
  }

  .association-section {
    padding: 12px;
  }

  .section-title {
    font-size: 16px;
  }
}
</style>
