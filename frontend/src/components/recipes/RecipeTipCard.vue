<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="warning">mdi-lightbulb-outline</v-icon>
      小贴士
      <v-chip size="small" class="ml-2" v-if="tipsList.length">
        {{ editing ? editRows.length : tipsList.length }}
      </v-chip>
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
      <v-card-text v-if="tipsList.length">
        <ul class="text-body-2 pl-4 mb-0">
          <li v-for="(tip, i) in tipsList" :key="i" class="mb-1">{{ tip }}</li>
        </ul>
      </v-card-text>
    </template>

    <!-- 编辑模式 -->
    <v-card-text v-else class="pa-0">
      <div
        v-for="(row, index) in editRows"
        :key="index"
        draggable="true"
        class="d-flex align-center pa-3 border-bottom"
        :class="{
          'border-bottom': index < editRows.length - 1,
          'drag-over': dragIndex !== null && index === dragIndex
        }"
        @dragstart="onDragStart(index)"
        @dragover.prevent="onDragOver(index)"
        @dragleave="dragIndex = null"
        @drop="onDrop(index)"
      >
        <v-icon size="small" class="mr-2 drag-handle" color="medium-emphasis">mdi-drag</v-icon>

        <v-textarea
          v-model="editRows[index]"
          label="小贴士"
          variant="outlined"
          density="compact"
          auto-grow
          rows="1"
          hide-details
          class="flex-grow-1"
        />

        <v-btn
          icon="mdi-delete"
          size="x-small"
          color="error"
          variant="text"
          class="ml-2"
          @click="removeRow(index)"
        />
      </div>

      <!-- 添加小贴士按钮 -->
      <div class="pa-3">
        <v-btn
          variant="text"
          color="primary"
          prepend-icon="mdi-plus"
          size="small"
          @click="addRow"
        >添加小贴士</v-btn>
      </div>
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
const editRows = ref<string[]>([])
const dragIndex = ref<number | null>(null)

const onDragStart = (index: number) => {
  dragIndex.value = index
}

const onDragOver = (index: number) => {
  if (dragIndex.value === null || dragIndex.value === index) return
  const from = dragIndex.value
  const to = index
  const item = editRows.value.splice(from, 1)[0]
  editRows.value.splice(to, 0, item)
  dragIndex.value = to
}

const onDrop = (index: number) => {
  dragIndex.value = null
}

const tipsList = computed(() => props.recipe.tips || [])

const startEdit = () => {
  editRows.value = [...(props.recipe.tips || [])]
  if (editRows.value.length === 0) {
    editRows.value.push('')
  }
  editing.value = true
}

const cancelEdit = () => {
  editing.value = false
}

const addRow = () => {
  editRows.value.push('')
}

const removeRow = (index: number) => {
  editRows.value.splice(index, 1)
}

const handleSave = async () => {
  saving.value = true
  try {
    const tips = editRows.value.filter(t => t.trim()).map(t => t.trim())

    if (JSON.stringify(tips) === JSON.stringify(props.recipe.tips)) {
      editing.value = false
      return
    }

    const result = await api.put(`/recipes/${props.recipe.id}`, { tips })
    emit('saved', result)
    editing.value = false
  } catch (e: any) {
    console.error('保存小贴士失败', e)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.border-bottom {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
}

.drag-handle {
  cursor: grab;
}

.drag-over {
  border-top: 2px solid rgb(var(--v-theme-primary)) !important;
}
</style>
