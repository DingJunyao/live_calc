<template>
  <!-- 顶部导航栏 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">单位管理</v-app-bar-title>
    <template #append>
      <v-btn color="primary" variant="tonal" @click="openCreateDialog">
        <v-icon start>mdi-plus</v-icon>
        添加单位
      </v-btn>
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 筛选器 -->
    <v-card class="rounded-lg mb-4">
      <v-card-text class="py-3">
        <v-row dense>
          <v-col cols="12" sm="3">
            <v-select
              v-model="filterSystem"
              :items="unitSystemOptions"
              label="单位体系"
              clearable
              prepend-icon="mdi-filter-outline"
              variant="outlined"
              density="compact"
              hide-details
              @update:model-value="fetchUnits"
            />
          </v-col>
          <v-col cols="12" sm="3">
            <v-select
              v-model="filterType"
              :items="unitTypeOptions"
              label="单位类型"
              clearable
              variant="outlined"
              density="compact"
              hide-details
              @update:model-value="fetchUnits"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model="searchQuery"
              label="搜索单位"
              prepend-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              @update:model-value="onSearchInput"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 主体内容：桌面端左右分列，移动端上下排列 -->
    <v-row v-if="!loading" no-gutters>
      <!-- 左侧/上方：单位列表（2/3） -->
      <v-col cols="12" md="8">
        <template v-for="group in displayedGroups" :key="group.key">
          <v-card class="rounded-lg mb-3">
            <v-card-title
              class="d-flex align-center py-3 cursor-pointer"
              @click="toggleGroup(group.key)"
            >
              <v-icon class="mr-2" :icon="group.icon" :color="group.color" />
              <span class="font-weight-bold">{{ group.label }}</span>
              <v-chip size="x-small" class="ml-2" variant="tonal">
                {{ getFilteredUnitsForSystem(group.key).length }}
              </v-chip>
              <v-spacer />
              <v-icon>
                {{ expandedGroups[group.key] ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
              </v-icon>
            </v-card-title>

            <v-expand-transition>
              <div v-show="expandedGroups[group.key]">
                <v-divider />
                <v-card-text class="pa-2">
                  <v-row dense>
                    <v-col
                      v-for="unit in getFilteredUnitsForSystem(group.key)"
                      :key="unit.id"
                      cols="6"
                      sm="4"
                      lg="3"
                    >
                      <v-card
                        variant="tonal"
                        class="rounded-lg unit-card"
                        :class="{ 'unit-card-selected': selectedUnit?.id === unit.id }"
                        @click="selectUnit(unit)"
                      >
                        <v-card-text class="pa-3 text-center">
                          <div class="text-subtitle-1 font-weight-bold">{{ unit.abbreviation }}</div>
                          <div class="text-caption text-medium-emphasis">{{ unit.name }}</div>
                          <div class="d-flex justify-center align-center mt-1 ga-1">
                            <v-chip v-if="unit.is_common" color="primary" size="x-small" label>
                              常用
                            </v-chip>
                            <v-chip v-if="unit.is_si_base" color="success" size="x-small" label>
                              基准
                            </v-chip>
                            <v-chip
                              v-if="unit.default_estimate != null"
                              size="x-small"
                              label
                              variant="outlined"
                            >
                              ~{{ unit.default_estimate }}{{ getBaseUnitAbbr(unit) }}
                            </v-chip>
                          </div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                    <v-col
                      v-if="getFilteredUnitsForSystem(group.key).length === 0"
                      cols="12"
                      class="text-center text-medium-emphasis py-4 text-body-2"
                    >
                      暂无单位
                    </v-col>
                  </v-row>
                </v-card-text>
              </div>
            </v-expand-transition>
          </v-card>
        </template>

        <div
          v-if="displayedGroups.length === 0"
          class="text-center text-medium-emphasis py-8"
        >
          <v-icon size="48" color="grey">mdi-magnify-close</v-icon>
          <div class="mt-2">没有找到匹配的单位</div>
        </div>
      </v-col>

      <!-- 右侧/下方：换算预览面板（1/3） -->
      <v-col cols="12" md="4" class="pl-md-4 pt-4 pt-md-0">
        <v-card v-if="selectedUnit" class="rounded-lg" sticky>
          <v-card-title class="d-flex align-center py-3">
            <v-icon class="mr-2" color="info">mdi-swap-horizontal</v-icon>
            <span>换算预览</span>
            <v-spacer />
            <v-tooltip location="top">
              <template #activator="{ props }">
                <v-btn v-bind="props" icon="mdi-pencil" size="small" variant="text" color="primary" @click="openEditDialog(selectedUnit!)" />
              </template>
              <span>编辑</span>
            </v-tooltip>
            <v-tooltip location="top">
              <template #activator="{ props }">
                <v-btn v-bind="props" icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDelete(selectedUnit!)" />
              </template>
              <span>删除</span>
            </v-tooltip>
            <v-btn icon="mdi-close" size="small" variant="text" @click="selectedUnit = null" />
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-4 pb-4">
            <div class="text-h6 mb-2">{{ selectedUnit.name }}（{{ selectedUnit.abbreviation }}）</div>
            <div class="mb-3">
              <div class="text-body-2 text-medium-emphasis">SI 因子</div>
              <div class="text-body-1 font-weight-medium">
                {{ selectedUnit.si_factor ?? '未设置' }}
                <span v-if="selectedUnit.is_si_base" class="text-success text-body-2">(基准单位)</span>
              </div>
            </div>
            <div v-if="conversionPreviews.length > 0" class="mb-2">
              <div class="text-body-2 text-medium-emphasis mb-2">同类型换算</div>
              <div class="d-flex flex-wrap ga-2">
                <v-chip
                  v-for="conv in conversionPreviews"
                  :key="conv.unit.id"
                  variant="tonal"
                  size="small"
                >
                  1 {{ selectedUnit.abbreviation }} = {{ conv.factor }} {{ conv.unit.abbreviation }}
                </v-chip>
              </div>
            </div>
            <div v-else class="text-body-2 text-medium-emphasis">
              暂无可计算的换算关系
            </div>
          </v-card-text>
        </v-card>
        <v-card v-else class="rounded-lg">
          <v-card-text class="text-center text-medium-emphasis py-8">
            <v-icon size="40" color="grey-lighten-1">mdi-cursor-default-click</v-icon>
            <div class="mt-2 text-body-2">点击单位查看换算预览</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 加载状态 -->
    <div v-if="loading" class="d-flex justify-center py-8">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <!-- 添加/编辑单位对话框 -->
    <v-dialog v-model="unitDialog" max-width="600px" persistent>
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center py-4">
          <v-icon class="mr-2">
            {{ editingUnit ? 'mdi-pencil' : 'mdi-plus' }}
          </v-icon>
          <span>{{ editingUnit ? '编辑单位' : '添加单位' }}</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-6">
          <v-form ref="formRef" @submit.prevent="saveUnit">
            <v-text-field
              v-model="unitForm.name"
              label="单位名称"
              variant="outlined"
              required
              :rules="[(v: string) => !!v || '请输入单位名称']"
            />
            <v-text-field
              v-model="unitForm.abbreviation"
              label="单位缩写"
              variant="outlined"
              required
              :rules="[(v: string) => !!v || '请输入单位缩写']"
            />
            <v-text-field
              v-model="unitForm.plural_form"
              label="复数形式（可选）"
              variant="outlined"
              hint="例如：pounds"
              persistent-hint
            />
            <v-select
              v-model="unitForm.unit_system"
              :items="unitSystemOptions"
              label="单位体系"
              variant="outlined"
              required
              :rules="[(v: string) => !!v || '请选择单位体系']"
            />
            <v-select
              v-model="unitForm.unit_type"
              :items="unitTypeOptions"
              label="单位类型"
              variant="outlined"
              required
              :disabled="unitForm.unit_system === 'vague'"
              :rules="[(v: string) => !!v || '请选择单位类型']"
            />
            <v-text-field
              v-model.number="unitForm.si_factor"
              label="SI 转换因子"
              type="number"
              variant="outlined"
              hint="转换为国际单位制的因子，基准单位设为 1"
              persistent-hint
            />
            <!-- 模糊量类型的默认估算值 -->
            <v-text-field
              v-if="unitForm.unit_system === 'vague'"
              v-model.number="unitForm.default_estimate"
              label="默认估算值（克）"
              type="number"
              variant="outlined"
              hint="模糊量的默认质量估算值（单位：克）"
              persistent-hint
            />
            <v-row>
              <v-col cols="6">
                <v-switch v-model="unitForm.is_si_base" label="SI 基本单位" color="success" />
              </v-col>
              <v-col cols="6">
                <v-switch v-model="unitForm.is_common" label="常用单位" color="primary" />
              </v-col>
            </v-row>
            <v-text-field
              v-model.number="unitForm.display_order"
              label="显示顺序"
              type="number"
              variant="outlined"
              hint="数值越小越靠前"
              persistent-hint
            />
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="tonal" @click="unitDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveUnit">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card class="rounded-lg">
        <v-card-title class="text-h6">确认删除</v-card-title>
        <v-card-text>
          确定要删除单位 <strong>{{ deleteTarget?.name }}</strong>（{{ deleteTarget?.abbreviation }}）吗？
          此操作不可撤销。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteUnit">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 操作成功提示 -->
    <v-snackbar v-model="showSuccess" color="success" timeout="2000">
      <v-icon start>mdi-check-circle</v-icon>
      {{ successMessage }}
    </v-snackbar>

    <!-- 错误提示 -->
    <v-snackbar v-model="showError" color="error" timeout="3000">
      <v-icon start>mdi-alert-circle</v-icon>
      {{ errorMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { api } from '@/api'
import type { Unit } from '@/types'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => {
  router.back()
}

// ============ 单位体系与类型配置 ============

// 单位体系选项
const unitSystemOptions = [
  { title: '公制', value: 'metric' },
  { title: '市制', value: 'market' },
  { title: '英制', value: 'imperial' },
  { title: '计数', value: 'count' },
  { title: '模糊量', value: 'vague' },
]

// 单位类型选项
const unitTypeOptions = [
  { title: '质量', value: 'mass' },
  { title: '体积', value: 'volume' },
  { title: '长度', value: 'length' },
  { title: '面积', value: 'area' },
  { title: '温度', value: 'temperature' },
  { title: '时间', value: 'time' },
  { title: '计数', value: 'count' },
]

// 分组展示配置
const unitSystemGroups = [
  { key: 'metric', label: '公制', icon: 'mdi-weight-kilogram', color: 'primary' },
  { key: 'market', label: '市制', icon: 'mdi-store', color: 'orange' },
  { key: 'imperial', label: '英制', icon: 'mdi-weight-pound', color: 'indigo' },
  { key: 'count', label: '计数', icon: 'mdi-numeric', color: 'teal' },
  { key: 'vague', label: '模糊量', icon: 'mdi-water-outline', color: 'purple' },
  { key: 'other', label: '未分类', icon: 'mdi-help-circle-outline', color: 'grey' },
]

// ============ 数据状态 ============

const units = ref<Unit[]>([])
const loading = ref(false)
const filterSystem = ref<string | null>(null)
const filterType = ref<string | null>(null)
const searchQuery = ref('')

// 分组展开状态
const expandedGroups = reactive<Record<string, boolean>>({
  metric: true,
  market: true,
  imperial: true,
  count: true,
  vague: true,
  other: true,
})

// 选中的单位（用于换算预览）
const selectedUnit = ref<Unit | null>(null)

// ============ 对话框状态 ============

const unitDialog = ref(false)
const editingUnit = ref<Unit | null>(null)
const saving = ref(false)
const formRef = ref<any>(null)

const unitForm = reactive({
  name: '',
  abbreviation: '',
  plural_form: '',
  unit_system: 'metric' as string,
  unit_type: 'mass' as string,
  si_factor: null as number | null,
  is_si_base: false,
  is_common: false,
  display_order: 0,
  default_estimate: null as number | null,
})

const deleteDialog = ref(false)
const deleting = ref(false)
const deleteTarget = ref<Unit | null>(null)

// 提示消息
const showSuccess = ref(false)
const successMessage = ref('')
const showError = ref(false)
const errorMessage = ref('')

// ============ 计算属性 ============

// 搜索关键词过滤
const searchFilteredUnits = computed(() => {
  if (!searchQuery.value) return units.value
  const query = searchQuery.value.toLowerCase()
  return units.value.filter(
    (u) =>
      u.name.toLowerCase().includes(query) ||
      u.abbreviation.toLowerCase().includes(query) ||
      (u.plural_form && u.plural_form.toLowerCase().includes(query))
  )
})

// 需要展示的分组（只显示有单位的分组）
const displayedGroups = computed(() => {
  if (filterSystem.value) {
    // 如果选了特定体系筛选，只显示该体系
    return unitSystemGroups.filter((g) => g.key === filterSystem.value || g.key === 'other')
  }
  // 没有体系筛选时，显示所有有单位的分组
  return unitSystemGroups.filter((g) => getFilteredUnitsForSystem(g.key).length > 0 || expandedGroups[g.key])
})

// 换算预览数据
const conversionPreviews = computed(() => {
  if (!selectedUnit.value || selectedUnit.value.si_factor == null) return []

  const siFactor = selectedUnit.value.si_factor
  // 找同类型、有 si_factor 且非自身的常用单位
  return units.value
    .filter(
      (u) =>
        u.id !== selectedUnit.value!.id &&
        u.unit_type === selectedUnit.value!.unit_type &&
        u.si_factor != null &&
        u.si_factor !== 0
    )
    .map((u) => ({
      unit: u,
      factor: siFactor !== 0 ? parseFloat((siFactor / u.si_factor!).toFixed(6)) : 0,
    }))
    .filter((c) => c.factor !== 0 && isFinite(c.factor))
    .sort((a, b) => a.factor - b.factor)
    .slice(0, 10)
})

// ============ 方法 ============

// 获取单位所属的体系分组 key
const getSystemGroupKey = (unit: Unit): string => {
  if (unit.unit_system) {
    // 检查是否在已知体系中
    const known = unitSystemGroups.some((g) => g.key === unit.unit_system)
    if (known) return unit.unit_system
  }
  return 'other'
}

// 获取某个体系分组中经过筛选的单位列表
const getFilteredUnitsForSystem = (systemKey: string): Unit[] => {
  let filtered = searchFilteredUnits.value

  // 按体系分组
  if (systemKey === 'other') {
    filtered = filtered.filter(
      (u) => !u.unit_system || !unitSystemGroups.some((g) => g.key === u.unit_system)
    )
  } else {
    filtered = filtered.filter((u) => u.unit_system === systemKey)
  }

  // 按类型筛选
  if (filterType.value) {
    filtered = filtered.filter((u) => u.unit_type === filterType.value)
  }

  // 按 display_order 排序
  return filtered.sort((a, b) => a.display_order - b.display_order)
}

// 获取基准单位缩写（用于显示 vague 类型的默认估算值单位）
const getBaseUnitAbbr = (unit: Unit): string => {
  // vague 类型默认估算值单位为克
  if (unit.unit_system === 'vague') return 'g'
  return ''
}

// 切换分组展开/折叠
const toggleGroup = (key: string) => {
  expandedGroups[key] = !expandedGroups[key]
}

// 选中单位，显示换算预览
const selectUnit = (unit: Unit) => {
  if (selectedUnit.value?.id === unit.id) {
    selectedUnit.value = null
  } else {
    selectedUnit.value = unit
  }
}

// 搜索输入防抖
let searchTimer: ReturnType<typeof setTimeout> | null = null
const onSearchInput = () => {
  // 立即触发计算属性更新即可，无需额外逻辑
}

// ============ API 调用 ============

const fetchUnits = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (filterType.value) params.unit_type = filterType.value
    if (filterSystem.value && filterSystem.value !== 'other') {
      params.unit_system = filterSystem.value
    }

    units.value = await api.get('/units/', { params })
  } catch (error) {
    console.error('获取单位列表失败:', error)
    showError.value = true
    errorMessage.value = '获取单位列表失败'
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editingUnit.value = null
  Object.assign(unitForm, {
    name: '',
    abbreviation: '',
    plural_form: '',
    unit_system: 'metric',
    unit_type: 'mass',
    si_factor: null,
    is_si_base: false,
    is_common: false,
    display_order: 0,
    default_estimate: null,
  })
  unitDialog.value = true
}

const openEditDialog = (unit: Unit) => {
  editingUnit.value = unit
  Object.assign(unitForm, {
    name: unit.name,
    abbreviation: unit.abbreviation,
    plural_form: unit.plural_form || '',
    unit_system: unit.unit_system || 'metric',
    unit_type: unit.unit_type,
    si_factor: unit.si_factor,
    is_si_base: unit.is_si_base,
    is_common: unit.is_common,
    display_order: unit.display_order,
    default_estimate: unit.default_estimate,
  })
  unitDialog.value = true
}

const saveUnit = async () => {
  // 表单验证
  const { valid } = formRef.value ? await formRef.value.validate() : { valid: true }
  if (!valid) return

  saving.value = true
  try {
    // 构建请求数据
    const data: Record<string, any> = {
      name: unitForm.name,
      abbreviation: unitForm.abbreviation,
      unit_type: unitForm.unit_system === 'vague' ? 'mass' : unitForm.unit_type,
      unit_system: unitForm.unit_system,
      si_factor: unitForm.si_factor,
      is_si_base: unitForm.is_si_base,
      is_common: unitForm.is_common,
      display_order: unitForm.display_order,
    }

    // 可选字段
    if (unitForm.plural_form) data.plural_form = unitForm.plural_form
    if (unitForm.unit_system === 'vague' && unitForm.default_estimate != null) {
      data.default_estimate = unitForm.default_estimate
    }

    if (editingUnit.value) {
      await api.put(`/units/${editingUnit.value.id}`, data)
      successMessage.value = '单位更新成功'
    } else {
      await api.post('/units/', data)
      successMessage.value = '单位创建成功'
    }
    unitDialog.value = false
    showSuccess.value = true
    fetchUnits()
  } catch (error: any) {
    console.error('保存单位失败:', error)
    showError.value = true
    errorMessage.value = error.response?.data?.detail || '保存单位失败'
  } finally {
    saving.value = false
  }
}

const confirmDelete = (unit: Unit) => {
  deleteTarget.value = unit
  deleteDialog.value = true
}

const deleteUnit = async () => {
  if (!deleteTarget.value) return

  deleting.value = true
  try {
    await api.delete(`/units/${deleteTarget.value.id}`)
    deleteDialog.value = false
    showSuccess.value = true
    successMessage.value = '单位已删除'
    // 如果删除的是当前选中的单位，清除选择
    if (selectedUnit.value?.id === deleteTarget.value.id) {
      selectedUnit.value = null
    }
    fetchUnits()
  } catch (error: any) {
    console.error('删除单位失败:', error)
    showError.value = true
    errorMessage.value = error.response?.data?.detail || '删除单位失败'
  } finally {
    deleting.value = false
  }
}

// ============ 监听器 ============

// 当 unit_system 变为 vague 时，自动设置 unit_type 为 mass
watch(
  () => unitForm.unit_system,
  (newVal) => {
    if (newVal === 'vague') {
      unitForm.unit_type = 'mass'
    }
  }
)

// ============ 初始化 ============

onMounted(() => {
  fetchUnits()
})
</script>

<style scoped>
.unit-card {
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
}

.unit-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.unit-card-selected {
  border: 2px solid rgb(var(--v-theme-primary));
}
</style>
