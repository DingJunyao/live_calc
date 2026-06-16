<script setup lang="ts">
import { ref } from 'vue'
import { searchUsdaFoods, getUsdaFood, matchIngredient, matchProduct } from '@/api/usda'

const props = defineProps<{
  modelValue: boolean
  entityType: 'ingredient' | 'product'
  entityId: number
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'matched'): void
}>()

const query = ref('')
const results = ref<any[]>([])
const loading = ref(false)
const selected = ref<any | null>(null)
const matching = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function onSearch() {
  if (!query.value || !query.value.trim()) {
    results.value = []
    return
  }
  loading.value = true
  try {
    results.value = await searchUsdaFoods(query.value)
  } finally {
    loading.value = false
  }
}

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(onSearch, 300)
}

async function pick(fdcId: number) {
  loading.value = true
  try {
    selected.value = await getUsdaFood(fdcId)
  } finally {
    loading.value = false
  }
}

async function confirmMatch() {
  if (!selected.value) return
  if (!confirm('确认匹配？将清空当前营养数据并写入 USDA 数据。')) return
  matching.value = true
  try {
    if (props.entityType === 'ingredient') {
      await matchIngredient(props.entityId, selected.value.fdc_id)
    } else {
      await matchProduct(props.entityId, selected.value.fdc_id)
    }
    emit('matched')
    emit('update:modelValue', false)
  } finally {
    matching.value = false
  }
}
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    max-width="780"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title>匹配 USDA 食材</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="query"
          label="搜索（空格分词，原文/译文任意命中）"
          prepend-inner-icon="mdi-magnify"
          @update:model-value="onInput"
          @keyup.enter="onSearch"
          clearable
        />
        <v-progress-linear v-if="loading" indeterminate />

        <v-list v-if="results.length && !selected" density="compact">
          <v-list-item v-for="r in results" :key="r.fdc_id" @click="pick(r.fdc_id)">
            <v-list-item-title>{{ r.description_zh || r.description }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ r.description }} · {{ r.data_type }} · {{ r.nutrient_count }} 项营养素
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <div v-if="selected">
          <v-btn variant="text" size="small" @click="selected = null">← 返回列表</v-btn>
          <h3 class="mt-2">{{ selected.description_zh || selected.description }}</h3>
          <p class="text-caption">{{ selected.description }}</p>
          <v-table density="compact" class="mt-2">
            <thead>
              <tr><th>营养素</th><th>值</th><th>单位</th></tr>
            </thead>
            <tbody>
              <tr v-for="n in selected.nutrients" :key="n.name">
                <td>{{ n.name_zh || n.name }}</td>
                <td>{{ n.amount }}</td>
                <td>{{ n.unit_name }}</td>
              </tr>
            </tbody>
          </v-table>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn color="primary" :disabled="!selected" :loading="matching" @click="confirmMatch">
          确认匹配
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
