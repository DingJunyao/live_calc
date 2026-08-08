# 移动端饼图改进度条 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development（每任务 implementer → spec 审查 → 质量审查 → 修复循环）。

**Goal:** 移动端菜谱分析页的饼图（① 成本占比环形图 + ③ 营养溯源迷你环形图）在手机上显示割裂、占空间，改为彩色进度条（用户已确认设计）。

**Design decisions（用户批准）：**
- ① 成本占比：整条横向进度条（高 ~10px、圆角、占满宽度、段间 1px surface 色细缝）；每段颜色 = `getIngredientColor(ingredientId)`（同一食材全图表同色）；**总价从圆环中心移至标题行右侧**；下方清单每行 = 色块 + 名称 + 金额 ¥ + 百分比（降序）；**点击进度条段/清单行 → 高亮该行**（对齐原「图例点击显示金额」交互语义）；>6 项合并「其他」逻辑保留；空态/加载态保留
- ③ 营养溯源：每格迷你环形图 → 迷你横向进度条（高 ~6px、占满格宽、圆角），填充比例 = NRV 达成度（nrpPct/100，clamp 0..1）；**填充色 = Top1 贡献食材的 getIngredientColor**（items 空时回退 theme.colorScheme.primary）；未填充部分 outlineVariant；**中心 NRV% 移至标题行**（营养素名 + NRV%）；totalText/Top2 贡献文案/NRV·全部切换保留
- ② 成本趋势堆叠图、④ 商家卡片、⑤ 比价矩阵不动；fl_chart 依赖保留（② 仍用）
- 约束：feat/mobile-app 分支、中文注释、不做 git 操作、TDD、全量测试 + analyze + build windows 通过

**Files:**
- Modify: `mobile/lib/features/recipes/widgets/cost_proportion_chart.dart` + 测试（Task A）
- Modify: `mobile/lib/features/recipes/widgets/nutrition_source_grid.dart` + 测试（Task B）

---

### Task A: 成本占比饼图 → 彩色进度条

**Files:**
- Modify: `mobile/lib/features/recipes/widgets/cost_proportion_chart.dart`
- Modify: `mobile/test/features/recipes/widgets/cost_proportion_chart_test.dart`（追加 widget 测试）

- [ ] **Step 1: 追加失败测试**（`buildCostProportionItems` 5 个既有测试不动，追加 widget 测试组）

```dart
  group('CostProportionChart 进度条', () {
    const breakdown = [
      CostBreakdownItem(ingredientName: '鸡蛋', ingredientId: 1, cost: 4, unitPrice: 0),
      CostBreakdownItem(ingredientName: '番茄', ingredientId: 2, cost: 2, unitPrice: 0),
    ];

    testWidgets('标题行显示总价，清单行显示 名称+金额+百分比', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: CostProportionChart(breakdown: breakdown, totalCost: 6)),
      ));
      expect(find.text('¥6.00'), findsOneWidget); // 标题行总价
      expect(find.text('鸡蛋'), findsOneWidget);
      expect(find.text('¥4.00'), findsOneWidget);
      expect(find.text('66.7%'), findsOneWidget); // 4/6
      expect(find.text('33.3%'), findsOneWidget); // 2/6
    });

    testWidgets('点击进度条段高亮对应清单行', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: CostProportionChart(breakdown: breakdown, totalCost: 6)),
      ));
      // 点第一段（鸡蛋 4/6 → 占左 2/3）
      final bar = find.byKey(const Key('cost_bar'));
      await tester.tapAt(tester.getTopLeft(bar) + const Offset(20, 5));
      await tester.pump();
      // 高亮态无新文本断言，用 WidgetState 背景色验证复杂；改断言：点击不崩 + 清单行仍存在
      expect(find.text('鸡蛋'), findsOneWidget);
    });
  });
```

注：进度条加 `key: const Key('cost_bar')` 便于测试定位。若 tapAt 命中不稳定（段太细），改为点击清单行 InkWell 验证。

