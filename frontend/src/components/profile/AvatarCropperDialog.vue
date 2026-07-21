<template>
  <v-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" max-width="560" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        裁剪头像
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="$emit('update:modelValue', false)" />
      </v-card-title>
      <v-card-text>
        <div class="cropper-wrap" style="width: 100%; height: 400px; background: #f5f5f5;">
          <cropper
            v-if="src"
            :src="src"
            :stencil-props="{ aspectRatio: 1 }"
            :resize="{ image: true }"
            image-restriction="stencil"
            @change="onChange"
          />
        </div>
        <div class="text-caption text-medium-emphasis mt-2">拖动调整位置，滚轮缩放，输出 512×512</div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">取消</v-btn>
        <v-btn color="primary" :loading="processing" @click="confirm">确认裁剪</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'

defineProps<{ modelValue: boolean; src: string }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; cropped: [Blob] }>()

const canvas = ref<HTMLCanvasElement | null>(null)
const processing = ref(false)

function onChange({ canvas: c }: { canvas: HTMLCanvasElement }) {
  canvas.value = c
}

async function confirm() {
  processing.value = true
  try {
    const sourceCanvas = canvas.value
    if (!sourceCanvas) {
      processing.value = false
      return
    }
    // resize 到 512×512
    const out = document.createElement('canvas')
    out.width = 512
    out.height = 512
    const ctx = out.getContext('2d')
    if (!ctx) {
      processing.value = false
      return
    }
    ctx.drawImage(sourceCanvas, 0, 0, 512, 512)
    const blob: Blob = await new Promise((resolve, reject) => {
      out.toBlob((b) => {
        if (b) resolve(b)
        else reject(new Error('Canvas 转 Blob 失败'))
      }, 'image/jpeg', 0.9)
    })
    emit('cropped', blob)
    emit('update:modelValue', false)
  } catch (e) {
    // toBlob reject 或其他异常——processing 会在 finally 复位
    console.error('裁剪失败:', e)
  } finally {
    processing.value = false
  }
}
</script>
