# SPEC：移动端菜谱分析页对齐 web

> 日期：2026-08-07
> 分支：feat/mobile-app
> 状态：已获用户确认（图表方案 fl_chart、五模块完整对齐）

## 背景与目标

移动端（Flutter）菜谱详情页的「分析」页与 web 端（Vue）分析页在页面名称、布局、功能上完全不同：

- 移动端页面标题叫「成本分析」，实际还包含营养信息，名不副实
- web 端有 5 个分析模块，移动端只有「成本分布条形列表 + 4 项核心营养图标」两块，且布局完全不同

目标：移动端分析页全面对齐 web 端 [RecipeAnalysisView.vue](frontend/src/views/recipes/RecipeAnalysisView.vue) 的布局与功能，体验一致（CLAUDE.md「各端体验一致性」硬要求）。

## Web 端 5 个模块（参照物）

1. **成本占比** `CostProportionChart.vue` — 环形饼图：食材成本占比，中心显示总价，按成本降序，前 5 + 其余合并为「其他」，扇区标签=名称+¥价+百分比，颜色按 `getIngredientColor(ingredient_id)`（16 色板 hash）
2. **成本趋势** `CostTrendAnalysis.vue` — 筛选周/月/季/年/全部（默认季=90 天），**堆叠面积图**（每食材一条堆叠线，半透明面积），右侧食材标签列表点击高亮（非高亮透明度 0.15）；无 breakdown 数据时回退 avg/min/max 折线+区间图
3. **营养贡献溯源** `NutritionSourceGrid.vue` — NRV 指标/全部切换（默认 NRV），每营养素一张迷你环形图（中心 NRV%）：总量 + Top2 贡献食材（`名称 占比% · 名称 占比%`）；17 项 NRV_KEYS、营养素排序常量、同名去重均需对齐
4. **按商家预估成本** `MerchantCostCards.vue` — 横向滚动卡片：商家名 + 「最实惠 ✓」徽章（is_recommended）+ 覆盖 `covered_count/total_ingredients` 种食材 + 总价（h5 加粗）+ 本店价/外部价 + 需外购清单（missing_ingredients）；fallback_chains 有则显示信息图标（悬浮提示）
5. **商家比价推荐** `MerchantPriceMatrix.vue` — 横向滚动矩阵表：行=食材（名称+用量 badge+fallback 信息图标），列=商家；单元格**优先显示 total_cost 预估总价、回退 price 单价**，`is_lowest` 橙色加粗高亮，无价格显示灰色「—」；首列 sticky

## 设计决策（已确认）

| 决策点 | 结论 |
|---|---|
| 图表方案 | 引入 **fl_chart**（最新稳定版） |
| 对齐范围 | **五模块完整对齐**（方案 A） |
| 页面标题 | 菜谱名 + 「分析」chip（对齐 web `{{ recipe?.name }} + 分析 chip`） |

## 改动清单

### 1. 依赖
- [mobile/pubspec.yaml](mobile/pubspec.yaml) 增加 `fl_chart`，`flutter pub get`

### 2. 数据层 [recipe_repository.dart](mobile/lib/features/recipes/repositories/recipe_repository.dart)
- 新增 `getRecipeMerchantCosts(int id)` → `GET /recipes/{id}/merchant-costs` → 返回 `RecipeMerchantCost`（模型已定义，缺方法）
- 新增 `getIngredientMerchantPrice(int ingredientId, {double? quantity, String? quantityUnit})` → `GET /nutrition/ingredients/{id}/latest-price-by-merchant?quantity=&quantity_unit=` → 返回 `List<MerchantPriceRecord>`（模型已定义）
- 补 `MerchantPriceItem.fromJson`（字段已定义、缺工厂）：`recipeIngredientId / ingredientId / ingredientName / prices / unit / qtyDisplay / fallbackChain`
- 复用已有 `resolveIngredientQuantity`（web `getEffectiveQuantity` 的移植，含「适量→100g / 少许→5g」模糊量回退）
- 商家比价并发控制对齐 web：每批 3 个请求 + 全局 35s 超时，超时保留已有部分结果

### 3. 新工具 [ingredient_colors.dart](mobile/lib/features/recipes/utils/ingredient_colors.dart)
- 移植 web [ingredientColors.ts](frontend/src/utils/ingredientColors.ts)：16 色板 `['#ff9800','#4caf50','#2196f3','#9c27b0','#f44336','#00bcd4','#ff5722','#607d8b','#e91e63','#3f51b5','#009688','#795548','#cddc39','#ffc107','#03a9f4','#8bc34a']` + `ingredientId.abs() % 16` 取色，null/无效 → `#e0e0e0`
- 保证同食材在成本占比、成本趋势、营养溯源三张图中同色

