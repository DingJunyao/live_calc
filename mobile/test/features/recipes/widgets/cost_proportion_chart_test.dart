import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/cost_proportion_chart.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';
import 'package:com_a4ding_livecalc/features/recipes/utils/ingredient_colors.dart';

void main() {
  group('buildCostProportionItems', () {
    test('降序排列，前 5 + 其他合并', () {
      final items = buildCostProportionItems([
        const CostBreakdownItem(
            ingredientName: 'a', ingredientId: 1, cost: 1, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'b', ingredientId: 2, cost: 5, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'c', ingredientId: 3, cost: 2, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'd', ingredientId: 4, cost: 4, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'e', ingredientId: 5, cost: 3, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'f', ingredientId: 6, cost: 6, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'g', ingredientId: 7, cost: 7, unitPrice: 0),
      ]);
      expect(items.length, 6); // 前 5 + 其他
      expect(items.first.name, 'g');
      expect(items[1].name, 'f');
      expect(items.last.name, '其他');
      expect(items.last.value, 3); // c(2)+a(1)
    });

    test('少于 6 项不合并', () {
      final items = buildCostProportionItems([
        const CostBreakdownItem(
            ingredientName: 'a', ingredientId: 1, cost: 1, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'b', ingredientId: 2, cost: 2, unitPrice: 0),
      ]);
      expect(items.length, 2);
      expect(items.first.name, 'b');
    });

    test('恰好 6 项不合并「其他」', () {
      final items = buildCostProportionItems([
        const CostBreakdownItem(
            ingredientName: 'a', ingredientId: 1, cost: 1, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'b', ingredientId: 2, cost: 2, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'c', ingredientId: 3, cost: 3, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'd', ingredientId: 4, cost: 4, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'e', ingredientId: 5, cost: 5, unitPrice: 0),
        const CostBreakdownItem(
            ingredientName: 'f', ingredientId: 6, cost: 6, unitPrice: 0),
      ]);
      expect(items.length, 6);
      expect(items.every((i) => i.name != '其他'), isTrue);
    });

    test('空名称回退为未知食材', () {
      final items = buildCostProportionItems([
        const CostBreakdownItem(
            ingredientName: '', ingredientId: 1, cost: 5, unitPrice: 0),
      ]);
      expect(items.length, 1);
      expect(items.first.name, '未知食材');
    });

    test('空数据返回空列表', () {
      expect(buildCostProportionItems([]), isEmpty);
    });
  });

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
      // 真断言高亮：清单第一行背景 = 鸡蛋色 alpha 0.2，第二行无高亮
      final row0 = tester.widget<Container>(find.byKey(const Key('cost_row_0')));
      expect((row0.decoration as BoxDecoration).color,
          getIngredientColor(1).withValues(alpha: 0.2));
      final row1 = tester.widget<Container>(find.byKey(const Key('cost_row_1')));
      expect((row1.decoration as BoxDecoration).color, isNull);
    });

    testWidgets('点击清单行高亮对应行', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: CostProportionChart(breakdown: breakdown, totalCost: 6)),
      ));
      await tester.tap(find.text('番茄'));
      await tester.pump();
      final row1 = tester.widget<Container>(find.byKey(const Key('cost_row_1')));
      expect((row1.decoration as BoxDecoration).color,
          getIngredientColor(2).withValues(alpha: 0.2));
      final row0 = tester.widget<Container>(find.byKey(const Key('cost_row_0')));
      expect((row0.decoration as BoxDecoration).color, isNull);
    });
  });
}
