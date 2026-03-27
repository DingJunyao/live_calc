<template>
  <v-container class="pa-4">
    <!-- 顶部标题栏 -->
    <v-app-bar elevation="0" color="background" density="comfortable" class="mb-4">
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

    <!-- 筛选器 -->
    <v-card class="rounded-lg mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="4">
            <v-select
              v-model="filterType"
              :items="unitTypes"
              label="单位类型"
              clearable
              prepend-icon="mdi-filter"
              variant="outlined"
              density="compact"
              hide-details
              @update:model-value="fetchUnits"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-switch
              v-model="filterCommon"
              label="仅显示常用单位"
              color="primary"
              hide-details
              @update:model-value="fetchUnits"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 单位列表 -->
    <v-card class="rounded-lg">
      <v-data-table
        :headers="headers"
        :items="units"
        :loading="loading"
        item-value="id"
        class="rounded-lg"
        group-by="unit_type"
      >
        <!-- 名称列 -->
        <template #item.name="{ item }">
          <div class="d-flex align-center">
            <div>
              <div class="font-weight-bold">{{ item.name }}</div>
              <div class="text-caption text-medium-emphasis">{{ item.abbreviation }}</div>
            </div>
            <v-chip v-if="item.is_common" color="primary" size="x-small" class="ml-2">
              常用
            </v-chip>
            <v-chip v-if="item.is_si_base" color="success" size="x-small" class="ml-2">
              SI基本
            </v-chip>
          </div>
        </template>

        <!-- 类型列 -->
        <template #item.unit_type="{ item }">
          <v-chip size="small" variant="tonal">
            {{ getUnitTypeLabel(item.unit_type) }}
          </v-chip>
        </template>

        <!-- 操作列 -->
        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            color="primary"
            @click="openEditDialog(item)"
          >
            <v-icon>mdi-pencil</v-icon>
            <v-tooltip activator="parent" location="top">编辑</v-tooltip>
          </v-btn>
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            @click="confirmDelete(item)"
          >
            <v-icon>mdi-delete</v-icon>
            <v-tooltip activator="parent" location="top">删除</v-tooltip>
          </v-btn>
          <v-btn
            icon="mdi-swap-horizontal"
            size="small"
            variant="text"
            color="info"
            @click="openConversionsDialog(item)"
          >
            <v-icon>mdi-swap-horizontal</v-icon>
            <v-tooltip activator="parent" location="top">换算关系</v-tooltip>
          </v-btn>
        </template>

        <!-- 分组标题 -->
        <template #group-header="{ item, columns, toggleGroup }">
          <tr class="bg-background">
            <td :colspan="columns.length">
              <v-btn
                icon="mdi-chevron-down"
                size="small"
                variant="text"
                @click="toggleGroup"
              />
              <span class="font-weight-bold ml-2">{{ getUnitTypeLabel(item.value) }}</span>
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-card>

    <!-- 创建/编辑单位对话框 -->
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
          <v-form ref="form" @submit.prevent="saveUnit">
            <v-text-field
              v-model="unitForm.name"
              label="单位名称"
              variant="outlined"
              required
              :rules="[(v) => !!v || '请输入单位名称']"
            />
            <v-text-field
              v-model="unitForm.abbreviation"
              label="单位缩写"
              variant="outlined"
              required
              :rules="[(v) => !!v || '请输入单位缩写']"
            />
            <v-text-field
              v-model="unitForm.plural_form"
              label="复数形式（可选）"
              variant="outlined"
              hint="例如：克 的复数形式"
            />
            <v-select
              v-model="unitForm.unit_type"
              :items="unitTypes"
              label="单位类型"
              variant="outlined"
              required
            />
            <v-text-field
              v-model.number="unitForm.si_factor"
              label="SI转换因子"
              type="number"
              variant="outlined"
              hint="转换为国际单位制的因子"
            />
            <v-row>
              <v-col cols="6">
                <v-switch v-model="unitForm.is_si_base" label="SI基本单位" />
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
          确定要删除单位 <strong>{{ deleteTarget?.name }}</strong> 吗？此操作不可撤销。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="tonal" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteUnit">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 换算关系对话框 -->
    <v-dialog v-model="conversionsDialog" max-width="800px">
      <v-card class="rounded-lg">
        <v-card-title class="d-flex align-center justify-space-between py-4">
          <div class="d-flex align-center">
            <v-icon class="mr-2">mdi-swap-horizontal</v-icon>
            <span>{{ selectedUnit?.name }} 的换算关系</span>
          </div>
          <v-btn icon="mdi-close" variant="text" @click="conversionsDialog = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <div class="d-flex align-center mb-4">
            <v-spacer />
            <v-btn size="small" variant="tonal" @click="openAddConversionDialog">
              <v-icon start>mdi-plus</v-icon>
              添加换算关系
            </v-btn>
          </div>
          <v-list>
            <v-list-item v-for="conv in conversions" :key="conv.id">
              <template #prepend>
                <v-chip size="small">{{ conv.from_unit.abbreviation }}</v-chip>
              </template>
              <v-list-item-title class="text-center">
                <v-icon>mdi-arrow-right</v-icon>
                {{ conv.conversion_factor }}
                <v-icon>mdi-arrow-right</v-icon>
              </v-list-item-title>
              <template #append>
                <v-chip size="small">{{ conv.to_unit.abbreviation }}</v-chip>
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  color="error"
                  class="ml-2"
                  @click="deleteConversion(conv.id)"
                />
              </template>
            </v-list-item>
            <v-list-item v-if="conversions.length === 0">
              <v-list-item-title class="text-center text-medium-emphasis">
                暂无换算关系
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import api from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => {
  router.back()
}

