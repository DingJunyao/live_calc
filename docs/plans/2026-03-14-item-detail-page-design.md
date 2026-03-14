# 商品/原料详情页设计方案

## 概述

为商品和原料创建统一的详情页面，整合营养、层级关系、归属等功能，支持查看和编辑，同时展示价格记录和价格变化图表。

---

## 1. 整体架构

创建两个新的详情页面组件：
- `ItemDetail.vue` - 主入口组件
- `NutritionEditForm.vue` - 营养数据编辑表单组件
- `AssociationManage.vue` - 关联管理页面组件

`ItemDetail.vue` 根据路由参数 `type`（product 或 ingredient）动态加载不同的数据和字段。

### 路由配置

```
/items/:type/:id → ItemDetail.vue (主详情页)
/items/:type/:id/nutrition/edit → NutritionEditForm.vue (营养编辑页)
/items/:type/:id/associations/manage → AssociationManage.vue (关联管理页)
```

### 数据流

- 主页通过 API 一次性加载商品/原料的完整数据（基本信息、价格历史、营养数据、层级关系、归属列表）
- 编辑操作通过模态框或独立页面进行，编辑完成后刷新主页面
- 价格记录使用后端现有的分页 API 进行加载

---

## 2. 页面结构

### ItemDetail.vue 模板结构

```vue
<PageHeader :title="item.name" :show-back="true" />
<div class="item-detail">
  <!-- 基本信息 -->
  <InfoCard :item="item" :type="type" @edit="handleEditInfo" />

  <!-- 价格记录 -->
  <PriceChartSection :records="priceRecords" @filter="handleFilterChange" />
  <PriceHistoryList :records="priceRecords" :pagination="pagination" />

  <!-- 营养数据 -->
  <NutritionDisplaySection :nutrition="nutritionData" @edit="goToNutritionEdit" />

  <!-- 层级关系 -->
  <HierarchyTreeSection
    :relations="hierarchyRelations"
    @add-relation="handleAddRelation"
    @delete-relation="handleDeleteRelation"
    @edit-strength="handleEditStrength"
  />

  <!-- 归属关系 -->
  <AssociationList
    :associations="associations"
    :type="associationType"
    @edit="goToAssociationManage"
  />
</div>
```

---

## 3. 价格记录模块

### 价格图表组件（PriceChartSection）

- 使用 ECharts LineChart 展示价格趋势
- X 轴为日期，Y 轴为价格（支持货币显示）
- 顶部时间范围筛选器：周/月/季/年
- 图表支持缩放和交互（显示具体日期和价格）

### 价格列表组件（PriceHistoryList）

- 表格展示：日期、商家、价格、数量、单位、备注
- 分页控制：每页 20 条记录
- 数据来源：现有 API `/api/v1/products/`（商品记录列表）

### API 调用逻辑

```typescript
// 加载价格历史
async function loadPriceHistory() {
  const response = await api.get('/products/', {
    params: {
      product_name: item.name,
      skip: (page - 1) * pageSize,
      limit: pageSize
    }
  })
  priceRecords.value = response.data.items
}
```

---

## 4. 营养数据模块

### 营养展示组件（NutritionDisplaySection）

- 复用现有的 `NutritionDisplay` 组件展示营养数据
- 右上角"编辑营养数据"按钮
- 显示 NRV 百分比（使用修复后的计算逻辑）

### 营养编辑表单页面（NutritionEditForm）

**路由**：`/items/:type/:id/nutrition/edit`

**功能**：
- 表单包含所有营养素的输入字段
- 每行显示：营养素名称、数值、单位、删除按钮
- 底部"添加营养素"下拉选择器（包含常见营养素）
- 支持设置数据源（USDA、用户自定义等）
- 提交时调用 API：
  - 商品：`POST/PUT /api/v1/nutrition/products/{id}/nutrition`
  - 原料：`POST/PUT /api/v1/nutrition/ingredients/{id}/nutrition`

**表单数据结构**：
```typescript
interface NutritionEditForm {
  base_quantity: number  // 基准数量
  base_unit: string      // 基准单位
  nutrients: {
    name: string
    value: number
    unit: string
    key?: string
  }[]
  source: string
}
```

---

## 5. 层级关系模块

### 双向树状图组件（HierarchyTreeSection）

**展示**：
- 使用 ECharts Tree 图型
- 当前节点居中显示，上方展示父级关系，下方展示子级关系
- 节点显示食材名称和关系类型标签
- 边线显示关系强度（通过线条粗细或颜色深浅）
- 点击节点 → 弹出模态框，可选择"添加关系"或查看详情
- 右键菜单：添加关系、编辑强度、删除关系

**关系类型展示**：
- 节点上显示类型标签：[包含]、[相似]、[替代]、[回退]
- 线条粗细表示强度

**添加关系流程**：
1. 点击"添加关系"按钮或节点右键菜单
2. 弹出模态框，选择目标食材（支持搜索）和方向（父级/子级）
3. 选择关系类型：CONTAINS、SIMILAR、SUBSTITUTABLE、FALLBACK
4. 设置关系强度（0-100 的滑块）
5. 提交到 API

**API 集成**：
- 获取关系：`GET /api/v1/ingredients/{id}/hierarchy`
- 添加关系：`POST /api/v1/ingredients/hierarchy`
- 删除关系：`DELETE /api/v1/ingredients/hierarchy/{relation_id}`

---

## 6. 归属关系模块

### 归属列表展示（AssociationList）

**商品详情页**：
- 展示归属的原料信息（名称、分类、标签）
- 右上角"编辑关联"按钮 → 跳转到关联管理页面

