import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:com_a4ding_livecalc/features/recipes/providers/recipe_provider.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';
import 'package:com_a4ding_livecalc/features/recipes/models/recipe_detail.dart';

class MockRepo extends Mock implements RecipeRepository {}

void main() {
  late MockRepo repo;
  late RecipeDetailPageNotifier notifier;

  setUp(() {
    repo = MockRepo();
    // 菜谱带一个鸡蛋原料（100g），使 _loadMerchantPrices 真正走到并发加载路径
    when(() => repo.getRecipe(1)).thenAnswer((_) async => const RecipeDetail(
        id: 1,
        name: '番茄炒蛋',
        servings: 2,
        ingredients: [
          RecipeIngredient(
              id: 10, ingredientId: 5, name: '鸡蛋', quantity: '100', unit: 'g'),
        ],
        steps: []));
    notifier = RecipeDetailPageNotifier(repo, 1);
  });

  /// load() 内子加载方法均为 fire-and-forget，等待其内部 Future 完成
  Future<void> settle() => Future<void>.delayed(Duration.zero);

  test('load 后并行加载 merchant 两路数据', () async {
    final merchantCost = RecipeMerchantCost(
        currency: 'CNY',
        merchants: [
          MerchantCostItem(
              merchantId: 2,
              merchantName: '盒马',
              coveredCost: 8,
              externalCost: 0,
              totalCost: 8,
              coveredCount: 3,
              totalIngredients: 3,
              isRecommended: true)
        ]);
    final priceItem = MerchantPriceItem(
        recipeIngredientId: 10,
        ingredientId: 5,
        ingredientName: '鸡蛋',
        prices: const []);
    when(() => repo.getRecipeCost(1)).thenAnswer((_) async =>
        const RecipeCost(totalCost: 12, costPerServing: 6, breakdown: []));
    when(() => repo.getRecipeNutrition(1)).thenAnswer((_) async =>
        const RecipeNutrition(
            totalCalories: 300,
            totalProtein: 10,
            totalFat: 8,
            totalCarbs: 20));
    when(() => repo.getRecipeCostHistory(1, days: 30))
        .thenAnswer((_) async => const []);
    when(() => repo.getRecipeMerchantCosts(1))
        .thenAnswer((_) async => merchantCost);
    when(() => repo.getIngredientMerchantPrice(5,
            recipeIngredientId: 10,
            ingredientName: '鸡蛋',
            quantity: 100,
            quantityUnit: 'g'))
        .thenAnswer((_) async => priceItem);

    await notifier.load();
    await settle();

    expect(notifier.state.detail?.name, '番茄炒蛋');
    expect(notifier.state.merchantCosts?.merchants.first.merchantName, '盒马');
    expect(notifier.state.merchantPrices.length, 1);
    expect(notifier.state.merchantPrices.first.ingredientName, '鸡蛋');
    expect(notifier.state.merchantPrices.first.recipeIngredientId, 10);
    expect(notifier.state.loadingMerchantCosts, false);
    expect(notifier.state.loadingMerchantPrices, false);
  });

  test('merchant 接口失败不阻断其他模块', () async {
    when(() => repo.getRecipeCost(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeNutrition(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeCostHistory(1, days: 30))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeMerchantCosts(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getIngredientMerchantPrice(any(),
            recipeIngredientId: any(named: 'recipeIngredientId'),
            ingredientName: any(named: 'ingredientName'),
            quantity: any(named: 'quantity'),
            quantityUnit: any(named: 'quantityUnit')))
        .thenAnswer((_) async => throw Exception('boom'));

    await notifier.load();
    await settle();

    expect(notifier.state.detail, isNotNull);
    expect(notifier.state.error, isNull);
    expect(notifier.state.loadingMerchantCosts, false);
    expect(notifier.state.loadingMerchantPrices, false);
  });

  test('部分原料比价失败只保留成功结果', () async {
    // 覆盖 getRecipe 返回 2 个原料（鸡蛋 id:5 + 番茄 id:6）
    when(() => repo.getRecipe(1)).thenAnswer((_) async => const RecipeDetail(
        id: 1,
        name: '番茄炒蛋',
        servings: 2,
        ingredients: [
          RecipeIngredient(
              id: 10, ingredientId: 5, name: '鸡蛋', quantity: '100', unit: 'g'),
          RecipeIngredient(
              id: 11, ingredientId: 6, name: '番茄', quantity: '200', unit: 'g'),
        ],
        steps: []));
    // 其余四路接口 stub 为抛异常：未 stub 的调用会抛 MissingStubError，而它
    // extends Error 而非 Exception，_load* 的 on Exception catch 吞不掉，
    // fire-and-forget 的未处理异步错误会直接判测试失败
    when(() => repo.getRecipeCost(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeNutrition(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeCostHistory(1, days: 30))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeMerchantCosts(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getIngredientMerchantPrice(5,
            recipeIngredientId: 10,
            ingredientName: '鸡蛋',
            quantity: 100,
            quantityUnit: 'g'))
        .thenAnswer((_) async => const MerchantPriceItem(
            recipeIngredientId: 10,
            ingredientId: 5,
            ingredientName: '鸡蛋'));
    when(() => repo.getIngredientMerchantPrice(6,
            recipeIngredientId: 11,
            ingredientName: '番茄',
            quantity: 200,
            quantityUnit: 'g'))
        .thenAnswer((_) async => throw Exception('boom'));

    await notifier.load();
    await settle();

    expect(notifier.state.merchantPrices.length, 1);
    expect(notifier.state.merchantPrices.first.ingredientName, '鸡蛋');
    expect(notifier.state.loadingMerchantPrices, false);
  });

  test('超过 3 个原料按每批 3 个分批并保持顺序', () async {
    // 覆盖 getRecipe 返回 5 个原料（ingredientId 1-5，id 101-105）
    when(() => repo.getRecipe(1)).thenAnswer((_) async => const RecipeDetail(
        id: 1,
        name: '五料菜谱',
        servings: 2,
        ingredients: [
          RecipeIngredient(
              id: 101, ingredientId: 1, name: 'A', quantity: '10', unit: 'g'),
          RecipeIngredient(
              id: 102, ingredientId: 2, name: 'B', quantity: '10', unit: 'g'),
          RecipeIngredient(
              id: 103, ingredientId: 3, name: 'C', quantity: '10', unit: 'g'),
          RecipeIngredient(
              id: 104, ingredientId: 4, name: 'D', quantity: '10', unit: 'g'),
          RecipeIngredient(
              id: 105, ingredientId: 5, name: 'E', quantity: '10', unit: 'g'),
        ],
        steps: []));
    // 其余四路接口 stub 为抛异常，避免 MissingStubError 成为未处理异步错误
    when(() => repo.getRecipeCost(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeNutrition(1))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeCostHistory(1, days: 30))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => repo.getRecipeMerchantCosts(1))
        .thenAnswer((_) async => throw Exception('boom'));
    for (var i = 1; i <= 5; i++) {
      when(() => repo.getIngredientMerchantPrice(i,
              recipeIngredientId: 100 + i,
              ingredientName: ['A', 'B', 'C', 'D', 'E'][i - 1],
              quantity: 10,
              quantityUnit: 'g'))
          .thenAnswer((_) async => MerchantPriceItem(
              recipeIngredientId: 100 + i,
              ingredientId: i,
              ingredientName: ['A', 'B', 'C', 'D', 'E'][i - 1]));
    }

    await notifier.load();
    await settle();

    expect(notifier.state.merchantPrices.length, 5);
    expect(
        notifier.state.merchantPrices.map((p) => p.ingredientName).toList(),
        ['A', 'B', 'C', 'D', 'E']);
    expect(notifier.state.loadingMerchantPrices, false);
  });
}
