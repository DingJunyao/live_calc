# 移动端菜谱分析页对齐 web 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重写移动端（Flutter）菜谱分析页，使其与 web 端 RecipeAnalysisView 的 5 个分析模块（成本占比 / 成本趋势 / 营养贡献溯源 / 按商家预估成本 / 商家比价推荐）布局与功能对齐。

**Architecture:** 按 spec（[SPEC_移动端菜谱分析页对齐web.md](SPEC_移动端菜谱分析页对齐web.md)）实施：数据层补齐 2 个 repository 方法 + `MerchantPriceItem.fromJson`；新建 5 个图表/表格组件（全部基于新引入的 fl_chart）；Provider 状态扩展；分析页重写组装。后端接口已存在，不动后端。

**Tech Stack:** Flutter（riverpod + go_router + dio + fl_chart）、mocktail（测试）

**提交约定：** 按 CLAUDE.md「不主动 git 提交」，每任务完成后的 commit 步骤仅当用户明确要求才执行；否则跳过并在汇报中说明。

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `mobile/pubspec.yaml` | 新增 fl_chart 依赖 |
| `mobile/lib/features/recipes/utils/ingredient_colors.dart` | 新建：16 色板 + ingredient_id hash 取色（移植 web ingredientColors.ts） |
| `mobile/lib/features/recipes/repositories/recipe_repository.dart` | 补 `getRecipeMerchantCosts`、`getIngredientMerchantPrice`、`MerchantPriceItem.fromJson` |
| `mobile/lib/features/recipes/providers/recipe_provider.dart` | State 增 merchant 两路数据与 loading；Notifier 增两个加载方法 |
| `mobile/lib/features/recipes/widgets/cost_proportion_chart.dart` | 新建：成本占比环形饼图 |
| `mobile/lib/features/recipes/widgets/cost_trend_stacked_chart.dart` | 新建：堆叠面积趋势图（含筛选与食材高亮） |
| `mobile/lib/features/recipes/widgets/nutrition_source_grid.dart` | 新建：营养贡献溯源迷你环形图网格 |
| `mobile/lib/features/recipes/widgets/merchant_cost_cards.dart` | 新建：按商家预估成本横向卡片 |
| `mobile/lib/features/recipes/widgets/merchant_price_matrix.dart` | 新建：商家比价矩阵（横向滚动表） |
| `mobile/lib/features/recipes/screens/recipe_analysis_screen.dart` | 重写：组装 5 模块 + AppBar「菜谱名+分析 chip」 |
| `mobile/lib/features/recipes/screens/recipe_detail_screen.dart` | tooltip「成本分析」→「菜谱分析」 |
| `mobile/test/features/recipes/utils/ingredient_colors_test.dart` | 新建测试 |
| `mobile/test/features/recipes/repositories/recipe_repository_test.dart` | 新建测试 |
| `mobile/test/features/recipes/providers/recipe_provider_test.dart` | 新建测试 |
| `mobile/test/features/recipes/widgets/cost_proportion_chart_test.dart` 等 | 新建组件测试 |

---

### Task 1: 引入 fl_chart 依赖

**Files:**
- Modify: `mobile/pubspec.yaml`

- [ ] **Step 1: 添加依赖**

```bash
cd d:/code/live_calc/mobile && flutter pub add fl_chart
```

- [ ] **Step 2: 验证依赖解析成功**

```bash
cd d:/code/live_calc/mobile && flutter pub get
```

Expected: exit 0，pubspec.yaml dependencies 中出现 `fl_chart: ^x.y.z`。

- [ ] **Step 3: 汇报（是否提交由用户决定）**

---

### Task 2: ingredient_colors 工具（TDD）

**Files:**
- Create: `mobile/lib/features/recipes/utils/ingredient_colors.dart`
- Test: `mobile/test/features/recipes/utils/ingredient_colors_test.dart`

- [ ] **Step 1: 写失败测试**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/utils/ingredient_colors.dart';

void main() {
  group('getIngredientColor', () {
    test('同一 ingredient_id 颜色一致', () {
      expect(getIngredientColor(3), getIngredientColor(3));
    });

    test('不同 id 从 16 色板取色（abs % 16）', () {
      expect(getIngredientColor(0), INGREDIENT_COLOR_PALETTE[0]);
      expect(getIngredientColor(16), INGREDIENT_COLOR_PALETTE[0]);
      expect(getIngredientColor(-1), INGREDIENT_COLOR_PALETTE[1]);
      expect(getIngredientColor(7), INGREDIENT_COLOR_PALETTE[7]);
    });

    test('null / 无效 id 返回灰色', () {
      expect(getIngredientColor(null), const Color(0xFFE0E0E0));
      expect(getIngredientColor(null), getIngredientColor(999999)); // 保证返回类型正确
    });
  });
}
```

注：`getIngredientColor(null)` 的断言写灰色即可，palette 索引取模天然不会越界，无需给无效分支。`Color` 来自 flutter/material。

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/utils/ingredient_colors_test.dart
```

Expected: FAIL（找不到 getIngredientColor / ingredient_colors.dart）。

- [ ] **Step 3: 实现工具（移植 web ingredientColors.ts）**

```dart
import 'package:flutter/material.dart';

/// 食材配色工具——同种食材在成本占比、成本趋势、营养溯源三张图表中使用相同颜色。
/// 通过 ingredient_id 的 hash 值从共享色板中取色（对齐 web utils/ingredientColors.ts）。
const INGREDIENT_COLOR_PALETTE = <Color>[
  Color(0xFFFF9800), Color(0xFF4CAF50), Color(0xFF2196F3), Color(0xFF9C27B0),
  Color(0xFFF44336), Color(0xFF00BCD4), Color(0xFFFF5722), Color(0xFF607D8B),
  Color(0xFFE91E63), Color(0xFF3F51B5), Color(0xFF009688), Color(0xFF795548),
  Color(0xFFCDDC39), Color(0xFFFFC107), Color(0xFF03A9F4), Color(0xFF8BC34A),
];

Color getIngredientColor(int? ingredientId) {
  if (ingredientId == null) return const Color(0xFFE0E0E0);
  return INGREDIENT_COLOR_PALETTE[ingredientId.abs() % INGREDIENT_COLOR_PALETTE.length];
}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/utils/ingredient_colors_test.dart
```

Expected: PASS（3 个测试）。

- [ ] **Step 5: 汇报**

---

### Task 3: Repository 补两个方法 + MerchantPriceItem.fromJson（TDD）

**Files:**
- Modify: `mobile/lib/features/recipes/repositories/recipe_repository.dart`
- Test: `mobile/test/features/recipes/repositories/recipe_repository_test.dart`

- [ ] **Step 1: 写失败测试**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dio/dio.dart';
import 'package:com_a4ding_livecalc/core/api/api_client.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

void main() {
  late RecipeRepository repository;
  late MockApiClient mockClient;
  late MockDio mockDio;

  setUp(() {
    mockClient = MockApiClient();
    mockDio = MockDio();
    when(() => mockClient.dio).thenReturn(mockDio);
    repository = RecipeRepository(client: mockClient);
  });

  group('getRecipeMerchantCosts', () {
    test('解析 merchant-costs 响应', () async {
      when(() => mockDio.get('/recipes/1/merchant-costs'))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                statusCode: 200,
                data: {
                  'currency': 'CNY',
                  'merchants': [
                    {
                      'merchant_id': 2,
                      'merchant_name': '盒马',
                      'covered_cost': '8.50',
                      'external_cost': '3.20',
                      'total_cost': '11.70',
                      'covered_count': 4,
                      'total_ingredients': 6,
                      'missing_ingredients': ['盐', '油'],
                      'fallback_chains': ['大米(kg) 按面粉价'],
                      'is_recommended': true,
                    }
                  ],
                },
              ));

      final res = await repository.getRecipeMerchantCosts(1);
      expect(res.currency, 'CNY');
      expect(res.merchants.length, 1);
      final m = res.merchants.first;
      expect(m.merchantId, 2);
      expect(m.merchantName, '盒马');
      expect(m.coveredCost, 8.5);
      expect(m.externalCost, 3.2);
      expect(m.totalCost, 11.7);
      expect(m.coveredCount, 4);
      expect(m.totalIngredients, 6);
      expect(m.missingIngredients, ['盐', '油']);
      expect(m.fallbackChains.length, 1);
      expect(m.isRecommended, true);
    });

    test('空 merchants 不崩', () async {
      when(() => mockDio.get('/recipes/9/merchant-costs'))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                statusCode: 200,
                data: {'currency': 'CNY'},
              ));
      final res = await repository.getRecipeMerchantCosts(9);
      expect(res.merchants, isEmpty);
    });
  });

  group('getIngredientMerchantPrice', () {
    test('透传 quantity/quantity_unit 参数并解析价格列表', () async {
      // 注意：仓库层 quantity 为 double，Dart num 相等比较 100.0 == 100 成立，
      // 因此 queryParameters 精确匹配时写 int 字面量即可。
      when(() => mockDio.get(
            '/nutrition/ingredients/5/latest-price-by-merchant',
            queryParameters: {'quantity': 100.0, 'quantity_unit': 'g'},
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                statusCode: 200,
                data: {
                  'prices': [
                    {
                      'merchant_id': 2,
                      'merchant_name': '盒马',
                      'price': '3.50',
                      'unit': 'g',
                      'total_cost': '3.50',
                      'is_lowest': true,
                    },
                    {
                      'merchant_id': 3,
                      'merchant_name': '永辉',
                      'price': '4.20',
                      'unit': 'g',
                    },
                  ],
                  'unit': 'g',
                  'fallback_chain': '用面粉代替',
                },
              ));

      final res = await repository.getIngredientMerchantPrice(5,
          quantity: 100, quantityUnit: 'g');
      expect(res.prices.length, 2);
      expect(res.prices.first.merchantName, '盒马');
      expect(res.prices.first.totalCost, 3.5);
      expect(res.prices.first.isLowest, true);
      expect(res.prices.last.isLowest, false);
      expect(res.unit, 'g');
      expect(res.fallbackChain, '用面粉代替');
    });

    test('不传数量参数时不带 quantity', () async {
      when(() => mockDio.get(
            '/nutrition/ingredients/5/latest-price-by-merchant',
            queryParameters: <String, dynamic>{},
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                statusCode: 200,
                data: {'prices': []},
              ));
      final res = await repository.getIngredientMerchantPrice(5);
      expect(res.prices, isEmpty);
      expect(res.ingredientId, 5);
    });
  });
}
```

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/repositories/recipe_repository_test.dart
```

