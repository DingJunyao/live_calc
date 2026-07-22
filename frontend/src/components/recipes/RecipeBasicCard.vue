<template>
  <v-card elevation="0" class="ma-4">
    <v-card-title class="d-flex align-center pb-2">
      <v-icon start color="primary">mdi-information-outline</v-icon>
      菜谱介绍
      <v-spacer />
      <template v-if="!editing">
        <v-btn
          size="small"
          variant="text"
          color="primary"
          prepend-icon="mdi-pencil"
          @click="startEdit"
        >编辑</v-btn>
      </template>
      <template v-else>
        <v-btn
          size="small"
          variant="text"
          color="success"
          prepend-icon="mdi-check"
          :loading="saving"
          @click="handleSave"
        >保存</v-btn>
        <v-btn
          size="small"
          variant="text"
          color="medium-emphasis"
          prepend-icon="mdi-close"
          :disabled="saving"
          @click="cancelEdit"
          class="ml-1"
        >取消</v-btn>
      </template>
    </v-card-title>
    <v-divider />

    <!-- 查看模式 -->
    <template v-if="!editing">
      <v-card-text>
        <div class="d-flex flex-wrap ga-2 mb-3">
          <v-chip
            v-if="recipe.category"
            size="small"
            variant="tonal"
            color="primary"
          >{{ recipe.category }}</v-chip>
          <v-chip
            v-if="recipe.difficulty"
            size="small"
            variant="tonal"
            color="secondary"
          >{{ difficultyLabel }}</v-chip>
          <v-chip
            v-if="resultIngredientName"
            size="small"
            variant="tonal"
            color="success"
          >⤴ 成品：{{ resultIngredientName }}</v-chip>
        </div>
        <div
          v-if="recipe.description"
          class="text-body-2"
          style="white-space: pre-wrap"
        >{{ recipe.description }}</div>
        <div
          v-else
          class="text-body-2 text-medium-emphasis"
        >暂未填写介绍</div>
      </v-card-text>
    </template>

    <!-- 编辑模式 -->
    <v-card-text v-else>
      <v-text-field
        v-model="editForm.name"
        label="菜谱名称"
        variant="outlined"
        density="compact"
        maxlength="200"
        hide-details
        class="mb-3"
      />
      <v-row class="mb-3">
        <v-col cols="6">
          <v-select
            v-model="editForm.category"
            label="分类"
            variant="outlined"
            density="compact"
            :items="categoryOptions"
            hide-details
          />
        </v-col>
        <v-col cols="6">
          <v-select
            v-model="editForm.difficulty"
            label="难度"
            variant="outlined"
            density="compact"
            :items="difficultyOptions"
            item-title="label"
            item-value="value"
            hide-details
          />
        </v-col>
      </v-row>
      <v-textarea
        v-model="editForm.description"
        label="菜谱简介"
        variant="outlined"
        density="compact"
        auto-grow
        rows="3"
        maxlength="2000"
        hide-details
        class="mb-4"
      />

      <!-- 成品产出原料（半成品菜谱） -->
      <div class="text-subtitle-2 mb-1">成品产出</div>
      <div class="text-caption text-medium-emphasis mb-2">若本菜谱产出的成品可作为其它菜谱的原料（如蒸米饭→米饭），请选择对应原料，其成本将由本菜谱推导。</div>
      <v-autocomplete
        v-model="editForm.result_ingredient_id"
        :items="ingredientOptions"
        item-title="name"
        item-value="id"
        label="成品产出原料"
        variant="outlined"
        density="compact"
        clearable
        :loading="ingredientSearching"
        @update:search="onIngredientSearch"
        hide-details
        class="mb-4"
      />

      <!-- 配图管理 -->
      <v-divider class="mb-3" />
      <div class="text-subtitle-2 mb-2">配图管理</div>
      <ImageManager
        v-model="editImages"
        :image-urls="recipe.image_urls"
        :recipe-id="recipe.id"
        :uploading="uploadingImage"
        @upload="handleImageUpload"
        @remove="handleImageRemove"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { api } from '@/api/client'
import ImageManager from './ImageManager.vue'
import type { RecipeDetail } from './types'

const props = defineProps<{
  recipe: RecipeDetail
}>()

const emit = defineEmits<{
  (e: 'saved', recipe: RecipeDetail): void
  (e: 'images-changed'): void
}>()

