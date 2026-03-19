<template>
  <PageHeader title="价格记录" :show-back="true">
    <template #extra>
      <button
          @click="openAddModal"
          class="btn-square add-btn"
          title="添加记录"
          :disabled="loading || merchantsLoading || loadingUnits || allProducts.length === 0 || allMerchants.length === 0"
          :class="{ 'btn-disabled': loading || merchantsLoading || loadingUnits || allProducts.length === 0 || allMerchants.length === 0 }"
        >
          <i class="mdi mdi-plus"></i>
        </button>
      </template>
  </PageHeader>

  <div class="product-list">
    <div class="search-filter">
      <div class="search-box">
        <input v-model="searchTerm" placeholder="搜索商品名称..." class="search-input" />
      </div>
      <div class="filter-options">
        <select v-model="selectedProduct" class="filter-select">
          <option value="">所有商品</option>
          <option v-for="product in allProducts" :key="product.id" :value="product.id">
            {{ product.name }}
          </option>
        </select>
        <select v-model="selectedMerchant" class="filter-select">
          <option value="">所有商家</option>
          <option v-for="merchant in allMerchants" :key="merchant.id" :value="merchant.id">
            {{ merchant.name }}
          </option>
        </select>
      </div>
      <button @click="loadProducts" class="btn-search" title="搜索">
        <i class="mdi mdi-magnify"></i>
      </button>
    </div>

    <!-- 检查商品和商家是否存在，如果不存在则显示提示 -->
    <div v-if="(!loading && allProducts.length === 0) || (!merchantsLoading && allMerchants.length === 0)" class="notification-banner full-width">
      <i class="mdi mdi-alert-outline"></i>
      <span>
        <template v-if="(!loading && allProducts.length === 0) && (!merchantsLoading && allMerchants.length === 0)">
          尚未创建商品和商家，请先
          <a href="#" @click.prevent="goToProductsManage()">创建商品</a>
          和
          <a href="#" @click.prevent="goToLocations()">创建商家</a>
        </template>
        <template v-else-if="!loading && allProducts.length === 0">
          尚未创建商品，无法记录价格。请先<a href="#" @click.prevent="goToProductsManage()">创建商品</a>
        </template>
        <template v-else-if="!merchantsLoading && allMerchants.length === 0">
          尚未创建商家，无法记录商品价格。请先<a href="#" @click.prevent="goToLocations()">创建商家</a>
        </template>
      </span>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="products.length === 0" class="empty-state">
      暂无价格记录
    </div>
    <div v-else class="product-grid">
      <div v-for="product in products" :key="product.id" class="product-card">
        <div class="product-header">
          <h3>{{ product.product_name }}</h3>
          <div class="product-actions">
            <button @click="editProduct(product)" class="btn-edit" title="编辑">
              <i class="mdi mdi-pencil"></i>
            </button>
            <button @click="deleteProduct(product)" class="btn-delete" title="删除">
              <i class="mdi mdi-delete"></i>
            </button>
          </div>
        </div>
        <div class="product-info">
          <p>价格: ¥{{ product.price }}</p>
          <p>数量: {{ product.original_quantity }} {{ product.original_unit }}</p>
          <p>商家: {{ product.merchant_name || '-' }}</p>
          <p>记录时间: {{ formatDate(product.recorded_at) }}</p>
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

    <!-- 添加/编辑价格记录模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ editingProduct ? '编辑价格记录' : '添加价格记录' }}</h2>
          <button class="close-btn" @click="closeModal" title="关闭">&times;</button>
        </div>
        <form @submit.prevent="addProduct" class="modal-form">
          <div class="form-group">
            <label for="productName">商品:</label>
            <input
              ref="productInputRef"
              v-model="productSearchTerm"
              type="text"
              id="productName"
              placeholder="输入搜索商品..."
              @input="onProductInput"
              @change="onProductChange"
              @focus="handleProductFocus"
              @keydown="handleKeydown"
              class="datalist-input"
            />
            <!-- 自定义下拉建议列表 -->
            <div
              v-show="showProductSuggestions && filteredProducts.length > 0"
              class="product-suggestions"
              :style="productSuggestionsStyle"
            >
              <div
                v-for="(product, index) in filteredProducts"
                :key="product.id"
                class="suggestion-item"
                :class="{ 'suggestion-selected': selectedIndex === index }"
                @click="selectProduct(product)"
              >
                <span class="suggestion-name">{{ product.name }}</span>
                <span v-if="product.brand" class="suggestion-brand"> - {{ product.brand }}</span>
                <!-- 显示匹配的别名 -->
                <span v-if="product.match_type === 'alias' && product.matched_alias" class="suggestion-alias">
                  ({{ product.matched_alias }})
                </span>
                <!-- 显示食材名称提示 -->
                <span v-else-if="product.match_type === 'ingredient_name' && product.ingredient_name" class="suggestion-ingredient">
                  ({{ product.ingredient_name }})
                </span>
              </div>
              <div
                v-if="showProductCreateOption"
                class="suggestion-item suggestion-create"
                :class="{ 'suggestion-selected': selectedIndex === filteredProducts.length }"
                @click="createNewProduct"
              >
                + 创建新商品: {{ productSearchTerm }}
              </div>
            </div>
          </div>
          <div class="form-group">
            <label for="price">价格 (元):</label>
            <input v-model.number="newProduct.price" type="number" id="price" step="0.01" min="0" required />
          </div>
          <div class="form-group">
            <label>数量与单位:</label>
            <div class="quantity-unit-row">
              <input
                v-model.number="newProduct.quantity"
                type="number"
                id="quantity"
                min="0"
                step="any"
                required
                placeholder="数量"
              />
              <select v-model="newProduct.unit" id="unit" required>
                <option v-for="unit in units" :key="unit.id" :value="unit.abbreviation">
                  {{ unit.name }}{{ unit.name !== unit.abbreviation ? ` (${unit.abbreviation})` : '' }}
                </option>
              </select>
            </div>
          </div>
          <div class="form-group checkbox-group">
            <label for="isPurchase" class="checkbox-label">
              <input
                type="checkbox"
                id="isPurchase"
                v-model="newProduct.is_purchase"
                class="checkbox-input"
              />
              <span>计入支出（购买记录）</span>
            </label>
          </div>
          <div class="form-group">
            <label for="recordedAt">记录时间:</label>
            <input
              v-model="newProduct.recorded_at"
              type="datetime-local"
              id="recordedAt"
              class="datetime-input"
            />
          </div>
          <div class="form-group">
            <label for="location">商家:</label>
            <input
              ref="locationInputRef"
              v-model="merchantSearchTerm"
              type="text"
              id="location"
              placeholder="输入搜索商家（可选）..."
              @input="onMerchantInput"
              @focus="handleLocationFocus"
              class="datalist-input"
            />
            <!-- 自定义下拉建议列表 -->
            <div
              v-show="showLocationSuggestions && filteredMerchants.length > 0"
              class="location-suggestions"
              :style="locationSuggestionsStyle"
            >
              <div
                v-for="(merchant, index) in filteredMerchants"
                :key="merchant.id"
                class="suggestion-item"
                :class="{ 'suggestion-selected': selectedLocationIndex === index }"
                @click="selectLocation(merchant)"
              >
                {{ merchant.name }}
                <span v-if="merchant.address" class="suggestion-address"> - {{ merchant.address }}</span>
              </div>
              <div
                v-if="showMerchantCreateOption"
                class="suggestion-item suggestion-create"
                :class="{ 'suggestion-selected': selectedLocationIndex === filteredMerchants.length }"
                @click="createNewMerchant"
              >
                + 创建新商家: {{ merchantSearchTerm }}
              </div>
            </div>
          </div>
        </form>
        <div class="form-actions">
          <button type="button" @click="addProduct" class="btn-primary">{{ editingProduct ? '更新' : '添加' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, Teleport, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productAPI, api } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'

type ProductSuggestion = {
  id: number
  name: string
  brand?: string
  ingredient_id?: number
  ingredient_name?: string
  match_type?: 'name' | 'ingredient_name' | 'alias'
  matched_alias?: string | null
}

type PriceRecord = {
  id: number
  product_id: number
  product_name: string
  merchant_id: number | null
  merchant_name: string | null
  price: number
  original_quantity: number
  original_unit: string
  standard_quantity: number
  standard_unit: string
  recorded_at: string
}

type Merchant = {
  id: number
  name: string
  address?: string
}

const route = useRoute()
const router = useRouter()
const products = ref<PriceRecord[]>([])
const allProducts = ref<ProductSuggestion[]>([])
const allMerchants = ref<Merchant[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const editingProduct = ref<PriceRecord | null>(null)
const searchTerm = ref('')
const selectedProduct = ref('')
const selectedMerchant = ref('')
const newProduct = ref({
  product_id: 0,
  product_name: '',
  price: 0,
  quantity: 1,
  unit: '',
  merchant_id: 0,
  merchant_name: '',
  is_purchase: true,
  recorded_at: ''
})

// 商品搜索和选择相关状态
const productSearchTerm = ref('')
const filteredProducts = ref<ProductSuggestion[]>([])
const showProductCreateOption = ref(false)
let productSearchTimeout: ReturnType<typeof setTimeout> | null = null  // 用于商品搜索防抖

// 商家搜索和选择相关状态
const merchantSearchTerm = ref('')
const filteredMerchants = ref<Merchant[]>([])
const showMerchantCreateOption = ref(false)
let merchantSearchTimeout: ReturnType<typeof setTimeout> | null = null  // 用于商家搜索防抖

// 添加商家加载状态
const merchantsLoading = ref(true)

// 添加单位相关状态
const units = ref<any[]>([])
const loadingUnits = ref(false)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 会话记忆功能（在同一会话中记住上一次的选择）
const lastIsPurchase = ref(true)  // 记住上一次是否购买
const lastMerchantId = ref(0)  // 记住上一次的商家ID
const lastMerchantName = ref('')  // 记住上一次的商家名称

// 自动完成下拉建议相关状态
const productInputRef = ref<HTMLInputElement | null>(null)
const locationInputRef = ref<HTMLInputElement | null>(null)
const showProductSuggestions = ref(false)
const showLocationSuggestions = ref(false)
const selectedIndex = ref(-1)
const selectedLocationIndex = ref(-1)
const productSuggestionsStyle = ref<Record<string, string>>({})
const locationSuggestionsStyle = ref<Record<string, string>>({})
const filteredSuggestions = ref<ProductSuggestion[]>([])
const filteredLocationSuggestions = ref<Merchant[]>([])

// 商品过滤选项
async function filterProductOptions() {
  const search = productSearchTerm.value.trim()

  // 如果搜索词太短，显示所有商品
  if (!search || search.length < 1) {
    filteredProducts.value = allProducts.value // 显示所有商品
    console.log(`显示所有商品，总数: ${allProducts.value.length}`)
    showProductCreateOption.value = false
    return
  }

  // 优先使用API进行搜索以获得最新最全的结果
  try {
    // 使用新的自动完成API进行搜索，支持别名匹配
    console.log(`调用自动完成API搜索: ${search}`)
    const response = await api.get(`/products/autocomplete?q=${encodeURIComponent(search)}&limit=100`);

    // API返回带有匹配类型和匹配别名的结果
    const items = Array.isArray(response) ? response : [];
    filteredProducts.value = items;
    console.log(`自动完成API搜索结果数量: ${items.length}, 搜索词: "${search}"`)

    // 检查是否显示创建选项
    showProductCreateOption.value = search.length > 0 &&
      !items.some((p: ProductSuggestion) => p.name.toLowerCase() === search.toLowerCase())
  } catch (error) {
    console.warn('API搜索失败，使用优化的本地搜索:', error);

    // 使用优化后的本地搜索逻辑
    console.log(`使用优化的本地搜索: ${search}`)
    console.log(`本地数据总数量: ${allProducts.value.length}`)

    // 检查是否需要获取完整数据集来进行搜索
    // 如果当前本地数据集较小，可能是因为没有加载所有数据
    // 在本地数据集中搜索，但使用更全面的方法
    const searchLower = search.toLowerCase();

    // 将所有商品按匹配类型分类
    const exactMatch = [];
    const startsWith = [];
    const nameContains = [];
    const brandContains = [];

    for (const p of allProducts.value) {
      const nameLower = p.name.toLowerCase();
      const brandLower = p.brand ? p.brand.toLowerCase() : '';

      // 检查名称匹配
      if (nameLower === searchLower) {
        exactMatch.push(p);
      } else if (nameLower.startsWith(searchLower)) {
        startsWith.push(p);
      } else if (nameLower.includes(searchLower)) {
        nameContains.push(p);
      }

      // 检查品牌匹配（避免重复）
      if (brandLower && brandLower.includes(searchLower)) {
        // 确保没有在名称匹配中已经添加过的商品
        if (!nameLower.includes(searchLower)) {
          brandContains.push(p);
        }
      }
    }

    // 合并结果，保持顺序：精确匹配 > 开头匹配 > 名称包含 > 品牌包含
    filteredProducts.value = [...exactMatch, ...startsWith, ...nameContains, ...brandContains];

    console.log(`优化本地搜索总结果数量: ${filteredProducts.value.length}, 搜索词: "${search}"`)
    console.log(`- 精确匹配: ${exactMatch.length}`)
    console.log(`- 开头匹配: ${startsWith.length}`)
    console.log(`- 名称包含: ${nameContains.length}`)
    console.log(`- 品牌包含: ${brandContains.length}`)

    // 检查是否显示创建选项
    showProductCreateOption.value = search.length > 0 &&
      !filteredProducts.value.some(p => p.name.toLowerCase() === search.toLowerCase())
  }

  console.log(`最终显示结果数量: ${filteredProducts.value.length}`)
}

// 商品选择变化处理
function onProductChange() {
  if (productSearchTerm.value === '+ 创建新商品') {
    // 如果用户选择了创建新商品选项
    openQuickCreateProduct();
    // 恢复搜索词为原来的值
    setTimeout(() => {
      productSearchTerm.value = newProduct.value.product_name || '';
    }, 100);
  } else {
    // 如果用户选择了一个具体的商品，将该商品的ID填入newProduct
    const matchedProduct = allProducts.value.find(p => p.name === productSearchTerm.value);
    if (matchedProduct) {
      newProduct.value.product_id = matchedProduct.id;
      newProduct.value.product_name = matchedProduct.name;
    } else {
      newProduct.value.product_id = 0;
      newProduct.value.product_name = productSearchTerm.value;
    }
  }
}

// 旧的商品选择变化处理函数（现在重命名为onProductIdChange）
function onProductIdChange() {
  if (newProduct.value.product_id === -1) {
    // 选择了创建新商品
    openQuickCreateProduct()
  }
}

// 商家过滤选项
async function filterMerchantOptions() {
  const search = merchantSearchTerm.value.trim()

  // 如果搜索词太短，显示所有商家
  if (!search || search.length < 1) {
    filteredMerchants.value = allMerchants.value // 显示所有商家
    console.log(`显示所有商家，总数: ${allMerchants.value.length}`)
    showMerchantCreateOption.value = false
    return
  }

  // 优先使用API进行搜索以获得最新最全的结果
  try {
    // 使用API端点进行搜索，利用后端的数据库索引进行高效匹配
    console.log(`调用API搜索商家: ${search}`)
    const response = await api.get(`/merchants?search=${encodeURIComponent(search)}&skip=0&limit=1000`);
    const items = response.items || response || [];
    filteredMerchants.value = items;
    console.log(`API搜索商家结果数量: ${items.length}, 搜索词: "${search}"`)

    // 检查是否显示创建选项
    showMerchantCreateOption.value = search.length > 0 &&
      !items.some((m: Merchant) => m.name.toLowerCase() === search.toLowerCase())
  } catch (error) {
    console.warn('API搜索商家失败，使用优化的本地搜索:', error);

    // 使用优化后的本地搜索逻辑
    console.log(`使用优化的本地商家搜索: ${search}`)

    // 直接在allMerchants.value上进行搜索，不设限
    const searchResults = allMerchants.value.filter(m =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      (m.address && m.address.toLowerCase().includes(search.toLowerCase()))
    );

    // 按照相关性排序：精确匹配 > 开头匹配 > 包含匹配
    const exactMatch = searchResults.filter(m => m.name.toLowerCase() === search.toLowerCase());
    const startsWith = searchResults.filter(m =>
      m.name.toLowerCase().startsWith(search.toLowerCase()) &&
      m.name.toLowerCase() !== search.toLowerCase());
    const contains = searchResults.filter(m =>
      !m.name.toLowerCase().startsWith(search.toLowerCase()) &&
      m.name.toLowerCase().includes(search.toLowerCase()));

    // 包含地址匹配的结果
    const addressMatch = allMerchants.value.filter(m =>
      !m.name.toLowerCase().includes(search.toLowerCase()) &&  // 避免重复
      m.address && m.address.toLowerCase().includes(search.toLowerCase())
    );

    // 合并结果，保持顺序：精确匹配 > 开头匹配 > 名称包含 > 地址包含
    filteredMerchants.value = [...exactMatch, ...startsWith, ...contains, ...addressMatch];

    console.log(`优化本地商家搜索总结果数量: ${filteredMerchants.value.length}, 搜索词: "${search}"`)
    console.log(`- 精确匹配: ${exactMatch.length}`)
    console.log(`- 开头匹配: ${startsWith.length}`)
    console.log(`- 名称包含: ${contains.length}`)
    console.log(`- 地址包含: ${addressMatch.length}`)

    // 检查是否显示创建选项
    showMerchantCreateOption.value = search.length > 0 &&
      !filteredMerchants.value.some(m => m.name.toLowerCase() === search.toLowerCase())
  }

  console.log(`商家最终显示结果数量: ${filteredMerchants.value.length}`)
}

// 商家选择变化处理
function onMerchantChange() {
  if (newProduct.value.merchant_id === -1) {
    // 选择了创建新商家
    openQuickCreateMerchant()
  }
}

// 打开快速创建商品对话框
async function openQuickCreateProduct() {
  const name = productSearchTerm.value.trim()
  if (!name) return

  const newName = prompt(`创建新商品：${name}\n\n品牌（可选）：`, '')
  if (newName === null) {
    // 用户取消，恢复选择
    newProduct.value.product_id = 0
    return
  }

  try {
    const response = await productAPI.create({
      name: newName || name,
      brand: ''
    })
    alert('商品创建成功')
    // 重新加载商品列表
    await loadAllProducts()
    // 自动选中新建的商品
    newProduct.value.product_id = (response as any).id
    newProduct.value.product_name = newName || name
    productSearchTerm.value = newName || name
    filterProductOptions()
  } catch (error: any) {
    console.error('Failed to create product:', error)
    alert(error.message || '创建商品失败')
    newProduct.value.product_id = 0
  }
}

// 打开快速创建商家对话框
async function openQuickCreateMerchant() {
  const name = merchantSearchTerm.value.trim()
  if (!name) return

  const newName = prompt(`创建新商家：${name}\n\n地址（可选）：`, '')
  if (newName === null) {
    // 用户取消，恢复选择
    newProduct.value.merchant_id = 0
    return
  }

  try {
    const response = await api.post('/merchants', {
      name: newName || name,
      address: ''
    })
    alert('商家创建成功')
    // 重新加载商家列表
    await loadAllMerchants()
    // 自动选中新建的商家
    newProduct.value.merchant_id = (response as any).id
    newProduct.value.merchant_name = newName || name
    merchantSearchTerm.value = newName || name
    filterMerchantOptions()
  } catch (error: any) {
    console.error('Failed to create merchant:', error)
    alert(error.message || '创建商家失败')
    newProduct.value.merchant_id = 0
  }
}

// 使用指定名称快速创建商品（不弹出prompt）
async function openQuickCreateProductWithName(name: string) {
  try {
    const response = await productAPI.create({
      name: name,
      brand: ''
    })
    alert('商品创建成功')
    // 重新加载商品列表
    await loadAllProducts()
    // 自动选中新建的商品
    const createdProduct = allProducts.value.find(p => p.name === name);
    if (createdProduct) {
      newProduct.value.product_id = createdProduct.id
      newProduct.value.product_name = name
      productSearchTerm.value = name
    }
    filterProductOptions()
  } catch (error: any) {
    console.error('Failed to create product:', error)
    alert(error.message || '创建商品失败')
    newProduct.value.product_id = 0
  }
}

// 创建新商品后自动选择
async function createAndSelectProduct(name: string) {
  try {
    const response = await productAPI.create({
      name: name,
      brand: ''
    })
    // 重新加载商品列表
    await loadAllProducts()
    // 找到刚创建的商品并自动选中
    const createdProduct = allProducts.value.find(p => p.name === name);
    if (createdProduct) {
      newProduct.value.product_id = createdProduct.id
      newProduct.value.product_name = name
      productSearchTerm.value = name
    }
    return createdProduct;
  } catch (error: any) {
    console.error('Failed to create product:', error)
    alert(error.message || '创建商品失败')
    return null;
  }
}

// 使用指定名称快速创建商家（不弹出prompt）
async function openQuickCreateMerchantWithName(name: string) {
  try {
    const response = await api.post('/merchants', {
      name: name,
      address: ''
    })
    alert('商家创建成功')
    // 重新加载商家列表
    await loadAllMerchants()
    // 自动选中新建的商家
    newProduct.value.merchant_id = (response as any).id
    merchantSearchTerm.value = name
    filterMerchantOptions()
  } catch (error: any) {
    console.error('Failed to create merchant:', error)
    alert(error.message || '创建商家失败')
    newProduct.value.merchant_id = 0
  }
}

// 遮罩层点击时不关闭（防止误触）
function handleOverlayClick(event: MouseEvent) {
  // 不执行任何操作，用户必须点击关闭按钮
}

onMounted(async () => {
  await loadProducts()
  await loadAllProducts()
  await loadAllMerchants()
  await loadUnits()  // 加载单位数据

  // 初始化过滤后的选项
  filteredProducts.value = allProducts.value
  filteredMerchants.value = allMerchants.value

  // 检查是否有从商品管理页面传来的参数
  const productId = route.query.product_id
  const productName = route.query.product_name as string
  if (productId && productName) {
    newProduct.value.product_id = Number(productId)
    newProduct.value.product_name = productName
    // 如果有路由参数，则检查是否有足够数据（商家），但不强制跳转
    // 如果商家为空，则直接打开模态框，让用户可以选择商家或被提示
    showAddModal.value = true
  }

  // 添加点击外部区域关闭下拉建议的功能，使用捕获阶段确保能接收到事件
  setTimeout(() => {
    document.addEventListener('click', handleClickOutside, true);
  }, 100); // 延迟添加事件监听器以确保DOM完全加载

  // 添加 visualViewport 监听器，用于移动端键盘弹出时重新计算下拉框位置
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', handleVisualViewportResize);
  }
})

onUnmounted(() => {
  // 移除事件监听器（同样使用捕获阶段）
  document.removeEventListener('click', handleClickOutside, true);

  // 移除窗口大小变化监听器
  window.removeEventListener('resize', handleWindowResize);

  // 移除屏幕方向改变监听器
  window.removeEventListener('orientationchange', handleOrientationChange);

  // 移除视口变化监听器
  window.removeEventListener('resize', handleViewportChange);

  // 移除 visualViewport 监听器
  if (window.visualViewport) {
    window.visualViewport.removeEventListener('resize', handleVisualViewportResize);
  }
})

// 处理点击外部区域关闭下拉建议
function handleClickOutside(event: Event) {
  const target = event.target as HTMLElement;

  // 检查点击是否在商品输入框或其下拉列表之内
  const isProductInputArea = target.closest('#product-input') ||
                            target.closest('.product-suggestions') ||
                            target.classList.contains('product-suggestions');

  // 检查点击是否在商家输入框或其下拉列表之内
  const isLocationInputArea = target.closest('#location-input') ||
                             target.closest('.location-suggestions') ||
                             target.classList.contains('location-suggestions');

  // 如果点击不在商品相关区域，隐藏商品下拉
  if (!isProductInputArea) {
    showProductSuggestions.value = false;
  }

  // 如果点击不在商家相关区域，隐藏商家下拉
  if (!isLocationInputArea) {
    showLocationSuggestions.value = false;
  }
}

onUnmounted(() => {
  // 移除事件监听器
  document.removeEventListener('click', handleClickOutside);

  // 移除窗口大小变化监听器
  window.removeEventListener('resize', handleWindowResize);
})

// 监听窗口大小变化，重新计算下拉建议位置
function handleWindowResize() {
  // 在下一个tick确保DOM已更新
  nextTick(() => {
    if (showProductSuggestions.value && productInputRef.value) {
      updateSuggestionsPosition(productInputRef.value, productSuggestionsStyle, false);
    }
    if (showLocationSuggestions.value && locationInputRef.value) {
      updateSuggestionsPosition(locationInputRef.value, locationSuggestionsStyle, true);
    }
  });
}

// 添加窗口大小变化监听器
window.addEventListener('resize', handleWindowResize);

// 专门处理移动端键盘显示/隐藏的情况
function handleOrientationChange() {
  // 在屏幕方向改变或键盘弹出/收起时重新计算位置
  setTimeout(() => {
    if (showProductSuggestions.value && productInputRef.value) {
      updateSuggestionsPosition(productInputRef.value, productSuggestionsStyle, false);
    }
    if (showLocationSuggestions.value && locationInputRef.value) {
      updateSuggestionsPosition(locationInputRef.value, locationSuggestionsStyle, true);
    }
  }, 300); // 等待界面布局完成
}

// 监听屏幕方向改变事件
window.addEventListener('orientationchange', handleOrientationChange);

// 监听视口变化，检测软键盘弹出（移动端）
let initialViewportHeight = window.innerHeight;

function handleViewportChange() {
  const currentViewportHeight = window.innerHeight;

  // 如果视口高度变化超过阈值，可能是因为软键盘弹出/收起
  const heightDifference = Math.abs(initialViewportHeight - currentViewportHeight);
  const threshold = 100; // 阈值设定为100px

  if (heightDifference > threshold) {
    // 更新初始视口高度
    initialViewportHeight = currentViewportHeight;

    // 重新计算下拉建议位置
    setTimeout(() => {
      if (showProductSuggestions.value && productInputRef.value) {
        updateSuggestionsPosition(productInputRef.value, productSuggestionsStyle, false);
      }
      if (showLocationSuggestions.value && locationInputRef.value) {
        updateSuggestionsPosition(locationInputRef.value, locationSuggestionsStyle, true);
      }
    }, 300); // 等待界面布局完成
  }
}

// 监听视口大小变化，主要用于检测移动设备上软键盘的弹出
window.addEventListener('resize', handleViewportChange);

// 使用 visualViewport API 处理移动端键盘弹出（更可靠的方法）
function handleVisualViewportResize() {
  // 重新计算下拉建议位置
  setTimeout(() => {
    if (showProductSuggestions.value && productInputRef.value) {
      updateSuggestionsPosition(productInputRef.value, productSuggestionsStyle, false);
    }
    if (showLocationSuggestions.value && locationInputRef.value) {
      updateSuggestionsPosition(locationInputRef.value, locationSuggestionsStyle, true);
    }
  }, 100); // 短延迟确保布局已更新
}

async function loadProducts() {
  loading.value = true
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    let url = `/products?skip=${skip}&limit=${pageSize.value}&sort_by=price_records`  // 按价格记录数量排序
    if (selectedProduct.value) {
      url += `&product_id=${selectedProduct.value}`
    }
    if (selectedMerchant.value) {
      url += `&merchant_id=${selectedMerchant.value}`
    }
    if (searchTerm.value) {
      url += `&search=${encodeURIComponent(searchTerm.value)}`
    }
    const response = await api.get<any>(url)

    let items: PriceRecord[]
    let totalCount = 0  // 使用不同的变量名避免与 ref 冲突

    if (response.items && response.total !== undefined) {
      // 新的 PaginatedResponse 格式
      items = response.items
      totalCount = response.total
    } else if (Array.isArray(response)) {
      // 旧的 List 格式
      items = response
      if (currentPage.value === 1 && !searchTerm.value && !selectedProduct.value && !selectedMerchant.value) {
        totalCount = items.length
      }
    }

    products.value = items || []
    total.value = totalCount
  } catch (error) {
    console.error('Failed to load products:', error)
    products.value = []
  } finally {
    loading.value = false
  }
}