Expected: FAIL（getRecipeMerchantCosts / getIngredientMerchantPrice 未定义）。

- [ ] **Step 3: 实现**

在 `recipe_repository.dart` 的 `RecipeRepository` 类内新增两个方法：

```dart
  Future<RecipeMerchantCost> getRecipeMerchantCosts(int id) async {
    final response = await _client.dio.get('/recipes/$id/merchant-costs');
    return RecipeMerchantCost.fromJson(response.data as Map<String, dynamic>);
  }

  /// 单个食材的商家比价。quantity/quantityUnit 可空（web 端只在有效数量时传参）。
  Future<MerchantPriceItem> getIngredientMerchantPrice(
    int ingredientId, {
    double? quantity,
    String? quantityUnit,
  }) async {
    final params = <String, dynamic>{};
    if (quantity != null && quantity > 0) {
      params['quantity'] = quantity;
      params['quantity_unit'] = quantityUnit ?? '';
    }
    final response = await _client.dio.get(
      '/nutrition/ingredients/$ingredientId/latest-price-by-merchant',
      queryParameters: params,
    );
    final data = response.data as Map<String, dynamic>;
    return MerchantPriceItem(
      // recipeIngredientId 字段为非空 int，缺失时兜底 0
      recipeIngredientId: _toIntOrNull(data['recipe_ingredient_id']) ?? 0,
      ingredientId: ingredientId,
      ingredientName: _str(data['ingredient_name']) ?? '',
      prices: ((data['prices'] as List?) ?? const [])
          .map((e) => MerchantPriceRecord.fromJson(e as Map<String, dynamic>))
          .toList(),
      unit: _str(data['unit']),
      qtyDisplay: _str(data['qty_display']),
      fallbackChain:
          _str(data['fallback_chain']) ?? _str(data['aggregation_chain']),
    );
  }
```

同时给现有 `MerchantPriceItem` 类补上 fromJson（当前只有字段定义；`recipeIngredientId` 为非空 int，同样兜底 0）：

```dart
  factory MerchantPriceItem.fromJson(Map<String, dynamic> json) {
    return MerchantPriceItem(
      recipeIngredientId: _toIntOrNull(json['recipe_ingredient_id']) ?? 0,
      ingredientId: _toIntOrNull(json['ingredient_id']) ?? 0,
      ingredientName: _str(json['ingredient_name']) ?? '',
      qtyDisplay: _str(json['qty_display']),
      unit: _str(json['unit']),
      fallbackChain:
          _str(json['fallback_chain']) ?? _str(json['aggregation_chain']),
      prices: ((json['prices'] as List?) ?? const [])
          .map((e) => MerchantPriceRecord.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
```

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/repositories/recipe_repository_test.dart
```

Expected: PASS（5 个测试）。

- [ ] **Step 5: 汇报**

---

### Task 4: Provider 扩展（TDD）

**Files:**
- Modify: `mobile/lib/features/recipes/providers/recipe_provider.dart`
- Test: `mobile/test/features/recipes/providers/recipe_provider_test.dart`

- [ ] **Step 1: 写失败测试**

```dart
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
          RecipeIngredient(id: 10, ingredientId: 5, name: '鸡蛋', quantity: '100', unit: 'g'),
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
            quantity: 100, quantityUnit: 'g'))
        .thenAnswer((_) async => priceItem);

    await notifier.load();
    await settle();

    expect(notifier.state.detail?.name, '番茄炒蛋');
    expect(notifier.state.merchantCosts?.merchants.first.merchantName, '盒马');
    expect(notifier.state.merchantPrices.length, 1);
    expect(notifier.state.merchantPrices.first.ingredientName, '鸡蛋');
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
}
```

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/providers/recipe_provider_test.dart
```

Expected: FAIL（merchantCosts / loadingMerchantCosts 字段不存在）。

- [ ] **Step 3: 实现**

`RecipeDetailPageState` 增加字段与 copyWith 参数：

```dart
  final RecipeMerchantCost? merchantCosts;
  final List<MerchantPriceItem> merchantPrices;
  final bool loadingMerchantCosts;
  final bool loadingMerchantPrices;
```

构造函数默认值：`this.merchantCosts, this.merchantPrices = const [], this.loadingMerchantCosts = false, this.loadingMerchantPrices = false`；copyWith 对应增加。

`RecipeDetailPageNotifier` 的 `load()` 中，在 `_loadHistory()` 后追加：

```dart
      _loadMerchantCosts();
      _loadMerchantPrices();
```

新增两个方法（异常捕获不阻断，对齐 web catch 忽略）：

```dart
  Future<void> _loadMerchantCosts() async {
    state = state.copyWith(loadingMerchantCosts: true);
    try {
      final costs = await _repo.getRecipeMerchantCosts(recipeId);
      state = state.copyWith(merchantCosts: costs, loadingMerchantCosts: false);
    } on Exception catch (_) {
      state = state.copyWith(loadingMerchantCosts: false);
    }
  }

  Future<void> _loadMerchantPrices() async {
    final detail = state.detail;
    if (detail == null) return;
    final ingredients =
        detail.ingredients.where((i) => i.ingredientId != null).toList();
    if (ingredients.isEmpty) return;
    state = state.copyWith(loadingMerchantPrices: true);
    try {
      // 并发控制对齐 web：每批 3 个 + 全局 35s 超时，保留已有部分结果
      final results = <MerchantPriceItem>[];
      final start = DateTime.now();
      const concurrency = 3;
      const globalTimeout = Duration(seconds: 35);
      for (var i = 0; i < ingredients.length; i += concurrency) {
        if (DateTime.now().difference(start) > globalTimeout) break;
        final batch = ingredients.sublist(
            i, (i + concurrency).clamp(0, ingredients.length));
        final futures = batch.map((ing) async {
          final q = resolveIngredientQuantity(ing);
          try {
            return await _repo.getIngredientMerchantPrice(ing.ingredientId!,
                quantity: q.qty, quantityUnit: q.qtyUnit);
          } catch (_) {
            return null;
          }
        });
        final settled = await Future.wait(futures);
        results.addAll(settled.whereType<MerchantPriceItem>());
      }
      state = state.copyWith(
          merchantPrices: results, loadingMerchantPrices: false);
    } on Exception catch (_) {
      state = state.copyWith(loadingMerchantPrices: false);
    }
  }
```

