<template>
  <v-container fluid>
    <!-- 顶部 -->
    <v-app-bar elevation="0" color="background">
      <v-app-bar-title class="text-h6">菜谱管理</v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadRecipes" />
      </template>
    </v-app-bar>

    <!-- 搜索栏 -->
    <v-text-field
      v-model="searchQuery"
      label="搜索菜谱..."
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      hide-details
      clearable
      class="mb-4"
      @update:model-value="debouncedSearch"
    />

    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadRecipes">重试</v-btn>
      </template>
    </v-alert>

    <!-- 菜谱网格 -->
    <v-row v-else>
      <v-col
        v-for="recipe in recipes"
        :key="recipe.id"
        cols="6"
      >
        <v-card
          class="recipe-card"
          @click="goToDetail(recipe.id)"
          hover
        >
          <!-- 图片占位 -->
          <v-avatar
            color="primary-container"
            size="120"
            class="mx-auto d-block my-4"
          >
            <v-icon size="64" color="primary">
              mdi-food
            </v-icon>
          </v-avatar>

          <v-card-title class="text-center pa-2 text-h6">
            {{ recipe.name }}
          </v-card-title>

          <v-card-text class="text-center pa-2">
            <div class="text-h5 font-weight-bold text-tertiary mb-1">
              ¥{{ formatCost(recipe.estimated_cost) }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ recipe.calories || '-' }} kcal
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 空状态 -->
      <v-col v-if="recipes.length === 0 && !loading" cols="12">
        <div class="text-center py-16 text-medium-emphasis">
          <v-icon size="80" color="medium-emphasis">mdi-book-open-variant</v-icon>
          <div class="text-h6 mt-4">暂无菜谱</div>
          <div class="text-body-2 mt-2">点击下方按钮添加第一个菜谱</div>
        </div>
      </v-col>
    </v-row>

    <!-- 分页器 -->
    <div v-if="total > 0" class="d-flex justify-center align-center ga-4 py-4">
      <v-select
        v-model="pageSize"
        :items="[10, 20, 50, 100]"
        label="每页"
        variant="outlined"
        density="compact"
        hide-details
        style="max-width: 100px"
        @update:model-value="handlePageSizeChange"
      />
      <v-pagination
        v-model="currentPage"
        :length="totalPages"
        :total-visible="5"
        rounded="circle"
      />
      <span class="text-caption text-medium-emphasis">共 {{ total }} 条</span>
    </div>

    <!-- 悬浮按钮 -->
    <v-fab
      icon="mdi-plus"
      color="primary"
      location="bottom right"
      size="large"
      app
      @click="showAddDialog = true"
    />

    <!-- 添加菜谱对话框（简化版） -->
    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>添加菜谱</v-card-title>
        <v-card-text>
          <v-alert type="info" class="mb-4">
            菜谱创建功能即将推出，敬请期待！
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'

interface Recipe {
  id: number
  name: string
  description?: string
  category?: string
  difficulty?: string
  cooking_time?: number
  servings?: number
  estimated_cost?: number | string
  calories?: number
  created_at?: string
}

const router = useRouter()

const recipes = ref<Recipe[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref('')
const showAddDialog = ref(false)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadRecipes()
  }, 300)
}

const loadRecipes = async () => {
  loading.value = true
  error.value = null
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params: Record<string, any> = {
      skip,
      limit: pageSize.value,
      include_cost: true
    }
    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    const response = await api.get('/recipes', { params })
    recipes.value = response.items || []
    total.value = response.total || 0
  } catch (e: any) {
    console.error('加载菜谱失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  loadRecipes()
}

watch(currentPage, () => {
  loadRecipes()
})

const formatCost = (cost: any) => {
  const num = parseFloat(cost) || 0
  return num.toFixed(2)
}

const goToDetail = (id: number) => {
  router.push(`/recipes/${id}`)
}

onMounted(() => {
  loadRecipes()
})
</script>

<style scoped>
.recipe-card {
  cursor: pointer;
  height: 100%;
}
</style>
