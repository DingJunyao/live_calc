<template>
  <div class="filter-bar d-flex flex-wrap ga-2">
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
            <span v-if="getValue(f.key).length > 1" class="text-caption text-medium-emphasis text-no-wrap">
              等{{ getValue(f.key).length }}项
            </span>
          </div>
        </template>
      </v-select>

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
    </template>

    <!-- 有激活的筛选时显示清除按钮 -->
    <v-btn
      v-if="hasActiveFilters"
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
import { computed, reactive } from 'vue'

export interface FilterConfig {
  key: string
  label: string
  type: 'select' | 'date-range'
  items?: { value: any; title: string }[]
  multiple?: boolean
  minWidth?: string
  maxWidth?: string
}

interface DateRangeValue {
  start: string | null
  end: string | null
}

type FilterValue = any[] | DateRangeValue | null

const props = defineProps<{
  filters: FilterConfig[]
  loading?: boolean
}>()

const emit = defineEmits<{
  change: [state: Record<string, any>]
}>()

// 内部状态
const state = reactive<Record<string, FilterValue>>({})

// 选项缓存（保存 items 映射用于 chip 显示）
const optionsMap = new Map<string, { value: any; title: string }[]>()

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
    } else {
      state[key] = []
    }
  }
  return state[key]!
}

// 是否有激活的筛选条件
const hasActiveFilters = computed(() => {
  return Object.entries(state).some(([key, val]) => {
    if (!val) return false
    if (Array.isArray(val)) return val.length > 0
    if (typeof val === 'object') return !!(val as DateRangeValue).start || !!(val as DateRangeValue).end
    return false
  })
})

let timer: ReturnType<typeof setTimeout> | null = null

const emitChange = () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    const payload: Record<string, any> = {}
    for (const [key, val] of Object.entries(state)) {
      if (Array.isArray(val)) {
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

const onDateChange = (key: string, field: 'start' | 'end', val: string) => {
  const current = getValue(key) as DateRangeValue
  current[field] = val || null
  emitChange()
}

// Edge 等浏览器上点击日期输入框触发原生日期选择器
const triggerDatePicker = (e: MouseEvent) => {
  // 点击清除按钮时不触发
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
  emitChange()
}
</script>