注：web 端 `getEffectiveQuantity` 返回的 qtyDisplay 不传给后端（只有 quantity/quantity_unit），此处 `resolveIngredientQuantity` 的 qtyDisplay 仅前端展示用。

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/providers/recipe_provider_test.dart
```

Expected: PASS（2 个测试）。若 mock 数量不匹配报错，检查 `getIngredientMerchantPrice` 的 when 是否覆盖了「有 qty」与「无 qty」两种调用（`resolveIngredientQuantity` 对无 quantity 的食材返回 null qty → 调用不带 quantity 参数，用 `any()` 兜底 or 单独 when）。

- [ ] **Step 5: 汇报**

---

### Task 5: 成本占比环形饼图组件（TDD）

**Files:**
- Create: `mobile/lib/features/recipes/widgets/cost_proportion_chart.dart`
- Test: `mobile/test/features/recipes/widgets/cost_proportion_chart_test.dart`

- [ ] **Step 1: 写失败测试（数据构建逻辑抽为纯函数测试）**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/cost_proportion_chart.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

void main() {
  group('buildCostProportionItems', () {
    test('降序排列，前 5 + 其他合并', () {
      final items = buildCostProportionItems([
        CostBreakdownItem(
            ingredientName: 'a', ingredientId: 1, cost: 1, unitPrice: 0),
        CostBreakdownItem(
            ingredientName: 'b', ingredientId: 2, cost: 5, unitPrice: 0),
        CostBreakdownItem(
            ingredientName: 'c', ingredientId: 3, cost: 2, unitPrice: 0),
        CostBreakdownItem(
            ingredientName: 'd', ingredientId: 4, cost: 4, unitPrice: 0),
        CostBreakdownItem(
            ingredientName: 'e', ingredientId: 5, cost: 3, unitPrice: 0),
        CostBreakdownItem(
            ingredientName: 'f', ingredientId: 6, cost: 6, unitPrice: 0),
        CostBreakdownItem(
            ingredientName: 'g', ingredientId: 7, cost: 7, unitPrice: 0),
      ]);
      expect(items.length, 6); // 前 5 + 其他
      expect(items.first.name, 'g');
      expect(items[1].name, 'f');
      expect(items.last.name, '其他');
      expect(items.last.value, 10); // 1+2+3+4
    });

    test('少于 6 项不合并', () {
      final items = buildCostProportionItems([
        CostBreakdownItem(
            ingredientName: 'a', ingredientId: 1, cost: 1, unitPrice: 0),
        CostBreakdownItem(
            ingredientName: 'b', ingredientId: 2, cost: 2, unitPrice: 0),
      ]);
      expect(items.length, 2);
      expect(items.first.name, 'b');
    });

    test('空数据返回空列表', () {
      expect(buildCostProportionItems([]), isEmpty);
    });
  });
}
```

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_proportion_chart_test.dart
```

Expected: FAIL（buildCostProportionItems 未定义）。

- [ ] **Step 3: 实现组件**

```dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../repositories/recipe_repository.dart';
import '../utils/ingredient_colors.dart';

/// 单个成本占比扇区
class CostProportionItem {
  final String name;
  final double value;
  final Color color;
  const CostProportionItem(
      {required this.name, required this.value, required this.color});
}

/// 构建成本占比数据：降序，前 5 + 其余合并为「其他」（对齐 web CostProportionChart）。
List<CostProportionItem> buildCostProportionItems(
    List<CostBreakdownItem> breakdown) {
  if (breakdown.isEmpty) return const [];
  final items = breakdown
      .map((b) => CostProportionItem(
          name: b.ingredientName.isEmpty ? '未知食材' : b.ingredientName,
          value: b.cost,
          color: getIngredientColor(b.ingredientId)))
      .toList()
    ..sort((a, b) => b.value.compareTo(a.value));
  if (items.length > 6) {
    final top5 = items.sublist(0, 5);
    final otherValue = items.sublist(5).fold<double>(0, (s, i) => s + i.value);
    top5.add(CostProportionItem(
        name: '其他', value: otherValue, color: const Color(0xFFE0E0E0)));
    return top5;
  }
  return items;
}

/// 食材成本占比环形饼图（中心显示总价，扇区标题=名称+百分比，点击扇区显示金额）。
class CostProportionChart extends StatefulWidget {
  final List<CostBreakdownItem> breakdown;
  final double totalCost;
  final bool loading;
  const CostProportionChart({
    super.key,
    required this.breakdown,
    required this.totalCost,
    this.loading = false,
  });

  @override
  State<CostProportionChart> createState() => _CostProportionChartState();
}