const editing = ref(false)
const saving = ref(false)
const uploadingImage = ref(false)
const editForm = ref({
  name: '',
  category: '',
  difficulty: '',
  description: '',
  result_ingredient_id: null as number | null,
})
const editImages = ref<string[]>([])

// 成品产出原料搜索
const ingredientOptions = ref<{ id: number; name: string }[]>([])
const ingredientSearching = ref(false)
const resultIngredientName = ref('')
let searchTimer: any = null

const onIngredientSearch = (q: string) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q || !q.trim()) return
  searchTimer = setTimeout(async () => {
    ingredientSearching.value = true
    try {
      const res = await api.get(`/ingredients/search-by-name/${encodeURIComponent(q.trim())}`)
      ingredientOptions.value = (res || []).map((i: any) => ({ id: i.id, name: i.name }))
    } catch (e) {
      console.error('搜索原料失败', e)
    } finally {
      ingredientSearching.value = false
    }
  }, 300)
}

// 成品原料名（查看模式展示）：初始加载时若已绑定则查名
watch(() => props.recipe.result_ingredient_id, async (id) => {
  if (id) {
    try {
      const r = await api.get(`/ingredients/${id}`)
      resultIngredientName.value = r?.name || ''
      ingredientOptions.value = [{ id, name: r?.name || '' }]
    } catch {
      resultIngredientName.value = ''
    }
  } else {
    resultIngredientName.value = ''
  }
}, { immediate: true })

const categoryOptions = [
  { title: '荤菜', value: '荤菜' },
  { title: '素菜', value: '素菜' },
  { title: '水产', value: '水产' },
  { title: '主食', value: '主食' },
  { title: '汤与粥', value: '汤与粥' },
  { title: '早餐', value: '早餐' },
  { title: '甜品', value: '甜品' },
  { title: '调料', value: '调料' },
  { title: '半成品', value: '半成品' },
  { title: '小食', value: '小食' },
]

const difficultyOptions = [
  { label: '简易', value: 'simple' },
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
  { label: '专家', value: 'expert' },
]

const difficultyLabel = computed(() => {
  const opt = difficultyOptions.find(d => d.value === props.recipe.difficulty)
  return opt?.label || props.recipe.difficulty || ''
})

const startEdit = () => {
  editForm.value = {
    name: props.recipe.name || '',
    category: props.recipe.category || '',
    difficulty: props.recipe.difficulty || '',
    description: props.recipe.description || '',
    result_ingredient_id: props.recipe.result_ingredient_id ?? null,
  }
  editImages.value = [...(props.recipe.images || [])]
  editing.value = true
}

const cancelEdit = () => {
  editing.value = false
}

// 上传配图 — 立即上传到后端
const handleImageUpload = async (file: File) => {
  uploadingImage.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const result = await api.post(`/recipes/${props.recipe.id}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (result?.image_path) {
      editImages.value.push(result.image_path)
    }
  } catch (e: any) {
    console.error('上传图片失败', e)
  } finally {
    uploadingImage.value = false
  }
}

// 删除配图 — 仅从本地列表移除，实际变更在保存时通过 PUT /recipes/{id} 的 images 字段提交
// 这样已发布菜谱会走审核提议流程（与菜谱信息编辑一致），未发布菜谱直接生效
const handleImageRemove = (index: number) => {
  editImages.value.splice(index, 1)
}

const handleSave = async () => {
  saving.value = true
  try {
    // 收集有变化的字段
    const payload: Record<string, any> = {}
    if (editForm.value.name !== props.recipe.name) payload.name = editForm.value.name
    if (editForm.value.category !== props.recipe.category) payload.category = editForm.value.category
    if (editForm.value.difficulty !== props.recipe.difficulty) payload.difficulty = editForm.value.difficulty
    if (editForm.value.description !== (props.recipe.description || '')) payload.description = editForm.value.description
    const newRiId = editForm.value.result_ingredient_id ?? null
    const oldRiId = props.recipe.result_ingredient_id ?? null
    if (newRiId !== oldRiId) payload.result_ingredient_id = newRiId
    if (JSON.stringify(editImages.value) !== JSON.stringify(props.recipe.images || [])) {
      payload.images = editImages.value
    }

    if (Object.keys(payload).length === 0) {
      editing.value = false
      return
    }

    const result = await api.put(`/recipes/${props.recipe.id}`, payload)
    emit('saved', result)
    emit('images-changed')
    editing.value = false
  } catch (e: any) {
    console.error('保存基本信息失败', e)
  } finally {
    saving.value = false
  }
}
</script>
