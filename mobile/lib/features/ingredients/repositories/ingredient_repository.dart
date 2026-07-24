import '../../../core/api/api_client.dart';
import '../models/ingredient.dart';

class IngredientRepository {
  final ApiClient _client;
  IngredientRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<List<Ingredient>> getIngredients({String? search, String? category, int page = 1, int pageSize = 50}) async {
    final params = <String, dynamic>{'page': page, 'page_size': pageSize};
    if (search != null) params['search'] = search;
    if (category != null) params['category'] = category;
    final response = await _client.dio.get('/ingredients', queryParameters: params);
    final list = response.data as List<dynamic>;
    return list.map((e) => Ingredient.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Ingredient> getIngredient(int id) async {
    final response = await _client.dio.get('/ingredients/$id');
    return Ingredient.fromJson(response.data as Map<String, dynamic>);
  }
}
