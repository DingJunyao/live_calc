# 菜谱成本与营养分析面板设计

## 概述

在菜谱详情页之外，新增独立分析页面，集中展示菜谱的成本构成、营养贡献溯源和商家比价信息。后端最小改动（仅新增一个端点），前端通过组合现有 API + 可视化呈现。

## 路由与导航

- **URL**：`/recipes/:id/analysis` → `RecipeAnalysisView.vue`
- **入口**：菜谱详情页 app-bar 新增「分析」按钮（`mdi-chart-box-outline`）
- **返回**：分析页顶部面包屑 `菜谱详情 > 分析`，点击返回详情页
- **路由守卫**：菜谱加载失败时跳回详情页

## 页面布局

- **布局模式**：纵向滚动 + 宽屏两栏
- **内容顺序**（按优先级）：
  1. 食材成本占比（单独占行，可左，宽屏居中）
  2. 成本趋势（增强）（可左，与 1 并排）
  3. 营养贡献溯源（单独占行）
  4. 商家比价 & 预估成本（并排：⑤卡片在上，④表格在下）
- **响应式**：宽屏 ≥960px 两栏并排，窄屏单列纵向排列

## 模块设计

### 1. 食材成本占比

**数据来源**：`GET /recipes/{id}/cost` → `cost_breakdown`（已有）

**展示方式**：
- ECharts 环形图（饼图）
- 中心显示总成本（¥xx.xx）
- 每个扇区标签显示：食材名 / 金额 / 百分比
- 底部图例行显示颜色 + 食材名 + 金额 + 百分比
- 食材超过 6 项时，只显示前 5 + "其他"聚合
- 食材颜色由统一的色盘按索引循环分配

### 2. 成本趋势（增强）

**数据来源**：
- 总趋势：`GET /recipes/{id}/cost-history-range`（已有）
- 单食材趋势：`GET /products?ingredient_id=xx&start_date=...&end_date=...`（已有）

**展示方式**：
- 左侧：ECharts **堆叠面积图**，所有食材成本累加成一条面积曲线，展示总成本随时间的变化
- 右侧：食材标签列表（带颜色点 + 占比百分比）
- 点击食材标签 → 右侧展开该食材的独立价格趋势迷你折线图
- 时间筛选器（周 / 月 / 季 / 年 / 全部）
- 窄屏时食材标签行移至图表下方
- 颜色与第 1 模块保持一致

### 3. 营养贡献溯源

**数据来源**：`GET /recipes/{id}/nutrition` → `ingredient_details`（已有，前端未展示）

**展示方式**：
- 每张图：120px 环形图，展示该营养素的食材贡献分解
- 中心显示：营养素总值 + NRV%
- 环图下方小字：TOP 2 贡献食材名称 + 占比
- 默认展示有 NRV 参考值的核心营养素网格
- 「全部」按钮切换显示所有有数据的营养素（含维生素、矿物质系列）
- 网格自适应：桌面 4-6 列，平板 3 列，手机 2 列
- 食材颜色与成本模块保持一致

### 4. 商家比价推荐

**数据来源**：并行请求 `GET /nutrition/ingredients/{id}/latest-price-by-merchant`（已有）

**展示方式**：
- **食材 × 商家价格矩阵表**
- 行 = 食材（含菜谱用量），列 = 商家
- 每个单元格显示按菜谱用量换算后的预估金额
- 每行最低价加粗 + 高亮标注
- "—" 表示该商家无此食材的价格记录
- 表头固定，可横向滚动（商家过多时）

### 5. 按商家预估成本

**数据来源**：新增 `GET /recipes/{id}/merchant-costs`

**展示方式**：
- 商家卡片对比列表
- 每张卡片显示：
  - 商家名称
  - 是否推荐（综合覆盖率和价格加权）
  - 覆盖食材数 / 总数（如 5/6）
  - 总成本预估
  - 缺失食材列表（如有）
