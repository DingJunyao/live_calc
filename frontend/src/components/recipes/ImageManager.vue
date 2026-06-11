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
          :src="getImageUrl(img)"
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
          icon="mdi-close-circle"
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
        <!-- 拖拽排序手柄 -->
        <v-icon
          class="image-drag-handle"
          size="small"
        >mdi-drag</v-icon>
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
import { api } from '@/api/client'

const props = defineProps<{
  modelValue: string[]
  uploading: boolean
  recipeId?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void
  (e: 'remove', index: number): void
  (e: 'upload', file: File): void
}>()

const fileInputRef = ref<any>(null)

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

const getImageUrl = (path: string) => {
  if (path.startsWith('http')) return path
  if (path.startsWith('/static/images/')) return `/api/v1${path}`
  return `${import.meta.env.VITE_DATA_REPO_IMAGE_BASE || 'https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out'}/${path}`
}
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

.image-drag-handle {
  position: absolute;
  top: 2px;
  left: 2px;
  z-index: 2;
  color: white;
  text-shadow: 0 0 3px rgba(0, 0, 0, 0.8);
  cursor: grab;
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
