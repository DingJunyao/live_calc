<template>
  <div class="daily-summary-bar">
    <v-sheet
      class="summary-sheet px-4 py-3"
      :class="{ 'summary-sheet--mobile': !isDesktop }"
      rounded="lg"
      elevation="1"
    >
      <!-- 加载骨架 -->
      <v-skeleton-loader
        v-if="loading"
        type="text@3"
        class="bg-transparent"
      />

      <template v-else-if="totals">
        <!-- 成本 -->
        <div class="d-flex align-center justify-space-between flex-wrap">
          <div class="d-flex align-center ga-4 flex-wrap">
            <div class="summary-item">
              <span class="text-caption text-medium-emphasis">💰 今日预估</span>
              <span class="text-h6 font-weight-bold ml-1">
                {{ totals.cost != null ? `¥${totals.cost.toFixed(2)}` : '--' }}
              </span>
            </div>

            <!-- 营养汇总 -->
            <div class="summary-item">
              <span class="text-caption text-medium-emphasis">🔥 热量</span>
              <span class="font-weight-medium ml-1">
                {{ totals.calories != null ? `${totals.calories} kcal` : '--' }}
              </span>
            </div>

            <div class="d-flex ga-2 flex-wrap">
              <div class="summary-item">
                <span class="text-caption text-medium-emphasis">🥩 蛋白</span>
                <span class="font-weight-medium ml-1">
                  {{ totals.protein_g != null ? `${totals.protein_g}g` : '--' }}
                </span>
              </div>
              <div class="summary-item">
                <span class="text-caption text-medium-emphasis">🍚 碳水</span>
                <span class="font-weight-medium ml-1">
                  {{ totals.carbs_g != null ? `${totals.carbs_g}g` : '--' }}
                </span>
              </div>
              <div class="summary-item">
                <span class="text-caption text-medium-emphasis">🥑 脂肪</span>
                <span class="font-weight-medium ml-1">
                  {{ totals.fat_g != null ? `${totals.fat_g}g` : '--' }}
                </span>
              </div>
            </div>
          </div>

          <!-- 进度条 -->
          <div v-if="goalProgress" class="progress-area mt-2 mt-md-0" style="min-width: 180px">
            <div class="d-flex justify-space-between text-caption mb-1">
              <span>{{ goalProgress.label }}</span>
              <span>{{ goalProgress.pct }}%</span>
            </div>
            <v-progress-linear
              :model-value="goalProgress.pct"
              :color="goalProgress.color"
              height="8"
              rounded
            />
          </div>
        </div>
      </template>

      <div v-else class="text-caption text-medium-emphasis text-center py-2">
        暂无数据
      </div>
    </v-sheet>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDisplay } from 'vuetify'
import type { DailyTotals } from '@/api/meals'

const { mdAndUp } = useDisplay()
const isDesktop = computed(() => mdAndUp.value)

const props = defineProps<{
  totals: DailyTotals | null
  loading: boolean
}>()

const goalProgress = computed(() => {
  if (!props.totals || props.totals.calories == null) return null

  const consumed = props.totals.calories
  const target = 2000
  const pct = Math.min(Math.round((consumed / target) * 100), 100)
  const color = pct > 100 ? 'error' : pct > 80 ? 'warning' : 'success'
  return { label: `热量目标 ${target} kcal`, pct, color }
})
</script>

<style scoped>
.summary-sheet {
  border: 1px solid rgba(var(--v-border-color), 0.12);
}
.summary-item {
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
}
.progress-area {
  max-width: 240px;
}
</style>
