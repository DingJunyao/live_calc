<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="primary">mdi-chef-hat</v-icon>
      做法步骤
      <v-chip size="small" class="ml-2" v-if="recipe.cooking_steps?.length">
        {{ editing ? editRows.length : recipe.cooking_steps.length }}
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
      <v-card-text v-if="recipe.cooking_steps?.length">
        <v-timeline align="start" density="compact">
          <v-timeline-item
            v-for="(step, index) in recipe.cooking_steps"
            :key="index"
            size="small"
          >
            <template #icon>
              <v-avatar :color="getColorByIndex(index)" size="32">
                {{ index + 1 }}
              </v-avatar>
            </template>
            <div class="step-content">
              {{ typeof step === 'object' ? step.content : step }}
            </div>
            <div
              v-if="typeof step === 'object' && step.tips"
              class="text-caption text-medium-emphasis mt-1 pl-2"
              style="border-left: 2px solid var(--v-warning-base)"
            >
              {{ step.tips }}
            </div>
          </v-timeline-item>
        </v-timeline>
      </v-card-text>
      <v-card-text v-else class="text-center py-4 text-medium-emphasis">
        暂无做法数据
      </v-card-text>
    </template>

    <!-- 编辑模式 -->
    <v-card-text v-else class="pa-0">
      <div
        v-for="(row, index) in editRows"
        :key="row.tempId"
        draggable="true"
        class="step-edit-item pa-3"
        :class="{
          'border-bottom': index < editRows.length - 1,
          'drag-over': dragIndex !== null && index === dragIndex
        }"
        @dragstart="(e) => onDragStart(e, index)"
        @dragover.prevent="onDragOver(index)"
        @dragleave="dragIndex = null"
        @drop="onDrop(index)"
      >
        <div class="d-flex align-start ga-2">
          <!-- 序号 -->
          <div class="step-number font-weight-bold text-primary mt-2" style="min-width: 24px">
            {{ index + 1 }}
          </div>

          <div class="flex-grow-1">
            <div class="d-flex ga-2 mb-2">
              <!-- 拖拽手柄 -->
              <v-icon size="small" class="drag-handle mt-2" color="medium-emphasis">mdi-drag</v-icon>

              <!-- 描述 -->
              <v-textarea
                v-model="row.content"
                label="步骤描述"
                variant="outlined"
                density="compact"
                auto-grow
                rows="2"
                hide-details
                class="flex-grow-1"
              />

              <!-- 小贴士 -->
              <v-text-field
                v-model="row.tips"
                label="小贴士"
                variant="outlined"
                density="compact"
                hide-details
                class="flex-shrink-0"
                style="width: 160px"
                clearable
              />

              <!-- 删除 -->
              <v-btn
                icon="mdi-delete"
                size="x-small"
                color="error"
                variant="text"
                class="mt-2"
                @click="removeRow(index)"
              />
            </div>

            <!-- 时长 -->
            <div class="d-flex ga-2">
              <div style="width: 16px"></div>
              <v-text-field
                v-model="row.duration_minutes"
                type="number"
                label="时长（分钟）"
                variant="outlined"
                density="compact"
                hide-details
                style="width: 160px"
                min="0"
                clearable
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 添加步骤按钮 -->
      <div class="pa-3">
        <v-btn
          variant="text"
          color="primary"
          prepend-icon="mdi-plus"
          size="small"
          @click="addRow"
        >添加步骤</v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import type { RecipeDetail, StepEditRow } from './types'

const props = defineProps<{
  recipe: RecipeDetail
}>()

const emit = defineEmits<{
  (e: 'saved', recipe: RecipeDetail): void
}>()

const editing = ref(false)
const saving = ref(false)
const editRows = ref<StepEditRow[]>([])
const dragIndex = ref<number | null>(null)

const onDragStart = (e: DragEvent, index: number) => {
  e.dataTransfer?.setData('text/plain', String(index))
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
  dragIndex.value = index
}

const onDragOver = (index: number) => {
  if (dragIndex.value === null || dragIndex.value === index) return
  const from = dragIndex.value
  const item = editRows.value.splice(from, 1)[0]
  editRows.value.splice(index, 0, item)
  dragIndex.value = index
}

const onDrop = () => {
  dragIndex.value = null
}

const getColorByIndex = (index: number) => {
  const colors = ['primary', 'secondary', 'tertiary', 'success', 'warning']
  return colors[index % colors.length] || 'primary'
}

const startEdit = () => {
  const steps = props.recipe.cooking_steps || []
  editRows.value = steps.map(s => {
    const stepObj = typeof s === 'object' ? s : { content: s }
    return {
      tempId: Date.now() + Math.random(),
      content: stepObj.content || '',
      duration_minutes: stepObj.duration_minutes !== undefined ? String(stepObj.duration_minutes) : '',
      tips: stepObj.tips || '',
    }
  })
  if (editRows.value.length === 0) {
    addRow()
  }
  editing.value = true
}

const cancelEdit = () => {
  editing.value = false
}

const addRow = () => {
  editRows.value.push({
    tempId: Date.now() + Math.random(),
    content: '',
    duration_minutes: '',
    tips: '',
  })
}

const removeRow = (index: number) => {
  editRows.value.splice(index, 1)
}

const handleSave = async () => {
  saving.value = true
  try {
    const cookingSteps = editRows.value
      .filter(row => row.content.trim())
      .map(row => {
        const step: any = { content: row.content.trim() }
        if (row.duration_minutes) {
          step.duration_minutes = parseFloat(row.duration_minutes)
        }
        if (row.tips) {
          step.tips = row.tips.trim()
        }
        return step
      })

    if (JSON.stringify(cookingSteps) === JSON.stringify(props.recipe.cooking_steps)) {
      editing.value = false
      return
    }

    const result = await api.put(`/recipes/${props.recipe.id}`, { cooking_steps: cookingSteps })
    emit('saved', result)
    editing.value = false
  } catch (e: any) {
    console.error('保存步骤失败', e)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.step-content {
  line-height: 1.5;
  color: rgb(var(--v-theme-on-surface));
}

.step-edit-item {
  transition: background-color 0.15s;
}

.step-edit-item:hover {
  background: rgba(var(--v-theme-primary), 0.02);
}

.border-bottom {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
}

.drag-handle {
  cursor: grab;
}

.drag-over {
  border-top: 2px solid rgb(var(--v-theme-primary)) !important;
}

.step-number {
  font-size: 1.1rem;
}
</style>
