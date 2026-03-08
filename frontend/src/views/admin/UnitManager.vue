<template>
  <PageHeader title="单位管理" :show-back="true" />

  <div class="unit-manager">

    <div class="manager-container">
      <!-- 统计信息 -->
      <div class="stats-section">
        <div class="stat-card">
          <span class="stat-label">单位总数</span>
          <span class="stat-number">{{ units.length }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">换算关系数</span>
          <span class="stat-number">{{ totalConversions }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">质量单位</span>
          <span class="stat-number">{{ getCountByType('mass') }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">体积单位</span>
          <span class="stat-number">{{ getCountByType('volume') }}</span>
        </div>
      </div>

      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <select v-model="filterType" @change="loadUnits" class="filter-select">
            <option value="">全部单位</option>
            <option value="mass">质量单位</option>
            <option value="volume">体积单位</option>
            <option value="length">长度单位</option>
            <option value="count">计数单位</option>
          </select>
          <input
            v-model="searchQuery"
            @input="loadUnits"
            placeholder="搜索单位..."
            class="search-input"
          />
        </div>
        <div class="toolbar-right">
          <button @click="showCreateDialog = true" class="btn-primary">
            + 新增单位
          </button>
        </div>
      </div>

      <!-- 单位列表 -->
      <div class="units-table">
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>缩写</th>
              <th>类型</th>
              <th>SI因子</th>
              <th>常用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="unit in filteredUnits" :key="unit.id">
              <td>{{ unit.name }}</td>
              <td>{{ unit.abbreviation }}</td>
              <td>{{ unit.unit_type }}</td>
              <td>{{ unit.si_factor }}</td>
              <td>
                <span :class="{ 'badge-yes': unit.is_common, 'badge-no': !unit.is_common }">
                  {{ unit.is_common ? '是' : '否' }}
                </span>
              </td>
              <td>
                <button @click="editUnit(unit)" class="btn-small">编辑</button>
                <button @click="showConversions(unit)" class="btn-small">换算</button>
                <button @click="deleteUnit(unit)" class="btn-small btn-danger">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <Pagination
        v-if="total > 0"
        :current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        @change-page="handlePageChange"
        @change-page-size="handlePageSizeChange"
      />
    </div>

    <!-- 创建/编辑单位对话框 -->
    <div v-if="showCreateDialog || showEditDialog" class="modal-overlay" @click="closeDialog">
      <div class="modal-content" @click.stop>
        <h3>{{ showCreateDialog ? '新增单位' : '编辑单位' }}</h3>
        <form @submit.prevent="saveUnit">
          <div class="form-group">
            <label>单位名称 *</label>
            <input v-model="unitForm.name" type="text" required />
          </div>
          <div class="form-group">
            <label>单位缩写 *</label>
            <input v-model="unitForm.abbreviation" type="text" required />
          </div>
          <div class="form-group">
            <label>复数形式</label>
            <input v-model="unitForm.plural_form" type="text" />
          </div>
          <div class="form-group">
            <label>单位类型 *</label>
            <select v-model="unitForm.unit_type" required>
              <option value="mass">质量</option>
              <option value="volume">体积</option>
              <option value="length">长度</option>
              <option value="count">计数</option>
              <option value="time">时间</option>
            </select>
          </div>
          <div class="form-group">
            <label>SI因子</label>
            <input v-model="unitForm.si_factor" type="number" step="any" />
          </div>
          <div class="form-group">
            <label>显示顺序</label>
            <input v-model="unitForm.display_order" type="number" />
          </div>
          <div class="form-group checkbox">
            <input v-model="unitForm.is_common" type="checkbox" id="is-common" />
            <label for="is-common">常用单位</label>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeDialog" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 换算关系对话框 -->
    <div v-if="showConversionsDialog" class="modal-overlay" @click="closeConversionsDialog">
      <div class="modal-content modal-large" @click.stop>
        <h3>换算关系 - {{ selectedUnit?.name }}</h3>
        <div class="conversions-toolbar">
          <button @click="showAddConversionDialog = true" class="btn-primary">
            + 新增换算关系
          </button>
        </div>
        <div class="conversions-table">
          <table>
            <thead>
              <tr>
                <th>从</th>
                <th>到</th>
                <th>转换因子</th>
                <th>双向</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="conv in conversions" :key="conv.id">
                <td>{{ conv.from_unit?.name }}</td>
                <td>{{ conv.to_unit?.name }}</td>
                <td>{{ conv.conversion_factor }}</td>
                <td>{{ conv.is_bidirectional ? '是' : '否' }}</td>
                <td>
                  <button @click="deleteConversion(conv)" class="btn-small btn-danger">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="form-actions">
          <button @click="closeConversionsDialog" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>

    <!-- 新增换算关系对话框 -->
    <div v-if="showAddConversionDialog" class="modal-overlay" @click="showAddConversionDialog = false">
      <div class="modal-content" @click.stop>
        <h3>新增换算关系</h3>
        <form @submit.prevent="saveConversion">
          <div class="form-group">
            <label>源单位 *</label>
            <select v-model="conversionForm.from_unit_id" required>
              <option v-for="unit in units" :key="unit.id" :value="unit.id">
                {{ unit.name }} ({{ unit.abbreviation }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>目标单位 *</label>
            <select v-model="conversionForm.to_unit_id" required>
              <option v-for="unit in units" :key="unit.id" :value="unit.id">
                {{ unit.name }} ({{ unit.abbreviation }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>转换因子 *</label>
            <input v-model="conversionForm.conversion_factor" type="number" step="any" required />
          </div>
          <div class="form-group checkbox">
            <input v-model="conversionForm.is_bidirectional" type="checkbox" id="is-bidirectional" />
            <label for="is-bidirectional">双向转换（自动创建反向关系）</label>
          </div>
          <div class="form-actions">
            <button type="button" @click="showAddConversionDialog = false" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

const router = useRouter()

// 数据
const units = ref<any[]>([])
const conversions = ref<any[]>([])
const selectedUnit = ref<any>(null)

// 过滤和搜索
const filterType = ref('')
const searchQuery = ref('')

// 对话框状态
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showConversionsDialog = ref(false)
const showAddConversionDialog = ref(false)

// 表单数据
const unitForm = ref({
  name: '',
  abbreviation: '',
  plural_form: '',
  unit_type: 'count',
  si_factor: 1.0,
  is_common: false,
  display_order: 0
})

const conversionForm = ref({
  from_unit_id: 0,
  to_unit_id: 0,
  conversion_factor: 1.0,
  is_bidirectional: true
})

// 编辑中的单位ID
const editingUnitId = ref<number | null>(null)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 计算属性
const filteredUnits = computed(() => {
  let result = units.value

  // 按类型过滤
  if (filterType.value) {
    result = result.filter((u) => u.unit_type === filterType.value)
  }

  // 按搜索词过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (u) =>
        u.name.toLowerCase().includes(query) ||
        u.abbreviation.toLowerCase().includes(query)
    )
  }

  return result
})

const totalConversions = computed(() => {
  return conversions.value.length
})

onMounted(async () => {
  await loadUnits()
  await loadConversions()
})

async function loadUnits() {
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const url = `/units/?skip=${skip}&limit=${pageSize.value}`
    const response = await api.get<any>(url)

    // 解析分页响应
    if (response.items && response.total !== undefined) {
      // 新的 PaginatedResponse 格式
      units.value = response.items
      total.value = response.total
    } else if (Array.isArray(response)) {
      // 旧的 List 格式
      units.value = response
      // 如果是第一页，用当前数据量作为 total
      if (currentPage.value === 1) {
        total.value = units.value.length
      }
    }
  } catch (error) {
    console.error('Failed to load units:', error)
    alert('加载单位列表失败')
  }
}

async function loadConversions() {
  if (!selectedUnit.value) {
    return
  }

  try {
    const response = await api.get<any>(`/units/${selectedUnit.value.id}/conversions`)
    conversions.value = response || []
  } catch (error) {
    console.error('Failed to load conversions:', error)
    alert('加载换算关系失败')
  }
}

function getCountByType(type: string): number {
  return units.value.filter((u) => u.unit_type === type).length
}

function editUnit(unit: any) {
  editingUnitId.value = unit.id
  unitForm.value = {
    name: unit.name,
    abbreviation: unit.abbreviation,
    plural_form: unit.plural_form || '',
    unit_type: unit.unit_type,
    si_factor: unit.si_factor,
    is_common: unit.is_common,
    display_order: unit.display_order
  }
  showEditDialog.value = true
}

async function saveUnit() {
  try {
    if (showEditDialog.value && editingUnitId.value) {
      // 更新
      await api.put(`/units/${editingUnitId.value}`, unitForm.value)
      alert('单位已更新')
    } else {
      // 新增
      await api.post('/units/', unitForm.value)
      alert('单位已创建')
    }

    closeDialog()
    await loadUnits()
  } catch (error: any) {
    console.error('Failed to save unit:', error)
    alert(error.response?.data?.detail || '保存单位失败')
  }
}

async function deleteUnit(unit: any) {
  if (!confirm(`确定要删除单位「${unit.name}」吗？`)) {
    return
  }

  try {
    await api.delete(`/units/${unit.id}`)
    alert('单位已删除')
    await loadUnits()
  } catch (error: any) {
    console.error('Failed to delete unit:', error)
    alert(error.response?.data?.detail || '删除单位失败')
  }
}

function showConversions(unit: any) {
  selectedUnit.value = unit
  showConversionsDialog.value = true
  loadConversions()
}

async function saveConversion() {
  try {
    await api.post('/units/conversions/', conversionForm.value)
    alert('换算关系已创建')
    showAddConversionDialog.value = false
    await loadConversions()
  } catch (error: any) {
    console.error('Failed to save conversion:', error)
    alert(error.response?.data?.detail || '保存换算关系失败')
  }
}

async function deleteConversion(conv: any) {
  if (!confirm('确定要删除这个换算关系吗？')) {
    return
  }

  try {
    await api.delete(`/units/conversions/${conv.id}`)
    alert('换算关系已删除')
    await loadConversions()
  } catch (error: any) {
    console.error('Failed to delete conversion:', error)
    alert(error.response?.data?.detail || '删除换算关系失败')
  }
}

function closeDialog() {
  showCreateDialog.value = false
  showEditDialog.value = false
  editingUnitId.value = null
  unitForm.value = {
    name: '',
    abbreviation: '',
    plural_form: '',
    unit_type: 'count',
    si_factor: 1.0,
    is_common: false,
    display_order: 0
  }
}

function closeConversionsDialog() {
  showConversionsDialog.value = false
  showAddConversionDialog.value = false
  conversions.value = []
  selectedUnit.value = null
}

// 分页处理函数
function handlePageChange(page: number) {
  currentPage.value = page
  loadUnits()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadUnits()
}
</script>

<style scoped>
.unit-manager {
  padding-left: 1rem;
  padding-right: 1rem;
}

.manager-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: white;
  padding: 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: bold;
  color: #42b883;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.toolbar-left {
  display: flex;
  gap: 1rem;
  flex: 1;
}

.filter-select,
.search-input {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.search-input {
  flex: 1;
  max-width: 300px;
}

.btn-primary {
  padding: 0.5rem 1rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #35a872;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.2s;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-small {
  padding: 0.375rem 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.8125rem;
  margin-right: 0.5rem;
  transition: background 0.2s;
}

.btn-small:hover {
  background: #5568d3;
}

.btn-danger {
  background: #dc3545;
}

.btn-danger:hover {
  background: #c82333;
}

.units-table,
.conversions-table {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  overflow-x: auto;
}

.units-table table,
.conversions-table table {
  width: 100%;
  border-collapse: collapse;
}

.units-table th,
.units-table td,
.conversions-table th,
.conversions-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.units-table th,
.conversions-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.units-table tr:hover,
.conversions-table tr:hover {
  background: #f8f9fa;
}

.badge-yes {
  background: #42b883;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.badge-no {
  background: #6c757d;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 0.5rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 700px;
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
  font-weight: 500;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.625rem;
  border: 1px solid #ddd;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.form-group.checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form-group.checkbox input {
  width: auto;
}

.form-group.checkbox label {
  margin-bottom: 0;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  justify-content: flex-end;
}

.conversions-toolbar {
  margin-bottom: 1rem;
  display: flex;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .unit-manager {
    padding: 1rem;
  }

  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }

  .toolbar {
    flex-direction: column;
    gap: 1rem;
  }

  .toolbar-left {
    flex-direction: column;
    width: 100%;
  }

  .search-input {
    max-width: 100%;
  }

  .units-table,
  .conversions-table {
    font-size: 0.8125rem;
  }

  .modal-content {
    padding: 1.5rem;
  }
}

@media (max-width: 480px) {
  .stats-section {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
  }

  .form-actions button {
    width: 100%;
  }
}
</style>
