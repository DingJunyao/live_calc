<template>
  <div class="image-manager">
    <!-- 缩略图网格 -->
    <div class="d-flex flex-wrap ga-2">
      <div
        v-for="(img, index) in modelValue"
        :key="index"
        class="image-thumb-wrapper"
      >
        <v-img
          :src="imageUrls?.[index] || getImageUrl(img)"
          width="80"
          height="80"
          cover
          class="rounded"
        >
          <template #placeholder>
            <div class="d-flex align-center justify-center fill-height bg-surface-variant">
              <v-progress-circular indeterminate size="small" color="primary" />
            </div>
          </template>
          <template #error>
            <div class="d-flex align-center justify-center fill-height bg-surface-variant">
              <v-icon size="small" color="medium-emphasis">mdi-image-broken</v-icon>
            </div>
          </template>
        </v-img>
        <!-- 删除按钮 -->
        <v-btn
          icon="mdi-delete"
          size="x-small"
          color="error"
          variant="flat"
          class="image-delete-btn"
          @click="$emit('remove', index)"
        />
        <!-- 封面标记 -->
        <v-chip
          v-if="index === 0"
          size="x-small"
          color="primary"
          variant="flat"
          class="image-cover-badge"
        >封面</v-chip>
        <!-- 左右移动按钮 -->
        <div class="image-move-btns">
          <v-btn
            icon="mdi-chevron-left"
            size="small"
            variant="text"
            density="compact"
            :disabled="index === 0"
            @click.stop="moveLeft(index)"
          />
          <v-btn
            icon="mdi-chevron-right"
            size="small"
            variant="text"
            density="compact"
            :disabled="index === modelValue.length - 1"
            @click.stop="moveRight(index)"
          />
        </div>
      </div>

      <!-- 添加上传按钮 -->
      <v-btn
        variant="outlined"
        class="image-add-btn"
        :loading="uploading"
        @click="triggerUpload"
      >
        <v-icon>mdi-plus</v-icon>
        <v-file-input
          ref="fileInputRef"
          accept="image/jpeg,image/png,image/gif,image/webp"
          hide-input
          density="compact"
          class="d-none"
          @change="onFileSelected"
        />
      </v-btn>
    </div>

    <!-- 提示文字 -->
    <div class="text-caption text-medium-emphasis mt-1">
      第一张图片为封面图。支持 JPG、PNG、GIF、WebP 格式。
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api'
import { resolveImageUrl } from '@/utils/image'

const props = defineProps<{
  modelValue: string[]
  imageUrls?: string[]  // 已解析的完整 URL，优先用于展示
  uploading: boolean
  recipeId?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void
  (e: 'remove', index: number): void
  (e: 'upload', file: File): void
  (e: 'reorder', images: string[]): void
}>()

const fileInputRef = ref<any>(null)
const dragIndex = ref<number | null>(null)

const moveLeft = (index: number) => {
  if (index <= 0) return
  const items = [...props.modelValue]
  const item = items.splice(index, 1)[0]
  items.splice(index - 1, 0, item)
  emit('update:modelValue', items)
  emit('reorder', items)
}
const moveRight = (index: number) => {
  if (index >= props.modelValue.length - 1) return
  const items = [...props.modelValue]
  const item = items.splice(index, 1)[0]
  items.splice(index + 1, 0, item)
  emit('update:modelValue', items)
  emit('reorder', items)
}

const triggerUpload = () => {
  fileInputRef.value?.click()
}

const onFileSelected = (event: any) => {
  const file = event?.target?.files?.[0]
  if (!file) return
  emit('upload', file)
  // 重置 file input 以便再次选择同一文件
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const getImageUrl = resolveImageUrl
</script>

<style scoped>
.image-thumb-wrapper {
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
}

.image-delete-btn {
  position: absolute;
  top: -6px;
  right: -6px;
  z-index: 2;
  min-width: 0;
  width: 20px;
  height: 20px;
}

.image-cover-badge {
  position: absolute;
  bottom: 2px;
  left: 2px;
  z-index: 2;
  font-size: 10px;
  height: 18px;
}

.image-move-btns {
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 0;
  z-index: 2;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 4px;
}
.image-move-btns :deep(.v-btn) {
  color: white;
}
.image-move-btns :deep(.v-btn.v-btn--disabled) {
  opacity: 0.4;
}

.image-add-btn {
  width: 80px;
  height: 80px;
  border: 2px dashed rgba(var(--v-border-color), 0.4);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
