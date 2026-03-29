<template>
  <v-dialog
    :model-value="modelValue"
    max-width="500"
    class="price-form-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center pa-4">
        <v-btn icon="mdi-arrow-left" variant="text" @click="close" />
        <span class="text-h6 ml-2">{{ isEdit ? '编辑价格' : '添加价格' }}</span>
        <v-spacer />
        <v-btn
          color="primary"
          variant="text"
          :loading="saving"
          @click="save"
        >
          保存
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-4">
        <v-form ref="formRef">
          <!-- 商品选择 -->
          <v-text-field
            v-model="form.product_name"
            label="商品名称 *"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            required
            :rules="[rules.required]"
            class="mb-4"
          />

          <!-- 价格 -->
          <v-text-field
            v-model="form.price"
            label="价格 *"
            prefix="¥"
            type="number"
            variant="outlined"
            required
            :rules="[rules.required]"
            class="mb-4"
          />

          <!-- 数量和单位 -->
          <v-row class="mb-4">
            <v-col cols="6">
              <v-text-field
                v-model="form.quantity"
                label="数量 *"
                type="number"
                variant="outlined"
                required
                :rules="[rules.required]"
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="form.unit"
                label="单位 *"
                :items="units"
                variant="outlined"
                required
              />
            </v-col>
          </v-row>

          <!-- 商家 -->
          <v-text-field
            v-model="form.merchant_name"
            label="商家（可选）"
            prepend-inner-icon="mdi-store"
            variant="outlined"
            clearable
            class="mb-4"
          />

          <!-- 计入支出 -->
          <v-checkbox
            v-model="form.is_purchase"
            label="计入支出"
            color="primary"
            density="comfortable"
            class="mb-4"
          />

          <!-- 记录时间 -->
          <v-text-field
            v-model="form.record_date"
            label="记录时间"
            prepend-inner-icon="mdi-calendar"
            type="date"
            variant="outlined"
          />
        </v-form>
      </v-card-text>

      <!-- 桌面端底部操作按钮 -->
      <v-card-actions class="pa-4 pt-0 d-none d-md-flex">
        <v-spacer />
        <v-btn variant="text" @click="close">取消</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :loading="saving"
          @click="save"
        >
          保存
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import type { PriceRecord } from '@/types'

interface Props {
  modelValue: boolean
  record?: PriceRecord
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'save', record: PriceRecord): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isEdit = computed(() => !!props.record)

const form = reactive({
  product_name: '',
  price: '',
  quantity: 1,
  unit: '个',
  merchant_name: '',
  is_purchase: true,
  record_date: new Date().toISOString().split('T')[0],
})

const units = ['个', '斤', 'kg', '克', '升', '毫升', '盒', '包', '袋', '瓶']

const saving = ref(false)

const rules = {
  required: (value: string) => !!value || '此字段必填',
}

// 监听 record 变化，填充表单
watch(() => props.record, (newRecord) => {
  if (newRecord) {
    form.product_name = newRecord.product_name
    form.price = newRecord.price.toString()
    form.quantity = newRecord.quantity
    form.unit = newRecord.unit
    form.merchant_name = newRecord.merchant_name || ''
    form.is_purchase = true
    form.record_date = newRecord.record_date.split('T')[0]
  } else {
    resetForm()
  }
}, { immediate: true })

const resetForm = () => {
  form.product_name = ''
  form.price = ''
  form.quantity = 1
  form.unit = '个'
  form.merchant_name = ''
  form.is_purchase = true
  form.record_date = new Date().toISOString().split('T')[0]
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

const close = () => {
  emit('update:modelValue', false)
  resetForm()
}

const save = () => {
  const record: PriceRecord = {
    id: props.record?.id || Date.now(),
    product_name: form.product_name,
    price: parseFloat(form.price),
    quantity: form.quantity,
    unit: form.unit,
    merchant_name: form.merchant_name || undefined,
    record_date: new Date(form.record_date).toISOString(),
    created_at: props.record?.created_at || new Date().toISOString(),
  }

  emit('save', record)
  close()
}
</script>

<style>
/* 移动端全屏显示对话框 */
@media (max-width: 959px) {
  .price-form-dialog .v-overlay__content {
    max-width: 100% !important;
    width: 100% !important;
    height: 100% !important;
    max-height: 100% !important;
    margin: 0 !important;
  }

  .price-form-dialog .v-card {
    height: 100%;
    border-radius: 0;
  }
}
</style>
