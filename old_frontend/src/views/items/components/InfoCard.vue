<template>
  <div class="info-card">
    <div class="info-card-header">
      <h2 class="info-title">基本信息</h2>
      <div class="header-actions">
        <button v-if="type === 'ingredient'" @click="$emit('merge')" class="btn-merge" title="合并到其他原料">
          <i class="mdi mdi-merge"></i> 合并
        </button>
        <button @click="$emit('edit')" class="btn-edit">
          <i class="mdi mdi-pencil"></i> 编辑
        </button>
      </div>
    </div>

    <div class="info-content">
      <div class="info-row">
        <span class="info-label">名称</span>
        <span class="info-value">{{ item.name }}</span>
      </div>

      <div class="info-row" v-if="type === 'product' && item.brand">
        <span class="info-label">品牌</span>
        <span class="info-value">{{ item.brand }}</span>
      </div>

      <div class="info-row" v-if="type === 'product' && item.barcodes && item.barcodes.length > 0">
        <span class="info-label">条码</span>
        <div class="barcode-list">
          <span
            v-for="(barcode, index) in item.barcodes"
            :key="index"
            class="barcode-tag"
            :class="{ 'primary': barcode.is_primary }"
          >
            {{ barcode.barcode }}
            <i v-if="barcode.is_primary" class="mdi mdi-star"></i>
          </span>
        </div>
      </div>

      <div class="info-row" v-if="item.image_url">
        <span class="info-label">图片</span>
        <img :src="item.image_url" :alt="item.name" class="item-image" />
      </div>

      <div class="info-row" v-if="item.tags && item.tags.length > 0">
        <span class="info-label">标签</span>
        <div class="tag-list">
          <span v-for="(tag, index) in item.tags" :key="index" class="tag">
            {{ tag }}
          </span>
        </div>
      </div>

      <div class="info-row" v-if="type === 'product' && item.ingredient_name">
        <span class="info-label">关联原料</span>
        <span
          class="info-value clickable"
          @click="handleIngredientClick"
        >
          {{ item.ingredient_name }}
          <i class="mdi mdi-chevron-right"></i>
        </span>
      </div>

      <div class="info-row" v-if="item.default_unit_name">
        <span class="info-label">默认单位</span>
        <span class="info-value">{{ item.default_unit_name }}</span>
      </div>

      <div class="info-row" v-if="item.aliases && item.aliases.length > 0">
        <span class="info-label">别名</span>
        <div class="alias-list">
          <span v-for="(alias, index) in item.aliases" :key="index" class="alias">
            {{ alias }}
          </span>
        </div>
      </div>

      <div class="info-row">
        <span class="info-label">创建时间</span>
        <span class="info-value">{{ formatDate(item.created_at) }}</span>
      </div>

      <div class="info-row" v-if="item.updated_at">
        <span class="info-label">更新时间</span>
        <span class="info-value">{{ formatDate(item.updated_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Item } from '../types'

const props = defineProps<{
  item: Item
  type: 'product' | 'ingredient'
}>()

const emit = defineEmits<{
  edit: []
  merge: []
  ingredientClick: [ingredientId: number]
}>()

function handleIngredientClick() {
  if (props.type === 'product' && props.item.ingredient_id) {
    emit('ingredientClick', props.item.ingredient_id)
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.info-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  overflow: hidden;
}

.info-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e5e5;
}

.info-title {
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

.btn-merge {
  background-color: #ff9800;
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

.btn-merge:hover {
  background-color: #f57c00;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.info-content {
  padding: 16px 20px;
}

.info-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  flex-shrink: 0;
  width: 100px;
  color: #666;
  font-weight: 500;
}

.info-value {
  flex: 1;
  color: #333;
}

.info-value.clickable {
  color: #42b883;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  text-decoration: none;
  transition: color 0.3s;
}

.info-value.clickable:hover {
  color: #3aa876;
  text-decoration: underline;
}

.info-value.clickable i {
  font-size: 16px;
}

.barcode-list,
.tag-list,
.alias-list {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.barcode-tag,
.tag,
.alias {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  background-color: #f5f5f5;
  border-radius: 12px;
  font-size: 13px;
  color: #666;
  gap: 4px;
}

.barcode-tag.primary {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.item-image {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #e5e5e5;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .info-card-header {
    padding: 12px 16px;
  }

  .info-content {
    padding: 12px 16px;
  }

  .info-row {
    flex-direction: column;
    gap: 4px;
  }

  .info-label {
    width: 100%;
    font-size: 13px;
  }

  .info-value {
    font-size: 14px;
  }

  .item-image {
    width: 60px;
    height: 60px;
  }
}
</style>
