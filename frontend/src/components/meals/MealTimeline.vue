<template>
  <div class="meal-timeline" :class="{ 'meal-timeline--mobile': !isDesktop }">
    <div
      v-for="(rec, index) in recommendations"
      :key="rec.meal_type"
      class="timeline-node"
      :class="{ 'timeline-node--current': rec.is_current_meal }"
    >
      <!-- 时间线节点区 -->
      <div class="timeline-marker">
        <div class="timeline-dot" :class="{ 'timeline-dot--current': rec.is_current_meal }">
          <v-icon v-if="rec.recipe" size="16">{{ mealIcon(rec.meal_type) }}</v-icon>
          <v-icon v-else size="16" color="grey">mdi-minus</v-icon>
        </div>
        <div class="timeline-label">
          <span class="text-body-2 font-weight-medium">{{ mealLabel(rec.meal_type) }}</span>
          <span class="text-caption text-medium-emphasis ml-2">{{ mealTime(rec.meal_type) }}</span>
        </div>
        <!-- 连线 -->
        <div v-if="index < recommendations.length - 1" class="timeline-line" />
      </div>

      <!-- 卡片区 -->
      <div class="timeline-card">
        <MealCard
          :recommendation="rec"
          :is-refreshing="refreshLoading[rec.meal_type] || false"
          @refresh="(mt: string) => $emit('refresh', mt)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDisplay } from 'vuetify'
import MealCard from './MealCard.vue'
import type { MealRecommendation } from '@/api/meals'

const { mdAndUp } = useDisplay()
const isDesktop = computed(() => mdAndUp.value)

defineProps<{
  recommendations: MealRecommendation[]
  refreshLoading: Record<string, boolean>
}>()

defineEmits<{
  refresh: [mealType: string]
}>()

function mealLabel(type: string) {
  const map: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
  }
  return map[type] || type
}

function mealTime(type: string) {
  const map: Record<string, string> = {
    breakfast: '07:30',
    lunch: '12:00',
    dinner: '18:30',
  }
  return map[type] || ''
}

function mealIcon(type: string) {
  const map: Record<string, string> = {
    breakfast: 'mdi-weather-sunny',
    lunch: 'mdi-white-balance-sunny',
    dinner: 'mdi-weather-night',
  }
  return map[type] || 'mdi-food'
}
</script>

<style scoped>
/* 桌面端：横向时间线 */
.meal-timeline:not(.meal-timeline--mobile) {
  display: flex;
  justify-content: center;
  gap: 0;
  padding: 24px 16px;
  overflow-x: auto;
}

.meal-timeline:not(.meal-timeline--mobile) .timeline-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 0 0 auto;
  min-width: 240px;
  max-width: 380px;
}

.meal-timeline:not(.meal-timeline--mobile) .timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  width: 100%;
}

.meal-timeline:not(.meal-timeline--mobile) .timeline-line {
  position: absolute;
  top: 16px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: rgba(var(--v-border-color), 0.5);
}

.meal-timeline:not(.meal-timeline--mobile) .timeline-card {
  width: 100%;
  margin-top: 12px;
  padding: 0 8px;
}

/* 移动端：纵向时间线 */
.meal-timeline--mobile {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
}

.meal-timeline--mobile .timeline-node {
  display: flex;
  align-items: flex-start;
  position: relative;
  padding-left: 40px;
  min-height: 100px;
}

.meal-timeline--mobile .timeline-marker {
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.meal-timeline--mobile .timeline-label {
  white-space: nowrap;
}

.meal-timeline--mobile .timeline-line {
  flex: 1;
  width: 2px;
  min-height: 20px;
  background: rgba(var(--v-border-color), 0.5);
  margin-top: 8px;
}

.meal-timeline--mobile .timeline-card {
  flex: 1;
  width: 100%;
}

/* 通用样式 */
.timeline-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(var(--v-theme-surface-variant), 1);
  border: 2px solid rgba(var(--v-border-color), 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  transition: all 0.3s;
}

.timeline-dot--current {
  background: rgb(var(--v-theme-primary));
  border-color: rgb(var(--v-theme-primary));
  transform: scale(1.2);
  box-shadow: 0 0 8px rgba(var(--v-theme-primary), 0.4);
}

.timeline-dot--current .v-icon {
  color: white !important;
}

.timeline-label {
  margin-top: 4px;
}
</style>
