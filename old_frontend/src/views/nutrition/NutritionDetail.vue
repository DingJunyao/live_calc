<template>
  <PageHeader :title="title" :show-back="true" />
  <div class="nutrition-detail">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else class="nutrition-content">
      <!-- 基本信息 -->
      <div class="info-card">
        <h2>{{ title }}</h2>
        <div class="info-row">
          <span class="label">名称:</span>
          <span class="value">{{ itemName }}</span>
        </div>
      </div>

      <!-- 营养数据 -->
      <NutritionDisplay
        v-if="nutritionData"
        :nutrition="nutritionData"
        :loading="false"
        :show-source="true"
        :show-nrp="true"
        :show-details="true"
        :show-reference="true"
        :reference-amount="referenceAmount"
        :reference-unit="referenceUnit"
        :source="dataSource"
        :nutrient-order="standardNutrientOrder"
      />
      <div v-else class="empty-state">
        暂无营养数据
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import NutritionDisplay from '@/components/NutritionDisplay.vue'

const route = useRoute()

// 转换后端营养数据格式为前端组件期望的格式
function transformNutritionData(data: any): any {
  if (!data) return null

  // 如果已经是正确格式，直接返回
  if (data.core_nutrients && data.all_nutrients) {
    return data
  }

  // 后端返回格式：{ "能量": { value, unit, ... }, "蛋白质": { value, unit, ... }, ... }
  // 需要转换为：{ core_nutrients: { ... }, all_nutrients: { ... }, nrp_totals: { ... } }
  const coreNutrients: Record<string, any> = {}
  const allNutrients: Record<string, any> = {}

  for (const [key, value] of Object.entries(data)) {
    if (value && typeof value === 'object' && 'value' in value) {
      // 放入 core_nutrients
      coreNutrients[key] = value
      // 也放入 all_nutrients（使用 key 字段的值作为键，如果没有则用中文键名）
      const englishKey = (value as any).key || key
      allNutrients[englishKey] = value
    }
  }

  return {
    core_nutrients: coreNutrients,
    all_nutrients: allNutrients,
    nrp_totals: {}
  }
}

// 获取路由参数
const itemType = computed(() => (route.params.type as 'product' | 'ingredient'))
const itemId = computed(() => Number(route.params.id))

// 状态
const loading = ref(true)
const error = ref<string | null>(null)
const itemName = ref<string>('')
const nutritionData = ref<any>(null)
const apiResponseData = ref<any>(null) // 保存完整的 API 响应数据

// 计算后的标题
const title = computed(() => {
  if (itemType.value === 'product') {
    return '商品营养详情'
  } else {
    return '原料营养详情'
  }
})

// 定义标准营养素顺序，与菜谱中的顺序保持一致
const standardNutrientOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '膳食纤维',
  '钙', '铁', '钠', '钾', '维生素A', '维生素C',
  '维生素B1', '维生素B2', '维生素B12', '维生素D',
  '维生素E', '维生素K'
]

// 数据源
const dataSource = computed(() => {
  if (apiResponseData.value?.source) {
    return apiResponseData.value.source
  }
  // 默认使用 USDA 导入的数据源
  return 'usda_import'
})

// 参考基准数量
const referenceAmount = computed(() => {
  return apiResponseData.value?.base_quantity || apiResponseData.value?.reference_amount || 100
})

// 参考基准单位
const referenceUnit = computed(() => {
  return apiResponseData.value?.base_unit || apiResponseData.value?.reference_unit || 'g'
})

onMounted(async () => {
  await loadNutritionData()
})

async function loadNutritionData() {
  loading.value = true
  error.value = null

  try {
    if (itemType.value === 'product') {
      // 加载商品营养数据
      const data = await api.get(`/nutrition/products/${itemId.value}/nutrition`)
      apiResponseData.value = data // 保存完整响应
      // 转换数据格式：后端返回 { nutrition: { "能量": {...}, ... } }
      // 前端组件期望 { core_nutrients: { ... }, all_nutrients: { ... }, nrp_totals: { ... } }
      nutritionData.value = transformNutritionData(data.nutrition || data)
      itemName.value = data.name || data.product_name || '商品'
    } else {
      // 加载原料营养数据
      const data = await api.get(`/nutrition/ingredients/${itemId.value}/nutrition`)
      apiResponseData.value = data // 保存完整响应
      nutritionData.value = transformNutritionData(data.nutrition || data)
      itemName.value = data.name || data.ingredient_name || '原料'
    }
  } catch (e: any) {
    console.error('Failed to load nutrition:', e)
    error.value = '加载失败，请重试'
    nutritionData.value = null
    apiResponseData.value = null
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.nutrition-detail {
  padding: 2rem;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: #666;
}

.error-state {
  text-align: center;
  padding: 4rem;
  color: #999;
  background: #f9f9f9;
  border-radius: 0.5rem;
}

.nutrition-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.info-card h2 {
  font-size: 1.25rem;
  color: #333;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.info-row .label {
  color: #666;
  font-weight: 500;
}

.info-row .value {
  color: #333;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #999;
  background: #f9f9f9;
  border-radius: 0.5rem;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .nutrition-detail {
    padding: 1rem;
  }

  .info-card {
    padding: 1rem;
  }
}
</style>
