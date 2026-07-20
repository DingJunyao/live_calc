<template>
  <!-- ============ 移动端：筛选按钮 + 模态框 ============ -->
  <template v-if="mobile">
    <v-btn
      :variant="hasActiveFilters ? 'tonal' : 'outlined'"
      :color="hasActiveFilters ? 'primary' : undefined"
      density="compact"
      class="filter-toggle-btn"
      @click="dialogOpen = true"
    >
      <v-icon size="20" :color="hasActiveFilters ? 'primary' : 'default'">mdi-filter-variant</v-icon>
      <span v-if="hasActiveFilters" class="ml-1 text-caption font-weight-bold text-primary">{{ activeFilterCount }}</span>
    </v-btn>

    <v-dialog v-model="dialogOpen" max-width="480">
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>筛选条件</span>
          <v-spacer />
          <v-btn
            v-if="hasActiveFilters"
            variant="text"
            size="small"
            color="medium-emphasis"
            @click="clearAll"
          >
            <v-icon start size="small">mdi-close</v-icon>
            清除
          </v-btn>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <div class="d-flex flex-column ga-3">
            <template v-for="f in filters" :key="f.key">
              <!-- 多选下拉 -->
              <v-select
                v-if="f.type === 'select'"
                :model-value="getValue(f.key)"
                :items="f.items || []"
                :label="f.label"
                :multiple="f.multiple !== false"
                variant="outlined"
                density="compact"
                hide-details
                clearable
                @update:model-value="onSelectChange(f.key, $event)"
              >
                <template #selection="{ item, index }">
                  <v-chip v-if="index < 3" size="small" closable @click:close="onRemoveChip(f.key, item.value)">
                    <span class="text-truncate" style="max-width: 100px">{{ item.title }}</span>
                  </v-chip>
                  <v-tooltip v-if="index === 3" location="top" open-on-click>
                    <template #activator="{ props: tp }">
                      <span v-bind="tp" class="text-caption text-medium-emphasis ml-1" style="cursor: pointer">
                        +{{ getValue(f.key).length - 3 }}
                      </span>
                    </template>
                    <div class="d-flex flex-column ga-1" style="max-width: 260px; max-height: 240px; overflow-y: auto">
                      <div v-for="(title, i) in getSelectedTitles(f.key)" :key="i" class="text-caption text-no-wrap">{{ title }}</div>
                    </div>
                  </v-tooltip>
                </template>
              </v-select>

              <!-- 搜索型多选下拉 -->
              <v-autocomplete
                v-if="f.type === 'autocomplete'"
                v-model:search="autocompleteSearchTexts[f.key]"
                :model-value="getValue(f.key)"
                :items="f.items || []"
                :label="f.label"
                :loading="f.loading"
                multiple
                variant="outlined"
                density="compact"
                hide-details
                clearable
                @update:model-value="onAutocompleteSelect(f.key, $event)"
              >
                <template #selection="{ item, index }">
                  <v-chip v-if="index < 3" size="small" closable @click:close="onRemoveChip(f.key, item.value)">
                    <span class="text-truncate" style="max-width: 100px">{{ item.title }}</span>
                  </v-chip>
                  <v-tooltip v-if="index === 3" location="top" open-on-click>
                    <template #activator="{ props: tp }">
                      <span v-bind="tp" class="text-caption text-medium-emphasis ml-1" style="cursor: pointer">
                        +{{ getValue(f.key).length - 3 }}
                      </span>
                    </template>
                    <div class="d-flex flex-column ga-1" style="max-width: 260px; max-height: 240px; overflow-y: auto">
                      <div v-for="(title, i) in getSelectedTitles(f.key)" :key="i" class="text-caption text-no-wrap">{{ title }}</div>
                    </div>
                  </v-tooltip>
                </template>
              </v-autocomplete>

              <!-- 日期范围 -->
              <div v-if="f.type === 'date-range'">
                <div class="text-caption text-medium-emphasis mb-1">{{ f.label }}</div>
                <div class="d-flex align-center ga-2">
                  <v-text-field
                    :model-value="getValue(f.key)?.start || ''"
                    type="date"
                    label="开始"
                    variant="outlined"
                    density="compact"
                    hide-details
                    clearable
                    prepend-inner-icon="mdi-calendar"
                    class="flex-grow-1"
                    @update:model-value="onDateChange(f.key, 'start', $event)"
                    @click="triggerDatePicker"
                  />
                  <span class="text-medium-emphasis">~</span>
                  <v-text-field
                    :model-value="getValue(f.key)?.end || ''"
                    type="date"
                    label="结束"
                    variant="outlined"
                    density="compact"
                    hide-details
                    clearable
                    prepend-inner-icon="mdi-calendar"
                    class="flex-grow-1"
                    @update:model-value="onDateChange(f.key, 'end', $event)"
                    @click="triggerDatePicker"
                  />
                </div>
              </div>

              <!-- 开关 -->
              <v-switch
                v-if="f.type === 'toggle'"
                :model-value="getValue(f.key) === true"
                :label="f.label"
                color="primary"
                density="compact"
                hide-details
                @update:model-value="onToggleChange(f.key, $event)"
              />

              <!-- 多选下拉（静态选项） -->
              <v-select
                v-if="f.type === 'multicheck'"
                :model-value="getValue(f.key)"
                :items="f.items || []"
                :label="f.label"
                multiple
                variant="outlined"
                density="compact"
                hide-details
                clearable
                @update:model-value="onSelectChange(f.key, $event)"
              >
                <template #selection="{ item, index }">
                  <v-chip v-if="index < 3" size="small" closable @click:close="onRemoveChip(f.key, item.value)">
                    <span class="text-truncate" style="max-width: 100px">{{ item.title }}</span>
                  </v-chip>
                  <v-tooltip v-if="index === 3" location="top" open-on-click>
                    <template #activator="{ props: tp }">
                      <span v-bind="tp" class="text-caption text-medium-emphasis ml-1" style="cursor: pointer">
                        +{{ getValue(f.key).length - 3 }}
                      </span>
                    </template>
                    <div class="d-flex flex-column ga-1" style="max-width: 260px; max-height: 240px; overflow-y: auto">
                      <div v-for="(title, i) in getSelectedTitles(f.key)" :key="i" class="text-caption text-no-wrap">{{ title }}</div>
                    </div>
                  </v-tooltip>
                </template>
              </v-select>
            </template>
          </div>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialogOpen = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </template>

  <!-- ============ 桌面端：内联筛选器 ============ -->
  <div v-else class="d-flex flex-wrap ga-2">
    <template v-for="f in filters" :key="f.key">
      <!-- 多选下拉 -->
      <v-select
        v-if="f.type === 'select'"
        :model-value="getValue(f.key)"
        :items="f.items || []"
        :label="f.label"
        :multiple="f.multiple !== false"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        :style="{ minWidth: f.minWidth || '180px', maxWidth: f.maxWidth || '280px' }"
        @update:model-value="onSelectChange(f.key, $event)"
      >
        <template #selection="{ item, index }">
          <div v-if="index === 0" class="d-inline-flex align-center ga-1" style="min-width: 0;">
            <v-chip size="small" closable @click:close="onRemoveChip(f.key, item.value)">
              <span class="text-truncate" style="max-width: 80px">{{ item.title }}</span>
            </v-chip>
            <v-tooltip v-if="getValue(f.key).length > 1" location="bottom" :open-on-click="mobile">
              <template #activator="{ props: tp }">
                <span v-bind="tp" class="text-caption text-medium-emphasis text-no-wrap" style="cursor: default">
                  等{{ getValue(f.key).length }}项
                </span>
              </template>
              <div class="d-flex flex-column ga-1" style="max-width: 260px; max-height: 240px; overflow-y: auto">
                <div v-for="(title, i) in getSelectedTitles(f.key)" :key="i" class="text-caption text-no-wrap">{{ title }}</div>
              </div>
            </v-tooltip>
          </div>
        </template>
      </v-select>

      <!-- 搜索型多选下拉 -->
      <v-autocomplete
        v-if="f.type === 'autocomplete'"
        v-model:search="autocompleteSearchTexts[f.key]"
        :model-value="getValue(f.key)"
        :items="f.items || []"
        :label="f.label"
        :loading="f.loading"
        multiple
        variant="outlined"
        density="compact"
        hide-details
        clearable
        :style="{ minWidth: f.minWidth || '180px', maxWidth: f.maxWidth || '280px' }"
        @update:model-value="onAutocompleteSelect(f.key, $event)"
      >
        <template #selection="{ item, index }">
          <div v-if="index === 0" class="d-inline-flex align-center ga-1" style="min-width: 0;">
            <v-chip size="small" closable @click:close="onRemoveChip(f.key, item.value)">
              <span class="text-truncate" style="max-width: 80px">{{ item.title }}</span>
            </v-chip>
            <v-tooltip v-if="getValue(f.key).length > 1" location="bottom" :open-on-click="mobile">
              <template #activator="{ props: tp }">
                <span v-bind="tp" class="text-caption text-medium-emphasis text-no-wrap" style="cursor: default">
                  等{{ getValue(f.key).length }}项
                </span>
              </template>
              <div class="d-flex flex-column ga-1" style="max-width: 260px; max-height: 240px; overflow-y: auto">
                <div v-for="(title, i) in getSelectedTitles(f.key)" :key="i" class="text-caption text-no-wrap">{{ title }}</div>
              </div>
            </v-tooltip>
          </div>
        </template>
      </v-autocomplete>

      <!-- 日期范围 -->
      <div v-if="f.type === 'date-range'" class="d-flex align-center ga-1" :style="{ minWidth: f.minWidth || '340px' }">
        <span class="text-caption text-medium-emphasis mr-1">{{ f.label }}</span>
        <v-text-field
          :model-value="getValue(f.key)?.start || ''"
          type="date"
          label="开始"
          variant="outlined"
          density="compact"
          hide-details
          clearable
          prepend-inner-icon="mdi-calendar"
          style="max-width: 155px"
          @update:model-value="onDateChange(f.key, 'start', $event)"
          @click="triggerDatePicker"
        />
        <span class="text-caption text-medium-emphasis">~</span>
        <v-text-field
          :model-value="getValue(f.key)?.end || ''"
          type="date"
          label="结束"
          variant="outlined"
          density="compact"
          hide-details
          clearable
          prepend-inner-icon="mdi-calendar"
          style="max-width: 155px"
          @update:model-value="onDateChange(f.key, 'end', $event)"
          @click="triggerDatePicker"
        />
      </div>

      <!-- 开关 -->
      <v-switch
        v-if="f.type === 'toggle'"
        :model-value="getValue(f.key) === true"
        :label="f.label"
        color="primary"
        density="compact"
        hide-details
        :style="{ minWidth: f.minWidth || '160px' }"
        @update:model-value="onToggleChange(f.key, $event)"
      />

      <!-- 多选下拉（静态选项） -->
      <v-select
        v-if="f.type === 'multicheck'"
        :model-value="getValue(f.key)"
        :items="f.items || []"
        :label="f.label"
        multiple
        variant="outlined"
        density="compact"
        hide-details
        clearable
        :style="{ minWidth: f.minWidth || '180px', maxWidth: f.maxWidth || '280px' }"
        @update:model-value="onSelectChange(f.key, $event)"
      >
        <template #selection="{ item, index }">
          <div v-if="index === 0" class="d-inline-flex align-center ga-1" style="min-width: 0;">
            <v-chip size="small" closable @click:close="onRemoveChip(f.key, item.value)">
              <span class="text-truncate" style="max-width: 80px">{{ item.title }}</span>
            </v-chip>
            <v-tooltip v-if="getValue(f.key).length > 1" location="bottom" :open-on-click="mobile">
              <template #activator="{ props: tp }">
                <span v-bind="tp" class="text-caption text-medium-emphasis text-no-wrap" style="cursor: default">
                  等{{ getValue(f.key).length }}项
                </span>
              </template>
              <div class="d-flex flex-column ga-1" style="max-width: 260px; max-height: 240px; overflow-y: auto">
                <div v-for="(title, i) in getSelectedTitles(f.key)" :key="i" class="text-caption text-no-wrap">{{ title }}</div>
              </div>
            </v-tooltip>
          </div>
        </template>
      </v-select>
    </template>

    <!-- 有激活的筛选时显示清除按钮（可通过 hideClearButton 关闭，如商家列表桌面端） -->
    <v-btn
      v-if="hasActiveFilters && !hideClearButton"
      variant="text"
      density="compact"
      color="medium-emphasis"
      size="small"
      class="mt-1"
      @click="clearAll"
    >
      <v-icon start size="small">mdi-close</v-icon>
      清除筛选
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

