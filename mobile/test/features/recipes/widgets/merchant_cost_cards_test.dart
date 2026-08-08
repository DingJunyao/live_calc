import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/merchant_cost_cards.dart';

void main() {
  group('MerchantCostCards', () {
    testWidgets('渲染商家卡片：名称/总价/覆盖数/需外购', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: MerchantCostCards(
            merchants: [
              MerchantCostItem(
                merchantId: 1,
                merchantName: '盒马',
                coveredCost: 8.5,
                externalCost: 3.2,
                totalCost: 11.7,
                coveredCount: 4,
                totalIngredients: 6,
                missingIngredients: ['盐'],
                isRecommended: true,
              ),
            ],
            loading: false,
          ),
        ),
      ));
      expect(find.text('盒马'), findsOneWidget);
      expect(find.text('¥11.70'), findsOneWidget);
      expect(find.textContaining('覆盖 4/6 种食材'), findsOneWidget);
      expect(find.textContaining('需外购'), findsOneWidget);
      expect(find.text('最实惠 ✓'), findsOneWidget);
    });

    testWidgets('fallback 链点击信息图标弹出弹窗', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: MerchantCostCards(
            merchants: [
              MerchantCostItem(
                merchantId: 1,
                merchantName: '盒马',
                coveredCost: 8.5,
                externalCost: 3.2,
                totalCost: 11.7,
                coveredCount: 4,
                totalIngredients: 6,
                missingIngredients: ['盐'],
                fallbackChains: ['盐 → 海盐'],
              ),
            ],
            loading: false,
          ),
        ),
      ));
      await tester.tap(find.byIcon(Icons.info_outline));
      await tester.pumpAndSettle();
      expect(find.text('根据以下食材计算价格：'), findsOneWidget);
      expect(find.text('盐 → 海盐'), findsOneWidget);
      // 关闭弹窗
      await tester.tap(find.text('知道了'));
      await tester.pumpAndSettle();
      expect(find.text('根据以下食材计算价格：'), findsNothing);
    });

    testWidgets('loading 显示进度条', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: MerchantCostCards(merchants: [], loading: true),
        ),
      ));
      // 不定动画：只用 pump，不用 pumpAndSettle
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('多商家横向滚动全部渲染', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: MerchantCostCards(
            merchants: [
              MerchantCostItem(
                merchantId: 1,
                merchantName: '盒马',
                coveredCost: 1,
                externalCost: 0,
                totalCost: 1,
                coveredCount: 1,
                totalIngredients: 2,
              ),
              MerchantCostItem(
                merchantId: 2,
                merchantName: '永辉',
                coveredCost: 2,
                externalCost: 0,
                totalCost: 2,
                coveredCount: 2,
                totalIngredients: 2,
              ),
              MerchantCostItem(
                merchantId: 3,
                merchantName: '山姆',
                coveredCost: 3,
                externalCost: 0,
                totalCost: 3,
                coveredCount: 2,
                totalIngredients: 2,
              ),
            ],
            loading: false,
          ),
        ),
      ));
      expect(find.text('盒马'), findsOneWidget);
      expect(find.text('永辉'), findsOneWidget);
      expect(find.text('山姆'), findsOneWidget);
    });

    testWidgets('暗色模式推荐卡用暗色表面色', (tester) async {
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData(brightness: Brightness.dark),
        home: const Scaffold(
          body: MerchantCostCards(
            merchants: [
              MerchantCostItem(
                merchantId: 1,
                merchantName: '盒马',
                coveredCost: 8.5,
                externalCost: 3.2,
                totalCost: 11.7,
                coveredCount: 4,
                totalIngredients: 6,
                missingIngredients: ['盐'],
                isRecommended: true,
              ),
            ],
            loading: false,
          ),
        ),
      ));
      final card = tester.widget<Container>(
        find
            .ancestor(of: find.text('盒马'), matching: find.byType(Container))
            .first,
      );
      final color = (card.decoration! as BoxDecoration).color;
      expect(color, ThemeData(brightness: Brightness.dark).colorScheme.surface);
      expect(color, isNot(const Color(0xFFFFF8E1)));
    });

    testWidgets('空数据显示空态', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: MerchantCostCards(merchants: [], loading: false)),
      ));
      expect(find.text('暂无商家价格数据'), findsOneWidget);
    });
  });
}
