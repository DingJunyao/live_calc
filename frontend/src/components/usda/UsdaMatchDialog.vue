<script setup lang="ts">
import { ref } from 'vue'
import { searchUsdaFoods, getUsdaFood, matchIngredient, matchProduct } from '@/api/usda'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const props = defineProps<{
  modelValue: boolean
  entityType: 'ingredient' | 'product'
  entityId: number
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'matched'): void
}>()

// 行内提示（管理员直写 / 补空自动通过 / 待审核 区分）
const snackbar = ref<{ show: boolean; message: string; color: string }>({
  show: false,
  message: '',
  color: 'success',
})

const query = ref('')
const results = ref<any[]>([])
const loading = ref(false)
const selected = ref<any | null>(null)
const matching = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function onSearch() {
  if (!query.value || !query.value.trim()) {
    results.value = []
    return
  }
  loading.value = true
  try {
    results.value = await searchUsdaFoods(query.value)
  } finally {
    loading.value = false
  }
}

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(onSearch, 300)
}

async function pick(fdcId: number) {
  loading.value = true
  try {
    selected.value = await getUsdaFood(fdcId)
  } finally {
    loading.value = false
  }
}

// 二级确认对话框状态（替代浏览器原生 confirm，避免阻塞且样式不统一）
const confirmDialog = ref(false)

function onConfirmClick() {
  if (!selected.value) return
  confirmDialog.value = true
}

async function confirmMatch() {
  confirmDialog.value = false
  matching.value = true
  try {
    let res: any
    if (props.entityType === 'ingredient') {
      res = await matchIngredient(props.entityId, selected.value.fdc_id)
    } else {
      res = await matchProduct(props.entityId, selected.value.fdc_id)
    }

    // 后端返回 message：管理员直写 / 补空自动通过 / 待审核
    const message: string = res?.message || ''
    const isAdmin = !!userStore.user?.is_admin
    const isPending = message.includes('待管理员审核') || /status=pending/.test(message)

    if (isAdmin) {
      snackbar.value = { show: true, message: 'USDA 匹配成功', color: 'success' }
    } else if (isPending) {
      // 普通用户、有数据：提议待审，营养数据未变
      snackbar.value = {
        show: true,
        message: message || '已提交，待管理员审核',
        color: 'info',
      }
    } else {
      // 普通用户补空自动通过
      snackbar.value = {
        show: true,
        message: message || 'USDA 匹配成功（补空自动通过）',
        color: 'success',
      }
    }

    // 数据已落地才刷新营养（管理员直写 / 补空自动通过）；pending 时数据未变，不触发刷新
    if (!isPending) {
      emit('matched')
    }
    emit('update:modelValue', false)
  } finally {
    matching.value = false
  }
}
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    max-width="780"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title>匹配 USDA 食材</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="query"
          label="搜索（空格分词，原文/译文任意命中）"
          prepend-inner-icon="mdi-magnify"
          @update:model-value="onInput"
          @keyup.enter="onSearch"
          clearable
        />
        <v-progress-linear v-if="loading" indeterminate />

        <v-list v-if="results.length && !selected" density="compact">
          <v-list-item v-for="r in results" :key="r.fdc_id" @click="pick(r.fdc_id)">
            <v-list-item-title>{{ r.description_zh || r.description }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ r.description }} · {{ r.data_type }} · {{ r.nutrient_count }} 项营养素
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <div v-if="selected">
          <v-btn variant="text" size="small" @click="selected = null">← 返回列表</v-btn>
          <h3 class="mt-2">{{ selected.description_zh || selected.description }}</h3>
          <p class="text-caption">{{ selected.description }}</p>
          <v-table density="compact" class="mt-2">
            <thead>
              <tr><th>营养素</th><th>值</th><th>单位</th></tr>
            </thead>
            <tbody>
              <tr v-for="n in selected.nutrients" :key="n.name">
                <td>{{ n.name_zh || n.name }}</td>
                <td>{{ n.amount }}</td>
                <td>{{ n.unit_name }}</td>
              </tr>
            </tbody>
          </v-table>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn color="primary" :disabled="!selected" :loading="matching" @click="onConfirmClick">
          确认匹配
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- 二级确认：模态对话框替代浏览器原生 confirm -->
  <v-dialog v-model="confirmDialog" max-width="420" persistent>
    <v-card>
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon color="warning" class="mr-2">mdi-alert-circle-outline</v-icon>
        确认匹配
      </v-card-title>
      <v-card-text>
        将清空当前营养数据并写入所选 USDA 食材的营养数据，此操作不可撤销。是否继续？
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="matching" @click="confirmDialog = false">取消</v-btn>
        <v-btn color="primary" :loading="matching" @click="confirmMatch">确认写入</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- 行内提示：按角色/status 区分（管理员直写 / 补空自动通过 / 待审核） -->
  <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
    {{ snackbar.message }}
  </v-snackbar>
</template>
