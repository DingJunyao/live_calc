# 成本数据延迟加载优化

## 概述

为加快页面加载速度，将菜谱管理列表和菜谱详情页的价格、成本等计算密集型数据改为延迟加载，先渲染基础数据，再后台异步加载计算数据。

## 涉及文件

- `backend/app/api/recipes.py` - 新增 `POST /batch-cost` 批量成本查询端点；`cost-history-range` 增加 `offset_days` 参数支持分批加载
- `backend/app/services/recipe_service.py` - `calculate_recipe_cost_range_trend` 增加 `offset_days` 参数
- `frontend/src/views/recipes/RecipesView.vue` - 列表页取消 `include_cost=true`，改为渲染后批量子请求
- `frontend/src/views/recipes/RecipeDetail.vue` - 详情页拆分加载流程，基础数据优先渲染，成本/营养/趋势各自独立
- `frontend/src/components/charts/PriceTrendChart.vue` - 加载状态改为覆盖层模式，不销毁图表 DOM

## 改动要点

### 后端

1. **新增 `POST /api/v1/recipes/batch-cost`**：接收 `{ ids: [1,2,3] }`，返回 `{ "1": { estimated_cost, calories } }`。复用已有 `batch_calculate_recipes_cost_nutrition`。

2. **`cost-history-range` 增加 `offset_days` 参数**：支持分批加载成本趋势数据。如 `days=30, offset_days=0` 为近30天；`days=60, offset_days=30` 为第31至90天。

### 前端 - 列表页

- `loadRecipes()` 不再传 `include_cost=true`，列表秒出
- 渲染完成后调 `loadCostsForVisibleRecipes()` → `POST /recipes/batch-cost` 后台加载成本
- 数据到前卡片显示 `--`，到了自动替换

### 前端 - 详情页

- `loadData()` 只加载菜谱基本信息 → 立即渲染
- 成本/营养/成本历史在后台分别加载，互不影响
- 趋势图分两批：先 30 天（秒出），用户点季/年时按需补数据

### 前端 - 串行队列（核心设计）

```typescript
let costHistoryQueue = Promise.resolve()

const enqueueCostHistory = async (targetDays: number, showLoading: boolean) => {
  // ...
  const promise = costHistoryQueue.then(async () => {
    const remaining = targetDays - maxDaysLoaded.value  // 动态算余量
    if (remaining <= 0) return
    await loadCostHistory(remaining, maxDaysLoaded.value)
  })
  costHistoryQueue = promise
  return promise
}
```

- 按目标总天数入队，运行时按 `maxDaysLoaded` 动态计算剩余天数
- 避免 0-90 天这类大范围请求，尽可能复用已加载数据
- `attemptedRanges` 记录已尝试过的范围，空结果不重复请求

### 前端 - 图表覆盖层（解决图表消失）

- 改 `v-if` 为覆盖层模式：加载中时半透明遮罩盖在图表上，不销毁图表 DOM
- echarts 实例一旦初始化，永久存活，不再因 loading 切换而丢失
- 筛选切换时图表实时更新，覆盖层只控制可见性

### 加载行为总结

| 筛选 | 初始行为 | 后续切换 |
|------|---------|---------|
| 周 | 已有 30 天数据，无需加载 | 无请求 |
| 月 | 首次加载 30 天 | 无请求 |
| 季 | 补加载 60 天（offset=30） | 同，attemptedRanges 防重 |
| 年 | 补加载 275 天（offset=90） | 同，空结果不重复 |

## 注意事项

- 空结果不更新 `maxDaysLoaded`，避免误判为数据已加载
- 切换回数据已足够的筛选时立即清除 loading 覆盖层
- `loadCostHistory` 不管理 loading 状态，由调用者（`onCostTrendFilterChange` / `loadCostHistoryInBatches`）控制