async function loadAllProducts() {
  try {
    // 加载所有商品作为完整数据集用于本地搜索
    let allItems: ProductSuggestion[] = []
    let skip = 0
    const limit = 100  // 增加单次请求量以减少请求数量
    let hasMore = true

    console.log('开始加载所有商品数据...')

    while (hasMore) {
      const response = await productAPI.list({ skip, limit })
      const items = (response as any).items || (Array.isArray(response) ? response : [])

      // 确保数据格式正确
      const products = items.map((item: any) => ({
        id: item.id,
        name: item.name,
        brand: item.brand || ''
      }))

      allItems = allItems.concat(products)

      // 如果返回的数据少于 limit，说明没有更多数据了
      if (items.length < limit) {
        hasMore = false
      } else {
        skip += limit
      }

      // 添加进度日志
      console.log(`已加载 ${allItems.length} 个商品...`)
    }

    allProducts.value = allItems
    console.log(`完成加载，共 ${allItems.length} 个商品`) // 调试信息
  } catch (error) {
    console.error('Failed to load products:', error)
    allProducts.value = []
  }
}

async function loadAllMerchants() {
  try {
    // 尝试获取所有商家（使用分页来获取所有数据，limit限制为100）
    let allItems: Merchant[] = [];
    let skip = 0;
    const limit = 100;  // 限制为100以满足API要求

    // 只加载前3页数据作为初始缓存，提高首次加载速度
    let pageCount = 0;
    const maxInitialPages = 3;

    while (pageCount < maxInitialPages) {
      const response = await api.get<any>(`/merchants?skip=${skip}&limit=${limit}`);
      const items = response.items || response || [];

      // 确保数据格式正确
      const merchants = items.map((item: any) => ({
        id: item.id,
        name: item.name,
        address: item.address || ''
      }));

      allItems = allItems.concat(merchants);

      // 如果返回的数据少于 limit，说明没有更多数据了
      if (items.length < limit) {
        break;
      }

      skip += limit;
      pageCount++;
    }

    allMerchants.value = allItems;
    console.log('处理后的商家列表:', allMerchants.value, `共 ${allItems.length} 条`); // 调试信息
  } catch (error) {
    console.error('Failed to load merchants:', error)
  } finally {
    merchantsLoading.value = false  // 更新加载状态
  }
}