export interface FilterConfig {
  key: string
  label: string
  type: 'select' | 'autocomplete' | 'date-range' | 'toggle' | 'multicheck'
  items?: { value: any; title: string }[]
  multiple?: boolean
  loading?: boolean
  minWidth?: string
  maxWidth?: string
  /** 初始值：仅 toggle 和 select/autocomplete 类型有效 */
  defaultValue?: any
}

interface DateRangeValue {
  start: string | null
  end: string | null
}

type FilterValue = any[] | DateRangeValue | boolean | null

const props = defineProps<{
  filters: FilterConfig[]
  mobile?: boolean
  loading?: boolean
  /** 隐藏桌面 inline 模式的「清除筛选」按钮（移动端 modal 内的清除按钮不受影响） */
  hideClearButton?: boolean
}>()

const emit = defineEmits<{
  change: [state: Record<string, any>]
}>()

// 移动端对话框
const dialogOpen = ref(false)

// 内部状态
const state = reactive<Record<string, FilterValue>>({})

// autocomplete 搜索文本（v-model:search 绑定）
const autocompleteSearchTexts = reactive<Record<string, string>>({})

// 选项缓存（保存 items 映射用于 chip 显示）
const optionsMap = new Map<string, { value: any; title: string }[]>()

// 获取指定筛选器已选中项的名称列表
const getSelectedTitles = (key: string): string[] => {
  const val = getValue(key)
  if (!Array.isArray(val) || val.length === 0) return []
  const filter = props.filters.find(f => f.key === key)
  const items = filter?.items || []
  return val.map(v => {
    const item = items.find((i: any) => i.value === v)
    return item?.title || String(v)
  })
}

