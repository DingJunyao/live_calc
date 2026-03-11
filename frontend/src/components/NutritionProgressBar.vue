<template>
  <div class="nutrition-progress-bar" :class="sizeClass">
    <div class="progress-container">
      <div
        class="progress-bar"
        :style="{
          width: `${Math.min(percentage, 100)}%`,
          backgroundColor: barColor
        }"
      ></div>
    </div>
    <div v-if="showPercentage" class="progress-label">
      {{ Math.round(percentage) }}%
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  percentage: number
  size?: 'default' | 'small'
  showPercentage?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default',
  showPercentage: false
})

const sizeClass = computed(() => `size-${props.size}`)

const barColor = computed(() => {
  if (props.percentage >= 100) {
    return '#ef5350' // 红色 - 超标
  } else if (props.percentage >= 80) {
    return '#ffa726' // 橙色 - 接近上限
  } else if (props.percentage >= 50) {
    return '#66bb6a' // 绿色 - 充足
  } else if (props.percentage >= 20) {
    return '#42a5f5' // 蓝色 - 适中
  } else {
    return '#bdbdbd' // 灰色 - 不足
  }
})
</script>

<style scoped>
.nutrition-progress-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-container {
  flex: 1;
  height: 100%;
  background: #f0f0f0;
  border-radius: 0.25rem;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
  border-radius: 0.25rem;
}

.progress-label {
  font-size: 0.75rem;
  color: #666;
  font-weight: 500;
  min-width: 40px;
  text-align: right;
}

.size-default {
  height: 24px;
}

.size-small {
  height: 16px;
}

.size-small .progress-label {
  font-size: 0.625rem;
  min-width: 32px;
}
</style>