// 加载单位
async function loadUnits() {
  try {
    loadingUnits.value = true
    const response = await api.get<any>('/ingredients/units')
    // 这个SB API返回的也是分页格式，需要从items里取数据
    units.value = response.items || []
  } catch (error) {
    console.error('Failed to load units:', error)
    units.value = []
  } finally {
    loadingUnits.value = false
  }
}

function openAddModal() {
  console.log('[openAddModal] 被调用')
  console.log('[openAddModal] loading:', loading.value, 'merchantsLoading:', merchantsLoading.value, 'loadingUnits:', loadingUnits.value)
  console.log('[openAddModal] allProducts.length:', allProducts.value.length, 'allMerchants.length:', allMerchants.value.length)

  // 检查按钮是否被禁用，如果是，则不执行任何操作
  if (loading.value || merchantsLoading.value || loadingUnits.value || allProducts.value.length === 0 || allMerchants.value.length === 0) {
    console.log('[openAddModal] 按钮被禁用，不执行操作')
    return;
  }
  console.log('[openAddModal] 开始打开模态框')

  editingProduct.value = null  // 清除编辑状态
  // 初始化表单并显示模态框，使用会话记忆填充上次的选择
  const now = new Date()
  // 格式化为 datetime-local 需要的格式: YYYY-MM-DDTHH:mm
  const localISOTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)

  newProduct.value = {
    product_id: 0,
    product_name: '',
    price: 0,
    quantity: 1,
    unit: '斤', // 默认单位为斤
    merchant_id: lastMerchantId.value,  // 使用记忆的商家ID
    merchant_name: lastMerchantName.value,  // 使用记忆的商家名称
    is_purchase: lastIsPurchase.value,  // 使用记忆的是否购买
    recorded_at: localISOTime  // 默认为当前时间
  }

  // 初始化搜索词
  productSearchTerm.value = ''
  merchantSearchTerm.value = lastMerchantName.value || ''

  // 初始化过滤后的选项
  filteredProducts.value = allProducts.value
  filteredMerchants.value = allMerchants.value

  // 关闭创建选项
  showProductCreateOption.value = false
  showMerchantCreateOption.value = false

  showAddModal.value = true
}