**原料详情页**：
- 展示归属于该原料的商品列表（条码、品牌、名称、最新价格）
- 每项右上角"×"按钮可删除归属关系（通过修改商品的 ingredient_id）
- 右上角"编辑关联"按钮 → 跳转到关联管理页面

### 关联管理页面（AssociationManage）

**路由**：`/items/:type/:id/associations/manage`

**功能**：
- 左侧：可添加的关联列表（支持搜索筛选）
- 右侧：已关联列表
- 中间：操作区域，可设置关联强度（用于层级关系的延伸）
- 支持：点击添加、点击删除、批量操作

**API 集成**：
- 商品 → 原料：通过 `Product.ingredient_id` 字段关联
- 原料 → 商品：反向查询 `Product` 表的 `ingredient_id`
- 更新关联：`PUT /api/v1/products/entity/{id}`（修改 ingredient_id）
- 获取关联列表：复用现有 API

---

## 7. 状态管理和数据加载

### 主页面状态结构

```typescript
const loading = ref(true)
const error = ref<string | null>(null)
const item = ref<Item>(null)  // 商品或原料信息
const priceRecords = ref<ProductRecord[]>([])
const nutritionData = ref<NutritionData>(null)
const hierarchyRelations = ref<HierarchyRelations>(null)
const associations = ref<Association[]>([])

const priceFilter = ref<'week' | 'month' | 'quarter' | 'year'>('month')
const pagination = ref({ page: 1, pageSize: 20, total: 0 })
```

### 数据加载策略

1. `onMounted` 时并行加载基本信息、营养数据、层级关系、归属列表
2. 价格记录初始加载第一页
3. 切换时间筛选或分页时单独加载价格数据

### 加载函数

```typescript
async function loadItemData() {
  loading.value = true
  try {
    await Promise.all([
      loadBaseInfo(),
      loadNutritionData(),
      loadHierarchyRelations(),
      loadAssociations()
    ])
    await loadPriceHistory()
  } catch (e) {
    error.value = '加载数据失败'
  } finally {
    loading.value = false
  }
}
```

---

## 8. 错误处理和验证

### 错误处理

- API 请求失败时显示友好错误提示，不中断其他模块加载
- 某个模块加载失败时显示"暂无数据"或"加载失败"状态
- 表单提交时验证必填字段，显示具体错误信息
- 网络错误时提供重试按钮

### 表单验证

- 基本信息：标签格式验证
- 营养数据：数值必须为正数、单位必须是有效单位
- 层级关系：不能创建循环关系、不能重复创建相同关系
- 归属关系：验证目标商品/原料存在性
- 条码：不需要唯一性检查（支持店内自编条码）

### 加载状态优化

- 骨架屏（Skeleton）代替简单的"加载中"文字
- 各模块独立加载，不互相阻塞
- 优先展示已加载的内容

---

## 9. 数据模型更新

### 新建 ProductBarcode 模型

支持一个商品对应多个条码（店内自编条码场景）。

```python
class ProductBarcode(Base):
    __tablename__ = 'product_barcodes'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    barcode = Column(String, nullable=False)
    barcode_type = Column(String, default='internal')  # internal/gtin/upc等
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    product = relationship("Product", back_populates="barcodes")
```

### Product 模型更新

移除 `barcode` 字段，添加关系：

```python
class Product(Base):
    # ... 其他字段 ...

    # 移除 barcode 字段，改用关系
    barcodes = relationship("ProductBarcode", back_populates="product", cascade="all, delete-orphan")

    @property
    def primary_barcode(self):
        primary = [b for b in self.barcodes if b.is_primary]
        return primary[0].barcode if primary else None
```

### 基本信息模块更新

**商品基本信息**：条码列表（支持多个）
- 展示：主条码高亮显示，其他条码列出
- 操作：添加条码、删除条码、设为主条码
- 编辑时：条码列表支持 CRUD 操作

**原料基本信息**：别名、分类、标签、描述（不变）

---

## 10. 组件文件结构

```
frontend/src/views/items/
├── ItemDetail.vue              # 主详情页
├── NutritionEditForm.vue      # 营养编辑表单
├── AssociationManage.vue       # 关联管理页面
└── components/
    ├── InfoCard.vue           # 信息卡片
    ├── PriceChartSection.vue  # 价格图表
    ├── PriceHistoryList.vue   # 价格历史列表
    ├── NutritionDisplaySection.vue  # 营养展示
    ├── HierarchyTreeSection.vue    # 层级关系树
    └── AssociationList.vue   # 归属列表
```

---

## 11. 后端 API 需求

### 商品条码 API

- `POST /api/v1/products/entity/{id}/barcodes` - 添加条码
- `GET /api/v1/products/entity/{id}/barcodes` - 获取条码列表
- `PUT /api/v1/products/entity/barcodes/{id}` - 更新条码（设为主条码）
- `DELETE /api/v1/products/entity/barcodes/{id}` - 删除条码

### 营养数据编辑 API

- `POST /api/v1/nutrition/products/{id}/nutrition` - 创建/更新商品营养数据
- `POST /api/v1/nutrition/ingredients/{id}/nutrition` - 创建/更新原料营养数据

---

## 12. 实施步骤

1. 数据库模型更新（ProductBarcode 表）
2. 后端 API 实现（条码 CRUD、营养编辑）
3. 前端基础组件开发（InfoCard、PriceChartSection 等）
4. 主页面 ItemDetail.vue 开发
5. 子页面开发（NutritionEditForm、AssociationManage）
6. ECharts 图表集成
7. 测试和优化