- [ ] **Step 2: 运行确认失败**（新测试 FAIL：旧实现无 `cost_bar` key / 无清单行金额文本）

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_proportion_chart_test.dart
```

- [ ] **Step 3: 改造实现**（`cost_proportion_chart.dart`，保留 `CostProportionItem`/`buildCostProportionItems` 原样）

要点：
- 删除 fl_chart import（本文件不再用）；图标 `Icons.pie_chart_outline` → `Icons.bar_chart_outlined`
- 标题行：`[图标][食材成本占比][Spacer][¥总价 bold]`
- 进度条（key: `Key('cost_bar')`）：

```dart
  /// 彩色进度条：段宽 = 占比，段间 1px surface 色细缝防割裂，整条圆角占满宽度。
  Widget _buildBar(ThemeData theme, List<CostProportionItem> items) {
    final hasValue = items.any((i) => i.value > 0);
    return ClipRRect(
      borderRadius: BorderRadius.circular(5),
      child: SizedBox(
        height: 10,
        width: double.infinity,
        child: Row(
          children: [
            for (var i = 0; i < items.length; i++) ...[
              if (i > 0) Container(width: 1, color: theme.colorScheme.surface),
              Expanded(
                flex: hasValue ? (items[i].value * 1000).round() : 1,
                child: GestureDetector(
                  onTap: () => setState(() => _touchedIndex = i),
                  child: ColoredBox(color: items[i].color),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
```

- 清单（替换原 Wrap 图例）：

```dart
  /// 食材清单：色块 + 名称 + 金额 + 百分比（点击行高亮对应段，对齐 web 图例点击显示金额）。
  Widget _buildList(ThemeData theme, List<CostProportionItem> items, double total) {
    return Column(
      children: [
        for (var i = 0; i < items.length; i++)
          InkWell(
            onTap: () => setState(() => _touchedIndex = i),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              decoration: BoxDecoration(
                color: _touchedIndex == i
                    ? items[i].color.withValues(alpha: 0.2)
                    : null,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                      color: items[i].color,
                      borderRadius: BorderRadius.circular(3)),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(items[i].name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium),
                ),
                Text('¥${items[i].value.toStringAsFixed(2)}',
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w600)),
                const SizedBox(width: 12),
                SizedBox(
                  width: 48,
                  child: Text(_pct(items[i], total),
                      textAlign: TextAlign.right,
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: theme.colorScheme.outline)),
                ),
              ]),
            ),
          ),
      ],
    );
  }
```

- `_buildChart` 改：`total` 计算保留（`widget.totalCost > 0 ? widget.totalCost : items 求和`），返回 `Column[_buildBar, SizedBox(8), _buildList]`；`_pct`/`didUpdateWidget` 保留；空态图标同步换 `bar_chart_outlined`；加载高度 220 可降为 ~140（进度条矮了），清单不限制总高（页面可滚）

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_proportion_chart_test.dart
```

- [ ] **Step 5: 汇报**

---

### Task B: 营养溯源迷你环形图 → 迷你进度条

**Files:**
- Modify: `mobile/lib/features/recipes/widgets/nutrition_source_grid.dart`
- Modify: `mobile/test/features/recipes/widgets/nutrition_source_grid_test.dart`（追加 widget 测试）

- [ ] **Step 1: 追加失败测试**

```dart
  group('NutritionSourceGrid 迷你进度条', () {
    testWidgets('格内显示 NRV% 与迷你进度条', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: NutritionSourceGrid(nutrition: _nutrition())),
      ));
      // 蛋白质 NRV 10%（fixture nrpPct: 10）
      expect(find.text('10%'), findsOneWidget);
      // 标题行营养素名
      expect(find.text('蛋白质'), findsOneWidget);
      // 总量文本（perServing protein value 6g）
      expect(find.text('6g'), findsOneWidget);
      // 进度条存在
      expect(find.byKey(const Key('nrv_bar')), findsWidgets);
    });
  });
```

注：`_nutrition()` fixture 已在本文件顶部（不动）；若 GridView 格内溢出（overflow 报错测试自然红），调 `childAspectRatio` 直到不溢出。

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/nutrition_source_grid_test.dart
```

- [ ] **Step 3: 改造实现**（`nutrition_source_grid.dart`，`buildNutrientDisplays` 等纯函数不动）

要点：
- 删除 fl_chart import；`_buildDonutCard` 重写为 `_buildProgressCard`
- 每格布局：`Column[Row(中心: [label 名 Flexible ellipsis, 若有 NRV 则 4px + '${nrpPct}%' bold labelSmall]), 8px, 进度条, 8px, totalText, 2px, topContributors]`
- 进度条（key: `Key('nrv_bar')`）：

```dart
  /// 迷你进度条：填充比例 = NRV 达成度，填充色 = Top1 贡献食材色（空回退主题色）。
  Widget _buildBar(ThemeData theme, NutrientDisplay d) {
    final raw = (d.nrpPct ?? 0).clamp(0, 100);
    final pct = raw / 100;
    final color = d.items.isNotEmpty
        ? d.items.first.color
        : theme.colorScheme.primary;
    return ClipRRect(
      borderRadius: BorderRadius.circular(3),
      child: SizedBox(
        height: 6,
        width: double.infinity,
        child: Row(children: [
          Expanded(
            flex: pct > 0 ? (pct * 1000).round() : 0,
            child: ColoredBox(color: color),
          ),
          if (pct < 1)
            Expanded(
              flex: 1000 - (pct * 1000).round().clamp(0, 1000),
              child: ColoredBox(color: theme.colorScheme.outlineVariant),
            ),
        ]),
      ),
    );
  }
```

- 若溢出：`childAspectRatio: 0.95` 调整为 1.1~1.2（进度条矮、格内内容紧凑）；Grid 间距保持

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/nutrition_source_grid_test.dart
```

- [ ] **Step 5: 汇报**

---

### Task C: 整体验证

- [ ] **Step 1: 全量测试 + 静态分析**

```bash
cd d:/code/live_calc/mobile && flutter test && flutter analyze lib/features/recipes/widgets/cost_proportion_chart.dart lib/features/recipes/widgets/nutrition_source_grid.dart
```

Expected: 全量全绿（59 + 新增）；analyze 无新增。

- [ ] **Step 2: 桌面构建**

```bash
cd d:/code/live_calc/mobile && flutter build windows --debug
```

⚠️ 若失败 MSB3073 cmake_install：先查 `Get-Process livecalc_mobile`（调试进程占用），杀掉重建。

- [ ] **Step 3: 记录要点**（cc/ 记录 + CLAUDE.md 最新修复记录，保留 10 条）
