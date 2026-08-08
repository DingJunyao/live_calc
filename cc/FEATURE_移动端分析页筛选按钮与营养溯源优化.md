# 移动端分析页筛选按钮与营养溯源优化

> 2026-08-08 完成（feat/mobile-app 分支）。用户 5 项反馈：①详情页成本估算调整范围按钮 RIGHT OVERFLOWED 22px ②分析页成本趋势调整范围按钮小屏拥挤 ③营养溯源顶部按钮同样 ④营养贡献溯源进度条样式应与食材成本占比一致、且细项需可展开折叠（AskUserQuestion 确认单列全宽列表）⑤成本趋势图表点击无提示。Subagent-Driven 三任务 + 双审查（spec → 质量 → 修复循环）。TDD 77/77 全绿（26 新增）+ analyze 3 改动文件 0 新增 + build windows 通过（36.5s）。

## 改动

### Task 1：详情页 CostTrendChart 按钮改下拉 + tap tooltip（[cost_trend_chart.dart](mobile/lib/features/recipes/widgets/cost_trend_chart.dart)）
- :55-75 `_buildRangeToggle`：SegmentedButton → `DropdownButton<_Range>`（`key: Key('range_dropdown')`、isDense、underline 空、labels 周/月/季、onChanged null 守卫 + `widget.onRangeChange?.call(days)`）——根治 RIGHT OVERFLOWED 22px（窄屏 3 段按钮挤爆，下拉自适应宽度）
- :124-135 `_Chart` GestureDetector 加 `onTapDown: (d) => _handleTouch(d.localPosition, constraints.biggest)`（tap 不清空 tooltip，驻留到下次触摸，对齐 web 点击选中语义）

### Task 2：分析页 CostTrendStackedChart 按钮改下拉 + tooltip 全链路重建（[cost_trend_stacked_chart.dart](mobile/lib/features/recipes/widgets/cost_trend_stacked_chart.dart)）
- `_buildFilterToggle`（:208-225）：SegmentedButton → `DropdownButton<String>`（`key: Key('filter_dropdown')`、5 选项、onChanged null 守卫）；调用处去 Flexible
- **tooltip 全链路重建（绕 fl_chart 1.2.0 竞技场缺陷）**：`handleBuiltInTouches: false` + Listener `_onPointerGlobal` + `RenderLineChart.getResponseAtLocation`（公开 API，按距离升序返回 spots）→ `_applySpots`（y 降序对齐内置 `_handleBuiltInTouch`）→ showingTooltipIndicators 驱动绘制；MouseRegion.onExit 清 tooltip（Listener 无 onPointerExit）；onPointerMove 加 `e.kind == PointerDeviceKind.mouse`（触屏拖滚不追）；didUpdateWidget 重置 _tooltipSpots
- `buildStackedTooltipItems` 纯函数（1 spot 1 item 契约）：
  - **锚点**：`final dayIndex = touchedSpots.first.x.toInt();` 必须在 barIndex 排序**之前**（touchedSpots 距离升序，first = 距触点最近 = 触点天；`sorted.first` 是 barIndex=0 底部线 ≠ 锚点——混日场景两者不同天）
  - **逆推与合计统一用 `spot.bar.spots[dayIndex].y`**（每条线独立取最近 spot 会跳 i±1 天 → 逆推负成本、Σ明细≠合计；LineBarSpot 持 bar 引用、spots 同长）
  - 日期并入首条 text（bold）、合计并入末条 children；文档注释注明调用约束
- 回退图（:360-440）：补 `touchSpotThreshold: double.infinity`（默认 10px 会过滤远线）+ getTooltipItems 1 spot 1 item（日期行 bold，均价/区间 plain）

### Task 3：营养溯源多色段进度条 + 单列列表 + 细项展开折叠（[nutrition_source_grid.dart](mobile/lib/features/recipes/widgets/nutrition_source_grid.dart)）
- 顶部 SegmentedButton（Flexible 包裹）→ `PopupMenuButton<bool>`（折叠按钮：`key: Key('show_all_menu')`、child 显当前选择 + arrow_drop_down、itemBuilder「NRV 指标」false/「全部」true）；删 Flexible
- GridView 2 列 → 单列 Column：每营养素一张卡片（`_buildItem`：展开箭头 expand_less/more + 名称 ellipsis + `NRV x%` + 总量 w600；InkWell 点击切换 `_expanded` Set<String>（按 d.key），展开时渲染明细）；state 加 `final Set<String> _expanded = {}`
- `_buildBar` 多色段进度条（对齐 cost_proportion_chart 同构）：ClipRRect 圆角 5 + 高 10 占满宽 + Row `CrossAxisAlignment.stretch` + 段间 1px surface 细缝 + `flex: max(1, (value/total*1000).round())` 仅保下界 + 段色 = 各食材 getIngredientColor；删旧单色 NRV 达成度条
- `_buildDetailList` 明细：色块 10x10 圆角 3 + 名称 ellipsis + `_fmt(value)+unit` w600 + `_pct(value,total)` 右对齐宽 48（1 位小数 ≥100 取整）；`NutrientContributor` 加 `unit` 字段（默认 ''），buildNutrientDisplays 构造处补 `unit: c.unit`；`topContributors` 字段保留不再渲染
- 质量审查收尾：抽 `_contribTotal(List<NutrientContributor>)` 消除两处重复 fold；补 flex 宽度断言（两段宽比 5.993 ≈ 6:1，钉「多段按占比」语义）+ 空 items 不变式测试（fiber 无贡献被 continue 过滤）

