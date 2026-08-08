import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/models/recipe_detail.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/merchant_price_matrix.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

void main() {
  group('buildMatrixRows', () {
    test('total_cost 优先、缺失显示占位', () {
      final rows = buildMatrixRows(
        ingredients: const [
          RecipeIngredient(
              id: 10, ingredientId: 5, name: '鸡蛋', quantity: '100', unit: 'g'),
          RecipeIngredient(
              id: 11, ingredientId: 6, name: '番茄', quantity: '200', unit: 'g'),
        ],
        prices: const [
          MerchantPriceItem(
            recipeIngredientId: 10,
            ingredientId: 5,
            ingredientName: '鸡蛋',
            prices: [
              MerchantPriceRecord(
                  merchantId: 1,
                  merchantName: '盒马',
                  price: 3.0,
                  totalCost: 3.5,
                  isLowest: true),
              MerchantPriceRecord(
                  merchantId: 2, merchantName: '永辉', price: 3.2),
            ],
          ),
        ],
      );
      expect(rows.length, 2);
      final row0 = rows.first;
      expect(row0.name, '鸡蛋');
      // 盒马显示 total_cost 3.50 且最低价
      expect(row0.cells['盒马']!.display, '3.50');
      expect(row0.cells['盒马']!.isLowest, true);
      // 永辉回退 price 3.20
      expect(row0.cells['永辉']!.display, '3.20');
      expect(row0.cells['永辉']!.isLowest, false);
      // 番茄两商家都缺失
      expect(rows.last.cells['盒马']!.display, '—');
      expect(rows.last.cells['永辉']!.display, '—');
      expect(rows.last.cells['永辉']!.hasPrice, false);
    });

    test('quantityRange 食材显示范围用量', () {
      final rows = buildMatrixRows(
        ingredients: const [
          RecipeIngredient(
              id: 12,
              ingredientId: 7,
              name: '土豆',
              quantityRange: QuantityRange(min: 100, max: 200),
              unit: 'g'),
        ],
        prices: const [],
      );
      expect(rows.single.quantityDisplay, '100-200g');
    });

    test('空 merchantName 回退商家 id 列标签', () {
      final rows = buildMatrixRows(
        ingredients: const [
          RecipeIngredient(
              id: 10, ingredientId: 5, name: '鸡蛋', quantity: '100', unit: 'g'),
        ],
        prices: const [
          MerchantPriceItem(
            recipeIngredientId: 10,
            ingredientId: 5,
            ingredientName: '鸡蛋',
            prices: [
              MerchantPriceRecord(merchantId: 9, merchantName: '', price: 1.0),
            ],
          ),
        ],
      );
      expect(rows.single.cells.containsKey('商家9'), isTrue);
      expect(rows.single.cells['商家9']!.display, '1.00');
    });
  });

  group('MerchantPriceMatrix', () {
    testWidgets('渲染矩阵：¥ 前缀显示 total_cost', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: MerchantPriceMatrix(
            ingredients: [
              RecipeIngredient(
                  id: 10,
                  ingredientId: 5,
                  name: '鸡蛋',
                  quantity: '100',
                  unit: 'g'),
            ],
            prices: [
              MerchantPriceItem(
                recipeIngredientId: 10,
                ingredientId: 5,
                ingredientName: '鸡蛋',
                prices: [
                  MerchantPriceRecord(
                      merchantId: 1,
                      merchantName: '盒马',
                      price: 3.0,
                      totalCost: 3.5,
                      isLowest: true),
                ],
              ),
            ],
          ),
        ),
      ));
      // ¥ 是前缀而非后缀（web .vue:46 与 Task 8 一致）
      expect(find.text('¥3.50'), findsOneWidget);
      expect(find.text('盒马'), findsOneWidget);
      expect(find.text('鸡蛋'), findsOneWidget);
    });

    testWidgets('fallback 链点击信息图标弹出弹窗', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: MerchantPriceMatrix(
            ingredients: [
              RecipeIngredient(
                  id: 10,
                  ingredientId: 5,
                  name: '鸡蛋',
                  quantity: '100',
                  unit: 'g'),
            ],
            prices: [
              MerchantPriceItem(
                recipeIngredientId: 10,
                ingredientId: 5,
                ingredientName: '鸡蛋',
                fallbackChain: '盐 → 海盐',
                prices: [
                  MerchantPriceRecord(
                      merchantId: 1, merchantName: '盒马', price: 3.0),
                ],
              ),
            ],
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

    testWidgets('空数据显示空态', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: MerchantPriceMatrix(ingredients: [], prices: [], loading: false),
        ),
      ));
      expect(find.text('暂无比价数据'), findsOneWidget);
    });
  });
}
