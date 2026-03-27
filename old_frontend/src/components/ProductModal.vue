<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <h2>{{ product ? '编辑商品' : '添加商品' }}</h2>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="productName">商品名称 *</label>
          <input
            v-model="formData.name"
            type="text"
            id="productName"
            required
          />
        </div>
        <div class="form-group">
          <label for="productBrand">品牌</label>
          <input
            v-model="formData.brand"
            type="text"
            id="productBrand"
          />
        </div>
        <div class="form-group">
          <label for="productBarcode">条码</label>
          <input
            v-model="formData.barcode"
            type="text"
            id="productBarcode"
          />
        </div>
        <div class="form-group">
          <label for="productImage">图片URL</label>
          <input
            v-model="formData.image_url"
            type="text"
            id="productImage"
          />
        </div>
        <div class="form-group">
          <label for="productIngredient">关联食材 *</label>
          <select
            v-model="formData.ingredient_id"
            id="productIngredient"
            required
          >
            <option value="">请选择食材</option>
            <option
              v-for="ingredient in ingredients"
              :key="ingredient.id"
              :value="ingredient.id"
            >
              {{ ingredient.name }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label for="productTags">标签（用逗号分隔）</label>
          <input
            v-model="tagsText"
            type="text"
            id="productTags"
            placeholder="例如: 有机, 进口, 促销"
          />
        </div>
        <div class="form-actions">
          <button type="button" @click="$emit('close')" class="btn-secondary">取消</button>
          <button type="submit" class="btn-primary">{{ product ? '更新' : '添加' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

interface Ingredient {
  id: number
  name: string
}

interface ProductCreate {
  name: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id: number
  tags?: string[]
}

interface ProductResponse {
  id: number
  name: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id: number
  tags?: string[]
}

const props = defineProps<{
  product?: ProductResponse | null
  show: boolean
}>()

const emit = defineEmits(['close', 'save'])

const formData = ref<ProductCreate>({
  name: '',
  brand: '',
  barcode: '',
  image_url: '',
  ingredient_id: 0,
  tags: []
})

const tagsText = ref('')
const ingredients = ref<Ingredient[]>([])

onMounted(async () => {
  await loadIngredients()
  if (props.product) {
    formData.value = {
      name: props.product.name,
      brand: props.product.brand || '',
      barcode: props.product.barcode || '',
      image_url: props.product.image_url || '',
      ingredient_id: props.product.ingredient_id,
      tags: props.product.tags || []
    }
    tagsText.value = (formData.value.tags || []).join(', ')
  }
})

async function loadIngredients() {
  try {
    const response = await api.get('/ingredients')
    ingredients.value = response as Ingredient[]
  } catch (error) {
    console.error('Failed to load ingredients:', error)
  }
}

function handleSubmit() {
  // 解析标签
  if (tagsText.value) {
    formData.value.tags = tagsText.value.split(',').map(t => t.trim()).filter(t => t)
  } else {
    formData.value.tags = []
  }

  emit('save', formData.value)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  max-width: 32rem;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  padding: 2rem;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.25rem;
  color: #333;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #667eea;
}

.form-group select {
  cursor: pointer;
  background: white;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-secondary {
  background: #f5f5f5;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .modal-content {
    padding: 1.5rem;
  }

  .modal-content h2 {
    font-size: 1.125rem;
    margin-bottom: 1.25rem;
  }

  .form-group label {
    font-size: 0.8125rem;
  }

  .form-group input,
  .form-group select {
    padding: 0.625rem 0.875rem;
    font-size: 0.8125rem;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
    padding: 0.625rem;
  }
}

@media (max-width: 480px) {
  .modal-content {
    padding: 1rem;
    max-width: 95%;
  }

  .modal-content h2 {
    font-size: 1rem;
  }

  .form-group input,
  .form-group select {
    padding: 0.5rem 0.75rem;
    font-size: 0.75rem;
  }
}
</style>
