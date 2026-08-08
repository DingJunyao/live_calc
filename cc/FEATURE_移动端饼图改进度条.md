# 移动端饼图改进度条（分析页 ① 成本占比 + ③ 营养溯源）

> 2026-08-08 完成（feat/mobile-app 分支）。用户反馈分析页饼图在手机上「显示非常差、色块图像割裂严重、太占空间」→ 设计确认（AskUserQuestion：范围=成本占比+营养溯源迷你图；呈现=进度条+下方清单）→ Subagent-Driven 两任务（Task A/B）+ 双审查。TDD 63/63 全绿 + analyze 0 新增 + build windows 通过。

## 改动

### Task A：成本占比环形饼图 → 彩色进度条（[cost_proportion_chart.dart](mobile/lib/features/recipes/widgets/cost_proportion_chart.dart)）
- 删 fl_chart import；图标 pie_chart_outline → bar_chart_outlined；加载/空态高度 220 → 140
- 标题行右侧总价（原圆环中心金额，加载/空态不闪 ¥0.00：`hasData && total > 0` 守卫）
- **进度条**：高 10px、ClipRRect 圆角 5、占满宽度、`key: Key('cost_bar')`；每段 `Expanded(flex: max(1, (value*1000).round()))` 宽=占比；段色 `getIngredientColor(ingredientId)`（同食材全图表同色）；段间 1px surface 色细缝防割裂；段 GestureDetector 点击设 `_touchedIndex`
- **下方清单**：每行 `key: Key('cost_row_$i')` 色块 10x10 圆角 + 名称 ellipsis + ¥xx.xx(w600) + 百分比右对齐固定宽 48；点击行高亮（背景 `color.withValues(alpha: 0.2)`）；降序由 `buildCostProportionItems` 承担（>6 前5+「其他」逻辑原样保留）
- 调用方 [recipe_analysis_screen.dart:93](mobile/lib/features/recipes/screens/recipe_analysis_screen.dart#L93) 构造参数不变，零兼容影响

### Task B：营养溯源迷你环形图 → 迷你进度条（[nutrition_source_grid.dart](mobile/lib/features/recipes/widgets/nutrition_source_grid.dart)）
- 删 fl_chart import；`_buildDonutCard` → `_buildProgressCard`
- 每格：标题行居中 `[营养素名 Flexible ellipsis + 4px + '${nrpPct}%' labelSmall bold]`（中心 NRV% 上移，null 不显示 %）→ 迷你进度条（高 6、圆角 3、`key: Key('nrv_bar')`）→ totalText → topContributors（Top2 文案保留）
- **进度条填充比例 = NRV 达成度**（`(nrpPct ?? 0).clamp(0,100)/100`），**填充色 = Top1 贡献食材的 getIngredientColor**（`items.first.color`，items 空回退 theme.colorScheme.primary），未填充 outlineVariant
- GridView childAspectRatio 0.95 → 1.2（donut 90px 高区被 6px 进度条替代，内容 ~92px；390dp 宽格高 ~142px，居中不溢出——测试强制在 390x844 手机尺寸验证）
- 纯函数 buildNutrientDisplays/sortIndex/nrvKeys/nrvLabels、NRV/全部切换、loading/空态原样

## Spec 审查抓到的关键问题（Task A，全修）

1. **进度条 0 高不可见（核心）**：`Row` 默认 `crossAxisAlignment.center` → flex 子项约束 minHeight 0 → `ColoredBox` 无子取 `constraints.smallest` = 高 0 → `_RenderColoredBox.paint` 还跳过 size==zero 绘制 → **整条进度条只剩 1px 细缝**（探针实测段 `Size(506.0, 0.0)`）。修复：进度条 Row 加 `crossAxisAlignment: CrossAxisAlignment.stretch`。→ 计划 Task B 同构片段预警，implementer 照修正版实现未复现
2. **flex 上界 clamp(1, 100000) 规格偏差**：单段 ≥¥100 时宽度被压平失真（[150,40,20] 画成 62.5%/25%/12.5% 而非 71.4%/19%/9.5%）；「防 flex:0 崩溃」理由不成立（SDK flex 布局 flex==0 走非弹性路径不崩）。修复：`max(1, (value*1000).round())` 仅保下界（零成本段保留可点细缝），去上界
3. **tap 测试假绿**：原测试只断言「点击不崩+行在」，检测不出 0 高段的死点击。修复：tap 进度条段后断言 `cost_row_0` 行 Container decoration color == `getIngredientColor(1).withValues(alpha: 0.2)`（且 row_1 为 null）+ 新增「点击清单行高亮」测试——真断言通过即证明段可见可点

## 验证

- TDD 红→绿：Task A 追加 2 测试先 FAIL（无 cost_bar key）→ 修复后 8/8；Task B 追加 1 测试先 FAIL（无 nrv_bar key）→ 5/5；全量 **63/63**（62 既有 + 1 净增）
- `flutter analyze`：6 个 issue 全为历史遗留（avoid_print/_fmtNum unused/constant_identifier_names/3×const），改动文件 0 新增
- `flutter build windows --debug` 通过（构建前先查 livecalc_mobile 调试进程占用，无则直接跑）

## 经验

- **Row + Expanded(flex) + ColoredBox 的 0 高陷阱**：无子 render 对象在交叉轴松约束下取最小尺寸 0，paint 又跳过 zero size → 不可见不可点。凡「Row 内 flex 撑满高度」必须 `crossAxisAlignment: CrossAxisAlignment.stretch`（或包 SizedBox.expand）。测试必须真断言渲染结果（尺寸/颜色/高亮），不能只断言「存在」——0 高时 find.byKey 照样命中
- 计划里的代码片段也可能有 bug（本计划 Task B 片段就漏 stretch）——spec 审查的探针实测（临时 widget 测试量渲染尺寸）是抓这类问题的有效手段

## 关联

- 计划：[PLAN_移动端饼图改进度条.md](PLAN_移动端饼图改进度条.md)
- 前序：移动端菜谱分析页对齐 web 端（[FEATURE_移动端菜谱分析页对齐web.md](FEATURE_移动端菜谱分析页对齐web.md)）——本特性为其 ①③ 模块的移动端 UI 迭代，②④⑤ 不变
