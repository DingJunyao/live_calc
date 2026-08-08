# 移动端分析页筛选按钮与营养溯源优化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development（每任务 implementer → spec 审查 → 质量审查 → 修复循环）。

**Goal:** 处理用户最新 5 项反馈：① 成本趋势范围按钮窄屏挤→改下拉 ② 营养溯源按钮→改折叠按钮 ③ 营养溯源进度条改为与成本占比一致的多色段进度条 + 细项可展开折叠 ④ 成本趋势图表点击无提示 ⑤ 详情页成本估算按钮 RIGHT OVERFLOWED BY 22 PIXELS。

**Design decisions（用户批准）：**
- ② 范围切换：分析页（周/月/季/年/全部）+ 详情页（周/月/季）SegmentedButton → **DropdownButton**（显示当前选中值，宽度自适应根治溢出）。用户原话「在小屏幕上做成下拉」→ 统一改下拉（KISS，不做响应式双形态）
- ③ 顶部切换：NRV 指标/全部 2 段 SegmentedButton → **PopupMenuButton**（child 显示当前选择 + arrow_drop_down 图标，点击弹出菜单）——即用户说的「折叠按钮」
- ③ 进度条：**与成本占比一致的多色段进度条**（高 10、圆角 5、段间 1px surface 色细缝、stretch、段宽 flex = max(1, 占比*1000)、段色 = getIngredientColor）——每段 = 一个食材对该营养素的贡献占比；**布局改单列全宽列表**（用户已确认「单列全宽列表（推荐）」）
- ③ 细项展开折叠：每项卡片 = 标题行（展开箭头 + 名称 + NRV% + 总量）+ 多色段进度条；**点击卡片展开/收起食材明细**（色块 + 名称 + 贡献值+单位 + 百分比，对齐成本占比清单行）；默认折叠
- ④ 图表点击无提示根因（已诊断）：详情页 [cost_trend_chart.dart:124](mobile/lib/features/recipes/widgets/cost_trend_chart.dart#L124) `_Chart` 用 `onPanDown`——快速点击（tap）手势竞技场中 Pan 不获胜，**tap 不触发 tooltip，只有按住拖动才显示** → 补 `onTapDown`；分析页 fl_chart 已有 `touchTooltipData` + `touchSpotThreshold: infinity`（[cost_trend_stacked_chart.dart:232](mobile/lib/features/recipes/widgets/cost_trend_stacked_chart.dart#L232)）→ 测试验证 tap 出 tooltip
- ⑤ 详情页溢出根因（已诊断）：[cost_trend_chart.dart:46](mobile/lib/features/recipes/widgets/cost_trend_chart.dart#L46) `_buildRangeToggle` 3 段 SegmentedButton **无 Flexible 包裹**（对比分析页有）→ 改 DropdownButton 顺带根治
- 约束：feat/mobile-app 分支、中文注释、不做 git 操作、TDD、全量测试 + analyze + build windows 通过

**Files:**
- Modify: `mobile/lib/features/recipes/widgets/cost_trend_chart.dart` + Create 测试（Task 1）
- Modify: `mobile/lib/features/recipes/widgets/cost_trend_stacked_chart.dart` + 测试追加（Task 2）
- Modify: `mobile/lib/features/recipes/widgets/nutrition_source_grid.dart` + 测试更新（Task 3）

---

### Task 1: 详情页 CostTrendChart 按钮改下拉 + tap tooltip

**Files:**
- Modify: `mobile/lib/features/recipes/widgets/cost_trend_chart.dart`（_buildRangeToggle + _Chart GestureDetector）
- Create: `mobile/test/features/recipes/widgets/cost_trend_chart_test.dart`（**目前该文件不存在**，新建）

背景：详情页「成本估算」卡内 `CostTrendChart(points: state.costHistory.map((p) => p.scaled(ratio)).toList(), loading: ..., onRangeChange: (days) => reloadHistory(days))`（[recipe_detail_screen.dart:210](mobile/lib/features/recipes/screens/recipe_detail_screen.dart#L210)）。私有枚举 `enum _Range { week, month, quarter }`（:26）。

- [ ] **Step 1: 新建失败测试** `test/features/recipes/widgets/cost_trend_chart_test.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/cost_trend_chart.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

CostHistoryPoint _point(String date, double avg) => CostHistoryPoint(
    date: date, minCost: avg - 1, maxCost: avg + 1, avgCost: avg);

void main() {
  group('CostTrendChart 范围下拉与点击提示', () {
    testWidgets('范围切换改下拉：选「周」回调 7 天且按钮显示「周」', (tester) async {
      int? got;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: CostTrendChart(
            points: [_point('07-01', 5), _point('07-02', 6), _point('07-03', 7)],
            onRangeChange: (days) => got = days,
          ),
        ),
      ));
      // 默认选中「月」
      expect(find.text('月'), findsOneWidget);
      await tester.tap(find.byKey(const Key('range_dropdown')));
      await tester.pumpAndSettle();
      // 菜单项出现（含按钮上当前值共 4 个文本，用 .last 点菜单里的「周」）
      await tester.tap(find.text('周').last);
      await tester.pumpAndSettle();
      expect(got, 7);
      expect(find.text('周'), findsOneWidget);
      expect(find.text('月'), findsNothing);
    });

    testWidgets('点击图表显示 tooltip（均价+区间），无需拖动', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: CostTrendChart(
            points: [_point('07-01', 5), _point('07-02', 6), _point('07-03', 7)],
          ),
        ),
      ));
      // 点图表中心（_Chart 的 GestureDetector 区域）
      await tester.tapAt(tester.getCenter(find.byType(CustomPaint).first));
      await tester.pump();
      expect(find.textContaining('均价 ¥'), findsOneWidget);
      expect(find.textContaining('区间 ¥'), findsOneWidget);
    });
  });
}
```

注：`DropdownButton<_Range>` 私有枚举不可引用，用 `key: Key('range_dropdown')` 定位；tooltip 文本是 `Text('均价 ¥5.00')`（_Tooltip :190-197，普通 Text 非 RichText，find.textContaining 默认可匹配）。

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_trend_chart_test.dart
```

Expected: 编译失败（`_buildRangeToggle` 还是 SegmentedButton 无 range_dropdown key；tap 无 tooltip——onPanDown 不触发）或断言失败。

- [ ] **Step 3: 改造实现**（`cost_trend_chart.dart`）

① `_buildRangeToggle`（:55-76）SegmentedButton → DropdownButton（**根治 RIGHT OVERFLOWED 22px**：DropdownButton 宽度自适应，无 Fixed 尺寸段撑爆）：

```dart
  Widget _buildRangeToggle() {
    const labels = {'week': '周', 'month': '月', 'quarter': '季'};
    return DropdownButton<_Range>(
      key: const Key('range_dropdown'),
      value: _selected,
      isDense: true,
      underline: const SizedBox.shrink(),
      items: _Range.values
          .map((r) =>
              DropdownMenuItem(value: r, child: Text(labels[r.name]!)))
          .toList(),
      onChanged: (r) {
        if (r == null) return;
        setState(() => _selected = r);
        final days = switch (r) {
          _Range.week => 7,
          _Range.month => 30,
          _Range.quarter => 90,
        };
        widget.onRangeChange?.call(days);
      },
    );
  }
```

调用处 :46 `_buildRangeToggle(theme)` → `_buildRangeToggle()`（签名去 theme，方法体不再用 ThemeData；或保留 theme 参数不传也行——去掉更干净）。

② `_Chart` 的 GestureDetector（:122-128）加 `onTapDown`（tap 也出 tooltip；保留 onPanDown/onPanUpdate 拖动连续浏览、onPanEnd 清空）：

```dart
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          // 快速点击（tap）也要出 tooltip——onPanDown 只在拖动手势竞技场获胜后触发，
          // 单点 tap 永远不触发，用户「点击没提示」的根因
          onTapDown: (d) => _handleTouch(d.localPosition, constraints.biggest),
          onPanDown: (d) => _handleTouch(d.localPosition, constraints.biggest),
          onPanUpdate: (d) =>
              _handleTouch(d.localPosition, constraints.biggest),
          onPanEnd: (_) => onTouch(null),
          child: Stack(...),
        );
```

（Tap 与 Pan 识别器共存：快速 tap → Tap 获胜 onTapDown 触发；拖动 → Pan 获胜。tap 后 tooltip 常驻显示，下次触摸更新/消失——可接受。）

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_trend_chart_test.dart
```

Expected: 2/2 PASS。

- [ ] **Step 5: 汇报**

---

### Task 2: 分析页 CostTrendStackedChart 按钮改下拉 + tap tooltip 验证

**Files:**
- Modify: `mobile/lib/features/recipes/widgets/cost_trend_stacked_chart.dart`（_buildFilterToggle）
- Modify: `mobile/test/features/recipes/widgets/cost_trend_stacked_chart_test.dart`（追加 widget 测试组，现有 6 个纯函数测试不动）

背景：分析页②成本趋势 `Flexible(child: _buildFilterToggle(theme))`（:110）5 段 SegmentedButton 窄屏挤；fl_chart 图已有 `touchTooltipData` + `touchSpotThreshold: double.infinity`（:232-262）——tap 理论上有 tooltip，测试实证。

- [ ] **Step 1: 追加失败测试**（现有文件末尾 main() 内追加 group）

```dart
  group('CostTrendStackedChart 筛选下拉与点击提示', () {
    CostHistoryPoint _p(String date, {List<CostHistoryBreakdownItem> breakdown = const []}) =>
        CostHistoryPoint(
            date: date, minCost: 1, maxCost: 3, avgCost: 2, breakdown: breakdown);

    testWidgets('范围改下拉：选「年」回调 year', (tester) async {
      String? got;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: CostTrendStackedChart(
            points: [
              _p('07-01',
                  breakdown: const [
                    CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 2),
                    CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 3),
                  ]),
              _p('07-02',
                  breakdown: const [
                    CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 4),
                    CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 1),
                  ]),
            ],
            onFilterChange: (f) => got = f,
          ),
        ),
      ));
      // 默认「季」
      expect(find.text('季'), findsOneWidget);
      await tester.tap(find.byKey(const Key('filter_dropdown')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('年').last);
      await tester.pumpAndSettle();
      expect(got, 'year');
      expect(find.text('年'), findsOneWidget);
      expect(find.text('季'), findsNothing);
    });

    testWidgets('点击图表显示 tooltip（食材成本明细）', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: CostTrendStackedChart(
            points: [
              _p('07-01',
                  breakdown: const [
                    CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 2),
                    CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 3),
                  ]),
              _p('07-02',
                  breakdown: const [
                    CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 4),
                    CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 1),
                  ]),
            ],
          ),
        ),
      ));
      // 点 LineChart 区域（Card 内 SizedBox(height:200) 的图表）
      final chartFinder = find.byType(LineChart);
      await tester.tapAt(tester.getCenter(chartFinder));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));
      // fl_chart tooltip 渲染为 RichText/Text.rich → findRichText 兜底
      expect(
          find.textContaining('鸡蛋', findRichText: true).evaluate().isNotEmpty,
          true);
    });
  });
```

注：若 `find.byType(LineChart)` 需要 import `package:fl_chart/fl_chart.dart`；tap 后 tooltip 内容含 `'鸡蛋: ¥2.00\n'`（getTooltipItems :250-253）。若 findRichText 版断言仍红，改用 `find.byType(LineTooltipItem)` 或 `find.textContaining('合计: ¥')` 定位（implementer 现场调整断言目标，以「tooltip 内容出现」为准）。

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_trend_stacked_chart_test.dart
```

Expected: 新测试 FAIL（无 filter_dropdown key / 或 tap 无 tooltip——若 tooltip 测试本来绿，说明点击提示已存在，此项仅验证不修）。

- [ ] **Step 3: 改造实现**（`cost_trend_stacked_chart.dart`）

`_buildFilterToggle`（:124-141）SegmentedButton → DropdownButton：

```dart
  Widget _buildFilterToggle(ThemeData theme) {
    const labels = {'week': '周', 'month': '月', 'quarter': '季', 'year': '年', 'all': '全部'};
    return DropdownButton<String>(
      key: const Key('filter_dropdown'),
      value: _filter,
      isDense: true,
      underline: const SizedBox.shrink(),
      style: theme.textTheme.bodyMedium,
      items: labels.keys
          .map((k) => DropdownMenuItem(value: k, child: Text(labels[k]!)))
          .toList(),
      onChanged: (v) {
        if (v == null) return;
        setState(() => _filter = v);
        widget.onFilterChange?.call(v);
      },
    );
  }
```

调用处 :110 `Flexible(child: _buildFilterToggle(theme))` → 直接 `_buildFilterToggle(theme)`（DropdownButton 自适应宽度，不再需要 Flexible；`Flexible` 包裹也无害，去掉让标题行干净）。若 Step 2 证明 tooltip 本就有（测试绿），不动 fl_chart 配置。

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_trend_stacked_chart_test.dart
```

Expected: 全 PASS（6 既有 + 2 新增）。

- [ ] **Step 5: 汇报**

---

### Task 3: 营养溯源多色段进度条 + 单列列表 + 细项展开折叠

**Files:**
- Modify: `mobile/lib/features/recipes/widgets/nutrition_source_grid.dart`
- Modify: `mobile/test/features/recipes/widgets/nutrition_source_grid_test.dart`

背景：分析页③营养贡献溯源。现有：GridView 2 列 + 每格单色 NRV 达成度条（`_buildBar` :284-311，填充 = nrpPct 达成度、单色 = Top1 食材色）+ SegmentedButton NRV/全部（:166-181）。外层 body 是 SingleChildScrollView（[recipe_analysis_screen.dart:87](mobile/lib/features/recipes/screens/recipe_analysis_screen.dart#L87)），单列 Column 无溢出风险。fixture：蛋白质 items=[鸡蛋6, 番茄1]、nrpPct 10、perServing '6g'；脂肪 nrpPct 7 5g；allNutrients water（nameZh 水分，番茄贡献 80g）。

- [ ] **Step 1: 更新+追加测试**（`nutrition_source_grid_test.dart`）

现有 group「NutritionSourceGrid 迷你进度条」的 widget 测试（:88-113）改造：

```dart
  group('NutritionSourceGrid 多色进度条', () {
    testWidgets('标题行显示 NRV% 与总量，进度条首段 = Top1 食材色', (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: NutritionSourceGrid(nutrition: _nutrition())),
      ));
      // 蛋白质 NRV 10%（移到标题行，带 NRV 前缀）
      expect(find.text('NRV 10%'), findsOneWidget);
      expect(find.text('蛋白质'), findsOneWidget);
      // 总量文本（perServing protein value 6g，标题行右侧）
      expect(find.text('6g'), findsOneWidget);
      // 多色段进度条存在，首段 = Top1 贡献食材（鸡蛋 id 1）色
      expect(find.byKey(const Key('nrv_bar')), findsWidgets);
      final firstSegment = tester.widget<ColoredBox>(find
          .descendant(
              of: find.byKey(const Key('nrv_bar')).first,
              matching: find.byType(ColoredBox))
          .first);
      expect(firstSegment.color, getIngredientColor(1));
    });

    testWidgets('进度条多段 = 各食材贡献比例（鸡蛋+番茄两段色）', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: NutritionSourceGrid(nutrition: _nutrition())),
      ));
      final bar = find.byKey(const Key('nrv_bar')).first;
      final segments = tester
          .widgetList<ColoredBox>(find.descendant(
              of: bar, matching: find.byType(ColoredBox)))
          .toList();
      // 蛋白质 items=[鸡蛋6, 番茄1] → 两段，色 = 各自 getIngredientColor
      expect(segments.length, 2);
      expect(segments[0].color, getIngredientColor(1));
      expect(segments[1].color, getIngredientColor(2));
    });

    testWidgets('点击项目展开食材明细，再点收起', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: NutritionSourceGrid(nutrition: _nutrition())),
      ));
      // 默认折叠：明细不可见
      expect(find.text('85.7%'), findsNothing); // 鸡蛋 6/7
      // 点蛋白质项展开
      await tester.tap(find.text('蛋白质'));
      await tester.pump();
      expect(find.text('85.7%'), findsOneWidget);
      expect(find.text('14.3%'), findsOneWidget); // 番茄 1/7
      expect(find.text('鸡蛋'), findsOneWidget);
      expect(find.text('番茄'), findsOneWidget);
      // 再点收起
      await tester.tap(find.text('蛋白质'));
      await tester.pump();
      expect(find.text('85.7%'), findsNothing);
    });

    testWidgets('顶部切换改折叠按钮：选「全部」出现水分项', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: NutritionSourceGrid(nutrition: _nutrition())),
      ));
      // 折叠按钮显示当前「NRV 指标」
      expect(find.text('NRV 指标'), findsOneWidget);
      expect(find.text('水分'), findsNothing);
      await tester.tap(find.byKey(const Key('show_all_menu')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('全部').last);
      await tester.pumpAndSettle();
      expect(find.text('水分'), findsOneWidget); // showAll=true 出现（nameZh 兜底）
      expect(find.text('NRV 指标'), findsNothing);
    });
  });
```

注：明细百分比与成本占比 `_pct` 一致（1 位小数：6/7=85.7%、1/7=14.3%）；展开明细行 '鸡蛋' 文本与进度条下方名称可能同现——fixture 里「蛋白质」项展开后明细含 '鸡蛋'（findsOneWidget：明细行唯一）；「水分」项在 showAll=false 时不存在（nrvKeys 不含 'water'）。

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/nutrition_source_grid_test.dart
```

Expected: 新断言 FAIL（无 'NRV 10%' 文本——旧实现 '10%'；无 show_all_menu key；多段色不符）。

- [ ] **Step 3: 改造实现**（`nutrition_source_grid.dart`，`buildNutrientDisplays`/`sortIndex`/`nrvKeys`/`nrvLabels` 纯函数基本不动，只给 contributor 加 unit）

① `NutrientContributor` 加 unit（明细行显示贡献值单位）：

```dart
class NutrientContributor {
  final String name;
  final double value;
  final String unit;
  final Color color;
  const NutrientContributor({
    required this.name,
    required this.value,
    this.unit = '',
    required this.color,
  });
}
```

`buildNutrientDisplays` :97-101 构造处补 `unit: c.unit`。

② 顶部切换 SegmentedButton（:165-181）→ PopupMenuButton（「折叠按钮」：child 显示当前选择 + 下拉箭头）：

```dart
              PopupMenuButton<bool>(
                key: const Key('show_all_menu'),
                initialValue: _showAll,
                tooltip: '显示范围',
                onSelected: (v) => setState(() => _showAll = v),
                itemBuilder: (context) => const [
                  PopupMenuItem(value: false, child: Text('NRV 指标')),
                  PopupMenuItem(value: true, child: Text('全部')),
                ],
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(_showAll ? '全部' : 'NRV 指标',
                      style: theme.textTheme.bodyMedium),
                  Icon(Icons.arrow_drop_down,
                      size: 20, color: theme.colorScheme.outline),
                ]),
              ),
```

（删掉 Flexible 包裹——PopupMenuButton 自适应宽度；标题行 :163-181 的 `Spacer` + 该按钮结构保留。）

③ GridView 2 列（:224-233）→ 单列 Column；`_buildProgressCard`（:237-281）重写为 `_buildItem`；`_buildBar`（:284-311）重写为多色段；新增 `_buildDetailList`。展开状态：

```dart
class _NutritionSourceGridState extends State<NutritionSourceGrid> {
  bool _showAll = false;
  final Set<String> _expanded = {};
```

④ `_buildGrid` → `_buildList`（单列，保留空态）：

```dart
  Widget _buildList(ThemeData theme) {
    final displays =
        buildNutrientDisplays(widget.nutrition!, showAll: _showAll);
    if (displays.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
            child: Text('暂无营养数据',
                style: TextStyle(color: theme.colorScheme.outline))),
      );
    }
    return Column(
      children: [for (final d in displays) _buildItem(theme, d)],
    );
  }