- 最实惠的商家卡片高亮 + "最实惠 ✓" 标记
- 覆盖不全的卡片显示警告色 + 缺失信息

## 后端 API 设计

### 新增：`GET /api/v1/recipes/{id}/merchant-costs`

**功能**：计算按商家购买菜谱所有食材的总成本估算

**请求参数**：无

**响应**：
```json
{
  "currency": "CNY",
  "merchants": [
    {
      "merchant_id": 1,
      "merchant_name": "yy菜市场",
      "total_cost": 21.80,
      "covered_count": 5,
      "total_ingredients": 6,
      "missing_ingredients": ["盐"],
      "is_recommended": true
    }
  ]
}
```

**实现逻辑**：
1. 获取菜谱所有 RecipeIngredient
2. 对每个食材，查询有价格记录的商家
3. 按商家维度聚合：该商家能覆盖哪些食材、最新价格是多少
4. 对覆盖食材数 ≥1 的商家计算总成本
5. 推荐算法：覆盖全部食材的商家中总价最低者优先；若全部商家都有缺项，则按覆盖率降序排列，覆盖率相同则总价低者优先

**放置位置**：`backend/app/api/recipes.py`，复用 `recipe_service.py` 中的现有成本计算函数

## 数据流

```
RecipeAnalysisView.vue (onMounted)
  │
  ├── GET /recipes/{id}                      → recipe
  ├── GET /recipes/{id}/cost                 → costData
  ├── GET /recipes/{id}/nutrition            → nutritionData
  ├── GET /recipes/{id}/cost-history-range   → costHistoryRecords
  ├── GET /recipes/{id}/merchant-costs       → merchantCosts (新增)
  └── 并行请求(每个食材):
       GET /nutrition/ingredients/{id}/latest-price-by-merchant → price矩阵
```

5 个独立请求并行发出，各自更新对应的响应式状态，互不阻塞。

## 组件结构

```
frontend/src/views/recipes/
  └── RecipeAnalysisView.vue          ← 路由页面，数据编排 + 布局容器

frontend/src/components/recipes/
  ├── CostProportionChart.vue         ← ① 成本占比环形图
  ├── CostTrendAnalysis.vue           ← ② 成本趋势（堆叠面积图 + 食材选择器）
  ├── NutritionSourceGrid.vue         ← ③ 营养贡献多环形图网格
  ├── MerchantCostCards.vue           ← ⑤ 商家成本卡片对比
  └── MerchantPriceMatrix.vue         ← ④ 食材×商家价格矩阵表
```

每个组件：
- 通过 props 接收数据
- 内部通过 ECharts 或纯 CSS/HTML 渲染
- 对数据源无副作用（纯展示）

## 跨模块约定

- **食材颜色统一**：所有模块用同一个色盘，按 `cost_breakdown` 数组顺序循环分配（确保食材在成本占比、趋势、营养溯源中的颜色一致）
- **商家价格矩阵并发**：N 个食材需 N 次 `/nutrition/ingredients/{id}/latest-price-by-merchant` 请求，通过 `Promise.all` 并行发出，前端设置整体超时（如 15s）
- **格式一致**：金额 ¥xx.xx，营养素 x.xg/x.mg/x.kcal，百分比 xx%
- **加载态**：每个模块独立 loading，不影响其他模块渲染
- **空态**：无数据时显示对应空状态提示，不崩溃

## 实施优先级

1. 实现后端 `merchant-costs` 端点
2. 创建 `RecipeAnalysisView.vue` 路由和页面骨架
3. 实现 `CostProportionChart.vue`
4. 增强 `PriceTrendChart` 或实现 `CostTrendAnalysis.vue`
5. 实现 `NutritionSourceGrid.vue`
6. 实现 `MerchantCostCards.vue` + `MerchantPriceMatrix.vue`
7. 集成测试 + 边缘情况处理
