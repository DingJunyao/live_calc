<template>
  <v-app-bar v-if="!isDesktop" elevation="0" color="background" density="comfortable">
    <v-app-bar-nav-icon @click="toggleDrawer" />
    <v-app-bar-title class="text-h6">
      {{ title }}
    </v-app-bar-title>
    <template #append>
      <slot name="append" />
    </template>
  </v-app-bar>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'

defineProps<{
  title: string
}>()

const { toggleDrawer } = useMobileDrawerControl()
const isDesktop = ref(true)
let mediaQuery: MediaQueryList | null = null

const updateIsDesktop = (e: MediaQueryListEvent | MediaQueryList) => {
  isDesktop.value = e.matches
}

onMounted(() => {
  mediaQuery = window.matchMedia('(min-width: 960px)')
  isDesktop.value = mediaQuery.matches
  mediaQuery.addEventListener('change', updateIsDesktop)
})

onUnmounted(() => {
  if (mediaQuery) {
    mediaQuery.removeEventListener('change', updateIsDesktop)
  }
})
</script>
