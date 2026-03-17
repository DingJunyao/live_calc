<template>
  <PageHeader title="商家管理" :show-back="true">
    <template #extra>
      <button @click="showAddModal = true" class="btn-square add-btn" title="添加商家">
        <i class="mdi mdi-plus"></i>
      </button>
    </template>
  </PageHeader>

  <div class="merchant-map">
    <div class="search-filter">
      <div class="search-box">
        <input v-model="searchTerm" placeholder="搜索商家名称或地址..." class="search-input" />
      </div>
      <button @click="loadMerchants" class="btn-search" title="搜索">
        <i class="mdi mdi-magnify"></i>
      </button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="merchants.length === 0" class="empty-state">
      暂无商家记录
    </div>

    <div v-else class="merchant-list">
      <div v-for="merchant in merchants" :key="merchant.id" class="merchant-card">
        <div class="merchant-header">
          <h3>{{ merchant.name }}</h3>
          <div class="merchant-actions">
            <button @click="editMerchant(merchant)" class="btn-edit" title="编辑">
              <i class="mdi mdi-pencil"></i>
            </button>
            <button @click="deleteMerchant(merchant)" class="btn-delete" title="删除">
              <i class="mdi mdi-delete"></i>
            </button>
          </div>
        </div>
        <div class="merchant-info">
          <p v-if="merchant.address">地址: {{ merchant.address }}</p>
          <p>纬度: {{ merchant.latitude }}</p>
          <p>经度: {{ merchant.longitude }}</p>
          <p>添加时间: {{ formatDate(merchant.created_at) }}</p>
        </div>
      </div>
    </div>

    <Pagination
      v-if="total > 0"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @change-page="handlePageChange"
      @change-page-size="handlePageSizeChange"
    />

    <!-- 添加/编辑商家模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingMerchant ? '编辑商家' : '添加商家' }}</h2>
        <form @submit.prevent="addMerchant">
          <div class="form-group">
            <label for="merchantName">商家名称:</label>
            <input v-model="newMerchant.name" type="text" id="merchantName" required />
          </div>
          <div class="form-group">
            <label for="address">地址:</label>
            <div class="address-input-group">
              <input v-model="newMerchant.address" type="text" id="address" class="address-input" />
              <button @click="searchAddressFromInput" class="search-address-btn" :disabled="!newMerchant.address.trim()">
                搜索地址
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>地图位置:</label>
            <MapPicker
              v-model="merchantCoordinate"
              height="300px"
              :show-search="false"
              :show-switcher="true"
              @address-selected="handleAddressSelected"
            />
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">{{ editingMerchant ? '更新' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'
import MapPicker from '@/components/MapPicker.vue'
import type { Coordinate } from '@/utils/mapTypes'

const merchants = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const editingMerchant = ref<any>(null)
const searchTerm = ref('')
const newMerchant = ref({
  name: '',
  address: '',
  latitude: 0,
  longitude: 0
})

// 商家的坐标（用于 MapPicker v-model）
const merchantCoordinate = ref<Coordinate>({ lat: 39.9042, lng: 116.4074 })

// 处理地址选择（反向地理编码结果）
function handleAddressSelected(data: { address: string; lat: number; lng: number }) {
  newMerchant.value.address = data.address
  newMerchant.value.latitude = data.lat
  newMerchant.value.longitude = data.lng
}

