# 移动端菜谱分析页对齐 web 端

> 2026-08-08 完成（feat/mobile-app 分支）。12 任务全部完成：fl_chart 引入 + 分析页 5 模块重写 + 详情页入口改名。Subagent-Driven 全流程：每任务 implementer → spec 审查 → 质量审查 → 修复循环，双审查抓到 7 个真问题。

## 背景

移动端菜谱详情「分析」页面与 web 端（[RecipeAnalysisView.vue](frontend/src/views/recipes/RecipeAnalysisView.vue)）完全不一致：页面名称是「成本分析」且只有单一成本分布模块，web 端实际是「菜谱分析」含营养等信息。CLAUDE.md「各端体验一致性」硬要求 → 批准 spec（[SPEC_移动端菜谱分析页对齐web.md](SPEC_移动端菜谱分析页对齐web.md)）：**引入 fl_chart** + 方案 A 五模块完整对齐。

## 改动清单（12 任务）

| 任务 | 文件 | 内容 |
|---|---|---|
| 1 | [pubspec.yaml](mobile/pubspec.yaml) | 引入 fl_chart ^1.2.0 |
| 2 | [ingredient_colors.dart](mobile/lib/features/recipes/utils/ingredient_colors.dart) | 16 色板，`ingredientId.abs() % 16` 取色（对齐 web ingredientColors.ts），null → 0xFFE0E0E0；成本占比/趋势/营养三图共用同色 |
| 3 | [recipe_repository.dart](mobile/lib/features/recipes/repositories/recipe_repository.dart) | `getRecipeMerchantCosts`/`getIngredientMerchantPrice`（带 recipeIngredientId/ingredientName/quantity/quantityUnit）+ MerchantPriceItem.fromJson/copyWith |
| 4 | [recipe_provider.dart](mobile/lib/features/recipes/providers/recipe_provider.dart) | RecipeDetailPageState 加 merchantCosts/merchantPrices/loading×2；_loadMerchantCosts/_loadMerchantPrices（每批 3 + 全局 35s 超时、批次内 catch 返回 null + whereType 过滤） |
| 5 | [cost_proportion_chart.dart](mobile/lib/features/recipes/widgets/cost_proportion_chart.dart) | 成本占比环形图：降序、>6 项前 5+「其他」合并、空名「未知食材」、中心总价、图例点击显示金额 |
| 6 | [cost_trend_stacked_chart.dart](mobile/lib/features/recipes/widgets/cost_trend_stacked_chart.dart) | 成本趋势堆叠图：周/月/季/年/全部、touchSpotThreshold: infinity、tooltip 差值逆推、无 breakdown 回退平均折线图 |
| 7 | [nutrition_source_grid.dart](mobile/lib/features/recipes/widgets/nutrition_source_grid.dart) | 营养贡献溯源：17 个 NRV 指标排序、每格迷你环形图 + Top2 贡献文案、NRV/全部切换 |
| 8 | [merchant_cost_cards.dart](mobile/lib/features/recipes/widgets/merchant_cost_cards.dart) | 按商家预估成本卡片：最实惠徽章/覆盖数/本店价/外部价/需外购，横向滚动 |
| 9 | [merchant_price_matrix.dart](mobile/lib/features/recipes/widgets/merchant_price_matrix.dart) | 商家比价矩阵：行=食材列=商家、最低价橙 0xFFE65100 加粗、缺失「—」、fallback 链弹窗 |
| 10 | [recipe_analysis_screen.dart](mobile/lib/features/recipes/screens/recipe_analysis_screen.dart) + 新测试 | 分析页整文件重写：AppBar 菜谱名+「分析」chip（primaryContainer）、initState `load()` + `reloadHistory(90)`（季默认）、5 模块顺序组装、错误/加载分支 |
| 11 | [recipe_detail_screen.dart](mobile/lib/features/recipes/screens/recipe_detail_screen.dart#L64) | 详情页入口 tooltip「成本分析」→「菜谱分析」 |
| 12 | 整体验证 | analyze + 全量测试 59/59 + `flutter build windows --debug` 通过 |

## 双审查抓到的 7 个真问题（每任务 implementer → spec 审查 → 质量审查 → 修复）

1. **计划堆叠算法跨天累加 bug（Task 6 spec 审查）**：计划代码跨天累加（鸡蛋 2→6）vs 测试契约/echarts 每天内累加（2→4）。修复为「天」外层循环 + 每日 acc 重置。
2. **fl_chart tooltip 触点顺序（Task 6）**：touchedSpots 按触点距离排序，差值逆推前必须先 `sort((a,b) => a.barIndex.compareTo(b.barIndex))`。
3. **null/duplicate ingredientId 破坏堆叠（Task 6 质量审查 Important）**：firstWhere 严格匹配 + 只取首个 → fold 求和 + where 过滤；缺失食材当日 y 平接前一序列累计值（对齐 echarts stack 补 0 渲染）。
4. **touchSpotThreshold 缺失（Task 6）**：默认 10px 过滤远距离线致 tooltip 数值错误 → `double.infinity`。
5. **暗色模式对比度（Task 8 Important）**：推荐卡 0xFFFFF8E1 浅琥珀背景配 theme 派生近白文字（1.5:1）→ 暗色回退 surface。
6. **IconButton M3 撑爆（Task 8，新测试抓出）**：info IconButton 超出 20x20 constraints 使卡片溢出 168px 16px → SizedBox(20x20) 包裹。
7. **¥ 渲染在数值后（Task 9 Important）**：「3.50 ¥」应为「¥3.50」→ 单 Text 嵌入前缀 `'¥${display}'`。

## 隐藏 bug：copyWith error 清空（Task 10 测试逼出，计划外修复）

`RecipeDetailPageState.copyWith` 末行 `error: error`（缺 `?? this.error`），任何未显式传 error 的 copyWith 都会把 error 清成 null。本页 initState 连续 `load()` + `reloadHistory(90)`，加载失败时 load() 的 catch 刚写入 error，紧接着 reloadHistory 完成即清空 → 错误页永远不显示，卡在无限加载。修复：`error: error ?? this.error`（对齐 `RecipeListState.copyWith` 既有写法）。**真实生产 bug，非测试特有问题**——错误页在生产中同样无法稳定显示。spec 审查判定合法（最小、必要、消费方无依赖清 error 的代码）。

## 最终整体审查发现并修复：initState 双请求竞态（Important）

**竞态**：原实现 initState 同时发 `load()`（内部 `_loadHistory` 默认 30 天）+ `reloadHistory(90)`，竞争同一 `state.costHistory`。时序：`load()` 的 getRecipe 完成后**整态重建**（清空 costHistory）→ `reloadHistory(90)` 先完成写入 90 天 → load() 内部 `_loadHistory(30)` 最后写入 30 天。**最终显示 30 天数据但趋势图筛选默认「季/90 天」**，且 90 天仅在慢查询时赢，非确定性。

**修复**：`load({int initialDays = 30})` 参数化初始天数（内部 `_loadHistory(days: initialDays)`），分析页改单请求 `load(initialDays: 90)`，删除独立 `reloadHistory(90)`；`_loadHistory({int days = 30})` 保留默认 30（详情页无参 `load()` 行为不变）。`reloadHistory` 仍保留（趋势图 onFilterChange 用）。同轮顺修 Minor：`MerchantPriceRecord.fromJson` 空名回退 `'merchant#'`（英文且无 id，所有缺名行同名）→ `'商家$id'` 对齐 web `_merchantLabel`；nutrition_source_grid_test 注释修正（core_nutrients 实际以中文作键，实现靠 `key` 字段兼容）。

**教训**：fire-and-forget 的并发写同一 state 字段（load 内 `_loadHistory` 默认值 + 外部显式覆盖）是「显式覆盖不生效」的经典时序坑——整态重建会先清空、后写者决定终态；初始参数应通过签名贯通而非二次调用。

## 已修正的计划漂移（派发时声明）

- 计划测试假设「MissingStubError 被 `on Exception catch` 吞掉」——**错误**，mocktail 的 MissingStubError 是 Error 非 Exception，测试必须全 stub 所有 dio 路径
- 计划 `CostTrendStackedChart(unit: '元')` 的 unit 参数 Task 6 已删
- onFilterChange 内联 days map → 复用已导出 `costHistoryDays` 常量（DRY）
- 契约核实：history URL 实为 `/recipes/{id}/cost-history-range`（非 cost-history，带 queryParameters days/offset_days）；merchant-costs 带 `Options(receiveTimeout: 35s)`；`_loadMerchantPrices` 在 ingredients 空时提前 return（fixture ingredients:[] 免 stub）

## 验证

- TDD 全程红绿：各任务测试先失败（旧行为）后通过；widgets 目录 28/28 → 全量 59/59 全绿（含 provider/repository/组件/页面）
- `flutter analyze`：6 个 issues 全为预先存在（avoid_print/_fmtNum unused/constant_identifier_names/3 个 const info），Task 10-11 文件 0 issues
- `flutter build windows --debug` 通过（25.2s 增量）。⚠️ 首次构建失败 `MSB3073 INSTALL.vcxproj cmake_install` —— 根因是**调试中的 `livecalc_mobile.exe` 占用构建输出文件**（非代码问题），`Stop-Process` 后重建通过。教训：`| tail` 管道会吞 flutter 的退出码（管道返回 tail 的 0），判定构建成败要看 `echo EXIT=$?` 或完整日志
- 手动核对待做（用户环境允许时）：`flutter run -d windows` 对照 web 逐模块核对 8 项（计划 Task 12 Step 4 清单）

## 测试陷阱备忘（后续任务可复用）

- mocktail：MissingStubError **extends Error 非 Exception**，`on Exception catch` 吞不掉；未匹配调用默认返回 null → TypeError 崩溃，**所有被调用路径必须全 stub**（不 stub 的抛 Exception('boom') 即可）
- 全 stub 模式：`when(() => mockClient.dio).thenReturn(mockDio)` + 分类 stub（无参 get / queryParameters / options 命名参数分别匹配 repository 实际调用签名）
- testWidgets 中 loading 测试必须用 `pump()` 不能用 `pumpAndSettle()`（不定动画永不 settle）；mock 全 async 闭包 + microtask 完成，`pump()` + `pump(100ms)` 确定性成立
- Dart SDK ^3.4.0：wildcard 参数 `(_, _)` 不可用（需 3.7+），用 `(_, __)`

## 已统一约定（5 组件 + 页面一致）

标题图标 `theme.colorScheme.tertiary`、标题 FontWeight.bold、空态用 outline（禁硬编码 Colors.grey）、SegmentedButton 包 Flexible 防窄屏溢出、fallback AlertDialog 加 `scrollable: true`、显式循环代替 firstOrNull（避免 collection 依赖）、货币 ¥ 前缀单 Text、fallback IconButton 用 SizedBox(20x20) 包裹防 M3 最小尺寸撑爆、中文注释。

## 关联

- 设计：[SPEC_移动端菜谱分析页对齐web.md](SPEC_移动端菜谱分析页对齐web.md)
- 计划：[PLAN_移动端菜谱分析页对齐web.md](PLAN_移动端菜谱分析页对齐web.md)
