<template>
  <v-snackbar v-model="show" :color="color" timeout="4000" location="top">
    {{ message }}
    <template #actions>
      <v-btn variant="text" @click="show = false">关闭</v-btn>
    </template>
  </v-snackbar>
</template>

<script setup lang="ts">
import { useGlobalSnackbar } from '@/composables/useGlobalSnackbar'

const { show, message, color } = useGlobalSnackbar()
</script>