function editProduct(product: PriceRecord) {
  editingProduct.value = product  // 设置编辑状态

  // 初始化表单数据为当前记录的数据
  const recordedDate = new Date(product.recorded_at)
  const localISOTime = new Date(recordedDate.getTime() - recordedDate.getTimezoneOffset() * 60000).toISOString().slice(0, 16)

  // 查找商品和商家信息
  const matchedProduct = allProducts.value.find(p => p.id === product.product_id)
  const matchedMerchant = allMerchants.value.find(m => m.id === product.merchant_id)

  newProduct.value = {
    product_id: product.product_id,
    product_name: matchedProduct?.name || product.product_name,
    price: Number(product.price),
    quantity: Number(product.original_quantity),
    unit: product.original_unit,
    merchant_id: product.merchant_id || 0,
    merchant_name: matchedMerchant?.name || '',
    is_purchase: product.record_type === 'purchase',  // 根据record_type设置
    recorded_at: localISOTime
  }

  // 初始化搜索词
  productSearchTerm.value = matchedProduct?.name || product.product_name || ''
  merchantSearchTerm.value = matchedMerchant?.name || ''

  // 初始化过滤后的选项
  filteredProducts.value = allProducts.value
  filteredMerchants.value = allMerchants.value

  // 关闭创建选项
  showProductCreateOption.value = false
  showMerchantCreateOption.value = false

  showAddModal.value = true

  // 在模态框显示后，需要一点延迟才能确保DOM已更新
  setTimeout(() => {
    // 检查是否有焦点元素，如果有则保持焦点；否则将焦点设置到商品输入框
    if (!document.activeElement || !document.activeElement.classList.contains('datalist-input')) {
      if (productInputRef.value) {
        productInputRef.value.focus();
      }
    }
  }, 100);
}