// 从地址输入框搜索地址
async function searchAddressFromInput() {
  const address = newMerchant.value.address?.trim()
  if (!address) return

  try {
    // 使用 Nominatim 进行地址搜索（不需要 API Key）
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`
    const response = await fetch(url)
    const data = await response.json()

    if (data && data.length > 0) {
      const result = data[0]
      const lat = parseFloat(result.lat)
      const lng = parseFloat(result.lon)

      // 更新坐标
      merchantCoordinate.value = { lat, lng }
      newMerchant.value.latitude = lat
      newMerchant.value.longitude = lng
      newMerchant.value.address = result.display_name

      alert(`找到位置: ${result.display_name}`)
    } else {
      alert('未找到该地址')
    }
  } catch (error) {
    console.error('Search address error:', error)
    alert('搜索地址失败，请重试')
  }
}

// 监听 MapPicker 坐标变化
function handleCoordinateChange(coord: Coordinate) {
  newMerchant.value.latitude = coord.lat
  newMerchant.value.longitude = coord.lng
}

// 监听坐标变化
watch(merchantCoordinate, (newCoord) => {
  if (newCoord) {
    handleCoordinateChange(newCoord)
  }
})

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

onMounted(async () => {
  await loadMerchants()
})

async function loadMerchants() {
  loading.value = true
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    let url = `/merchants?skip=${skip}&limit=${pageSize.value}`
    if (searchTerm.value) {
      url += `&search=${encodeURIComponent(searchTerm.value)}`
    }
    const data = await api.get<{
      items: any[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(url)
    merchants.value = data?.items || []
    total.value = data?.total || 0
  } catch (error) {
    console.error('Failed to load merchants:', error)
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadMerchants()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadMerchants()
}

// 模态框操作
function openAddModal() {
  editingMerchant.value = null
  newMerchant.value = {
    name: '',
    address: '',
    latitude: 0,
    longitude: 0
  }
  // 设置默认坐标（北京）
  merchantCoordinate.value = { lat: 39.9042, lng: 116.4074 }
  showAddModal.value = true
}

function editMerchant(merchant: any) {
  editingMerchant.value = merchant
  const lat = merchant.latitude || 0
  const lng = merchant.longitude || 0
  newMerchant.value = {
    name: merchant.name,
    address: merchant.address || '',
    latitude: lat,
    longitude: lng
  }
  // 设置当前坐标
  merchantCoordinate.value = lat && lng ? { lat, lng } : { lat: 39.9042, lng: 116.4074 }
  showAddModal.value = true
}

function closeModal() {
  showAddModal.value = false
  editingMerchant.value = null
}

async function addMerchant() {
  try {
    if (editingMerchant.value) {
      // 编辑模式
      await api.put(`/merchants/${editingMerchant.value.id}`, newMerchant.value)
      alert('商家更新成功')
    } else {
      // 添加模式
      await api.post('/merchants', newMerchant.value)
      alert('商家添加成功')
    }
    closeModal()
    await loadMerchants()
  } catch (error: any) {
    console.error('Failed to save merchant:', error)
    alert(error?.response?.data?.detail || '保存商家失败，请重试')
  }
}

async function deleteMerchant(merchant: any) {
  if (confirm(`确定要删除商家 "${merchant.name}" 吗？`)) {
    try {
      await api.delete(`/merchants/${merchant.id}`)
      alert('商家删除成功')
      await loadMerchants()
    } catch (error: any) {
      console.error('Failed to delete merchant:', error)
      alert(error?.response?.data?.detail || '删除商家失败，请重试')
    }
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.merchant-map {
  padding-left: 1rem;
  padding-right: 1rem;
}

.search-filter {
  display: flex;
  align-items: stretch;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  padding: 0.5rem;
  width: 100%;
  box-sizing: border-box;
}

.search-box {
  flex: 2;
  min-width: 0;
}

.search-input {
  width: 100%;
  height: 100%;
  padding: 0.375rem 0.625rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
  line-height: 1.5;
}

.btn-search {
  flex: 0 0 auto;
  aspect-ratio: 1;
  min-width: 44px;
  max-width: 48px;
  background: #667eea;
  color: white;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: background-color 0.2s;
}

.btn-search:hover {
  background: #5a6fd8;
}

.btn-primary {
  padding: 0.5rem 1rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.add-btn {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
}

.add-btn:hover {
  background: #36966d;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 4rem;
  color: #999;
}

.merchant-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.merchant-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.merchant-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.merchant-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.merchant-header h3 {
  font-size: 1.125rem;
  color: #333;
  margin: 0;
  flex-grow: 1;
}

.merchant-actions {
  display: flex;
  gap: 0.5rem;
}

.merchant-actions button {
  width: 2rem;
  height: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-edit {
  background: #667eea;
  color: white;
}

.btn-edit:hover {
  background: #5a6fd8;
}

.btn-delete {
  background: #de350b;
  color: white;
}

.btn-delete:hover {
  background: #bc2e0b;
}

.merchant-info p {
  margin: 0.25rem 0;
  color: #666;
  font-size: 0.875rem;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .merchant-map {
    padding: 0.75rem;
  }

  .add-btn {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .merchant-list {
    gap: 0.75rem;
  }

  .merchant-card {
    padding: 1rem;
  }

  .merchant-header h3 {
    font-size: 1rem;
  }

  .merchant-actions button {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.75rem;
  }

  .merchant-info p {
    font-size: 0.8125rem;
  }

  .modal-content {
    padding: 1.5rem;
  }

  .modal-content h2 {
    font-size: 1.25rem;
  }

  .form-group {
    margin-bottom: 0.75rem;
  }

  .form-group input {
    font-size: 0.875rem;
  }

  .search-filter {
    gap: 0.375rem;
  }

  .btn-search {
    min-width: 40px;
    max-width: 44px;
  }

  .search-input {
    padding: 0.5rem 0.625rem;
    font-size: 0.875rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .merchant-map {
    padding: 0.5rem;
  }

  .add-btn {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .merchant-list {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .merchant-card {
    padding: 0.75rem;
  }

  .merchant-header h3 {
    font-size: 0.9375rem;
  }

  .merchant-actions {
    gap: 0.375rem;
  }

  .merchant-actions button {
    width: 1.5rem;
    height: 1.5rem;
    font-size: 0.6875rem;
  }

  .merchant-info p {
    font-size: 0.75rem;
  }

  .modal-content {
    padding: 1rem;
    max-width: calc(100% - 1rem);
  }

  .btn-fab {
    width: 2.75rem;
    height: 2.75rem;
    bottom: 1rem;
    right: 1rem;
    font-size: 1rem;
  }

  .search-filter {
    gap: 0.25rem;
  }

  .btn-search {
    min-width: 36px;
    max-width: 40px;
  }

  .search-input {
    padding: 0.375rem 0.5625rem;
    font-size: 0.8125rem;
  }
}

.address-input-group {
  display: flex;
  gap: 0.5rem;
}

.address-input {
  flex: 1;
}

.search-address-btn {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  white-space: nowrap;
}

.search-address-btn:hover:not(:disabled) {
  background: #5a6fd8;
}

.search-address-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