```

⑤ 每项卡片（标题行 + 多色段进度条 + 条件明细）：

```dart
  /// 单列卡片：标题行（箭头+名称+NRV%+总量）+ 多色段进度条 +（展开）食材明细。
  Widget _buildItem(ThemeData theme, NutrientDisplay d) {
    final expanded = _expanded.contains(d.key);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest
            .withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(8),
      ),
      child: InkWell(
        onTap: () => setState(() {
          if (expanded) {
            _expanded.remove(d.key);
          } else {
            _expanded.add(d.key);
          }
        }),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(expanded ? Icons.expand_less : Icons.expand_more,
                    size: 18, color: theme.colorScheme.outline),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(d.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge
                          ?.copyWith(fontWeight: FontWeight.w600)),
                ),
                if (d.nrpPct != null) ...[
                  Text('NRV ${d.nrpPct}%',
                      style: theme.textTheme.labelSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(width: 8),
                ],
                Text(d.totalText,
                    style: theme.textTheme.labelMedium
                        ?.copyWith(fontWeight: FontWeight.w600)),
              ]),
              const SizedBox(height: 8),
              _buildBar(theme, d),
              if (expanded) ...[
                const SizedBox(height: 8),
                _buildDetailList(theme, d),
              ],
            ],
          ),
        ),
      ),
    );
  }
