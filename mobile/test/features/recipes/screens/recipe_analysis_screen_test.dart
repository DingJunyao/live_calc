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

    // 成功路径：菜谱详情（ingredients 为空 → _loadMerchantPrices 提前 return，
    // 无需 stub latest-price-by-merchant）
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

    // 其余 load() 触发的 dio 路径全部 stub 抛异常：
    // mocktail 未匹配的调用返回 null（_voidResponse），会以 TypeError 等
    // Error（非 Exception）形式崩溃，provider 的 on Exception catch 吞不掉，
    // 一律显式 stub。各路径按 repository 实际调用签名：
    // - /cost、/nutrition：无 queryParameters/options
    // - /cost-history-range：带 queryParameters {'days': N, 'offset_days': 0}
    //   （分析页 load(initialDays: 90) 单次请求，页面不再另行 reloadHistory）
    // - /merchant-costs：带 options: Options(receiveTimeout: 35s)
    when(() => mockDio.get('/recipes/1/cost'))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => mockDio.get('/recipes/1/nutrition'))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => mockDio.get('/recipes/1/cost-history-range',
            queryParameters: any(named: 'queryParameters')))
        .thenAnswer((_) async => throw Exception('boom'));
    when(() => mockDio.get('/recipes/1/merchant-costs',
            options: any(named: 'options')))
        .thenAnswer((_) async => throw Exception('boom'));
  });

  Widget buildApp() {
    return ProviderScope(
      overrides: [
        recipeDetailPageProvider(1).overrideWith(
            (ref) => RecipeDetailPageNotifier(
                RecipeRepository(client: mockClient), 1)),
      ],
      child: const MaterialApp(home: RecipeAnalysisScreen(id: 1)),
    );
  }

  testWidgets('数据加载后 AppBar 显示菜谱名 + 分析 chip', (tester) async {
    await tester.pumpWidget(buildApp());
    // 触发 initState 中的 load(initialDays: 90)（趋势初始天数单请求传入）
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // AppBar 标题 = 菜谱名（非旧版「番茄炒蛋 - 成本分析」单串）
    expect(find.text('番茄炒蛋'), findsOneWidget);
    // 分析 chip（独立文本节点，非 AppBar 拼接串的一部分）
    expect(find.text('分析'), findsOneWidget);
  });

  testWidgets('加载失败显示错误页（标题仍为菜谱分析）', (tester) async {
    // 覆盖默认 stub 使其失败（mocktail 按注册倒序匹配，后注册的 stub 生效）
    when(() => mockDio.get('/recipes/1'))
        .thenAnswer((_) async => throw Exception('network error'));

    await tester.pumpWidget(buildApp());
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // 错误页 AppBar 标题固定为「菜谱分析」（非旧版「成本分析」）
    expect(find.text('菜谱分析'), findsOneWidget);
    // ErrorDisplay 渲染 message 文本（e.toString() → 'Exception: network error'）
    expect(find.textContaining('network error'), findsOneWidget);
  });
}
