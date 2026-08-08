import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
// fl_chart 的 tooltip 是画布绘制（TextPainter），widget finder 无法定位；
// 引入内部渲染类，直接断言驱动绘制的 showingTooltipIndicators 状态
import 'package:fl_chart/src/chart/line_chart/line_chart_renderer.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/cost_trend_stacked_chart.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

void main() {
  group('buildStackedSeries', () {
    test('按食材累加 y 值实现堆叠', () {
      final points = [
        const CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 2),
          CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 3),
        ]),
        const CostHistoryPoint(date: '07-02', minCost: 1, maxCost: 4, avgCost: 3, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 4),
          CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 1),
        ]),
      ];
      final series = buildStackedSeries(points);
      // 两个食材两条线
      expect(series.length, 2);
      // 鸡蛋线：第1天 2，第2天 4
      expect(series.first.spots.first.y, 2);
      expect(series.first.spots.last.y, 4);
      // 番茄线（累加）：第1天 2+3=5，第2天 4+1=5
      expect(series.last.spots.first.y, 5);
      expect(series.last.spots.last.y, 5);
    });

    test('无 breakdown 时返回空（由调用方回退折线图）', () {
      final points = [
        const CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2),
      ];
      expect(buildStackedSeries(points), isEmpty);
    });

    test('某天缺某食材 → 0 贡献（y 平接上一序列）+ 跨天 acc 重置', () {
      final points = [
        const CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 2),
        ]),
        const CostHistoryPoint(date: '07-02', minCost: 1, maxCost: 4, avgCost: 3, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 4),
          CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 1),
        ]),
      ];
      final series = buildStackedSeries(points);
      expect(series.length, 2);
      // 鸡蛋：第1天 2，第2天 4（跨天重置，不是 2+4=6）
      expect(series.first.spots.first.y, 2);
      expect(series.first.spots.last.y, 4);
      // 番茄：第1天缺失 → 自身贡献 0，y 平接在鸡蛋线上（2）；第2天 4+1=5
      expect(series.last.spots.first.y, 2);
      expect(series.last.spots.last.y, 5);
    });

    test('某食材只出现在后面天数 → 锁定首次出现顺序', () {
      final points = [
        const CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 3),
        ]),
        const CostHistoryPoint(date: '07-02', minCost: 1, maxCost: 4, avgCost: 3, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 2),
          CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 1),
        ]),
      ];
      final series = buildStackedSeries(points);
      // 番茄先出现 → 排前（y 顺序即堆叠顺序）；鸡蛋第2天才出现 → 排后
      expect(series.map((s) => s.name).toList(), ['番茄', '鸡蛋']);
      // 鸡蛋第1天缺失 → 自身贡献 0，y 平接在番茄线上（3）；第2天 1+2=3
      expect(series.last.spots.first.y, 3);
      expect(series.last.spots.last.y, 3);
      // 番茄为底部序列，y 即自身成本
      expect(series.first.spots.first.y, 3);
      expect(series.first.spots.last.y, 1);
    });

    test('null ingredientId → 归入 key 0 系列且成本计入', () {
      final points = [
        const CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2, breakdown: [
          CostHistoryBreakdownItem(ingredientName: '自选食材', cost: 2),
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 3),
        ]),
      ];
      final series = buildStackedSeries(points);
      // 两条序列：null 归 key 0（灰色），成本 2 计入堆叠
      expect(series.length, 2);
      final custom = series.firstWhere((s) => s.name == '自选食材');
      expect(custom.spots.single.y, 2);
      // 鸡蛋在自选食材之上：3 + 2 = 5
      final egg = series.firstWhere((s) => s.name == '鸡蛋');
      expect(egg.spots.single.y, 5);
    });

    test('同天重复 id → 成本求和', () {
      final points = [
        const CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 2),
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 3),
        ]),
      ];
      final series = buildStackedSeries(points);
      expect(series.length, 1);
      // 同一天同 id 的两条明细都计入：2 + 3 = 5
      expect(series.first.spots.single.y, 5);
    });
  });

  group('buildStackedTooltipItems', () {
    const egg = StackedSeries(name: '鸡蛋', color: Colors.amber, spots: []);
    const tomato = StackedSeries(name: '番茄', color: Colors.red, spots: []);
    final eggSpot = LineBarSpot(
        LineChartBarData(spots: const [FlSpot(0, 2)]), 0, const FlSpot(0, 2));
    final tomatoSpot = LineBarSpot(
        LineChartBarData(spots: const [FlSpot(0, 5)]), 1, const FlSpot(0, 5));

    test('乱序输入按 barIndex 重排，差值逆推成本，日期/合计并入首尾条', () {
      // fl_chart 传入顺序按到触点距离（番茄线在上先列出），须重排为序列顺序
      final items = buildStackedTooltipItems([egg, tomato], [tomatoSpot, eggSpot], '07-01');
      // fl_chart 契约：返回条数必须与 touchedSpots 一致（painter 校验不一致 throw）
      expect(items.length, 2);
      // 第一条：日期行（粗体）+ 底部序列（鸡蛋）明细
      expect(items[0].text, '07-01\n');
      expect(items[0].children!.single.text, '鸡蛋: ¥2.00');
      // 第二条：顶部序列番茄，成本 = 累加值差值 5 - 2 = 3
      expect(items[1].text, '番茄: ¥3.00');
      // 合计并入最后一条 children（粗体）
      expect(items[1].children!.single.text, '\n合计: ¥5.00');
    });

    test('单序列：日期与合计都并入同一条', () {
      final items = buildStackedTooltipItems([egg], [eggSpot], '07-02');
      expect(items.length, 1);
      expect(items[0].text, '07-02\n');
      expect(items[0].children!.length, 2);
      expect(items[0].children![0].text, '鸡蛋: ¥2.00');
      expect(items[0].children![1].text, '\n合计: ¥2.00');
    });

    test('无命中 spots → 空列表', () {
      expect(buildStackedTooltipItems([egg], [], '07-03'), isEmpty);
    });

    test('相邻天像素过密时远线跳到邻天 → 仍统一触点天逆推（不混日）', () {
      // 两天数据：鸡蛋第0天2/第1天10，番茄（累计值）第0天5/第1天15
      const eggSeries = StackedSeries(
          name: '鸡蛋', color: Colors.amber, spots: [FlSpot(0, 2), FlSpot(1, 10)]);
      const tomatoSeries = StackedSeries(
          name: '番茄', color: Colors.red, spots: [FlSpot(0, 5), FlSpot(1, 15)]);
      // fl_chart 对每条线独立按「到触点像素距离」取最近点：触点在第 0 天，
      // 相邻天像素宽小 + 番茄线 y 差大时，远线（番茄）会取到第 1 天
      // （x=1 与触点错位）。输入按距离序：最近线在前（鸡蛋 day0）。
      final eggSpot = LineBarSpot(
          LineChartBarData(spots: eggSeries.spots), 0, const FlSpot(0, 2));
      final tomatoSpot = LineBarSpot(
          LineChartBarData(spots: tomatoSeries.spots), 1, const FlSpot(1, 15));
      final items = buildStackedTooltipItems(
          const [eggSeries, tomatoSeries], [eggSpot, tomatoSpot], '07-01');
      expect(items.length, 2);
      // 统一到触点天（第0天）逆推：鸡蛋 2，番茄 5-2=3（若混日会算出 15-10=5）
      expect(items[0].children!.single.text, '鸡蛋: ¥2.00');
      expect(items[1].text, '番茄: ¥3.00');
      // 合计 = 触点天堆叠总值 5（混日会错算成 15）
      expect(items[1].children!.single.text, '\n合计: ¥5.00');
    });

    test('锚点必须是距触点最近的线（touchedSpots.first），非重排后底部线', () {
      // 反例构造：番茄距触点最近且落在第0天（day0），底部线鸡蛋的最近点
      // 落在第1天（x=1）。touchedSpots.first = 番茄(day0) → 触点天 day0；
      // 若误用 barIndex 重排后 sorted.first（=鸡蛋，x=1）→ 明细/合计全取
      // day1、日期却显示触点天 day0 → 日期与数值错日。
      const eggSeries = StackedSeries(
          name: '鸡蛋', color: Colors.amber, spots: [FlSpot(0, 2), FlSpot(1, 10)]);
      const tomatoSeries = StackedSeries(
          name: '番茄', color: Colors.red, spots: [FlSpot(0, 5), FlSpot(1, 15)]);
      final eggSpot = LineBarSpot(
          LineChartBarData(spots: eggSeries.spots), 0, const FlSpot(1, 10));
      final tomatoSpot = LineBarSpot(
          LineChartBarData(spots: tomatoSeries.spots), 1, const FlSpot(0, 5));
      final items = buildStackedTooltipItems(
          const [eggSeries, tomatoSeries], [tomatoSpot, eggSpot], '07-01');
      // 触点天 day0：鸡蛋 2、番茄 5-2=3、合计 5
      expect(items[0].children!.single.text, '鸡蛋: ¥2.00');
      expect(items[1].text, '番茄: ¥3.00');
      expect(items[1].children!.single.text, '\n合计: ¥5.00');
    });
  });

  group('costHistoryDays', () {
    test('筛选映射 周/月/季/年/全部', () {
      expect(costHistoryDays['week'], 7);
      expect(costHistoryDays['month'], 30);
      expect(costHistoryDays['quarter'], 90);
      expect(costHistoryDays['year'], 365);
      expect(costHistoryDays['all'], 3650);
    });
  });

  group('CostTrendStackedChart 筛选下拉与点击提示', () {
    CostHistoryPoint _p(String date,
            {List<CostHistoryBreakdownItem> breakdown = const []}) =>
        CostHistoryPoint(
            date: date,
            minCost: 1,
            maxCost: 3,
            avgCost: 2,
            breakdown: breakdown);

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
      // 点 LineChart 区域（图表 SizedBox(height:200)）
      final chartFinder = find.byType(LineChart);
      await tester.tapAt(tester.getCenter(chartFinder));
      await tester.pump();
      // fl_chart LineChart 有默认 150ms 数据动画：pump 200ms 走完动画，
      // 避免读到线几何动画中间态
      await tester.pump(const Duration(milliseconds: 200));
      // fl_chart tooltip 为画布绘制（TextPainter），finder 找不到文本（原「鸡蛋」断言
      // 命中图表下方食材 chip 是假绿）。改真实验证驱动绘制的状态：
      // tap 后 showingTooltipIndicators 必须非空，否则画布上根本画不出 tooltip。
      // 注意不能用 e.renderObject is RenderLineChart 的 predicate：
      // KeyedSubtree 是 StatelessWidget，其 element.renderObject 会解析到第一个
      // 子渲染对象（也是 RenderLineChart）→ 匹配 2 个。须按 widget 类型精确匹配。
      final renderChart = tester.renderObject<RenderLineChart>(
          find.byElementPredicate((e) => e.widget is LineChartLeaf));
      expect(renderChart.data.showingTooltipIndicators, isNotEmpty);
      // 两条食材线全量命中（touchSpotThreshold: infinity 不过滤远线）
      expect(
          renderChart.data.showingTooltipIndicators.single.showingSpots.length,
          2);
    });

    testWidgets('回退图（无 breakdown）tap 不崩且 tooltip 出现', (tester) async {
      // 无 breakdown → buildStackedSeries 返回空 → 走 avg/min/max 回退折线图。
      // 单线图仅命中 1 个 spot，tooltip 条数必须与其一致（否则 painter throw）。
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: CostTrendStackedChart(
            points: [_p('07-01'), _p('07-02'), _p('07-03')],
          ),
        ),
      ));
      // 回退图只渲染一个 LineChart
      expect(find.byType(LineChart), findsOneWidget);
      await tester.tapAt(tester.getCenter(find.byType(LineChart)));
      await tester.pump();
      // 同主图：走完 fl_chart 150ms 数据动画后读携带 tooltip 状态的 end 值
      await tester.pump(const Duration(milliseconds: 200));
      final renderChart = tester.renderObject<RenderLineChart>(
          find.byElementPredicate((e) => e.widget is LineChartLeaf));
      expect(renderChart.data.showingTooltipIndicators, isNotEmpty);
      // 回退图核心是单线图：恰命中 1 个 spot（1:1 契约，1 条 tooltip item）
      expect(
          renderChart.data.showingTooltipIndicators.single.showingSpots.length,
          1);
    });
  });
}
