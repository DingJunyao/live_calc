<template>
  <div class="nutrition-display-section">
    <div class="section-header">
      <h2 class="section-title">营养成分</h2>
      <button @click="$emit('edit')" class="btn-edit">
        <i class="mdi mdi-pencil"></i> 编辑
      </button>
    </div>

    <div v-if="!nutrition" class="no-data">
      <i class="mdi mdi-food-apple"></i>
      <p>暂无营养数据</p>
    </div>

    <div v-else class="nutrition-content">
      <div class="nutrition-info">
        <span class="info-label">基准量:</span>
        <span class="info-value">{{ nutrition.base_quantity }}{{ nutrition.base_unit }}</span>
      </div>

      <!-- 核心营养素 -->
      <div class="nutrients-grid">
        <div
          v-for="(nutrient, name) in coreNutrients"
          :key="name"
          class="nutrient-card"
        >
          <div class="nutrient-name">{{ name }}</div>
          <div class="nutrient-value">{{ nutrient.value }}{{ nutrient.unit }}</div>
          <div
            class="nutrient-nrp"
            :class="{ 'high': nutrient.nrp_pct > 30 }"
          >
            {{ nutrient.nrp_pct }}% NRV
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NutritionData } from '../types'

const props = defineProps<{
  nutrition: NutritionData | null
  type: 'product' | 'ingredient'
}>()

defineEmits<{
  edit: []
}>()

const coreNutrients = computed(() => {
  if (!props.nutrition) return {}

  const core = props.nutrition.nutrition.core_nutrients || {}
  const result: Record<string, any> = {}

  // 常见核心营养素
  const nutrientNames = ['能量', '蛋白质', '脂肪', '碳水化合物', '膳食纤维', '钠', '钾', '钙']

  nutrientNames.forEach(name => {
    if (core[name]) {
      result[name] = core[name]
    }
  })

  return result
})
</script>

<style scoped>
.nutrition-display-section {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
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

.nutrition-info {
  padding: 12px;
  background-color: #f9f9f9;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 14px;
}

.info-label {
  color: #666;
  margin-right: 8px;
}

.info-value {
  color: #333;
  font-weight: 600;
}

.nutrients-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.nutrient-card {
  background-color: #f9f9f9;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.nutrient-name {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.nutrient-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.nutrient-nrp {
  font-size: 12px;
  color: #666;
}

.nutrient-nrp.high {
  color: #ff9800;
  font-weight: 600;
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

/* 移动端适配 */
@media (max-width: 768px) {
  .nutrition-display-section {
    padding: 12px;
  }

  .nutrients-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 8px;
  }

  .nutrient-card {
    padding: 10px 8px;
  }

  .nutrient-name {
    font-size: 13px;
  }

  .nutrient-value {
    font-size: 16px;
  }
}
</style>
