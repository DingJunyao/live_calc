<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="primary">mdi-information-outline</v-icon>
      菜谱介绍
      <v-spacer />
      <template v-if="!editing">
        <v-btn
          size="small"
          variant="text"
          color="primary"
          prepend-icon="mdi-pencil"
          @click="startEdit"
        >编辑</v-btn>
      </template>
      <template v-else>
        <v-btn
          size="small"
          variant="text"
          color="success"
          prepend-icon="mdi-check"
          :loading="saving"
          @click="handleSave"
        >保存</v-btn>
        <v-btn
          size="small"
          variant="text"
          color="medium-emphasis"
          prepend-icon="mdi-close"
          :disabled="saving"
          @click="cancelEdit"
          class="ml-1"
        >取消</v-btn>
      </template>
    </v-card-title>
    <v-divider />

    <!-- 查看模式 -->
    <template v-if="!editing">
      <v-card-text>
        <div class="d-flex flex-wrap ga-2 mb-3">
          <v-chip
            v-if="recipe.category"
            size="small"
            variant="tonal"
            color="primary"
          >{{ recipe.category }}</v-chip>
          <v-chip
            v-if="recipe.difficulty"
            size="small"
            variant="tonal"
            color="secondary"
          >{{ difficultyLabel }}</v-chip>
        </div>
        <div
          v-if="recipe.description"
          class="text-body-2"
          style="white-space: pre-wrap"
        >{{ recipe.description }}</div>
        <div
          v-else
          class="text-body-2 text-medium-emphasis"
        >暂未填写介绍</div>
      </v-card-text>
    </template>

    <!-- 编辑模式 -->
    <v-card-text v-else>
      <v-text-field
        v-model="editForm.name"
        label="菜谱名称"
        variant="outlined"
        density="compact"
        maxlength="200"
        hide-details
        class="mb-3"
      />
      <v-row class="mb-3">
        <v-col cols="6">
          <v-select
            v-model="editForm.category"
            label="分类"
            variant="outlined"
            density="compact"
            :items="categoryOptions"
            hide-details
          />
        </v-col>
        <v-col cols="6">
          <v-select
            v-model="editForm.difficulty"
            label="难度"
            variant="outlined"
            density="compact"
            :items="difficultyOptions"
            item-title="label"
            item-value="value"
            hide-details
          />
        </v-col>
      </v-row>
      <v-textarea
        v-model="editForm.description"
        label="菜谱简介"
        variant="outlined"
        density="compact"
        auto-grow
        rows="3"
        maxlength="2000"
        hide-details
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import type { RecipeDetail } from './types'

const props = defineProps<{
  recipe: RecipeDetail
}>()

const emit = defineEmits<{
  (e: 'saved', recipe: RecipeDetail): void
}>()

const editing = ref(false)
const saving = ref(false)
const editForm = ref({
  name: '',
  category: '',
  difficulty: '',
  description: '',
})

const categoryOptions = [
  { title: '荤菜', value: '荤菜' },
  { title: '素菜', value: '素菜' },
  { title: '水产', value: '水产' },
  { title: '主食', value: '主食' },
  { title: '汤与粥', value: '汤与粥' },
  { title: '早餐', value: '早餐' },
  { title: '甜品', value: '甜品' },
  { title: '调料', value: '调料' },
  { title: '半成品', value: '半成品' },
  { title: '小食', value: '小食' },
]

const difficultyOptions = [
  { label: '简易', value: 'simple' },
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
  { label: '专家', value: 'expert' },
]

const difficultyLabel = computed(() => {
  const opt = difficultyOptions.find(d => d.value === props.recipe.difficulty)
  return opt?.label || props.recipe.difficulty || ''
})

const startEdit = () => {
  editForm.value = {
    name: props.recipe.name || '',
    category: props.recipe.category || '',
    difficulty: props.recipe.difficulty || '',
    description: props.recipe.description || '',
  }
  editing.value = true
}

const cancelEdit = () => {
  editing.value = false
}

const handleSave = async () => {
  saving.value = true
  try {
    const payload: Record<string, any> = {}
    if (editForm.value.name !== props.recipe.name) payload.name = editForm.value.name
    if (editForm.value.category !== props.recipe.category) payload.category = editForm.value.category
    if (editForm.value.difficulty !== props.recipe.difficulty) payload.difficulty = editForm.value.difficulty
    if (editForm.value.description !== (props.recipe.description || '')) payload.description = editForm.value.description

    if (Object.keys(payload).length === 0) {
      editing.value = false
      return
    }

    const result = await api.put(`/recipes/${props.recipe.id}`, payload)
    emit('saved', result)
    editing.value = false
  } catch (e: any) {
    console.error('保存基本信息失败', e)
  } finally {
    saving.value = false
  }
}
</script>
