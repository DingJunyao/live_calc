<template>
  <v-card
    class="meal-card"
    :class="{
      'meal-card--current': recommendation.is_current_meal,
      'meal-card--empty': !recommendation.recipe,
    }"
    :elevation="recommendation.is_current_meal ? 3 : 1"
    rounded="lg"
    @click="goToRecipe"
  >
    <!-- 加载遮罩 -->
    <v-overlay
      :model-value="isRefreshing"
      contained
      class="align-center justify-center"
      persistent
    >
      <v-progress-circular indeterminate color="primary" size="32" />
    </v-overlay>

    <!-- 空状态 -->
    <v-card-text v-if="!recommendation.recipe" class="empty-state pa-6 text-center">
      <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-book-plus-outline</v-icon>
      <p class="text-body-2 text-medium-emphasis mb-3">
        请完整维护菜谱，以获取推荐信息
      </p>
      <v-btn
        size="small"
        variant="outlined"
        color="primary"
        @click.stop="goToRecipes"
      >
        去添加菜谱
      </v-btn>
    </v-card-text>

    <!-- 正常卡片 -->
    <template v-else>
      <v-img
        v-if="recipeImage"
        :src="recipeImage"
        height="140"
        cover
        class="align-end"
      >
        <v-toolbar
          color="rgba(0,0,0,0.4)"
          density="compact"
          class="meal-card__overlay-toolbar"
        >
          <v-toolbar-title class="text-white text-body-1">
            {{ recommendation.recipe.name }}
          </v-toolbar-title>
        </v-toolbar>
      </v-img>

      <v-card-item v-if="!recipeImage">
        <v-card-title class="text-body-1">{{ recommendation.recipe.name }}</v-card-title>
        <v-card-subtitle v-if="recommendation.recipe.category">
          {{ recommendation.recipe.category }}
        </v-card-subtitle>
      </v-card-item>

      <v-card-text class="pb-2">
        <div class="d-flex align-center ga-3 flex-wrap">
          <span class="text-caption text-medium-emphasis">
            💰 {{ costText }}
          </span>
          <span class="text-caption text-medium-emphasis">
            🔥 {{ calorieText }}
          </span>
          <span class="text-caption text-medium-emphasis">
            🥩 {{ proteinText }}
          </span>
        </div>
        <div
          v-if="!recommendation.recipe.nutrition_per_serving"
          class="text-caption text-disabled mt-1"
        >
          该菜谱暂无营养数据
        </div>
      </v-card-text>

      <v-card-actions class="pt-0">
        <v-spacer />
        <v-btn
          size="small"
          variant="text"
          :loading="isRefreshing"
          @click.stop="onRefresh"
          :disabled="isRefreshing"
        >
          <v-icon start size="18">mdi-refresh</v-icon>
          换一个
        </v-btn>
      </v-card-actions>
    </template>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { MealRecommendation } from '@/api/meals'

const router = useRouter()

const props = defineProps<{
  recommendation: MealRecommendation
  isRefreshing: boolean
}>()

const emit = defineEmits<{
  refresh: [mealType: string]
}>()

const recipeImage = computed(() => {
  const images = props.recommendation.recipe?.images
  if (images && images.length > 0) {
    const raw = images[0]
    if (!raw) return null
    // 如果是相对路径，补上 API 前缀
    if (raw.startsWith('/')) {
      const base = import.meta.env.VITE_API_URL || '/api/v1'
      return base + raw
    }
    return raw
  }
  return null
})

const costText = computed(() => {
  const cost = props.recommendation.recipe?.cost_estimate
  return cost != null ? `¥${cost.toFixed(2)}` : '--'
})

const calorieText = computed(() => {
  const cal = props.recommendation.recipe?.nutrition_per_serving?.calories
  return cal != null ? `${cal} kcal` : '--'
})

const proteinText = computed(() => {
  const pro = props.recommendation.recipe?.nutrition_per_serving?.protein_g
  return pro != null ? `${pro}g` : '--'
})

function goToRecipe() {
  if (props.recommendation.recipe) {
    router.push(`/recipes/${props.recommendation.recipe.id}`)
  }
}

function goToRecipes() {
  router.push('/recipes')
}

function onRefresh() {
  emit('refresh', props.recommendation.meal_type)
}
</script>

<style scoped>
.meal-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.meal-card--current {
  border-left: 4px solid rgb(var(--v-theme-primary));
  animation: pulse-glow 2s ease-in-out infinite;
}
.meal-card--empty {
  cursor: default;
}
.meal-card:hover:not(.meal-card--empty) {
  transform: translateY(-2px);
}
.meal-card__overlay-toolbar {
  background: linear-gradient(to top, rgba(0,0,0,0.6), transparent) !important;
}
.empty-state {
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(var(--v-theme-primary), 0.3); }
  50% { box-shadow: 0 0 12px 2px rgba(var(--v-theme-primary), 0.15); }
}
</style>
