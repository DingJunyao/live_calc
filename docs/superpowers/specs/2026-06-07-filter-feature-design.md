# 多实体筛选功能设计文档

## 概述

在价格记录、菜谱、原料、商品四个列表页的搜索功能基础上，增加筛选器支持，让用户可以通过多选维度对列表进行过滤。

## 设计范围

| 实体 | 筛选维度 | 多选？ | 类型 |
|------|---------|--------|------|
| 价格记录 | 商家、原料分类、记录类型（购买/比价）、日期范围 | 是（日期范围除外） | select, date-range |
| 菜谱 | 分类、难度 | 是 | select |
| 原料 | 分类 | 是 | select |
| 商品 | 关联原料、原料分类、品牌 | 是 | select |

商家页面本次不加筛选。

## 组件架构

### FilterBar 通用组件

新增 `frontend/src/components/common/FilterBar.vue`，通过 props 接收筛选配置，内部渲染筛选器 UI。

```
FilterBar.vue
├── props:
│   ├── filters: FilterConfig[]    筛选维度配置
│   └── loading: boolean           加载态
├── emits:
│   └── change(obj: Record<string, any>)  任一筛选变化时触发
└── 内部渲染:
    ├── <v-select multiple chips closable-chips>  多选下拉
    └── <v-text-field type="date"> × 2            日期范围
```

### FilterConfig 类型

```typescript
interface FilterConfig {
  key: string                           // 参数字段名
  label: string                         // 显示标签
  type: 'select' | 'date-range'         // 控件类型
  items?: { value: any; title: string }[]  // select 的选项
  multiple?: boolean                    // 是否多选，默认 true
}
```

### 交互行为

- 多选下拉：Vuetify 原生 `v-select multiple chips closable-chips`
- 日期范围：两个并排 `v-text-field type="date"`，校验开始 ≤ 结束
- 任一筛选变化 → 防抖 300ms → emit `change` 事件，携带完整筛选状态
- 父页面收到事件 → 重置页码为 1 → 重新加载列表
- 移动端：筛选器超出一行自动换行，日期范围在小屏上竖排

## 后端 API 改动

### 多选参数格式

统一使用**逗号分隔字符串**传多选值，后端用 `in_()` 或 OR 条件查询。

| 实体 | API 端点 | 参数 | 说明 |
|------|---------|------|------|
| 价格记录 | `GET /products/` | `merchant_ids` | 改造现有 `merchant_id`，多选 |
| | | `record_types` | 新增，如 "purchase,price" |
| | | `ingredient_category_ids` | 新增，跨表筛选 |
| | | `start_date` / `end_date` | 已有，不动 |
| 菜谱 | `GET /recipes/` | `categories` | 新增，多选 |
| | | `difficulties` | 新增，多选 |
| 原料 | `GET /ingredients` | `category_ids` | 新增，多选 |
| 商品 | `GET /products/entity/` | `ingredient_ids` | 新增，多选 |
| | | `ingredient_category_ids` | 新增，跨表筛选 |
| | | `brands` | 新增，多选 |

### 跨表查询逻辑

**价格记录按原料分类筛选**（`ingredient_category_ids`）：
```python
ProductRecord.product.has(
    Product.ingredient.has(
        Ingredient.category_id.in_(category_ids)
    )
)
```

**商品按原料分类筛选**（`ingredient_category_ids`）：
```python
Product.ingredient.has(
    Ingredient.category_id.in_(category_ids)
)
```

### 兼容性

- 现有 `merchant_id` 参数保留，新版 `merchant_ids` 优先级更高
- 所有新参数均为 `Optional`，不传则无此筛选条件

## 前端各视图集成

### 价格记录页 (PricesView.vue)

- 筛选配置：商家、原料分类、记录类型、日期范围
- 筛选选项来源：商家列表从 `/merchants`，分类从 `/ingredients/categories`
- 请求时拼合 `merchant_ids`、`ingredient_category_ids`、`record_types`、`start_date`、`end_date`

### 菜谱页 (RecipesView.vue)

- 筛选配置：分类（预置 10 种分类）、难度（简单/中等/困难）
- 请求时拼合 `categories`、`difficulties`

### 原料页 (IngredientsView.vue)

- 筛选配置：分类
- 筛选选项从 `/ingredients/categories` 加载
- 请求时拼合 `category_ids`

### 商品页 (ProductsView.vue)

- 筛选配置：关联原料、原料分类、品牌
- 原料选项从 `/ingredients` 加载，分类从 `/ingredients/categories` 加载，品牌从现有商品数据提取 distinct 列表
- 请求时拼合 `ingredient_ids`、`ingredient_category_ids`、`brands`

## 文件变更清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/components/common/FilterBar.vue` | 通用筛选器组件 |

### 修改文件
| 文件 | 变更 |
|------|------|
| `backend/app/api/products.py` | `GET /products/` 增加多选参数和跨表筛选 |
| `backend/app/api/recipes.py` | `GET /recipes/` 增加 categories、difficulties 参数 |
| `backend/app/api/nutrition.py` | `GET /ingredients` 增加 category_ids 参数 |
| `backend/app/api/products_entity.py` | `GET /products/entity/` 增加多选参数和跨表筛选 |
| `frontend/src/views/prices/PricesView.vue` | 集成 FilterBar |
| `frontend/src/views/recipes/RecipesView.vue` | 集成 FilterBar |
| `frontend/src/views/data/IngredientsView.vue` | 集成 FilterBar |
| `frontend/src/views/data/ProductsView.vue` | 集成 FilterBar |

## 未包含的范围

- 商家页面的筛选（已排除）
- 筛选条件持久化到 URL 参数（轻量级设计，暂不包含）
- 筛选条件本地缓存/记忆（后续如需可追加）
- 筛选器之间的联动过滤（如选分类后原料列表随之过滤）