class _CostProportionChartState extends State<CostProportionChart> {
  int _touchedIndex = -1;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.pie_chart_outline,
                  color: theme.colorScheme.tertiary, size: 20),
              const SizedBox(width: 8),
              Text('食材成本占比',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
            ]),
            const SizedBox(height: 12),
            if (widget.loading)
              const SizedBox(
                  height: 220,
                  child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2)))
            else if (widget.breakdown.isEmpty)
              const SizedBox(
                height: 220,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.pie_chart_outline,
                          size: 40, color: Colors.grey),
                      SizedBox(height: 8),
                      Text('暂无成本数据',
                          style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                ),
              )
            else
              _buildChart(theme),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(ThemeData theme) {
    final items = buildCostProportionItems(widget.breakdown);
    final total = widget.totalCost > 0
        ? widget.totalCost
        : items.fold<double>(0, (s, i) => s + i.value);
    return Column(
      children: [
        SizedBox(
          height: 220,
          child: Stack(
            alignment: Alignment.center,
            children: [
              PieChart(
                PieChartData(
                  centerSpaceRadius: 52,
                  sectionsSpace: 2,
                  startDegreeOffset: -90,
                  pieTouchData: PieTouchData(
                    touchCallback: (event, response) {
                      if (event is FlTapUpEvent && response != null) {
                        final i = response.touchedSection?.touchedSectionIndex;
                        setState(() => _touchedIndex = i ?? -1);
                      }
                    },
                  ),
                  sections: items.asMap().entries.map((e) {
                    final i = e.key;
                    final item = e.value;
                    final isTouched = i == _touchedIndex;
                    return PieChartSectionData(
                      value: item.value,
                      color: item.color,
                      radius: isTouched ? 78 : 70,
                      showTitle: true,
                      title: '${item.name}\n${_pct(item, total)}',
                      titleStyle: TextStyle(
                          fontSize: isTouched ? 11 : 10,
                          fontWeight: FontWeight.w600,
                          color: Colors.black87),
                      titlePositionPercentageOffset: 0.62,
                      borderSide: BorderSide(
                          color: theme.colorScheme.surface, width: 2),
                    );
                  }).toList(),
                ),
              ),
              // 中心总价
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('总成本',
                      style: theme.textTheme.labelSmall
                          ?.copyWith(color: theme.colorScheme.outline)),
                  Text('¥${total.toStringAsFixed(2)}',
                      style: theme.textTheme.titleLarge
                          ?.copyWith(fontWeight: FontWeight.bold)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        // 图例（点击显示金额明细）
        Wrap(
          spacing: 12,
          runSpacing: 6,
          children: items.asMap().entries.map((e) {
            final item = e.value;
            return InkWell(
              onTap: () => setState(() => _touchedIndex = e.key),
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _touchedIndex == e.key
                      ? item.color.withValues(alpha: 0.2)
                      : null,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                        width: 10,
                        height: 10,
                        decoration: BoxDecoration(
                            color: item.color,
                            shape: BoxShape.circle)),
                    const SizedBox(width: 4),
                    Text(item.name,
                        style: theme.textTheme.labelSmall),
                    const SizedBox(width: 4),
                    Text(
                      _touchedIndex == e.key
                          ? '¥${item.value.toStringAsFixed(2)}'
                          : _pct(item, total),
                      style: theme.textTheme.labelSmall
                          ?.copyWith(color: theme.colorScheme.outline),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  String _pct(CostProportionItem item, double total) {
    if (total <= 0) return '';
    final pct = item.value / total * 100;
    return '${pct.toStringAsFixed(pct >= 100 ? 0 : 1)}%';
  }
}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_proportion_chart_test.dart
```

Expected: PASS（3 个测试）。

- [ ] **Step 5: 汇报**

---

### Task 6: 成本趋势堆叠面积图组件（TDD）

**Files:**
- Create: `mobile/lib/features/recipes/widgets/cost_trend_stacked_chart.dart`
- Test: `mobile/test/features/recipes/widgets/cost_trend_stacked_chart_test.dart`

- [ ] **Step 1: 写失败测试（堆叠累加抽为纯函数测试）**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/cost_trend_stacked_chart.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

void main() {
  group('buildStackedSeries', () {
    test('按食材累加 y 值实现堆叠', () {
      final points = [
        CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2, breakdown: [
          CostHistoryBreakdownItem(ingredientId: 1, ingredientName: '鸡蛋', cost: 2),
          CostHistoryBreakdownItem(ingredientId: 2, ingredientName: '番茄', cost: 3),
        ]),
        CostHistoryPoint(date: '07-02', minCost: 1, maxCost: 4, avgCost: 3, breakdown: [
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
        CostHistoryPoint(date: '07-01', minCost: 1, maxCost: 3, avgCost: 2),
      ];
      expect(buildStackedSeries(points), isEmpty);
    });
  });

  group('costHistoryDays', () {
    test('筛选映射 周/月/季/年/全部', () {
      expect(costHistoryDays('week'), 7);
      expect(costHistoryDays('month'), 30);
      expect(costHistoryDays('quarter'), 90);
      expect(costHistoryDays('year'), 365);
      expect(costHistoryDays('all'), 3650);
    });
  });
}
```

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_trend_stacked_chart_test.dart
```

Expected: FAIL（buildStackedSeries / costHistoryDays 未定义）。

- [ ] **Step 3: 实现组件**

```dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../repositories/recipe_repository.dart';
import '../utils/ingredient_colors.dart';

const costHistoryDays = <String, int>{
  'week': 7, 'month': 30, 'quarter': 90, 'year': 365, 'all': 3650,
};

/// 堆叠面积图单条序列
class StackedSeries {
  final String name;
  final Color color;
  final List<FlSpot> spots;
  const StackedSeries(
      {required this.name, required this.color, required this.spots});
}

/// 从成本历史构建堆叠序列：每食材一条线，y 按「本食材成本 + 前面所有食材成本」累加
/// （对齐 web echarts stack:'total'）。无 breakdown 时返回空列表。
List<StackedSeries> buildStackedSeries(List<CostHistoryPoint> points) {
  if (points.isEmpty) return const [];
  final hasBreakdown = points.any((p) => p.breakdown.isNotEmpty);
  if (!hasBreakdown) return const [];

  // 收集所有食材（按首次出现顺序 + 成本降序？web 按 breakdown 首次收集顺序）
  final ingOrder = <int, String>{};
  for (final p in points) {
    for (final b in p.breakdown) {
      ingOrder.putIfAbsent(b.ingredientId ?? 0, () => b.ingredientName);
    }
  }

  final running = <int, double>{};
  final series = <StackedSeries>[];
  for (final entry in ingOrder.entries) {
    final spots = <FlSpot>[];
    for (var i = 0; i < points.length; i++) {
      final day = points[i];
      final cost = day.breakdown
          .firstWhere((b) => b.ingredientId == entry.key,
              orElse: () =>
                  CostHistoryBreakdownItem(
                      ingredientId: entry.key,
                      ingredientName: entry.value,
                      cost: 0))
          .cost;
      running[entry.key] = (running[entry.key] ?? 0) + cost;
      spots.add(FlSpot(i.toDouble(), running[entry.key] ?? 0));
    }
    series.add(StackedSeries(
      name: entry.value,
      color: getIngredientColor(entry.key == 0 ? null : entry.key),
      spots: spots,
    ));
  }
  return series;
}

/// 成本趋势堆叠面积图：周/月/季/年/全部筛选 + 食材标签点击高亮；
/// 无 breakdown 数据时回退 avg/min/max 折线+区间（对齐 web CostTrendAnalysis）。
class CostTrendStackedChart extends StatefulWidget {
  final List<CostHistoryPoint> points;
  final bool loading;
  final String unit;
  final ValueChanged<String>? onFilterChange;
  const CostTrendStackedChart({
    super.key,
    required this.points,
    this.loading = false,
    this.unit = '元',
    this.onFilterChange,
  });

  @override
  State<CostTrendStackedChart> createState() => _CostTrendStackedChartState();
}

class _CostTrendStackedChartState extends State<CostTrendStackedChart> {
  String _filter = 'quarter';
  int? _highlightIndex;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.show_chart, color: theme.colorScheme.tertiary, size: 20),
              const SizedBox(width: 8),
              Text('成本趋势',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const Spacer(),
              _buildFilterToggle(theme),
            ]),
            const SizedBox(height: 12),
            SizedBox(height: 200, child: _buildBody(theme)),
            if (widget.points.any((p) => p.breakdown.isNotEmpty)) ...[
              const SizedBox(height: 12),
              _buildIngredientTags(theme),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFilterToggle(ThemeData theme) {
    const labels = {'week': '周', 'month': '月', 'quarter': '季', 'year': '年', 'all': '全部'};
    return SegmentedButton<String>(
      style: const ButtonStyle(
        visualDensity: VisualDensity.compact,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        textStyle: WidgetStatePropertyAll(TextStyle(fontSize: 11)),
      ),
      segments: labels.keys
          .map((k) => ButtonSegment(value: k, label: Text(labels[k]!)))
          .toList(),
      selected: {_filter},
      onSelectionChanged: (s) {
        setState(() => _filter = s.first);
        widget.onFilterChange?.call(_filter);
      },
    );
  }

  Widget _buildBody(ThemeData theme) {
    if (widget.loading && widget.points.isEmpty) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    }
    if (widget.points.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.show_chart, size: 40, color: theme.colorScheme.outline),
            const SizedBox(height: 8),
            Text('暂无成本趋势数据',
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.outline)),
          ],
        ),
      );
    }
    final series = buildStackedSeries(widget.points);
    if (series.isEmpty) return _buildFallbackLineChart(theme);
    return _buildStackedChart(theme, series);
  }

  Widget _buildStackedChart(ThemeData theme, List<StackedSeries> series) {
    final isHighlighted = _highlightIndex != null;
    final lineBars = series.asMap().entries.map((e) {
      final i = e.key;
      final s = e.value;
      final highlight = _highlightIndex == i;
      final dimmed = isHighlighted && !highlight;
      return LineChartBarData(
        spots: s.spots,
        color: s.color,
        barWidth: highlight ? 2.5 : 1.5,
        isCurved: true,
        curveSmoothness: 0.35,
        dotData: const FlDotData(show: false),
        belowBarData: BarAreaData(
          show: true,
          color: s.color.withValues(alpha: dimmed ? 0.05 : 0.30),
        ),
      );
    }).toList();

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: 1,
          getDrawingHorizontalLine: (v) => FlLine(
              color: theme.colorScheme.outlineVariant, strokeWidth: 0.5),
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              getTitlesWidget: (v, meta) =>
                  Text('¥${v.toInt()}',
                      style: const TextStyle(fontSize: 9, color: Colors.grey)),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 1,
              getTitlesWidget: (v, meta) {
                final i = v.toInt();
                if (i < 0 || i >= widget.points.length) {
                  return const SizedBox.shrink();
                }
                final idxList = {0, widget.points.length ~/ 2, widget.points.length - 1};
                if (!idxList.contains(i)) return const SizedBox.shrink();
                final date = widget.points[i].date;
                final label = date.length >= 5 ? date.substring(5) : date;
                return Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(label,
                      style:
                          const TextStyle(fontSize: 9, color: Colors.grey)),
                );
              },
            ),
          ),
          topTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) {
              final items = <LineTooltipItem>[];
              // 逆推每食材本日成本 = 累加值差值
              final date = widget.points[touchedSpots.first.x.toInt()].date;
              items.add(LineTooltipItem('$date\n',
                  const TextStyle(
                      fontWeight: FontWeight.bold, color: Colors.white)));
              var prev = 0.0;
              for (final spot in touchedSpots) {
                items.add(LineTooltipItem(
                    '${series[spot.barIndex].name}: ¥${(spot.y - prev).toStringAsFixed(2)}\n',
                    const TextStyle(color: Colors.white)));
                prev = spot.y;
              }
              items.add(LineTooltipItem(
                  '合计: ¥${touchedSpots.last.y.toStringAsFixed(2)}',
                  const TextStyle(
                      fontWeight: FontWeight.bold, color: Colors.white)));
              return items;
            },
          ),
        ),
        lineBarsData: lineBars,
      ),
    );
  }

  // 回退：avg/min/max 折线+区间（对齐 web 无 breakdown 时的回退图）
  Widget _buildFallbackLineChart(ThemeData theme) {
    final points = widget.points;
    final avg = LineChartBarData(
      spots: [
        for (var i = 0; i < points.length; i++)
          FlSpot(i.toDouble(), points[i].avgCost)
      ],
      color: const Color(0xFFFF9800),
      barWidth: 2,
      isCurved: true,
      dotData: const FlDotData(show: false),
      belowBarData: BarAreaData(
        show: true,
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFFFF9800).withValues(alpha: 0.25),
            const Color(0xFFFF9800).withValues(alpha: 0.02),
          ],
        ),
      ),
    );
    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (v) =>
              FlLine(color: theme.colorScheme.outlineVariant, strokeWidth: 0.5),
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              getTitlesWidget: (v, meta) =>
                  Text('¥${v.toInt()}',
                      style: const TextStyle(fontSize: 9, color: Colors.grey)),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 1,
              getTitlesWidget: (v, meta) {
                final i = v.toInt();
                if (i < 0 || i >= points.length) return const SizedBox.shrink();
                if (!{0, points.length ~/ 2, points.length - 1}.contains(i)) {
                  return const SizedBox.shrink();
                }
                final date = points[i].date;
                final label = date.length >= 5 ? date.substring(5) : date;
                return Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(label,
                      style: const TextStyle(fontSize: 9, color: Colors.grey)),
                );
              },
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) {
              final date = points[touchedSpots.first.x.toInt()].date;
              return [
                LineTooltipItem('$date\n',
                    const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                LineTooltipItem('均价: ¥${points[touchedSpots.first.x.toInt()].avgCost.toStringAsFixed(2)}\n',
                    const TextStyle(color: Colors.white)),
                LineTooltipItem('区间: ¥${points[touchedSpots.first.x.toInt()].minCost.toStringAsFixed(2)} ~ ¥${points[touchedSpots.first.x.toInt()].maxCost.toStringAsFixed(2)}',
                    const TextStyle(color: Colors.white)),
              ];
            },
          ),
        ),
        lineBarsData: [avg],
      ),
    );
  }

  // 食材标签（点击高亮/取消，对齐 web toggleIngredientHighlight）
  Widget _buildIngredientTags(ThemeData theme) {
    final series = buildStackedSeries(widget.points);
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: series.asMap().entries.map((e) {
        final i = e.key;
        final s = e.value;
        final selected = _highlightIndex == i;
        return ActionChip(
          avatar: Icon(Icons.circle, size: 12, color: s.color),
          label: Text(s.name,
              style: TextStyle(fontWeight: selected ? FontWeight.bold : null)),
          visualDensity: VisualDensity.compact,
          side: BorderSide(
              color: selected ? s.color : theme.colorScheme.outlineVariant),
          onPressed: () => setState(() {
            _highlightIndex = selected ? null : i;
          }),
        );
      }).toList(),
    );
  }
}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/cost_trend_stacked_chart_test.dart
```

Expected: PASS（3 个测试）。

- [ ] **Step 5: 汇报**

---

### Task 7: 营养贡献溯源组件（TDD）

**Files:**
- Create: `mobile/lib/features/recipes/widgets/nutrition_source_grid.dart`
- Test: `mobile/test/features/recipes/widgets/nutrition_source_grid_test.dart`

- [ ] **Step 1: 写失败测试（营养数据构建抽为纯函数）**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/nutrition_source_grid.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

/// 注意：perServingNutrients 的 key 为英文（对齐后端 core_nutrients），
/// 实现按 nrvLabels 映射中文名；空 map 会导致 buildNutrientDisplays 直接返回空。
RecipeNutrition _nutrition() => RecipeNutrition(
      totalCalories: 300,
      totalProtein: 10,
      totalFat: 8,
      totalCarbs: 20,
      perServingNutrients: const {
        'protein': NutritionItem(value: 6, unit: 'g', nrpPct: 10, key: 'protein'),
        'fat': NutritionItem(value: 5, unit: 'g', nrpPct: 7, key: 'fat'),
      },
      allNutrients: const {},
      ingredientDetails: [
        IngredientNutritionDetail(
          recipeIngredientId: 1,
          ingredientId: 1,
          ingredientName: '鸡蛋',
          nutritionContribution: {
            '蛋白质': NutritionItem(value: 6, unit: 'g'),
            '脂肪': NutritionItem(value: 5, unit: 'g'),
          },
        ),
        IngredientNutritionDetail(
          recipeIngredientId: 2,
          ingredientId: 2,
          ingredientName: '番茄',
          nutritionContribution: {
            '蛋白质': NutritionItem(value: 1, unit: 'g'),
          },
        ),
      ],
    );

void main() {
  group('buildNutrientDisplays', () {
    test('构建营养素列表（含总量与 Top2 贡献）', () {
      final result = buildNutrientDisplays(_nutrition(), showAll: false);
      // 蛋白质（6+1=7g，Top2 鸡蛋86%/番茄14%）与脂肪（5g）
      expect(result.length, greaterThanOrEqualTo(2));
      final protein = result.firstWhere((d) => d.label == '蛋白质');
      expect(protein.totalText, isNotEmpty);
      expect(protein.items.length, 2);
      expect(protein.items.first.name, '鸡蛋');
      expect(protein.items.first.value, 6);
      expect(protein.topContributors, contains('鸡蛋'));
      expect(protein.topContributors, contains('番茄'));
      // NRV% 从 perServing 的 nrpPct 读
      expect(protein.nrpPct, 10);
    });

    test('排序：能量 > 蛋白质 > 脂肪 > 碳水化合物 > 钠', () {
      final result = buildNutrientDisplays(_nutrition(), showAll: false);
      final labels = result.map((d) => d.label).toList();
      for (var i = 1; i < labels.length; i++) {
        // 使用 sortIndex 验证有序
        expect(sortIndex(labels[i - 1]) <= sortIndex(labels[i]), true,
            reason: '${labels[i - 1]} 应排在 ${labels[i]} 前');
      }
    });

    test('showAll=false 过滤非 NRV 指标', () {
      final filtered = buildNutrientDisplays(_nutrition(), showAll: false);
      expect(filtered.any((d) => d.key == 'protein'), true);
      // 非 NRV 键（如 'water'）在 showAll=false 时不出现
      expect(filtered.any((d) => d.key == 'water'), false);
    });
  });
}
```

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/nutrition_source_grid_test.dart
```

Expected: FAIL（buildNutrientDisplays 未定义）。

- [ ] **Step 3: 实现组件**

```dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../repositories/recipe_repository.dart';
import '../utils/ingredient_colors.dart';