function closeModal() {
  showAddModal.value = false
  // 清除搜索词
  productSearchTerm.value = ''
  merchantSearchTerm.value = ''
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadProducts()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadProducts()
}

async function addProduct() {
  console.log('[addProduct] 函数被调用')
  console.log('[addProduct] newProduct.value:', newProduct.value)
  console.log('[addProduct] productSearchTerm.value:', productSearchTerm.value)
  console.log('[addProduct] merchantSearchTerm.value:', merchantSearchTerm.value)

  try {
    // 获取用户输入的商品名称
    const productName = productSearchTerm.value.trim()
    if (!productName) {
      alert('请输入商品名称')
      return
    }

    // 尝试匹配商品
    let productId = newProduct.value.product_id
    if (!productId || productId === -1) {
      // 尝试通过名称查找商品ID
      const matched = allProducts.value.find(p => p.name.toLowerCase() === productName.toLowerCase())
      if (matched) {
        productId = matched.id
        newProduct.value.product_id = productId
      } else if (productName === '+ 创建新商品') {
        // 用户选择了创建新商品选项
        await openQuickCreateProduct()
        return
      } else {
        // 没有匹配的商品，询问是否创建
        if (confirm(`未找到商品"${productName}"，是否创建一个新商品？`)) {
          await openQuickCreateProductWithName(productName)
          return
        }
        return
      }
    }

    // 商家处理
    const merchantName = merchantSearchTerm.value.trim()
    let merchantId = newProduct.value.merchant_id
    if (merchantName && (!merchantId || merchantId === -1)) {
      // 尝试通过名称查找商家ID
      const matched = allMerchants.value.find(m => m.name.toLowerCase() === merchantName.toLowerCase())
      if (matched) {
        merchantId = matched.id
        newProduct.value.merchant_id = merchantId
      } else if (merchantName === '+ 创建新商家') {
        await openQuickCreateMerchant()
        return
      } else if (confirm(`未找到商家"${merchantName}"，是否创建一个新商家？`)) {
        await openQuickCreateMerchantWithName(merchantName)
        return
      }
    }

    if (merchantId === -1) {
      merchantId = 0
    }

    // 验证价格、数量等必填字段
    if (newProduct.value.price <= 0) {
      alert('请输入有效的价格')
      return
    }

    if (newProduct.value.quantity <= 0) {
      alert('请输入有效的数量')
      return
    }

    const requestData = {
      product_id: productId,
      price: newProduct.value.price,
      original_quantity: newProduct.value.quantity,
      original_unit: newProduct.value.unit,
      merchant_id: merchantId || undefined,
      record_type: newProduct.value.is_purchase ? 'purchase' : 'price',
      recorded_at: newProduct.value.recorded_at || undefined
    }

    if (editingProduct.value) {
      // 编辑模式
      await api.put(`/products/${editingProduct.value.id}`, requestData)
      alert('价格记录更新成功')
    } else {
      // 添加模式
      await api.post('/products/', requestData)
      alert('价格记录添加成功')
    }

    // 保存当前选择到会话记忆
    lastIsPurchase.value = newProduct.value.is_purchase
    if (merchantId) {
      lastMerchantId.value = merchantId
    }
    // 保存商家名称（从搜索词获取）
    if (merchantSearchTerm.value) {
      lastMerchantName.value = merchantSearchTerm.value
    }

    closeModal()
    await loadProducts()
  } catch (error) {
    console.error('Failed to save product:', error)
    alert(error?.response?.data?.detail || '保存价格记录失败，请重试')
  }
}