interface Unit {
  id: number
  name: string
  abbreviation: string
  plural_form: string | null
  unit_type: string
  si_factor: number
  is_si_base: boolean
  is_common: boolean
  display_order: number
}

interface UnitConversion {
  id: number
  from_unit_id: number
  to_unit_id: number
  conversion_factor: number
  formula: string | null
  is_bidirectional: boolean
  precision: number
  from_unit: Unit
  to_unit: Unit
}

const headers = [
  { title: '单位名称', key: 'name', sortable: false },
  { title: '类型', key: 'unit_type', sortable: false },
  { title: 'SI因子', key: 'si_factor', sortable: false },
  { title: '显示顺序', key: 'display_order', sortable: false },
  { title: '操作', key: 'actions', sortable: false, align: 'end' },
]

const unitTypes = [
  { title: '质量', value: 'mass' },
  { title: '体积', value: 'volume' },
  { title: '长度', value: 'length' },
  { title: '计数', value: 'count' },
  { title: '面积', value: 'area' },
  { title: '温度', value: 'temperature' },
  { title: '时间', value: 'time' },
]

const units = ref<Unit[]>([])
const loading = ref(false)
const filterType = ref<string | null>(null)
const filterCommon = ref(false)

const unitDialog = ref(false)
const editingUnit = ref<Unit | null>(null)
const saving = ref(false)
const unitForm = reactive({
  name: '',
  abbreviation: '',
  plural_form: '',
  unit_type: 'mass',
  si_factor: 1.0,
  is_si_base: false,
  is_common: false,
  display_order: 0,
})

const deleteDialog = ref(false)
const deleting = ref(false)
const deleteTarget = ref<Unit | null>(null)

const conversionsDialog = ref(false)
const selectedUnit = ref<Unit | null>(null)
const conversions = ref<UnitConversion[]>([])

const fetchUnits = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (filterType.value) params.unit_type = filterType.value
    if (filterCommon.value) params.is_common = true

    units.value = await api.get('/units/', { params })
  } catch (error) {
    console.error('获取单位列表失败:', error)
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
    unit_type: 'mass',
    si_factor: 1.0,
    is_si_base: false,
    is_common: false,
    display_order: 0,
  })
  unitDialog.value = true
}

const openEditDialog = (unit: Unit) => {
  editingUnit.value = unit
  Object.assign(unitForm, unit)
  unitDialog.value = true
}

const saveUnit = async () => {
  saving.value = true
  try {
    if (editingUnit.value) {
      await api.put(`/units/${editingUnit.value.id}`, unitForm)
    } else {
      await api.post('/units/', unitForm)
    }
    unitDialog.value = false
    fetchUnits()
  } catch (error) {
    console.error('保存单位失败:', error)
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
    fetchUnits()
  } catch (error) {
    console.error('删除单位失败:', error)
  } finally {
    deleting.value = false
  }
}

const openConversionsDialog = async (unit: Unit) => {
  selectedUnit.value = unit
  conversionsDialog.value = true
  try {
    conversions.value = await api.get(`/units/${unit.id}/conversions`)
  } catch (error) {
    console.error('获取换算关系失败:', error)
  }
}

const openAddConversionDialog = () => {
  // TODO: 实现添加换算关系的对话框
  alert('添加换算关系功能待实现')
}

const deleteConversion = async (conversionId: number) => {
  try {
    await api.delete(`/units/conversions/${conversionId}`)
    if (selectedUnit.value) {
      openConversionsDialog(selectedUnit.value)
    }
  } catch (error) {
    console.error('删除换算关系失败:', error)
  }
}

const getUnitTypeLabel = (type: string) => {
  const item = unitTypes.find((t) => t.value === type)
  return item?.title || type
}

onMounted(() => {
  fetchUnits()
})
</script>
