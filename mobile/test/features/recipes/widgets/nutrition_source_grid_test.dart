import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/widgets/nutrition_source_grid.dart';
import 'package:com_a4ding_livecalc/features/recipes/repositories/recipe_repository.dart';
import 'package:com_a4ding_livecalc/features/recipes/utils/ingredient_colors.dart';

/// 注意：perServingNutrients 的 key 实际为中文 display_name（后端
/// core_nutrients 以中文作键），实现靠 NutritionItem.key 字段兼容英文键映射
/// （本 fixture 用英文键 + 对应 key 字段模拟兼容场景）；空 map 会导致
/// buildNutrientDisplays 直接返回空。
RecipeNutrition _nutrition() => const RecipeNutrition(
      totalCalories: 300,
      totalProtein: 10,
      totalFat: 8,
      totalCarbs: 20,
      perServingNutrients: {
        'protein': NutritionItem(
            value: 6, unit: 'g', nrpPct: 10, key: 'protein'),
        'fat': NutritionItem(value: 5, unit: 'g', nrpPct: 7, key: 'fat'),
        // fiber 无任何食材贡献（ingredientDetails 不含 'fiber'/'膳食纤维'），
        // 用于钉住 contributors.isEmpty → continue 过滤语义
        'fiber': NutritionItem(value: 2, unit: 'g', nrpPct: 3, key: 'fiber'),
      },
      allNutrients: {
        'water': NutritionItem(value: 120, unit: 'g', nameZh: '水分'),
      },
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
            '水分': NutritionItem(value: 80, unit: 'g'),
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
      // 精确断言：showAll=false 下仅 NRV 指标，按 sortIndex 排序（蛋白质 > 脂肪）
      expect(labels, ['蛋白质', '脂肪']);
    });

    test('showAll=false 过滤非 NRV 指标', () {
      final filtered = buildNutrientDisplays(_nutrition(), showAll: false);
      expect(filtered.any((d) => d.key == 'protein'), true);
      // 非 NRV 键（如 'water'）在 showAll=false 时不出现
      expect(filtered.any((d) => d.key == 'water'), false);
    });

    test('showAll=true 显示非 NRV 指标（nameZh 兜底 + 中文 label 匹配贡献）', () {
      final all = buildNutrientDisplays(_nutrition(), showAll: true);
      // water 无 nrvLabels 映射 → 走 nameZh 兜底（'水分'）
      expect(all.any((d) => d.key == 'water'), true);
      final water = all.firstWhere((d) => d.key == 'water');
      expect(water.label, '水分');
      // 中文 label 匹配到食材贡献
      expect(water.topContributors, contains('番茄'));
    });

    test('无食材贡献的营养素被过滤（contributors.isEmpty → continue）', () {
      final result = buildNutrientDisplays(_nutrition(), showAll: true);
      // fiber 是 NRV 键、值 > 0，但无食材贡献 → 被 continue 过滤
      expect(result.any((d) => d.key == 'fiber'), false);
    });
  });

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
      // 跳过段间 1px surface 细缝（Container 内部同为 ColoredBox，按色排除）
      final surface = Theme.of(tester.element(bar)).colorScheme.surface;
      final segments = tester
          .widgetList<ColoredBox>(find.descendant(
              of: bar, matching: find.byType(ColoredBox)))
          .where((w) => w.color != surface)
          .toList();
      // 蛋白质 items=[鸡蛋6, 番茄1] → 两段，色 = 各自 getIngredientColor
      expect(segments.length, 2);
      expect(segments[0].color, getIngredientColor(1));
      expect(segments[1].color, getIngredientColor(2));
      // 段宽 = 贡献占比（flex 857:143 ≈ 6:1；1px 细缝影响可忽略）
      final w0 = tester.getSize(find.byWidget(segments[0])).width;
      final w1 = tester.getSize(find.byWidget(segments[1])).width;
      expect(w0 / w1, closeTo(6.0, 0.5));
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
}
