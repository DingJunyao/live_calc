# 管理列表「特殊条件」筛选设计

## 日期

2026-06-23

## 目标

在原料、商品、菜谱、商家四个管理列表页，各新增一个名为「特殊条件」的复选下拉框，用来快速筛选出数据异常/缺失的项目。

## 各列表特殊条件

### 原料管理列表（6 项）

| 前端标签 | 后端参数 | 说明 |
|---|---|---|
| 未配置营养成分 | `no_nutrition=true` | 原料层面无 is_verified 营养数据 |
| 没有维护过价格 | `no_price=true` | 其下所有活跃商品均无价格记录 |
| 仅有一条价格记录 | `single_price=true` | 其下所有商品的价格记录总数为 1 |
| 仅有一家商家有其价格 | `single_merchant=true` | 所有价格记录来自唯一商家 |
| 无相关菜谱 | `no_recipe=true` | 未被任何菜谱引用 |
| 无下属商品 | `no_product=true` | 无活跃商品关联 |

### 商品管理列表（3 项）

| 前端标签 | 后端参数 | 说明 |
|---|---|---|
| 没有维护过价格 | `no_price=true` | 无价格记录 |
| 仅有一条价格记录 | `single_price=true` | 价格记录数为 1 |
| 仅有一家商家有其价格 | `single_merchant=true` | 所有价格记录来自唯一商家 |

### 菜谱管理列表（2 项）

| 前端标签 | 后端参数 | 说明 |
|---|---|---|
| 存在原料没有维护价格 | `has_unpriced_ingredient=true` | 菜谱中至少一种原料无价格记录 |
| 存在原料没有维护营养成分 | `has_unnourished_ingredient=true` | 菜谱中至少一种原料无已验证营养数据 |

### 商家管理列表（1 项 + toggle）

| 前端标签 | 后端参数 | 说明 |
|---|---|---|
| 显示已关闭商家 | `include_closed=true/false` | toggle 开关（迁入 FilterBar） |
| 未维护过价格 | `no_price=true` | 无价格记录 |

## 架构决策

### 过滤位置：后端

与现有所有筛选一致，全部在后端 SQL 层面过滤。每个特殊条件对应一个独立的布尔 query param，默认不传（不启用）。多个条件同时选中时 AND 组合。

### 前端组件：扩展现有 FilterBar

给 `FilterBar.vue` 新增两种类型：
- **toggle**：渲染 `v-switch`，emit 布尔值，用于「显示已关闭商家」等开关
- **multicheck**：渲染 `v-select multiple chips`，emit 选中值数组，用于「特殊条件」多选下拉

### API 参数风格：独立 bool 参数

每个条件一个独立 query param，如 `?no_nutrition=true&no_price=true`。前端 FilterBar emit 的 `special_conditions` 数组值由各页面的 load 函数展开为独立参数。

## 改动范围

| 文件 | 改动内容 |
|---|---|
| `FilterBar.vue` | 新增 `toggle` + `multicheck` 类型，桌面端/移动端双模板 |
| `ingredient_extended.py` | `get_ingredients` 加 6 个 bool 参数 + EXISTS/COUNT 子查询 |
| `products_entity.py` | `list_products` 加 3 个 bool 参数 + EXISTS/COUNT 子查询 |
| `recipes.py` | `get_recipes` 加 2 个 bool 参数 + EXISTS 子查询 |
| `merchants.py` | `get_merchants` 加 1 个 `no_price` bool 参数 + NOT EXISTS 子查询 |
| `IngredientsView.vue` | FilterBar 配置加 special_conditions（6 项），load 展开参数 |
| `ProductsView.vue` | FilterBar 配置加 special_conditions（3 项），load 展开参数 |
| `RecipesView.vue` | FilterBar 配置加 special_conditions（2 项），load 展开参数 |
| `MerchantsView.vue` | 接入 FilterBar：include_closed toggle + special_conditions multicheck，删除旧的切换按钮 |

## SQL 逻辑

### 原料

```sql
-- no_nutrition
NOT EXISTS (SELECT 1 FROM nutrition_data WHERE ingredient_id = ingredients.id AND is_verified = TRUE)

-- no_price
NOT EXISTS (
  SELECT 1 FROM products p
  JOIN product_records pr ON pr.product_id = p.id
  WHERE p.ingredient_id = ingredients.id AND p.is_active = TRUE
)

-- single_price
(SELECT COUNT(*) FROM products p
 JOIN product_records pr ON pr.product_id = p.id
 WHERE p.ingredient_id = ingredients.id AND p.is_active = TRUE) = 1

-- single_merchant
(SELECT COUNT(DISTINCT pr.merchant_id) FROM products p
 JOIN product_records pr ON pr.product_id = p.id
 WHERE p.ingredient_id = ingredients.id AND p.is_active = TRUE) = 1

-- no_recipe
NOT EXISTS (SELECT 1 FROM recipe_ingredients WHERE ingredient_id = ingredients.id)

-- no_product
NOT EXISTS (SELECT 1 FROM products WHERE ingredient_id = ingredients.id AND is_active = TRUE)
```

### 商品

```sql
-- no_price
NOT EXISTS (SELECT 1 FROM product_records WHERE product_id = products.id)

-- single_price
(SELECT COUNT(*) FROM product_records WHERE product_id = products.id) = 1

-- single_merchant
(SELECT COUNT(DISTINCT merchant_id) FROM product_records WHERE product_id = products.id) = 1
```

### 菜谱

```sql
-- has_unpriced_ingredient
EXISTS (
  SELECT 1 FROM recipe_ingredients ri
  JOIN products p ON p.ingredient_id = ri.ingredient_id AND p.is_active = TRUE
  WHERE ri.recipe_id = recipes.id
    AND NOT EXISTS (SELECT 1 FROM product_records pr WHERE pr.product_id = p.id)
)

-- has_unnourished_ingredient
EXISTS (
  SELECT 1 FROM recipe_ingredients ri
  WHERE ri.recipe_id = recipes.id
    AND NOT EXISTS (
      SELECT 1 FROM nutrition_data nd
      WHERE nd.ingredient_id = ri.ingredient_id AND nd.is_verified = TRUE
    )
)
```

### 商家

```sql
-- no_price
NOT EXISTS (SELECT 1 FROM product_records WHERE merchant_id = merchants.id)
```

## 实现步骤

1. FilterBar 加 `toggle` + `multicheck` 两种类型
2. 四个后端 API 各补 bool 参数 + SQL 子查询
3. 三个已有 FilterBar 页面（原料/商品/菜谱）配 multicheck
4. 商家页面接入 FilterBar（toggle + multicheck），删除旧切换按钮
5. 构建验证
