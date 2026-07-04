<template>
  <v-alert
    v-if="proposal"
    :type="alertType"
    variant="tonal"
    density="comfortable"
    class="mb-3"
    :icon="icon"
  >
    <div class="text-body-2">
      {{ message }}
    </div>
  </v-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  proposal: {
    id: number
    action: string
    payload: Record<string, any>
  } | null
}>()

const alertType = computed(() => {
  if (!props.proposal) return 'info'
  return props.proposal.action === 'delete' ? 'warning' : 'info'
})

const icon = computed(() => {
  if (!props.proposal) return 'mdi-information'
  return props.proposal.action === 'delete'
    ? 'mdi-delete-clock-outline'
    : 'mdi-clock-edit-outline'
})

const message = computed(() => {
  if (!props.proposal) return ''
  if (props.proposal.action === 'delete') {
    return '该条目已提交删除申请，待管理员审核。审核通过后该条目将被删除。'
  }
  return '修改待审核——您看到的是已提交的修改内容。审核通过后将正式生效。'
})
</script>