// 初始化或更新选项缓存
const initOptionsMap = () => {
  for (const f of props.filters) {
    if (f.type === 'select' && f.items) {
      optionsMap.set(f.key, f.items)
    }
  }
}

initOptionsMap()

// 按 key 获取值，惰性初始化
const getValue = (key: string): FilterValue => {
  if (!(key in state)) {
    const cfg = props.filters.find(f => f.key === key)
    if (cfg?.type === 'date-range') {
      state[key] = { start: null, end: null } as DateRangeValue
    } else if (cfg?.type === 'toggle') {
      state[key] = cfg?.defaultValue ?? false
    } else {
      state[key] = cfg?.defaultValue ?? []
    }
  }
  return state[key]!
}

// 是否有激活的筛选条件
const hasActiveFilters = computed(() => {
  return Object.entries(state).some(([key, val]) => {
    if (!val && typeof val !== 'boolean') return false
    if (typeof val === 'boolean') return val === true
    if (Array.isArray(val)) return val.length > 0
    if (typeof val === 'object') return !!(val as DateRangeValue).start || !!(val as DateRangeValue).end
    return false
  })
})

// 激活的筛选项数量（用于按钮 badge）
const activeFilterCount = computed(() => {
  let count = 0
  for (const [, val] of Object.entries(state)) {
    if (!val && typeof val !== 'boolean') continue
    if (typeof val === 'boolean' && val) count++
    else if (Array.isArray(val) && val.length > 0) count++
    else if (typeof val === 'object') {
      const dr = val as DateRangeValue
      if (dr.start || dr.end) count++
    }
  }
  return count
})

