<template>
  <PageHeader :title="pageTitle" :show-back="true" />

  <div class="nutrition-edit-form">
    <form @submit.prevent="handleSubmit" class="form">
      <!-- 基础信息 -->
      <div class="form-section">
        <h3 class="section-title">基础信息</h3>
        <div class="form-row">
          <label class="form-label">基准数量</label>
          <div class="input-group">
            <input
              v-model.number="form.base_quantity"
              type="number"
              step="0.1"
              min="0"
              class="form-input"
              required
            />
            <select v-model="form.base_unit" class="form-select">
              <option value="g">g</option>
              <option value="kg">kg</option>
              <option value="ml">ml</option>
              <option value="l">l</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label">数据来源</label>
          <select v-model="form.source" class="form-select">
            <option value="custom">自定义</option>
            <option value="usda">USDA</option>
            <option value="ai_match">AI匹配</option>
          </select>
        </div>
      </div>

      <!-- 营养素列表 -->
      <div class="form-section">
        <h3 class="section-title">营养素</h3>
        <div class="nutrients-list">
          <div
            v-for="(nutrient, index) in form.nutrients"
            :key="index"
            class="nutrient-item"
          >
            <input
              v-model="nutrient.name"
              type="text"
              placeholder="营养素名称"
              class="form-input nutrient-name"
            />
            <input
              v-model.number="nutrient.value"
              type="number"
              step="0.01"
              min="0"
              placeholder="数值"
              class="form-input nutrient-value"
            />
            <select v-model="nutrient.unit" class="form-select nutrient-unit">
              <option value="kcal">kcal</option>
              <option value="kJ">kJ</option>
              <option value="g">g</option>
              <option value="mg">mg</option>
              <option value="μg">μg</option>
              <option value="IU">IU</option>
            </select>
            <button
              @click="removeNutrient(index)"
              class="btn-remove"
              type="button"
            >
              <i class="mdi mdi-delete"></i>
            </button>
          </div>
        </div>

        <button @click="addNutrient" class="btn-add-nutrient" type="button">
          <i class="mdi mdi-plus"></i> 添加营养素
        </button>
      </div>

      <!-- 提交按钮 -->
      <div class="form-actions">
        <button type="submit" class="btn-submit" :disabled="saving">
          <i v-if="saving" class="mdi mdi-loading mdi-spin"></i>
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button type="button" @click="handleCancel" class="btn-cancel">
          取消
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { api } from '@/api/client'

const route = useRoute()
const router = useRouter()

const type = computed(() => route.params.type as 'product' | 'ingredient')
const itemId = computed(() => parseInt(route.params.id as string))

const saving = ref(false)
const form = ref({
  base_quantity: 100,
  base_unit: 'g',
  source: 'custom',
  nutrients: [] as Array<{
    name: string
    value: number
    unit: string
    key?: string
  }>
})

const pageTitle = computed(() => {
  const typeName = type.value === 'product' ? '商品' : '原料'
  return `编辑${typeName}营养数据`
})

// 常见营养素预设
const commonNutrients = [
  { name: '能量', unit: 'kcal' },
  { name: '蛋白质', unit: 'g' },
  { name: '脂肪', unit: 'g' },
  { name: '碳水化合物', unit: 'g' },
  { name: '膳食纤维', unit: 'g' },
  { name: '钠', unit: 'mg' },
  { name: '钾', unit: 'mg' },
  { name: '钙', unit: 'mg' }
]

function addNutrient(name?: string) {
  if (name) {
    const common = commonNutrients.find(n => n.name === name)
    if (common && !form.value.nutrients.find(n => n.name === name)) {
      form.value.nutrients.push({
        name: common.name,
        value: 0,
        unit: common.unit
      })
    }
  } else {
    form.value.nutrients.push({
      name: '',
      value: 0,
      unit: 'g'
    })
  }
}

function removeNutrient(index: number) {
  form.value.nutrients.splice(index, 1)
}

async function handleSubmit() {
  saving.value = true

  try {
    const endpoint = type.value === 'product'
      ? `/nutrition/products/${itemId.value}/nutrition`
      : `/nutrition/ingredients/${itemId.value}/nutrition`

    await api.post(endpoint, form.value)

    // 返回详情页
    router.push({
      name: 'item-detail',
      params: { type: type.value, id: itemId.value }
    })
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

function handleCancel() {
  router.back()
}

onMounted(() => {
  // 加载现有数据（如果有）
  // TODO: 实现数据加载逻辑
  // 添加常见营养素
  commonNutrients.forEach(nutrient => {
    addNutrient(nutrient.name)
  })
})
</script>

<style scoped>
.nutrition-edit-form {
  padding: 16px;
  max-width: 800px;
  margin: 0 auto;
}

.form {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.form-section {
  margin-bottom: 24px;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.form-row {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.input-group {
  display: flex;
  gap: 8px;
}

.form-input,
.form-select {
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #42b883;
}

.form-input {
  flex: 1;
}

.form-select {
  min-width: 80px;
}

.nutrients-list {
  margin-bottom: 16px;
}

.nutrient-item {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.nutrient-name {
  flex: 2;
  min-width: 120px;
}

.nutrient-value {
  flex: 1;
  min-width: 80px;
}

.nutrient-unit {
  flex: 1;
  min-width: 80px;
}

.btn-remove {
  width: 36px;
  height: 36px;
  border: 1px solid #e5e5e5;
  background-color: white;
  border-radius: 4px;
  cursor: pointer;
  color: #c33;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.btn-remove:hover {
  background-color: #fee;
  border-color: #c33;
}

.btn-add-nutrient {
  width: 100%;
  padding: 10px;
  border: 1px dashed #42b883;
  background-color: white;
  border-radius: 4px;
  cursor: pointer;
  color: #42b883;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.3s;
}

.btn-add-nutrient:hover {
  background-color: #f0f9f4;
}

.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e5e5e5;
}

.btn-submit,
.btn-cancel {
  flex: 1;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-submit {
  background-color: #42b883;
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background-color: #3aa876;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background-color: #f5f5f5;
  color: #666;
}

.btn-cancel:hover {
  background-color: #e5e5e5;
}

@media (max-width: 768px) {
  .nutrition-edit-form {
    padding: 12px;
  }

  .form {
    padding: 16px;
  }

  .nutrient-item {
    flex-wrap: wrap;
  }

  .nutrient-name,
  .nutrient-value,
  .nutrient-unit {
    flex: 1 1 100%;
    min-width: auto;
  }

  .btn-remove {
    width: 100%;
  }

  .form-actions {
    flex-direction: column;
  }
}
</style>
