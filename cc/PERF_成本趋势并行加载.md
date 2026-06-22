# 菜谱详情成本趋势并行加载优化

## 背景

菜谱详情页（[RecipeDetail.vue](../frontend/src/views/recipes/RecipeDetail.vue)）的成本趋势图，切换「季」「年」「全部」等大跨度区间时，分批加载是**串行**的（`while` 循环里 `await loadCostHistory(...)`，每批 90 天，一批接一批），墙钟时间 = 各批延迟之和，跨度越大越慢。

后端端点 `GET /recipes/{id}/cost-history-range` 接受 `days`（≤365）与 `offset_days`，各段 offset 互不重叠时彼此独立、纯读计算无竞态，天然适合并发。

## 优化方案

保留「任务间串行队列（`costHistoryQueue`）+ 去重（`attemptedRanges`）+ 累积池（`maxDaysLoaded`）」的外层骨架不变，只把**每个任务内部**从串行改成并行。三刀：

### 1. 拆出无副作用的并行核心

原 `loadCostHistory`（请求 + 合并 + 更新 `maxDaysLoaded` 副作用揉在一起）拆成：

- `fetchCostHistoryBatch(days, offsetDays)`：纯请求，返回 `CostHistoryRecord[]`，无副作用。
- `loadCostHistoryParallel(targetDays, fromDays)`：
  - 按 90 天/批切分 `[fromDays, targetDays)`，构造 `{days, offsetDays}[]`（offset 升序、互不重叠）。
  - `Promise.all` 并发请求各批。
  - 合并：非空批按 `offsetDays` 降序（越早越靠前）前置到现有 `costHistoryRecords`。
  - 返回 `{ maxOffset, hitEmpty }`：`maxOffset` = 已探过的最远边界；`hitEmpty` = 末批（offset 最大、日期最早）是否为空，供「全部」模式判断终止。

### 2. 固定区间（季/年等）一次性并行

`enqueueCostHistory` 原来的 `while` 串行循环，改为一次 `loadCostHistoryParallel(targetDays, maxDaysLoaded)` 调用。例：「年」(365 天) 从已加载 30 天出发 → 4 批并发，墙钟 ≈ 最慢一批而非 4 批之和。

### 3. 「全部」区间分波次并行

`loadAllCostHistory` 不知道终点，改成**分波次**：每波 `COST_HISTORY_ALL_WAVE_BATCHES = 4` 批（≈360 天）并发，`hitEmpty` 即越过最早记录，终止。每波最多浪费末批一个请求，但轮次数从 N 降到 N/4。

## 不变项

- `costHistoryQueue` 串行队列：多次区间切换（如快速点「年」再点「全部」）仍互斥，避免并发竞态。
- `attemptedRanges` 去重、`maxDaysLoaded` 累积池、切菜谱时的三件套重置（`costHistoryRecords` / `maxDaysLoaded` / `attemptedRanges`）。
- 后端无改动（端点本就支持 `offset_days` 分段）。

## 收益

- 固定大跨度区间：≈ 批数倍提速（「年」约 4×）。
- 「全部」：≈ 每波批数倍提速（约 4×）。
- 后端总计算量不变，只是把分摊到时间轴的请求压扁到同一时间窗。
