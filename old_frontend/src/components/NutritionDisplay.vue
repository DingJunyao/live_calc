<template>
  <div class="nutrition-display">
    <div v-if="loading" class="loading">加载营养数据中...</div>

    <div v-else-if="!nutrition" class="empty-state">
      暂无营养数据
    </div>

    <div v-else class="nutrition-content">
      <!-- 数据源标识 -->
      <div v-if="showSource" class="data-source">
        <span
          :class="['source-badge', getSourceClass()]"
          :title="getSourceTitle()"
        >
          {{ getSourceLabel() }}
        </span>
      </div>

      <!-- 营养素展示 - 统一格式 -->
      <div v-if="orderedCoreNutrients && Object.keys(orderedCoreNutrients).length > 0" class="nutrition-section">
        <h3>营养成分</h3>
        <div class="nutrient-grid">
          <div
            v-for="(data, name) in orderedCoreNutrients"
            :key="name"
            class="nutrient-item"
          >
            <div class="nutrient-info">
              <span class="label">{{ name }}:</span>
              <span class="value">
                {{ formatValue(data.value) }} {{ data.unit }}
              </span>
            </div>
            <div class="nutrient-actions" v-if="showNRP">
              <NutritionProgressBar
                :percentage="data.nrp_pct"
                :show-percentage="true"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 详细营养素（可展开） -->
      <div v-if="showDetails && allNutrients" class="nutrition-section">
        <div class="section-header">
          <h3>详细营养成分</h3>
          <button
            @click="toggleDetails"
            class="toggle-button"
          >
            {{ detailsExpanded ? '收起' : '展开' }}
            <i :class="['mdi', detailsExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down']"></i>
          </button>
        </div>

        <div v-if="detailsExpanded" class="nutrient-details-grid">
          <div
            v-for="(data, key) in allNutrients"
            :key="key"
            class="nutrient-detail-item"
          >
            <div class="detail-header">
              <span class="detail-key">{{ formatNutrientKey(key) }}</span>
              <span class="detail-value">{{ formatValue(data.value) }} {{ data.unit }}</span>
            </div>
            <div v-if="data.nrp_pct > 0" class="detail-nrp">
              <NutritionProgressBar
                :percentage="data.nrp_pct"
                :show-percentage="true"
              />
            </div>
            <div v-if="data.note" class="detail-note">
              {{ data.note }}
            </div>
            <div class="detail-meta">
              <span class="meta-tag">{{ data.standard }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 参考基准信息 -->
      <div v-if="showReference" class="nutrition-section">
        <h3>参考基准</h3>
        <p class="reference-info">
          基于 {{ referenceAmount }}{{ referenceUnit }} 的营养成分
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import NutritionProgressBar from './NutritionProgressBar.vue'

interface NutrientData {
  value: number
  unit: string
  nrp_pct: number
  standard?: string
  note?: string
  key?: string
}

interface NutritionDisplayProps {
  nutrition: {
    core_nutrients?: Record<string, NutrientData>
    all_nutrients?: Record<string, NutrientData>
    nrp_totals?: Record<string, number>
  }
  source?: string
  referenceAmount?: number
  referenceUnit?: string
  showSource?: boolean
  showNRP?: boolean
  showDetails?: boolean
  showReference?: boolean
  progressSize?: 'default' | 'small'
  loading?: boolean
  nutrientOrder?: string[]  // 新增：指定营养素显示顺序
}

const props = withDefaults(defineProps<NutritionDisplayProps>(), {
  showSource: true,
  showNRP: true,
  showDetails: true,
  showReference: false,
  progressSize: 'default',
  loading: false,
  referenceAmount: 100,
  referenceUnit: 'g',
  nutrientOrder: () => []
})

const detailsExpanded = ref(false)

// 定义标准营养素顺序，与菜谱中的顺序保持一致
const standardNutrientOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '膳食纤维',
  '钙', '铁', '钠', '钾', '维生素A', '维生素C',
  '维生素B1', '维生素B2', '维生素B12', '维生素D',
  '维生素E', '维生素K'
]

