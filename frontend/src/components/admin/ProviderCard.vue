<!-- 单个翻译 provider 的配置卡片：按 fields 配置渲染表单 + 测试连接就地反馈 -->
<script setup lang="ts">
defineProps<{
  title: string
  fields: Array<{ key: string; label: string; type?: 'text' | 'password' | 'switch' }>
  values: Record<string, any>
  testing?: boolean
  testResult?: { ok: boolean; detail: string } | null
  hint?: string
}>()

const emit = defineEmits<{
  (e: 'update:field', payload: { field: string; value: any }): void
  (e: 'test'): void
}>()
</script>

<template>
  <v-card class="my-3" variant="outlined">
    <v-card-title>{{ title }}</v-card-title>
    <v-card-text>
      <p v-if="hint" class="text-caption">{{ hint }}</p>
      <template v-for="f in fields" :key="f.key">
        <v-switch
          v-if="f.type === 'switch'"
          :model-value="values[f.key]"
          :label="f.label"
          density="compact"
          hide-details="auto"
          @update:model-value="emit('update:field', { field: f.key, value: $event })"
        />
        <v-text-field
          v-else
          :model-value="values[f.key]"
          :label="f.label"
          :type="f.type === 'password' ? 'password' : 'text'"
          density="compact"
          hide-details="auto"
          @update:model-value="emit('update:field', { field: f.key, value: $event })"
        />
      </template>
      <div class="d-flex align-center mt-2">
        <v-btn :loading="testing" @click="emit('test')">测试连接</v-btn>
        <span
          v-if="testResult"
          class="ml-3 text-body-2"
          :class="testResult.ok ? 'text-success' : 'text-error'"
        >
          {{ testResult.detail }}
        </span>
      </div>
    </v-card-text>
  </v-card>
</template>
