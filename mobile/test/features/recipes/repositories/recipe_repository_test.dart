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
      when(() => mockDio.get('/recipes/1/merchant-costs',
              options: any(named: 'options')))
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
      when(() => mockDio.get('/recipes/9/merchant-costs',
              options: any(named: 'options')))
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
      // 仓库层 quantity 为 double，Dart num 相等比较 100.0 == 100 成立
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
          recipeIngredientId: 10, ingredientName: '鸡蛋',
          quantity: 100, quantityUnit: 'g');
      expect(res.prices.length, 2);
      expect(res.prices.first.merchantName, '盒马');
      expect(res.prices.first.totalCost, 3.5);
      expect(res.prices.first.isLowest, true);
      // 第二条无 total_cost（永辉），保持 null 语义区别于 0
      expect(res.prices.last.totalCost, isNull);
      expect(res.prices.last.isLowest, false);
      expect(res.unit, 'g');
      expect(res.fallbackChain, '用面粉代替');
      // 调用方提供的字段覆盖（后端响应无这些字段）
      expect(res.recipeIngredientId, 10);
      expect(res.ingredientName, '鸡蛋');
      expect(res.ingredientId, 5);
    });

    test('quantity 为 0 时不带任何参数', () async {
      when(() => mockDio.get(
            '/nutrition/ingredients/5/latest-price-by-merchant',
            queryParameters: <String, dynamic>{},
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                statusCode: 200,
                data: {'prices': []},
              ));
      final res = await repository.getIngredientMerchantPrice(5, quantity: 0);
      expect(res.prices, isEmpty);
      expect(res.ingredientId, 5);
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