/// NRV 指标白名单（对齐 web NRV_KEYS）
const nrvKeys = <String>{
  'energy', 'protein', 'fat', 'carbohydrate', 'fiber',
  'calcium', 'iron', 'sodium', 'potassium',
  'vitamin_a_rae', 'vitamin_c', 'vitamin_b1', 'vitamin_b2',
  'vitamin_b12', 'vitamin_d', 'vitamin_e', 'vitamin_k',
};

/// NRV 中文名（对齐 web NRV_LABELS）
const nrvLabels = <String, String>{
  'energy': '能量', 'protein': '蛋白质', 'fat': '脂肪', 'carbohydrate': '碳水化合物',
  'fiber': '膳食纤维', 'calcium': '钙', 'iron': '铁', 'sodium': '钠', 'potassium': '钾',
  'vitamin_a_rae': '维生素A', 'vitamin_c': '维生素C', 'vitamin_b1': '维生素B1',
  'vitamin_b2': '维生素B2', 'vitamin_b12': '维生素B12', 'vitamin_d': '维生素D',
  'vitamin_e': '维生素E', 'vitamin_k': '维生素K',
};

/// 营养排序（对齐 web nutrientSortOrder 前 17 项）
const _nutrientSortOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '钠',
  '膳食纤维', '钙', '铁', '钾',
  '维生素A', '维生素B1', '维生素B2', '维生素B12', '维生素C',
  '维生素D', '维生素E', '维生素K',
];

int sortIndex(String label) {
  final i = _nutrientSortOrder.indexOf(label);
  return i == -1 ? _nutrientSortOrder.length + label.length : i;
}

/// 单个营养素展示数据
class NutrientDisplay {
  final String key;
  final String label;
  final String totalText;
  final int? nrpPct;
  final String topContributors;
  final List<NutrientContributor> items;
  const NutrientDisplay({
    required this.key,
    required this.label,
    required this.totalText,
    this.nrpPct,
    required this.topContributors,
    required this.items,
  });
}

class NutrientContributor {
  final String name;
  final double value;
  final Color color;
  const NutrientContributor(
      {required this.name, required this.value, required this.color});
}

/// 构建营养溯源展示数据（对齐 web displayNutrients 逻辑：NRV 过滤、同名去重、Top2 贡献）
List<NutrientDisplay> buildNutrientDisplays(RecipeNutrition nutrition,
    {required bool showAll}) {
  final perServing = nutrition.perServingNutrients;
  if (perServing.isEmpty) return const [];
  final all = {...nutrition.allNutrients, ...perServing};

  // NRV 百分比映射（core 条目带 nrp_pct）
  final nrpPctMap = <String, double>{};
  for (final entry in perServing.entries) {
    final item = entry.value;
    if (item.key != null && item.nrpPct > 0) {
      nrpPctMap[item.key!] = item.nrpPct;
    }
  }

  final result = <NutrientDisplay>[];
  final usedLabels = <String>{};
  for (final entry in all.entries) {
    final key = entry.key;
    final item = entry.value;
    if (item.value <= 0) continue;
    final isNrv = nrvKeys.contains(key);
    if (!showAll && !isNrv) continue;

    // 中文名：perServing 的 key 已是中文；英文键映射
    final label = nrvLabels[key] ?? item.nameZh ?? key;
    if (showAll && usedLabels.contains(label)) continue;
    usedLabels.add(label);

    final contributors = <NutrientContributor>[];
    for (final d in nutrition.ingredientDetails) {
      final c = d.nutritionContribution[label] ??
          d.nutritionContribution[key];
      if (c != null && c.value > 0) {
        contributors.add(NutrientContributor(
          name: d.ingredientName.isEmpty ? '未知食材' : d.ingredientName,
          value: c.value,
          color: getIngredientColor(d.ingredientId),
        ));
      }
    }
    if (contributors.isEmpty) continue;
    contributors.sort((a, b) => b.value.compareTo(a.value));

    final total = contributors.fold<double>(0, (s, c) => s + c.value);
    final top2 = contributors.take(2).map((c) =>
        '${c.name} ${total > 0 ? (c.value / total * 100).round() : 0}%').join(' · ');

    result.add(NutrientDisplay(
      key: key,
      label: label,
      totalText: '${_fmt(item.value)}${item.unit}',
      nrpPct: item.nrpPct > 0
          ? item.nrpPct.round()
          : (nrpPctMap[key] ?? 0) > 0
              ? nrpPctMap[key]!.round()
              : null,
      topContributors: top2,
      items: contributors,
    ));
  }
  result.sort((a, b) => sortIndex(a.label).compareTo(sortIndex(b.label)));
  return result;
}

String _fmt(double v) => v == v.roundToDouble()
    ? v.toStringAsFixed(0)
    : v.toStringAsFixed(2);

/// 营养贡献溯源：迷你环形图网格（中心 NRV%），NRV 指标/全部切换（对齐 web NutritionSourceGrid）。
class NutritionSourceGrid extends StatefulWidget {
  final RecipeNutrition? nutrition;
  final bool loading;
  const NutritionSourceGrid({super.key, this.nutrition, this.loading = false});