### 4. Provider [recipe_provider.dart](mobile/lib/features/recipes/providers/recipe_provider.dart)
- `RecipeDetailPageState` 增加字段：`merchantCosts`（RecipeMerchantCost?）、`merchantPrices`（List<MerchantPriceItem>）、`loadingMerchantCosts`、`loadingMerchantPrices`
- `RecipeDetailPageNotifier` 增加 `_loadMerchantCosts()` / `_loadMerchantPrices()`，异常捕获不阻断（对齐 web catch 忽略）

### 5. 新组件（[widgets/](mobile/lib/features/recipes/widgets/) 下 5 个文件）
- **cost_proportion_chart.dart**：fl_chart `PieChart` 环形（inner radius 约 40%/70%），Stack 中心显示总价 `¥xx.xx`；降序前 5 + 「其他」合并；扇区标题=名称+百分比（移动端空间有限，金额不放在扇区标签，由中心总价体现）；点击扇区弹出该食材成本明细（名称+¥金额+百分比，对齐 web tooltip 的信息量）
- **cost_trend_stacked_chart.dart**：fl_chart `LineChart`，每食材一条线，**手动累加 y 实现堆叠** + 半透明 fill（对齐 echarts stack:'total' 视觉）；筛选 SegmentedButton 周/月/季/年/全部（默认季，天数为 7/30/90/365/3650）；食材标签 Wrap 点击高亮/再点取消（非高亮 alpha 0.15、高亮线宽加粗）；无 breakdown 回退 avg/min/max 折线区间（对齐 web 同款回退逻辑）；注：分析页无份数调节，数据为原始口径（web 分析页也未传 servingRatio）
- **nutrition_source_grid.dart**：GridView 2 列迷你 `PieChart` 环形（中心 NRV%）；卡=营养素名 + 环形 + 总量 `xx.x unit` + Top2 贡献 `名称 占比% · 名称 占比%`；SegmentedButton「NRV 指标/全部」切换；17 项 NRV_KEYS（energy/protein/fat/carbohydrate/fiber/calcium/iron/sodium/potassium/vitamin_a_rae/vitamin_c/vitamin_b1/vitamin_b2/vitamin_b12/vitamin_d/vitamin_e/vitamin_k）与 NRV_LABELS 中文名、营养排序（能量→蛋白质→脂肪→碳水化合物→钠→膳食纤维→钙→铁→钾→维生素A/B1/B2/B12/C/D/E/K）、同名去重均对齐 web 常量
- **merchant_cost_cards.dart**：横向滚动 `ListView`，卡片=商家名+最实惠徽章+覆盖 x/y+总价 h5+本店/外部价+需外购（缺失项 join「、」）；fallback 信息图标点开弹层显示链
- **merchant_price_matrix.dart**：横向滚动 `DataTable`/自绘表格：行=食材（名称+用量+fallback 图标），列=商家名；单元格 total_cost 优先/price 回退、is_lowest 橙色加粗、缺失灰色「—」

### 6. 分析页重写 [recipe_analysis_screen.dart](mobile/lib/features/recipes/screens/recipe_analysis_screen.dart)
- 模块顺序对齐 web：①成本占比 → ②成本趋势 → ③营养溯源 → ④商家成本卡片 → ⑤商家比价矩阵
- AppBar：`Row(菜谱名溢出省略, 「分析」chip)`；进入时 `load()`（已有逻辑会带出 cost/nutrition/history + 新增 merchant 两路）
- 各模块独立 loading / 空态文案对齐 web：「暂无成本数据」「暂无成本趋势数据」「暂无营养数据」「暂无商家价格数据」「暂无比价数据」

### 7. 详情页微调 [recipe_detail_screen.dart](mobile/lib/features/recipes/screens/recipe_detail_screen.dart)
- 分析入口 icon tooltip：「成本分析」→「菜谱分析」

## 不做的事（YAGNI）
- 不改后端（接口全部存在：`/recipes/{id}/merchant-costs`、`/nutrition/ingredients/{id}/latest-price-by-merchant`）
- 不动 web 端任何代码
- 分析页不加 web 没有的功能（如导出、分享）

## 验证
1. `flutter analyze` 无新增告警
2. `flutter build windows --debug` 构建通过
3. 桌面端运行，对照 web 端逐模块核对：5 模块齐全、顺序一致、空态/loading 文案一致、同食材同色、商家比价与 web 数值一致
4. 数据存在性：用有成本/营养/商家数据的菜谱验证；无数据菜谱验证空态

## 参考
- Web 分析页：[RecipeAnalysisView.vue](frontend/src/views/recipes/RecipeAnalysisView.vue)（5 模块组装）
- Web 组件：CostProportionChart / CostTrendAnalysis / NutritionSourceGrid / MerchantCostCards / MerchantPriceMatrix（均在 [components/recipes/](frontend/src/components/recipes/)）
- 移动端现有：详情页 [recipe_detail_screen.dart](mobile/lib/features/recipes/screens/recipe_detail_screen.dart)（已有成本估算+趋势简版）、趋势图 [cost_trend_chart.dart](mobile/lib/features/recipes/widgets/cost_trend_chart.dart)（手写 CustomPaint，保留不动）
