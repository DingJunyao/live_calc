<template>
  <div v-if="hasData" ref="containerRef" class="sparkline-background">
    <v-sparkline
      :model-value="data"
      :gradient="gradientColors"
      :smooth="10"
      :line-width="1"
      :padding="4"
      :gradient-direction="'top'"
      :fill="true"
      :auto-draw="false"
      :height="height"
      type="trend"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  data: number[]
  color?: string
  height?: number | string
  opacity?: number
}>(), {
  color: 'primary',
  height: '100%',
  opacity: 0.18
})

const containerRef = ref<HTMLElement>()
const hasData = computed(() => props.data && props.data.length >= 2)

// 窄容器（移动端 64px）中 v-sparkline 的 viewBox 300:36 会导致内容只有 ~8px 高。
// 仅在容器宽度 < 200px 时添加 preserveAspectRatio="none" 拉伸填充；
// 桌面端卡片（>200px）保持默认，宽高比合理无需拉伸。
function fixSvgAspectRatio() {
  nextTick(() => {
    const container = containerRef.value
    if (!container) return
    const svg = container.querySelector('svg')
    if (!svg) return
    if (container.clientWidth < 200) {
      if (!svg.hasAttribute('preserveAspectRatio')) {
        svg.setAttribute('preserveAspectRatio', 'none')
      }
      container.classList.add('sparkline-fix-narrow')
    } else {
      container.classList.remove('sparkline-fix-narrow')
    }
  })
}

onMounted(fixSvgAspectRatio)
watch(() => props.data, fixSvgAspectRatio)

// 构建 gradient 数组：使用主题 CSS 变量以适配暗色模式
const gradientColors = computed(() => {
  return [
    `rgba(var(--v-theme-${props.color}), ${props.opacity})`,
    `rgba(var(--v-theme-${props.color}), ${props.opacity * 0.55})`,
    `rgba(var(--v-theme-${props.color}), ${props.opacity * 0.1})`,
  ]
})
</script>

<style scoped>
.sparkline-background {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

/* 确保 sparkline 填充整个容器 */
.sparkline-background :deep(.v-sparkline) {
  width: 100%;
  height: 100%;
}

/* v-sparkline 的 SVG 有固定 viewBox，默认保持宽高比。
   仅在窄容器中强制撑满 + preserveAspectRatio="none" 拉伸填充。 */
.sparkline-background.sparkline-fix-narrow :deep(svg) {
  width: 100% !important;
  height: 100% !important;
}
</style>