  @override
  State<NutritionSourceGrid> createState() => _NutritionSourceGridState();
}

class _NutritionSourceGridState extends State<NutritionSourceGrid> {
  bool _showAll = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.food_bank_outlined,
                  color: theme.colorScheme.primary, size: 20),
              const SizedBox(width: 8),
              Text('营养贡献溯源',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const Spacer(),
              SegmentedButton<bool>(
                style: const ButtonStyle(
                  visualDensity: VisualDensity.compact,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  textStyle: WidgetStatePropertyAll(TextStyle(fontSize: 11)),
                ),
                segments: const [
                  ButtonSegment(value: false, label: Text('NRV 指标')),
                  ButtonSegment(value: true, label: Text('全部')),
                ],
                selected: {_showAll},
                onSelectionChanged: (s) => setState(() => _showAll = s.first),
              ),
            ]),
            const SizedBox(height: 12),
            if (widget.loading)
              const SizedBox(
                  height: 120,
                  child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2)))
            else if (widget.nutrition == null)
              const SizedBox(
                height: 120,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.food_bank_outlined,
                          size: 40, color: Colors.grey),
                      SizedBox(height: 8),
                      Text('暂无营养数据', style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                ),
              )
            else
              _buildGrid(theme),
          ],
        ),
      ),
    );
  }

  Widget _buildGrid(ThemeData theme) {
    final displays =
        buildNutrientDisplays(widget.nutrition!, showAll: _showAll);
    if (displays.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(
            child: Text('暂无营养数据', style: TextStyle(color: Colors.grey))),
      );
    }
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 0.95,
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      children: displays.map((d) => _buildDonutCard(theme, d)).toList(),
    );
  }

  Widget _buildDonutCard(ThemeData theme, NutrientDisplay d) {
    final total = d.items.fold<double>(0, (s, i) => s + i.value);
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest
            .withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(d.label,
              style: theme.textTheme.labelLarge
                  ?.copyWith(fontWeight: FontWeight.w500),
              textAlign: TextAlign.center),
          const SizedBox(height: 4),
          SizedBox(
            height: 90,
            width: 90,
            child: Stack(
              alignment: Alignment.center,
              children: [
                PieChart(PieChartData(
                  centerSpaceRadius: 26,
                  sectionsSpace: 1,
                  startDegreeOffset: -90,
                  sections: d.items.map((c) {
                    return PieChartSectionData(
                      value: c.value,
                      color: c.color,
                      radius: 36,
                      showTitle: false,
                    );
                  }).toList(),
                )),
                if (d.nrpPct != null)
                  Text('${d.nrpPct}%',
                      style: theme.textTheme.labelSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          const SizedBox(height: 4),
          Text(d.totalText,
              style: theme.textTheme.labelSmall
                  ?.copyWith(color: theme.colorScheme.outline)),
          const SizedBox(height: 2),
          Text(d.topContributors,
              style: theme.textTheme.labelSmall
                  ?.copyWith(color: theme.colorScheme.outline, fontSize: 10),
              maxLines: 1,
              overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/nutrition_source_grid_test.dart
```

Expected: PASS（2 个测试）。

- [ ] **Step 5: 汇报**

---

### Task 8: 按商家预估成本卡片（TDD）

**Files:**
- Create: `mobile/lib/features/recipes/widgets/merchant_cost_cards.dart`
- Test: `mobile/test/features/recipes/widgets/merchant_cost_cards_test.dart`

- [ ] **Step 1: 写失败测试**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/merchant_cost_cards.dart';

void main() {
  group('MerchantCostCards', () {
    testWidgets('渲染商家卡片：名称/总价/覆盖数/需外购', (tester) async {
      await tester.pumpWidget(MaterialApp(
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

    testWidgets('空数据显示空态', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(body: MerchantCostCards(merchants: [], loading: false)),
      ));
      expect(find.text('暂无商家价格数据'), findsOneWidget);
    });
  });
}
```

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/merchant_cost_cards_test.dart
```

Expected: FAIL（MerchantCostCards 未定义）。

- [ ] **Step 3: 实现组件**

```dart
import 'package:flutter/material.dart';
import '../repositories/recipe_repository.dart';

/// 按商家预估成本：横向滚动卡片（对齐 web MerchantCostCards）。
class MerchantCostCards extends StatelessWidget {
  final List<MerchantCostItem> merchants;
  final bool loading;
  const MerchantCostCards(
      {super.key, required this.merchants, this.loading = false});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Icon(Icons.store_outlined, color: theme.colorScheme.primary, size: 20),
          const SizedBox(width: 8),
          Text('按商家预估成本',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 12),
        if (loading && merchants.isEmpty)
          const SizedBox(
            height: 140,
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          )
        else if (merchants.isEmpty)
          const SizedBox(
            height: 120,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.store_outlined, size: 40, color: Colors.grey),
                  SizedBox(height: 8),
                  Text('暂无商家价格数据', style: TextStyle(color: Colors.grey)),
                ],
              ),
            ),
          )
        else
          SizedBox(
            height: 168,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: merchants.length,
              separatorBuilder: (_, __) => const SizedBox(width: 12),
              itemBuilder: (context, i) => _buildCard(theme, merchants[i]),
            ),
          ),
      ],
    );
  }

  Widget _buildCard(ThemeData theme, MerchantCostItem m) {
    return Container(
      width: 220,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(
          color: m.isRecommended
              ? const Color(0xFFFF9800)
              : theme.colorScheme.outlineVariant,
          width: m.isRecommended ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(12),
        color: m.isRecommended
            ? const Color(0xFFFFF8E1)
            : theme.colorScheme.surface,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
              child: Text(m.merchantName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodyLarge
                      ?.copyWith(fontWeight: FontWeight.w600)),
            ),
            if (m.isRecommended)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF9800),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text('最实惠 ✓',
                    style: TextStyle(
                        fontSize: 10,
                        color: Colors.white,
                        fontWeight: FontWeight.bold)),
              ),
          ]),
          const SizedBox(height: 4),
          Row(children: [
            Text('覆盖 ${m.coveredCount}/${m.totalIngredients} 种食材',
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.outline)),
            if (m.fallbackChains.isNotEmpty) ...[
              const SizedBox(width: 4),
              IconButton(
                visualDensity: VisualDensity.compact,
                constraints: const BoxConstraints(
                    minWidth: 20, minHeight: 20),
                padding: EdgeInsets.zero,
                iconSize: 14,
                icon: Icon(Icons.info_outline,
                    color: theme.colorScheme.primary),
                onPressed: () => _showFallbackDialog(context, m),
              ),
            ],
          ]),
          const SizedBox(height: 4),
          Text('¥${m.totalCost.toStringAsFixed(2)}',
              style: theme.textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 2),
          Text.rich(TextSpan(children: [
            TextSpan(
                text: '本店 ¥${m.coveredCost.toStringAsFixed(2)}',
                style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFF2E7D32),
                    fontWeight: FontWeight.w600)),
            if (m.externalCost > 0)
              TextSpan(
                text: '  外部 ¥${m.externalCost.toStringAsFixed(2)}',
                style: const TextStyle(fontSize: 12, color: Color(0xFFEF6C00)),
              ),
          ])),
          if (m.missingIngredients.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text('⚠ 需外购 ${m.missingIngredients.join('、')}',
                style: const TextStyle(fontSize: 11, color: Color(0xFFF9A825)),
                maxLines: 1,
                overflow: TextOverflow.ellipsis),
          ],
        ],
      ),
    );
  }

  void _showFallbackDialog(BuildContext context, MerchantCostItem m) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('根据以下食材计算价格：'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final chain in m.fallbackChains)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(chain,
                    style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/merchant_cost_cards_test.dart
```

Expected: PASS（2 个测试）。若「¥11.70」断言失败，检查 toStringAsFixed 输出格式。

- [ ] **Step 5: 汇报**

---

### Task 9: 商家比价矩阵组件（TDD）

**Files:**
- Create: `mobile/lib/features/recipes/widgets/merchant_price_matrix.dart`
- Test: `mobile/test/features/recipes/widgets/merchant_price_matrix_test.dart`

- [ ] **Step 1: 写失败测试（单元格构建抽为纯函数）**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/merchant_price_matrix.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

void main() {
  group('buildMatrixRows', () {
    test('total_cost 优先、缺失显示占位', () {
      final rows = buildMatrixRows(
        ingredients: [
          RecipeIngredient(
              id: 10, ingredientId: 5, name: '鸡蛋', quantity: '100', unit: 'g'),
          RecipeIngredient(
              id: 11, ingredientId: 6, name: '番茄', quantity: '200', unit: 'g'),
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
    });
  });
}
```

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/merchant_price_matrix_test.dart
```

Expected: FAIL（buildMatrixRows 未定义）。

- [ ] **Step 3: 实现组件**

```dart
import 'package:flutter/material.dart';
import '../repositories/recipe_repository.dart';

/// 矩阵单元格
class MatrixCell {
  final String display;
  final bool isLowest;
  final bool hasPrice;
  const MatrixCell(
      {required this.display, this.isLowest = false, this.hasPrice = true});
}

/// 矩阵行
class MatrixRow {
  final String name;
  final String quantityDisplay;
  final String? fallbackChain;
  final Map<String, MatrixCell> cells;
  const MatrixRow({
    required this.name,
    required this.quantityDisplay,
    this.fallbackChain,
    required this.cells,
  });
}

/// 构建比价矩阵行（对齐 web MerchantPriceMatrix.tableRows：
/// 优先 total_cost 预估总价、回退 price 单价；is_lowest 高亮；无价格「—」）。
List<MatrixRow> buildMatrixRows({
  required List<RecipeIngredient> ingredients,
  required List<MerchantPriceItem> prices,
}) {
  if (ingredients.isEmpty) return const [];
  final names = <String>[];
  for (final p in prices) {
    for (final pr in p.prices) {
      final n = pr.merchantName.isEmpty ? '商家${pr.merchantId}' : pr.merchantName;
      if (!names.contains(n)) names.add(n);
    }
  }

  return ingredients
      .where((ing) => ing.ingredientId != null)
      .map((ing) {
        final item = prices
            .where((p) => p.recipeIngredientId == ing.id)
            .firstOrNull;
        final cells = <String, MatrixCell>{};
        for (final name in names) {
          final match = item?.prices.where((p) =>
              (p.merchantName.isEmpty ? '商家${p.merchantId}' : p.merchantName) ==
              name).firstOrNull;
          if (match != null) {
            final displayVal =
                match.totalCost ?? match.price;
            cells[name] = MatrixCell(
              display: displayVal.toStringAsFixed(2),
              isLowest: match.isLowest,
            );
          } else {
            cells[name] = const MatrixCell(
                display: '—', isLowest: false, hasPrice: false);
          }
        }
        return MatrixRow(
          name: ing.name,
          quantityDisplay: _qtyText(ing),
          fallbackChain: item?.fallbackChain,
          cells: cells,
        );
      })
      .toList();
}

String _qtyText(RecipeIngredient ing) {
  if (ing.quantityRange != null && ing.quantityRange!.min > 0) {
    return '${_fmt(ing.quantityRange!.min)}-${_fmt(ing.quantityRange!.max)}${ing.unit ?? ''}';
  }
  final q = ing.quantity;
  if (q != null && q.isNotEmpty) return '$q${ing.unit ?? ''}';
  if (ing.originalQuantity != null && ing.originalQuantity!.isNotEmpty) {
    return ing.originalQuantity!;
  }
  return '';
}

String _fmt(double v) => v == v.roundToDouble()
    ? v.toInt().toString()
    : v.toStringAsFixed(1).replaceFirst(RegExp(r'\.0$'), '');

/// 商家比价推荐矩阵：横向滚动表（行=食材，列=商家），最低价橙色加粗、缺失「—」。
class MerchantPriceMatrix extends StatelessWidget {
  final List<RecipeIngredient> ingredients;
  final List<MerchantPriceItem> prices;
  final bool loading;
  const MerchantPriceMatrix({
    super.key,
    required this.ingredients,
    required this.prices,
    this.loading = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final rows = buildMatrixRows(ingredients: ingredients, prices: prices);
    final names = <String>[];
    for (final r in rows) {
      for (final name in r.cells.keys) {
        if (!names.contains(name)) names.add(name);
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Icon(Icons.table_chart_outlined,
              color: theme.colorScheme.primary, size: 20),
          const SizedBox(width: 8),
          Text('商家比价推荐',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 12),
        if (loading && rows.isEmpty)
          const SizedBox(
            height: 100,
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          )
        else if (names.isEmpty)
          const SizedBox(
            height: 100,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.table_chart_outlined,
                      size: 40, color: Colors.grey),
                  SizedBox(height: 8),
                  Text('暂无比价数据', style: TextStyle(color: Colors.grey)),
                ],
              ),
            ),
          )
        else
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: theme.colorScheme.outlineVariant),
              borderRadius: BorderRadius.circular(12),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: _buildTable(theme, rows, names),
            ),
          ),
      ],
    );
  }

  Widget _buildTable(
      ThemeData theme, List<MatrixRow> rows, List<String> names) {
    return Table(
      columnWidths: {
        for (var i = 0; i < names.length + 1; i++)
          i: const FixedColumnWidth(110),
      },
      defaultVerticalAlignment: TableCellVerticalAlignment.middle,
      border: TableBorder(
        horizontalInside: BorderSide(
            color: theme.colorScheme.outlineVariant, width: 0.5),
        verticalInside: BorderSide(
            color: theme.colorScheme.outlineVariant, width: 0.5),
      ),
      children: [
        // 表头
        TableRow(
          decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest),
          children: [
            _headerCell(theme, '食材 / 用量'),
            for (final n in names) _headerCell(theme, n, right: true),
          ],
        ),
        for (final row in rows)
          TableRow(children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              child: Row(children: [
                Expanded(
                  child: Text(row.name,
                      style: theme.textTheme.bodyMedium
                          ?.copyWith(fontWeight: FontWeight.w500),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                ),
                if (row.fallbackChain != null && row.fallbackChain!.isNotEmpty)
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    constraints: const BoxConstraints(
                        minWidth: 20, minHeight: 20),
                    padding: EdgeInsets.zero,
                    iconSize: 14,
                    icon: Icon(Icons.info_outline,
                        color: theme.colorScheme.primary),
                    onPressed: () => showDialog<void>(
                      context: context,
                      builder: (context) => AlertDialog(
                        title: const Text('根据以下食材计算价格：'),
                        content: Text(row.fallbackChain!,
                            style:
                                const TextStyle(fontWeight: FontWeight.bold)),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.of(context).pop(),
                            child: const Text('知道了'),
                          ),
                        ],
                      ),
                    ),
                  ),
              ]),
            ),
            for (final n in names)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Flexible(
                      child: Text(
                        row.cells[n]!.display,
                        textAlign: TextAlign.right,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 13,
                          color: !row.cells[n]!.hasPrice
                              ? Colors.grey.shade300
                              : row.cells[n]!.isLowest
                                  ? const Color(0xFFE65100)
                                  : null,
                          fontWeight: row.cells[n]!.isLowest
                              ? FontWeight.bold
                              : null,
                        ),
                      ),
                    ),
                    if (row.cells[n]!.hasPrice) ...[
                      const SizedBox(width: 2),
                      Text('¥',
                          style: TextStyle(
                              fontSize: 11,
                              color: row.cells[n]!.isLowest
                                  ? const Color(0xFFE65100)
                                  : Colors.grey)),
                    ],
                  ],
                ),
              ),
          ]),
      ],
    );
  }

  Widget _headerCell(ThemeData theme, String text, {bool right = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Text(text,
          textAlign: right ? TextAlign.right : TextAlign.left,
          style: theme.textTheme.labelMedium
              ?.copyWith(fontWeight: FontWeight.w600)),
    );
  }
}
```

注意：`firstOrNull` 需要 Dart 3 集合扩展（dart:core 3.0+ 有 `Iterable.firstOrNull`？——需 `import 'package:collection/collection.dart'` 或 Dart 3 内建）。Dart 3.0 起 `firstOrNull` 属于 `package:collection` 扩展；SDK ^3.4 需在 pubspec 加 `collection` 或改用 `prices.cast<...>().where(...).isEmpty ? null : ...`。**计划采用安全的写法：用显式循环查找，避免额外依赖。**

```dart
MatrixRow _findRow(...) // 不用 firstOrNull，改用：
MerchantPriceItem? item;
for (final p in prices) {
  if (p.recipeIngredientId == ing.id) { item = p; break; }
}
// 商家匹配同理：
MerchantPriceRecord? match;
for (final pr in item?.prices ?? const <MerchantPriceRecord>[]) {
  if ((pr.merchantName.isEmpty ? '商家${pr.merchantId}' : pr.merchantName) == name) {
    match = pr;
    break;
  }
}
```

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/widgets/merchant_price_matrix_test.dart
```