// 根据指定顺序整理核心营养素
const orderedCoreNutrients = computed(() => {
  const nutrients = props.nutrition?.core_nutrients || {}
  const order = props.nutrientOrder.length > 0 ? props.nutrientOrder : standardNutrientOrder

  // 按照顺序排列存在的营养素
  const ordered: Record<string, NutrientData> = {}

  // 先按指定顺序添加
  for (const nutrientName of order) {
    if (nutrients[nutrientName]) {
      ordered[nutrientName] = nutrients[nutrientName]
    }
  }

  // 再添加不在顺序中的其他营养素
  for (const [name, data] of Object.entries(nutrients)) {
    if (!ordered[name]) {
      ordered[name] = data
    }
  }

  return ordered
})

const coreNutrients = computed(() => props.nutrition?.core_nutrients || {})
const allNutrients = computed(() => props.nutrition?.all_nutrients || {})
const nrpTotals = computed(() => props.nutrition?.nrp_totals || {})

function formatValue(value: number): string {
  if (value === 0) return '0'
  if (value < 0.01) return value.toFixed(3)
  if (value < 0.1) return value.toFixed(2)
  if (value < 100) return value.toFixed(1)
  return Math.round(value).toString()
}

function formatNutrientKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function getSourceLabel(): string {
  switch (props.source) {
    case 'usda_import':
      return 'USDA'
    case 'custom':
      return '自定义'
    case 'ai_match':
      return 'AI匹配'
    default:
      return ''
  }
}

function getSourceClass(): string {
  return `source-${props.source || 'default'}`
}

function getSourceTitle(): string {
  switch (props.source) {
    case 'usda_import':
      return '数据来源：USDA 营养数据库'
    case 'custom':
      return '数据来源：用户自定义'
    case 'ai_match':
      return '数据来源：AI 智能匹配'
    default:
      return ''
  }
}

function toggleDetails() {
  detailsExpanded.value = !detailsExpanded.value
}
</script>

<style scoped>
.nutrition-display {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #999;
  background: #f9f9f9;
  border-radius: 0.5rem;
}

.data-source {
  margin-bottom: 1rem;
  text-align: right;
}

.source-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
}

.source-usda_import {
  background: #e3f2fd;
  color: #1976d2;
}

.source-custom {
  background: #f3e5f5;
  color: #7b1fa2;
}

.source-ai_match {
  background: #fff3e0;
  color: #f57c00;
}

.source-default {
  background: #f5f5f5;
  color: #666;
}

.nutrition-section {
  margin-bottom: 1.5rem;
}

.nutrition-section h3 {
  font-size: 1.125rem;
  color: #333;
  margin: 0 0 1rem 0;
  font-weight: 600;
}

.nutrient-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.nutrient-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e0e0e0;
}

.nutrient-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.nutrient-info .label {
  color: #666;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.nutrient-info .value {
  font-size: 1.125rem;
  font-weight: 600;
  color: #333;
}

.nutrient-actions {
  min-width: 150px;
  margin-left: 1rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  margin: 0;
}

.toggle-button {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  background: #f5f5f5;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #666;
  cursor: pointer;
  transition: background 0.2s ease;
}

.toggle-button:hover {
  background: #e0e0e0;
}

.nutrient-details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  max-height: 500px;
  overflow-y: auto;
  padding: 0.5rem;
}

.nutrient-detail-item {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e0e0e0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.detail-key {
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.detail-value {
  font-size: 0.875rem;
  color: #667eea;
  font-weight: 600;
}

.detail-nrp {
  margin-top: 0.5rem;
}

.detail-note {
  font-size: 0.75rem;
  color: #999;
  margin-top: 0.5rem;
  font-style: italic;
}

.detail-meta {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.meta-tag {
  display: inline-block;
  padding: 0.125rem 0.375rem;
  background: #e0e0e0;
  border-radius: 0.125rem;
  font-size: 0.625rem;
  color: #666;
}

.reference-info {
  color: #666;
  font-size: 0.875rem;
  margin: 0;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .nutrition-display {
    padding: 1rem;
  }

  .nutrient-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .nutrient-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .nutrient-actions {
    width: 100%;
    margin-left: 0;
  }

  .section-header h3 {
    font-size: 1rem;
  }
}
</style>
