# 价格趋势「全部」区间标签

## 功能

给菜谱、商品、原料三个详情页的价格趋势图（公共组件 `PriceTrendChart`），在「周/月/季/年」之后追加「全部」标签，可查看完整历史区间的趋势。附带修正：商品/原料的图表原先基于「分页 10 条」聚合（翻页时图表跟着变、看不到完整历史），改为按时间区间累积取数。

设计文档：[2026-06-21-价格趋势全部区间-design.md](../docs/superpowers/specs/2026-06-21-价格趋势全部区间-design.md)
实现计划：[2026-06-21-价格趋势全部区间.md](../docs/superpowers/plans/2026-06-21-价格趋势全部区间.md)

## 改动（纯前端，后端零改动）

- `frontend/src/components/charts/PriceTrendChart.vue`：`filters` 加「全部」；`selectedFilter`/`emit` 类型加 `'all'`；`chartData` 在 `all` 时不做时间切片（返回全部仅排序）；清理一个重复的 `watch(selectedFilter)`。
- `frontend/src/views/recipes/RecipeDetail.vue`：`onCostTrendFilterChange` 加 `all` 分支调 `loadAllCostHistory`；新增 `loadAllCostHistory` 循环分批（每批 `COST_HISTORY_BATCH_DAYS=90`，空批终止）、`enqueueCostHistory` 同改循环分批（每批 ≤90）、`loadCostHistory` 放宽 `timeout` 30s（实测 `days=365` 单批超 10s），**纳入 `costHistoryQueue` 串行队列**避免竞态；`loadData` 开头重置 `costHistoryRecords`/`maxDaysLoaded`/`attemptedRanges`（修复 A→B 导航残留）。
- `frontend/src/views/products/ProductDetail.vue` / `frontend/src/views/ingredients/IngredientDetail.vue`：新增图表专用累积池 `chartPriceRecords` + 覆盖游标 `chartEarliestDate`（`undefined`=未请求 / `null`=已全量 / `Date`=已覆盖到该日）+ `loadingChartPrices`；新增 `loadChartPriceRecords(startDate?)`（按 `start_date` 时间区间取数、id 去重合并、已覆盖则跳过，「全部」不传 `start_date` + `timeout` 放宽 30s）与 `onPriceTrendFilterChange`（周/月/季/年→`daysAgo(7/30/90/365)`、全部→`undefined`）；`chartData` 数据源由分页 `priceRecords` 换成 `chartPriceRecords`；组件绑 `@filter-change` + `:loading="loadingChartPrices"`；`loadData` 默认拉近 30 天（月），原料 `loadData` 开头重置累积池（导航残留）。商品用 `product_id`、原料用 `ingredient_id`。下方分页价格记录列表不动。

## 关键决策

- **按时间区间取数，非条数**：周/月/季/年是时间窗口，图表按 `start_date` 拿该窗口全部记录（复用 `/products` 已有的 `start_date/end_date` 参数），不再被分页 10 条限制。
- **超时规避（前端 axios 10s 上限）**：
  - 菜谱：成本计算重、按天前向填充（每日有值），循环分批（每批 90 天、`loadCostHistory` 放宽 `timeout` 30s，空批止），规避单批超过 10s 超时（实测 `days=365` 单批会超 10s，故每批降到 90）。
  - 商品/原料：轻量 SQL 查询，「全部」单请求放宽 `timeout` 到 30s；不分批（原始记录有日期空档，空批终止会误判漏数据）。
- **累积池**：切过的范围记在 `chartEarliestDate`，切回更窄区间不发请求、组件直接切片；切「全部」置 `null`（全量），之后任意区间都直接切片。菜谱同理用 `maxDaysLoaded`。
- **后端零改动**：`/products` 已支持 `start_date/end_date`；菜谱 `cost-history-range` 已支持 `offset_days`，保持 `days le=365` 不放宽（分批替代）。

## 验证

- `npm run build` 通过。
- 三个详情页均经 implementer → spec 合规 → 代码质量 两道审查；整体最终审查通过（揪出并修复了 A→B 导航累积池残留问题）。
- 手动验证（三详情页点「全部」看完整历史、切换不超时、导航不残留）待在登录的真实环境执行。