async function deleteProduct(product: PriceRecord) {
  if (confirm(`确定要删除这条价格记录吗？\n商品: ${product.product_name}\n价格: ¥${product.price}`)) {
    try {
      await api.delete(`/products/${product.id}`)
      alert('价格记录删除成功')
      await loadProducts()
    } catch (error: any) {
      console.error('Failed to delete product:', error)
      alert(error?.response?.data?.detail || '删除价格记录失败，请重试')
    }
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function handleProductFocus() {
  // 隐藏商家下拉框，避免两个下拉框同时显示
  showLocationSuggestions.value = false
  locationSuggestionsStyle.value = {}

  // 延迟执行，确保DOM已经更新
  setTimeout(() => {
    updateSuggestionsPosition(productInputRef.value, productSuggestionsStyle, false)
    showProductSuggestions.value = true
  }, 50)
}

function onProductInput() {
  if (productSearchTimeout) {
    clearTimeout(productSearchTimeout)
  }
  // 进一步减少延迟时间以实现更快速响应
  productSearchTimeout = setTimeout(() => {
    // 重置选中的商品ID，因为用户可能正在修改
    if (!allProducts.value.find(p => p.name === newProduct.value.product_name)) {
      newProduct.value.product_id = 0
    }
    // 调用过滤函数
    filterProductOptions()
  }, 25)  // 减少延迟到25ms，实现更快响应
}

function onMerchantInput() {
  if (merchantSearchTimeout) {
    clearTimeout(merchantSearchTimeout)
  }
  // 减少延迟时间以实现更快速响应
  merchantSearchTimeout = setTimeout(() => {
    // 重置选中的商家ID，因为用户可能正在修改
    if (!allMerchants.value.find(m => m.name === newProduct.value.merchant_name)) {
      newProduct.value.merchant_id = 0
    }
    // 调用过滤函数
    filterMerchantOptions()
  }, 25)  // 减少延迟到25ms，实现更快响应
}

function selectProduct(product: ProductSuggestion) {
  newProduct.value.product_id = product.id
  newProduct.value.product_name = product.name
  productSearchTerm.value = product.name  // 确保输入框显示商品名称
  showProductSuggestions.value = false
  selectedIndex.value = -1
  productSuggestionsStyle.value = {}

  // 在选择商品后，将焦点移到商家输入框，这样用户可以看到商家下拉框
  setTimeout(() => {
    if (locationInputRef.value) {
      locationInputRef.value.focus()

      // 手动触发商家输入框的焦点处理函数以显示下拉框
      setTimeout(() => {
        handleLocationFocus()
      }, 50)
    }
  }, 100)
}

function handleKeydown(event: KeyboardEvent) {
  // 更新filteredSuggestions以保持向后兼容
  filteredSuggestions.value = filteredProducts.value;

  // 检查建议列表是否可见且有内容
  if (!showProductSuggestions.value || filteredProducts.value.length === 0) {
    if (event.key === 'Escape') {
      showProductSuggestions.value = false
      selectedIndex.value = -1
      productSuggestionsStyle.value = {}
    }
    return
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    // 包含创建选项的总长度
    const totalLength = filteredProducts.value.length + (showProductCreateOption.value ? 1 : 0)
    selectedIndex.value = Math.min(selectedIndex.value + 1, totalLength - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedIndex.value >= 0) {
    event.preventDefault()
    if (selectedIndex.value < filteredProducts.value.length) {
      // 选择已有商品
      selectProduct(filteredProducts.value[selectedIndex.value])
    } else {
      // 选择创建新商品选项
      createNewProduct()
    }
  } else if (event.key === 'Escape') {
    event.preventDefault()
    showProductSuggestions.value = false
    selectedIndex.value = -1
    productSuggestionsStyle.value = {}
  }
}

function handleLocationFocus() {
  // 隐藏商品下拉框，避免两个下拉框同时显示
  showProductSuggestions.value = false
  productSuggestionsStyle.value = {}

  // 延迟执行，确保DOM已经更新
  setTimeout(() => {
    updateSuggestionsPosition(locationInputRef.value, locationSuggestionsStyle, true)
    showLocationSuggestions.value = true
  }, 50)
}

function onLocationInput() {
  if (merchantSearchTimeout) {
    clearTimeout(merchantSearchTimeout)
  }
  // 进一步减少延迟时间以实现更快速响应
  merchantSearchTimeout = setTimeout(() => {
    // 重置选中的地点ID，因为用户可能正在修改
    if (!allMerchants.value.find(l => l.name === newProduct.value.merchant_name)) {
      newProduct.value.merchant_id = 0
    }
    // 调用过滤函数
    filterMerchantOptions()
  }, 50)  // 减少延迟到50ms，实现更快速响应
}

function selectLocation(location: Merchant) {
  newProduct.value.merchant_id = location.id
  newProduct.value.merchant_name = location.name
  merchantSearchTerm.value = location.name  // 确保输入框显示商家名称
  showLocationSuggestions.value = false
  selectedLocationIndex.value = -1
  locationSuggestionsStyle.value = {}

  // 在选择商家后，将焦点移回商品输入框，这样用户可以继续输入其他商品
  setTimeout(() => {
    if (productInputRef.value) {
      productInputRef.value.focus();
    }
  }, 100)
}

// 创建新商品处理
function createNewProduct() {
  if (productSearchTerm.value.trim()) {
    openQuickCreateProduct()
    showProductSuggestions.value = false
    selectedIndex.value = -1
    productSuggestionsStyle.value = {}
  }
}

// 创建新商家处理
function createNewMerchant() {
  if (merchantSearchTerm.value.trim()) {
    openQuickCreateMerchant()
    showLocationSuggestions.value = false
    selectedLocationIndex.value = -1
    locationSuggestionsStyle.value = {}
  }
}

function handleLocationKeydown(event: KeyboardEvent) {
  // 更新filteredLocationSuggestions以保持向后兼容
  filteredLocationSuggestions.value = filteredMerchants.value;

  // 检查建议列表是否可见且有内容
  if (!showLocationSuggestions.value || filteredMerchants.value.length === 0) {
    if (event.key === 'Escape') {
      showLocationSuggestions.value = false
      selectedLocationIndex.value = -1
      locationSuggestionsStyle.value = {}
    }
    return
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    // 包含创建选项的总长度
    const totalLength = filteredMerchants.value.length + (showMerchantCreateOption.value ? 1 : 0)
    selectedLocationIndex.value = Math.min(selectedLocationIndex.value + 1, totalLength - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedLocationIndex.value = Math.max(selectedLocationIndex.value - 1, -1)
  } else if (event.key === 'Enter' && selectedLocationIndex.value >= 0) {
    event.preventDefault()
    if (selectedLocationIndex.value < filteredMerchants.value.length) {
      // 选择已有商家
      selectLocation(filteredMerchants.value[selectedLocationIndex.value])
    } else {
      // 选择创建新商家选项
      createNewMerchant()
    }
  } else if (event.key === 'Escape') {
    event.preventDefault()
    showLocationSuggestions.value = false
    selectedLocationIndex.value = -1
    locationSuggestionsStyle.value = {}
  }
}

function goToProductsManage() {
  router.push('/products/manage')
}

function goToLocations() {
  router.push('/merchants')
}

function viewNutrition(product: PriceRecord) {
  // 导航到营养详情页面，传入商品ID
  router.push(`/nutrition/product/${product.product_id}`)
}

// 更新建议列表位置
function updateSuggestionsPosition(
  inputRef: HTMLInputElement | null,
  styleRef: { value: Record<string, string> },
  isLocation: boolean = false
) {
  if (!inputRef) return

  // 使用 getBoundingClientRect 获取元素相对于视口的位置
  const inputRect = inputRef.getBoundingClientRect()

  // 获取页面的当前滚动位置
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop || 0
  const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft || 0

  // 计算下拉框相对于页面的位置
  const inputTop = inputRect.top + scrollTop
  const inputBottom = inputRect.bottom + scrollTop
  const inputLeft = inputRect.left + scrollLeft
  const inputWidth = inputRect.width

  // 计算可用空间
  const windowHeight = window.innerHeight || document.documentElement.clientHeight
  const windowWidth = window.innerWidth || document.documentElement.clientWidth
  const spaceAbove = inputRect.top // 输入框上方的可用空间
  const spaceBelow = windowHeight - inputRect.bottom // 输入框下方的可用空间

  // 计算下拉框的高度（估算）
  const estimatedDropdownHeight = Math.min(filteredProducts.value.length * 44, 200) // 每个项目约44px

  // 默认位置：下拉框显示在输入框下方
  let positionTop = inputBottom
  let maxHeight = Math.min(200, spaceBelow - 10) // 留10px边距

  // 如果下方空间不足，尝试放在输入框上方
  if (maxHeight < 60 && spaceAbove > spaceBelow) {
    positionTop = inputTop - estimatedDropdownHeight - 10 // 放在输入框上方
    maxHeight = Math.min(200, spaceAbove - 10)
  }

  // 确保位置不会超出视窗边界
  const safeTop = Math.max(10, positionTop) // 至少10px边距
  const safeLeft = Math.max(10, inputLeft) // 至少10px边距
  const safeWidth = Math.min(inputWidth, windowWidth - safeLeft - 10) // 确保不超过视窗宽度

  // 应用样式
  styleRef.value = {
    top: `${safeTop}px`,
    left: `${safeLeft}px`,
    width: `${safeWidth}px`,
    maxHeight: `${maxHeight}px`,
    position: 'fixed', // 使用fixed定位以应对页面滚动
    zIndex: '1001',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    borderRadius: '4px',
    border: '1px solid #ddd',
    backgroundColor: 'white',
  }
}
</script>

<style scoped>
@import '@/styles/product-modal-fix.css';

.product-list {
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

.filter-options {
  display: flex;
  gap: 0.5rem;
  flex: 0 0 auto;
}

.filter-select {
  flex: 1;
  min-width: 80px;
  max-width: 140px;
  height: 100%;
  padding: 0.375rem 2rem 0.375rem 0.625rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  background: white;
  font-size: 1rem;
  box-sizing: border-box;
  line-height: 1.5;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
  background-size: 12px 12px;
  padding-right: 2rem;
}

.filter-select:focus {
  outline: none;
  border-color: #667eea;
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

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.add-btn {
  position: relative;
  z-index: 10;
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
  transition: background-color 0.2s;
}

.add-btn:hover {
  background: #36996d;
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

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.product-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s, transform 0.2s;
}

.product-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.product-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.product-header h3 {
  margin-top: 0;
  margin-bottom: 0;
  font-size: 1.25rem;
  color: #333;
  flex-grow: 1;
}

.product-actions {
  display: flex;
  gap: 0.5rem;
}

.product-actions button {
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

.btn-nutrition {
  background: #66bb6a;
  color: white;
}

.btn-nutrition:hover {
  background: #4caf50;
}

.product-info p {
  margin: 0.5rem 0;
  color: #666;
  font-size: 0.875rem;
}

/* 模态框样式 */
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
  z-index: 10000;
}

.modal-content {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-content {
  padding: 0;
}

/* 模态框内容区域采用flex布局，使标题栏、表单内容区和底部按钮区垂直排列 */
.modal-content {
  display: flex;
  flex-direction: column;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  margin: 5vh auto;
  background: white;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

/* 模态框标题栏 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  flex-shrink: 0;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
}

/* 表单区域可滚动 */
.modal-form {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;  /* 修复：改为hidden以避免不必要的横向滚动 */
  padding: 1.5rem 2rem;
  min-width: 100%;
  box-sizing: border-box;
}

/* 底部按钮区域 */
.form-actions {
  display: flex;
  justify-content: flex-end;
  padding: 1rem 2rem;
  flex-shrink: 0;
  border-top: 1px solid #eee;
  background: #fafafa;
}


.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
  padding: 0.25rem 0.5rem;
  line-height: 1;
}

.close-btn:hover {
  color: #333;
}

/* 可编辑下拉输入框 */
.datalist-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.datalist-input:focus {
  outline: none;
  border-color: #42b883;
}

/* 数量与单位行 - 始终1:1比例 */
.quantity-unit-row {
  display: flex;
  gap: 0.5rem;
}

.quantity-unit-row input,
.quantity-unit-row select {
  flex: 1;
  min-width: 0;
}

.quantity-unit-row select {
  max-width: 50%;
}

/* 表单操作区域 - 只保留提交按钮 */
.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.form-group input:not([type="checkbox"]) {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group select {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  background: white;
  box-sizing: border-box;
}

.form-group input:not([type="checkbox"]):focus {
  outline: none;
  border-color: #42b883;
}

/* 复选框样式 */
.checkbox-group {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}

.checkbox-group label.checkbox-label {
  display: flex;
  align-items: center;
  margin-bottom: 0;
  cursor: pointer;
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
  user-select: none;
  width: 100%;
  justify-content: flex-start; /* 确保内容左对齐 */
}

.checkbox-input {
  height: 1.125rem;
  margin-right: 0.5rem;
  cursor: pointer;
  accent-color: #42b883;
  width: 1.125rem !important;
}

.checkbox-label:hover .checkbox-input {
  border-color: #36996d;
}

/* 日期时间选择器样式 */
.datetime-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.autocomplete-container {
  position: relative;
}

.suggestions-list {
  position: fixed; /* 改用 fixed 定位，避免在模态框内占据空间 */
  background: white;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
  z-index: 1000;
  list-style: none;
  margin: 0;
  padding: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.suggestions-list li {
  padding: 0.75rem 1rem;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
}

.suggestions-list li:last-child {
  border-bottom: none;
}

.suggestions-list li:hover,
.suggestions-list li.suggestion-selected {
  background-color: #f5f5f5;
}

.suggestions-list .brand {
  color: #999;
  font-size: 0.8125rem;
  margin-left: 0.5rem;
}

.suggestions-list .address {
  color: #999;
  font-size: 0.8125rem;
  margin-left: 0.5rem;
}

.suggestions-list li:hover .brand,
.suggestions-list li.suggestion-selected .brand {
  color: #666;
}

.suggestions-list li:hover .address,
.suggestions-list li.suggestion-selected .address {
  color: #666;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s;
}

.btn-primary:hover {
  background: #36996d;
}

/* 通知横幅样式 */
.notification-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  margin: 0 0 1.5rem 0; /* 上右下左：保持左边距，减少右边距 */
  font-size: 0.875rem;
}

.notification-banner.full-width {
  width: 100%; /* 让其占用全部宽度，内部通过padding实现对齐 */
  box-sizing: border-box;
}

.notification-banner i {
  font-size: 1.25rem;
}

.notification-banner a {
  color: #667eea;
  text-decoration: underline;
  font-weight: 500;
}

.notification-banner a:hover {
  color: #5568d3;
}

/* 小按钮样式 */
.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  border-radius: 0.375rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .product-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1rem;
  }

  .product-header h3 {
    font-size: 1.125rem;
  }

  .product-actions button {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.75rem;
  }

  .modal-content {
    max-height: 85vh;
  }

  .modal-header {
    padding: 1rem;
  }

  .modal-header h2 {
    font-size: 1.25rem;
  }

  .modal-form {
    padding: 1rem;
  }

  .close-btn {
    font-size: 1.25rem;
  }

  .datalist-input {
    padding: 0.625rem 0.875rem;
    font-size: 0.9375rem;
  }

  .add-btn {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .search-filter {
    gap: 0.375rem;
  }

  .filter-select {
    min-width: 60px;
    max-width: 100px;
    padding: 0.5rem 1.5rem 0.5rem 0.625rem;
    font-size: 0.875rem;
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

@media (max-width: 480px) {
  .product-grid {
    grid-template-columns: 1fr;
  }

  .product-header h3 {
    font-size: 1rem;
  }

  .product-actions {
    gap: 0.375rem;
  }

  .product-actions button {
    width: 1.5rem;
    height: 1.5rem;
    font-size: 0.6875rem;
  }

  .modal-content {
    max-width: calc(100% - 1rem);
    max-height: 85vh;
  }

  .modal-header {
    padding: 0.75rem;
  }

  .modal-header h2 {
    font-size: 1.125rem;
  }

  .modal-form {
    padding: 0.75rem;
  }

  .form-actions {
    flex-direction: column;
    padding: 0.75rem;
  }

  .btn-primary {
    width: 100%;
  }

  .search-filter {
    gap: 0.25rem;
  }

  .filter-select {
    min-width: 50px;
    max-width: 80px;
    padding: 0.375rem 1.25rem 0.375rem 0.5625rem;
    font-size: 0.8125rem;
  }

  .btn-search {
    min-width: 36px;
    max-width: 40px;
  }

  .search-input {
    padding: 0.375rem 0.5625rem;
    font-size: 0.8125rem;
  }

  /* 在超小屏幕上保持数量和单位在一行 */
  .quantity-unit-row {
    flex-direction: row;
  }

  .quantity-unit-row input,
  .quantity-unit-row select {
    flex: 1;
    min-width: 0;
  }
}

/* 按钮禁用样式 */
.btn-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* 自定义下拉建议样式 */
.product-suggestions,
.location-suggestions {
  position: fixed;
  top: 0;
  left: 0;
  background: white;
  border: 1px solid #ddd;
  max-height: 200px;
  overflow-y: auto;
  z-index: 10001;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 0 0 4px 4px;
  box-sizing: border-box;
  font-size: 1rem;
}

.suggestion-item {
  padding: 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid #eee;
  transition: background-color 0.2s;
}

.suggestion-item:hover,
.suggestion-item.selected {
  background-color: #f5f5f5;
}

.suggestion-item:last-child {
  border-bottom: none;
}

.suggestion-brand,
.suggestion-address {
  color: #666;
  font-size: 0.9em;
}

.suggestion-alias,
.suggestion-ingredient {
  color: #999;
  font-size: 0.85em;
  margin-left: 0.25rem;
}

.suggestion-name {
  /* 商品名称默认样式 */
}

/* 创建新项目的特殊样式 */
.suggestion-item.create-new {
  background-color: #e8f4fd;
  font-style: italic;
  color: #007bff;
}

.suggestion-item.create-new:hover {
  background-color: #d1e8ff;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .product-suggestions,
  .location-suggestions {
    max-height: 150px;
    font-size: 1rem;
  }

  .suggestion-item {
    padding: 0.8rem;
  }

  /* 确保在移动设备上有足够的触摸目标 */
  .suggestion-item {
    min-height: 44px; /* iOS推荐的最小触摸目标 */
    display: flex;
    align-items: center;
  }
}
</style>
