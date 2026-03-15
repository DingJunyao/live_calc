<template>
  <div class="association-list">
    <div class="section-header">
      <h2 class="section-title">
        {{ type === 'product' ? '关联原料' : '关联商品' }}
      </h2>
      <button @click="$emit('edit')" class="btn-edit">
        <i class="mdi mdi-pencil"></i> 管理
      </button>
    </div>

    <div v-if="associations.length === 0" class="no-data">
      <i class="mdi mdi-link-variant"></i>
      <p>暂无关联数据</p>
    </div>

    <div v-else class="association-items">
      <div
        v-for="assoc in associations"
        :key="assoc.id"
        class="association-item"
        @click="handleItemClick(assoc)"
      >
        <div class="item-icon">
          <i class="mdi" :class="type === 'product' ? 'mdi-food' : 'mdi-shopping'"></i>
        </div>
        <div class="item-info">
          <div class="item-name">{{ assoc.name }}</div>
          <div v-if="assoc.brand" class="item-brand">{{ assoc.brand }}</div>
        </div>
        <div class="item-arrow">
          <i class="mdi mdi-chevron-right"></i>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Association } from '../types'

const props = defineProps<{
  associations: Association[]
  type: 'product' | 'ingredient'
}>()

const emit = defineEmits<{
  edit: []
  click: [association: Association]
}>()

function handleItemClick(assoc: Association) {
  console.log('AssociationList - 点击关联项:', assoc)
  console.log('AssociationList - 当前 type:', props.type)
  emit('click', assoc)
}
</script>

<style scoped>
.association-list {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.btn-edit {
  background-color: #42b883;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-edit:hover {
  background-color: #3aa876;
}

.association-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.association-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: #f9f9f9;
  border-radius: 6px;
  transition: background-color 0.3s;
}

.association-item:hover {
  background-color: #f0f0f0;
}

.item-icon {
  width: 40px;
  height: 40px;
  background-color: #e8f5e9;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #42b883;
  font-size: 20px;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
}

.item-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.item-brand {
  font-size: 13px;
  color: #666;
}

.item-arrow {
  color: #999;
  font-size: 18px;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
}

.no-data i {
  font-size: 48px;
  margin-bottom: 12px;
  color: #e5e5e5;
}

.no-data p {
  margin: 0;
  font-size: 14px;
}

@media (max-width: 768px) {
  .association-list {
    padding: 12px;
  }

  .item-icon {
    width: 36px;
    height: 36px;
    font-size: 18px;
  }

  .item-name {
    font-size: 13px;
  }

  .item-brand {
    font-size: 12px;
  }

  .item-arrow {
    font-size: 16px;
  }
}
</style>
