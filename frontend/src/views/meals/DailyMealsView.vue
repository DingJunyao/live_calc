<template>
  <div class="daily-meals-view">
    <!-- 顶部栏 -->
    <v-app-bar flat density="comfortable" color="background">
      <v-app-bar-nav-icon
        @click="toggleSidebar(isDesktop)"
        icon="mdi-menu"
      />
      <v-app-bar-title>
        今日推荐
        <span class="text-caption text-medium-emphasis ml-2">
          {{ formattedDate }}
        </span>
      </v-app-bar-title>

      <template #append>
        <v-btn
          icon="mdi-cog-outline"
          size="small"
          variant="text"
          @click="goToProfile"
          title="营养目标设置"
        />
      </template>
    </v-app-bar>

    <!-- 加载状态 -->
    <div v-if="store.loading" class="px-4 pt-4">
      <v-skeleton-loader type="card@3" />
    </div>

    <!-- 后台生成中 -->
    <v-container v-else-if="store.generating" class="text-center mt-12">
      <v-progress-circular
        indeterminate
        color="primary"
        size="64"
        width="4"
      />
      <p class="text-body-1 text-medium-emphasis mt-4">
        正在为你计算今日推荐…
      </p>
      <p class="text-caption text-disabled mt-1">
        正在评估所有可用菜谱的营养搭配与成本，稍等一下～
      </p>
    </v-container>

    <!-- 错误状态 -->
    <v-container v-else-if="store.error" class="text-center mt-8">
      <v-icon size="64" color="grey-lighten-1">mdi-alert-circle-outline</v-icon>
      <p class="text-body-1 text-medium-emphasis mt-3">{{ store.error }}</p>
      <v-btn variant="outlined" color="primary" @click="store.loadRecommendations()">
        重试
      </v-btn>
    </v-container>

    <!-- 正常内容 -->
    <template v-else>
      <!-- 汇总条 -->
      <div class="px-4 pt-4">
        <DailySummaryBar :totals="store.totals" :loading="false" />
      </div>

      <!-- 时间线 -->
      <MealTimeline
        :recommendations="store.recommendations"
        :refresh-loading="store.refreshLoading"
        @refresh="handleRefresh"
      />
    </template>

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { useMealsStore } from '@/stores/meals'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import DailySummaryBar from '@/components/meals/DailySummaryBar.vue'
import MealTimeline from '@/components/meals/MealTimeline.vue'

const router = useRouter()
const store = useMealsStore()
const { mdAndUp } = useDisplay()
const isDesktop = computed(() => mdAndUp.value)
const { toggleSidebar } = useMobileDrawerControl()

const snackbar = reactive({
  show: false,
  message: '',
  color: 'info',
})

const formattedDate = computed(() => {
  if (!store.date) return ''
  const d = new Date(store.date)
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 星期${weekdays[d.getDay()]}`
})

function goToProfile() {
  router.push('/profile')
}

async function handleRefresh(mealType: string) {
  try {
    await store.refreshMeal(mealType)
    snackbar.color = 'success'
    snackbar.message = '换好啦～'
    snackbar.show = true
  } catch (e: any) {
    snackbar.color = e.response?.status === 429 ? 'warning' : 'error'
    snackbar.message = e.userMessage || '刷新失败，请稍后重试'
    snackbar.show = true
  }
}

onMounted(() => {
  store.loadRecommendations()
})
</script>

<style scoped>
.daily-meals-view {
  min-height: 100vh;
  max-width: 1200px;
  margin: 0 auto;
}

@media (max-width: 959px) {
  .daily-meals-view {
    max-width: 100%;
  }
}
</style>