```

⑥ 多色段进度条（对齐成本占比 _buildBar 同构，段色 = 各食材 getIngredientColor）：

```dart
  /// 多色段进度条：段宽 = 食材贡献占比（对齐成本占比样式），
  /// 段间 1px surface 色细缝，stretch 撑满高度。
  Widget _buildBar(ThemeData theme, NutrientDisplay d) {
    final total = d.items.fold<double>(0, (s, c) => s + c.value);
    return ClipRRect(
      key: const Key('nrv_bar'),
      borderRadius: BorderRadius.circular(5),
      child: SizedBox(
        height: 10,
        width: double.infinity,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < d.items.length; i++) ...[
              if (i > 0) Container(width: 1, color: theme.colorScheme.surface),
              Expanded(
                // 段宽 = 占比（无上界）；下界 1：零值段保留细缝
                flex: max(1, (d.items[i].value / total * 1000).round()),
                child: ColoredBox(color: d.items[i].color),
              ),
            ],
          ],
        ),
      ),
    );
  }
```

（`total` 恒 > 0：buildNutrientDisplays 过滤 `c.value > 0` 且 `contributors.isEmpty` 时 continue。）

⑦ 食材明细（对齐成本占比清单行：色块 + 名称 + 贡献值+单位 + 百分比）：

```dart
  /// 食材贡献明细：色块 + 名称 + 贡献值（含单位）+ 占比（对齐成本占比清单行）。
  Widget _buildDetailList(ThemeData theme, NutrientDisplay d) {
    final total = d.items.fold<double>(0, (s, c) => s + c.value);
    return Column(
      children: [
        for (final c in d.items)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                    color: c.color, borderRadius: BorderRadius.circular(3)),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(c.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodyMedium),
              ),
              Text('${_fmt(c.value)}${c.unit}',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(width: 12),
              SizedBox(
                width: 48,
                child: Text(_pct(c.value, total),
                    textAlign: TextAlign.right,
                    style: theme.textTheme.bodySmall
                        ?.copyWith(color: theme.colorScheme.outline)),
              ),
            ]),
          ),
      ],
    );
  }

  String _pct(double value, double total) {
    if (total <= 0) return '';
    final pct = value / total * 100;
    return '${pct.toStringAsFixed(pct >= 100 ? 0 : 1)}%';
  }
```

（`_fmt` 文件内已有 :130-132；_buildGrid 引用改 _buildList，删掉 GridView 相关代码。）

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/nutrition_source_grid_test.dart
```

Expected: 4 纯函数 + 4 widget 全 PASS。

- [ ] **Step 5: 汇报**

---

### Task 4: 整体验证

- [ ] **Step 1: 全量测试 + 静态分析**

```bash
cd d:/code/live_calc/mobile && flutter test && flutter analyze lib/features/recipes/widgets/cost_trend_chart.dart lib/features/recipes/widgets/cost_trend_stacked_chart.dart lib/features/recipes/widgets/nutrition_source_grid.dart
```

Expected: 全量全绿（63 + 新增）；analyze 无新增（6 个历史遗留除外）。

- [ ] **Step 2: 桌面构建**

```bash
cd d:/code/live_calc/mobile && flutter build windows --debug
```

⚠️ 若失败 MSB3073 cmake_install：先查 `Get-Process livecalc_mobile`（调试进程占用），杀掉重建。判定构建成败用 `echo EXIT=$?`（`| tail` 会吞退出码）。

- [ ] **Step 3: 记录要点**（cc/ 记录 + CLAUDE.md 最新修复记录，保留 10 条）