Expected: PASS（1 个测试）。

- [ ] **Step 5: 汇报**

---

### Task 10: 分析页重写组装（TDD）

**Files:**
- Modify: `mobile/lib/features/recipes/screens/recipe_analysis_screen.dart`（整文件重写）
- Test: `mobile/test/features/recipes/screens/recipe_analysis_screen_test.dart`

- [ ] **Step 1: 写失败测试（页面标题与数据加载）**

只 mock `getRecipe` 成功；cost/nutrition/history/merchant 四路未 stub 时 mocktail 抛 MissingStubError，被 Notifier 内各 `_load*` 的 try/catch 吞掉（已验证现有实现全部有 `on Exception catch`），不影响 detail 渲染。

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dio/dio.dart';
import 'package:com_a4ding_livecalc/core/api/api_client.dart';
import 'package:com_a4ding_livecalc/features/recipes/screens/recipe_analysis_screen.dart';
import 'package:com_a4ding_livecalc/features/recipes/providers/recipe_provider.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

void main() {
  late MockApiClient mockClient;
  late MockDio mockDio;

  setUp(() {
    mockClient = MockApiClient();
    mockDio = MockDio();
    when(() => mockClient.dio).thenReturn(mockDio);
    when(() => mockDio.get('/recipes/1')).thenAnswer((_) async => Response(
          requestOptions: RequestOptions(path: ''),
          statusCode: 200,
          data: {
            'id': 1,
            'name': '番茄炒蛋',
            'servings': 2,
            'ingredients': [],
            'steps': [],
          },
        ));
  });

  testWidgets('数据加载后 AppBar 显示菜谱名 + 分析 chip', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [
        recipeDetailPageProvider(1).overrideWith(
            (ref) => RecipeDetailPageNotifier(
                RecipeRepository(client: mockClient), 1)),
      ],
      child: const MaterialApp(home: RecipeAnalysisScreen(id: 1)),
    ));
    await tester.pump(); // 触发 initState 中的 load()
    await tester.pump(const Duration(milliseconds: 100)); // 等待 detail 加载
    expect(find.text('番茄炒蛋'), findsOneWidget);
    expect(find.text('分析'), findsOneWidget);
  });

  testWidgets('加载失败显示错误页（标题仍为菜谱分析）', (tester) async {
    // 覆盖默认 stub 使其失败
    when(() => mockDio.get('/recipes/1')).thenAnswer(
        (_) async => throw Exception('network error'));
    await tester.pumpWidget(ProviderScope(
      overrides: [
        recipeDetailPageProvider(1).overrideWith(
            (ref) => RecipeDetailPageNotifier(
                RecipeRepository(client: mockClient), 1)),
      ],
      child: const MaterialApp(home: RecipeAnalysisScreen(id: 1)),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('菜谱分析'), findsOneWidget);
    expect(find.textContaining('network error'), findsOneWidget);
  });
}
```

注：ErrorDisplay 文案需确认渲染了错误消息文本——若项目 ErrorDisplay 只显示图标+按钮不显示 message 文本，第二个测试改为断言 `find.text('菜谱分析')` + ErrorDisplay 存在即可（用 `find.byType` 或项目实际组件）。

- [ ] **Step 2: 运行确认失败**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/screens/recipe_analysis_screen_test.dart
```