let timer: ReturnType<typeof setTimeout> | null = null

const emitChange = () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    const payload: Record<string, any> = {}
    for (const [key, val] of Object.entries(state)) {
      if (Array.isArray(val)) {
        payload[key] = val
      } else if (typeof val === 'boolean') {
        payload[key] = val
      } else if (val && typeof val === 'object') {
        const dr = val as DateRangeValue
        if (dr.start) payload[`${key}_start`] = dr.start
        if (dr.end) payload[`${key}_end`] = dr.end
      }
    }
    emit('change', payload)
  }, 300)
}

const onSelectChange = (key: string, val: any) => {
  state[key] = val ?? []
  emitChange()
}

const onRemoveChip = (key: string, value: any) => {
  const current = getValue(key)
  if (Array.isArray(current)) {
    state[key] = current.filter(v => v !== value)
    emitChange()
  }
}

// autocomplete 选中回调：更新状态并清除搜索文本
const onAutocompleteSelect = (key: string, val: any) => {
  state[key] = val ?? []
  autocompleteSearchTexts[key] = ''
  emitChange()
}

const onDateChange = (key: string, field: 'start' | 'end', val: string) => {
  const current = getValue(key) as DateRangeValue
  current[field] = val || null
  emitChange()
}

const onToggleChange = (key: string, val: boolean) => {
  state[key] = val
  emitChange()
}

// Edge 等浏览器上点击日期输入框触发原生日期选择器
const triggerDatePicker = (e: MouseEvent) => {
  if ((e.target as HTMLElement)?.closest('.v-input__append')) return
  const el = (e.currentTarget as HTMLElement)?.querySelector('input[type="date"]')
  if (el && typeof (el as any).showPicker === 'function') {
    (el as any).showPicker()
  }
}

const clearAll = () => {
  for (const key of Object.keys(state)) {
    delete state[key]
  }
  for (const key of Object.keys(autocompleteSearchTexts)) {
    delete autocompleteSearchTexts[key]
  }
  emitChange()
}
</script>

<style scoped>
.filter-toggle-btn {
  min-height: 40px;
  border-radius: 4px;
  border-color: rgba(var(--v-theme-on-surface), 0.24) !important;
}
.filter-toggle-btn:hover {
  border-color: rgba(var(--v-theme-on-surface), 0.6) !important;
}
</style>