## 审查抓到的真问题（全修）

1. **fl_chart 1.2.0 竞技场吞 tap（用户反馈④真根因）**：RenderBaseChart 先注册 longPress 再注册 tap（render_base_chart.dart:139-144），LongPressGestureRecognizer.acceptGesture 空实现自注「may happen from a sweep」（long_press.dart:875-879）→ sweep 盲取 members.first → 移动端 tap 被 reject → FlTapCancelEvent(null 位置) → line_chart.dart:135-143 清空 tooltip → 真实用户 tap 点不出 tooltip。onTapDown 也走竞技场必被吞，GestureDetector 方案不可行；必须 `handleBuiltInTouches: false`（touchCallback 为 null 时 recognizers 不启动）绕开
2. **fl_chart tooltip 契约 throw**：painter 强校验 `tooltipItems.length == showingSpots.length` 否则 `throw Exception('tooltipItems and touchedSpots size should be same')`（line_chart_painter.dart:1096-1098）→ 1 spot 1 item，多行文本用 text + children 合并；回退图 getTooltipItems 3 条 vs 单线图 1 spot → P1 崩溃，spec 复审抓出
3. **混日 bug（质量审查抓）**：每条线独立取最近 spot 可能不同天 → 90 天视图相邻天 ~3-4px，远线跳到 i±1 天 → 逆推负成本、Σ明细≠合计 → 统一 `spot.bar.spots[dayIndex]`；测试红→绿精确复现（旧实现 15-2=13）
4. **锚点错误（复审抓，1 行）**：`dayIndex = sorted.first.x`（barIndex 0 底部线）≠ 触点锚点 `touchedSpots.first` → 移到排序前 + 锚点反例测试（[tomatoSpot(x=0), eggSpot(x=1)]：旧实现取 day1 出 '鸡蛋: ¥10.00'，修复后 '鸡蛋: ¥2.00'）守住
5. **测试数段把细缝算进去（规格自身矛盾）**：段间 1px 细缝 `Container(color: surface)` 内部也是 ColoredBox → `find.byType(ColoredBox)` 数到 3 个。修复测试按 `w.color != theme.colorScheme.surface` 排除（M3 light surface #FEF7FF 不在 16 色食材色板中，无撞色风险；过滤读主题实际色，主题变更鲁棒）

## 验证

- TDD 红→绿：Task 1 测试先 FAIL（无 range_dropdown key）→ 2/2；Task 2 15/15（含混日/锚点反例）；Task 3 9/9（含宽度断言 5.993、fiber 过滤）
- 全量 **77/77** 全绿（26 新增），analyze 三个改动文件 No issues found（全量 7 个历史遗留不在改动文件内）
- `flutter build windows --debug` 通过（36.5s，构建前先杀 livecalc_mobile PID 8764 调试进程占用，避免 MSB3073；判定用 `echo EXIT=$LASTEXITCODE` 不用管道）

## 经验

- **fl_chart tap 失效先查版本级缺陷**：竞技场 recognizer 注册顺序问题（longPress sweep 吞 tap）是 1.2.0 已知坑，绕开需 `handleBuiltInTouches: false` + Listener + `getResponseAtLocation`（公开 API）+ `chartRendererKey`（GlobalKey + findRenderObject 是文档认可模式）
- **fl_chart tooltip 契约是硬校验**：`tooltipItems.length == showingSpots.length` 否则 throw——先算 spots 再按 spots 数构造 items，绝不能反向
- **touchedSpots 锚点 = 距离升序 first**：不是 barIndex 排序后的 first（那是底部线）；与排序顺序无关的锚点逻辑必须放在排序前
- **tap 后 pump(200ms)**：默认 150ms 动画走完才读到 showingTooltipIndicators
- **细缝也是 widget**：Container(width:1) 内部渲染 ColoredBox，`find.byType` 计数会把布局辅助元素算进去——按颜色/类型排除或用测试专用 key

## 关联

- 计划：[PLAN_移动端分析页筛选按钮与营养溯源优化.md](PLAN_移动端分析页筛选按钮与营养溯源优化.md)
- 前序：移动端菜谱分析页对齐 web（[FEATURE_移动端菜谱分析页对齐web.md](FEATURE_移动端菜谱分析页对齐web.md)）——本特性为其②③模块的移动端 UI 迭代；多色段进度条样式继承自 [FEATURE_移动端饼图改进度条.md](FEATURE_移动端饼图改进度条.md)