Expected: FAIL（旧页面标题「成本分析」，找不到「番茄炒蛋」+「分析」chip）。

- [ ] **Step 3: 重写分析页**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/recipe_provider.dart';
import '../widgets/cost_proportion_chart.dart';
import '../widgets/cost_trend_stacked_chart.dart';
import '../widgets/nutrition_source_grid.dart';
import '../widgets/merchant_cost_cards.dart';
import '../widgets/merchant_price_matrix.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

class RecipeAnalysisScreen extends ConsumerStatefulWidget {
  final int id;
  const RecipeAnalysisScreen({super.key, required this.id});
  @override
  ConsumerState<RecipeAnalysisScreen> createState() =>
      _RecipeAnalysisScreenState();
}

class _RecipeAnalysisScreenState extends ConsumerState<RecipeAnalysisScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      final notifier = ref.read(recipeDetailPageProvider(widget.id).notifier);
      notifier.load();
      // 趋势默认「季」90 天（对齐 web loadCostHistory('quarter')）；
      // 详情页初始 30 天由 load() 内部默认值决定，此处显式覆盖。
      notifier.reloadHistory(90);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(recipeDetailPageProvider(widget.id));
    final detail = state.detail;

    if (state.error != null && detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('菜谱分析')),
        body: ErrorDisplay(
          message: state.error!,
          onRetry: () =>
              ref.read(recipeDetailPageProvider(widget.id).notifier).load(),
        ),
      );
    }
    if (detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('菜谱分析')),
        body: const LoadingIndicator(message: '加载中...'),
      );
    }

    final breakdown = state.cost?.breakdown ?? const [];
    final totalCost = state.cost?.totalCost ?? 0;

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(detail.name,
                  maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text('分析',
                  style: theme.textTheme.labelSmall?.copyWith(
                      color: theme.colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ① 成本占比
            CostProportionChart(
              breakdown: breakdown,
              totalCost: totalCost,
              loading: state.loadingCost,
            ),
            const SizedBox(height: 16),
            // ② 成本趋势
            CostTrendStackedChart(
              points: state.costHistory,
              loading: state.loadingHistory,
              unit: '元',
              onFilterChange: (filter) {
                final days = {
                  'week': 7,
                  'month': 30,
                  'quarter': 90,
                  'year': 365,
                  'all': 3650,
                }[filter] ??
                    90;
                ref
                    .read(recipeDetailPageProvider(widget.id).notifier)
                    .reloadHistory(days);
              },
            ),
            const SizedBox(height: 16),
            // ③ 营养贡献溯源
            NutritionSourceGrid(
              nutrition: state.nutrition,
              loading: state.loadingNutrition,
            ),
            const SizedBox(height: 16),
            // ④ 按商家预估成本
            MerchantCostCards(
              merchants: state.merchantCosts?.merchants ?? const [],
              loading: state.loadingMerchantCosts,
            ),
            const SizedBox(height: 16),
            // ⑤ 商家比价推荐
            MerchantPriceMatrix(
              ingredients: detail.ingredients,
              prices: state.merchantPrices,
              loading: state.loadingMerchantPrices,
            ),
          ],
        ),
      ),
    );
  }
}
```

注意：**不改** `_loadHistory()` 的默认天数 30——详情页趋势图初始选中「月」（对应 30 天），改默认会破坏详情页初始一致性。分析页默认季由上述 `initState` 中的显式 `reloadHistory(90)` 实现。

- [ ] **Step 4: 运行确认通过**

```bash
cd d:/code/live_calc/mobile && flutter test test/features/recipes/screens/recipe_analysis_screen_test.dart
```

Expected: PASS。若 provider 注入太复杂，确保页面测试至少覆盖「加载态标题」。并跑全量测试确认无回归：

```bash
cd d:/code/live_calc/mobile && flutter test
```

- [ ] **Step 5: 汇报**

---

### Task 11: 详情页 tooltip 微调

**Files:**
- Modify: `mobile/lib/features/recipes/screens/recipe_detail_screen.dart:64`

- [ ] **Step 1: 修改 tooltip**

```dart
tooltip: '菜谱分析',
```

（原为 `tooltip: '成本分析'`）

- [ ] **Step 2: 验证**

```bash
cd d:/code/live_calc/mobile && flutter analyze
```

Expected: 无新增问题（仅剩预先存在的 avoid_print / unused 警告）。

- [ ] **Step 3: 汇报**

---

### Task 12: 整体验证

- [ ] **Step 1: 静态分析**

```bash
cd d:/code/live_calc/mobile && flutter analyze
```

Expected: 无新增告警。

- [ ] **Step 2: 全量测试**

```bash
cd d:/code/live_calc/mobile && flutter test
```

Expected: 全部 PASS（含新增的 ingredient_colors / repository / provider / 组件测试）。

- [ ] **Step 3: 桌面构建**

```bash
cd d:/code/live_calc/mobile && flutter build windows --debug
```

Expected: 构建成功（约 2 分钟）。

- [ ] **Step 4: 手动核对（可选，用户环境允许时）**

`flutter run -d windows` 运行桌面端，对照 web 端逐模块核对：
1. 标题「菜谱名 + 分析」chip
2. ① 成本占比环形图：颜色与 web 一致、中心总价、点击扇区/图例显示金额
3. ② 成本趋势：切换周/月/季/年/全部触发重新加载；食材标签点击高亮；无 breakdown 数据菜谱显示折线回退图
4. ③ 营养溯源：NRV/全部切换；迷你环形图与 Top2 贡献文案
5. ④ 商家卡片：最实惠徽章、覆盖数、本店/外部价、需外购
6. ⑤ 比价矩阵：横向滚动、最低价橙色、缺失「—」
7. 无数据菜谱（如新建空菜谱）各模块空态文案
8. 详情页右上角图标 tooltip 显示「菜谱分析」

- [ ] **Step 5: 记录要点**（按 CLAUDE.md 记录规范，写入 cc/ 目录）

---

## 自审记录

**Spec 覆盖检查：**
- 页面命名与入口（spec §1）→ Task 10 + 11 ✓
- fl_chart 依赖（spec §1 决策）→ Task 1 ✓
- repository 两个方法 + fromJson（spec §2）→ Task 3 ✓
- ingredient_colors（spec §3）→ Task 2 ✓
- provider 扩展（spec §4）→ Task 4 ✓
- 5 个组件（spec §5）→ Task 5-9 ✓
- 分析页组装（spec §6）→ Task 10 ✓
- 验证（spec §验证）→ Task 12 ✓

**已知风险与对策：**
- fl_chart 版本 API 差异：以 `flutter pub add` 安装的版本为准，若 PieChartData/LineChartData 参数名变更，按报错修正
- `firstOrNull` 避免使用（Dart 版本兼容），显式循环
- 测试中 mock 数量不匹配：mocktail 的 when 需精确匹配调用参数，`resolveIngredientQuantity` 使 `getIngredientMerchantPrice` 可能带或不带 quantity 参数，测试用 `any()` 兜底
