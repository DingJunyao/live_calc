<template>
  <v-dialog v-model="visible" max-width="600" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-upload</v-icon>
        数据导入
      </v-card-title>

      <v-card-text>
        <v-alert v-if="result" :type="result.success ? 'success' : 'error'"
                 variant="tonal" class="mb-4" closable>
          <div v-if="result.success">
            导入完成：
            <span v-for="(v, k) in result.stats" :key="k" class="mr-2">
              {{ k }}={{ v }}
            </span>
          </div>
          <div v-else>{{ result.errors?.join('; ') }}</div>
          <div v-if="result.warnings?.length" class="mt-1">
            <div v-for="(w, i) in result.warnings" :key="i" class="text-caption">{{ w }}</div>
          </div>
        </v-alert>

        <v-file-input
          v-model="file"
          label="选择 ZIP 压缩包"
          accept=".zip"
          :loading="uploading"
          :disabled="uploading"
          @update:model-value="result = null"
        />

        <div v-if="uploading" class="text-center py-4">
          <v-progress-circular indeterminate color="primary" />
          <div class="mt-2">正在导入，请稍候…</div>
        </div>

        <v-btn block color="primary" :loading="uploading" :disabled="!file"
               class="mt-2" @click="handleUpload">
          <v-icon start>mdi-upload</v-icon>
          开始导入
        </v-btn>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="uploading" @click="close">关闭</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import axios from 'axios'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })

const file = ref<File | null>(null)
const uploading = ref(false)
const result = ref<any>(null)

async function handleUpload() {
  if (!file.value) return
  uploading.value = true
  result.value = null
  try {
    const form = new FormData()
    form.append('file', file.value)
    const token = localStorage.getItem('access_token')
    const baseURL = import.meta.env.VITE_API_URL || '/api/v1'
    const resp = await axios.post(`${baseURL}/import/data/upload`, form, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    result.value = resp.data
  } catch (e: any) {
    result.value = {
      success: false,
      errors: [e.response?.data?.detail || e.message],
    }
  } finally {
    uploading.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}
</script>
