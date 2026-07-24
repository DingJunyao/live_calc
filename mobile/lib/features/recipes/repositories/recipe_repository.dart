import '../../../core/api/api_client.dart';
import '../models/recipe_summary.dart';
import '../models/recipe_detail.dart';

class RecipeRepository {
  final ApiClient _client;
  RecipeRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<List<RecipeSummary>> getRecipes({String? search, int page = 1, int pageSize = 50}) async {
    final params = <String, dynamic>{'page': page, 'page_size': pageSize};
    if (search != null) params['search'] = search;
    final response = await _client.dio.get('/recipes', queryParameters: params);
    final list = response.data as List<dynamic>;
    return list.map((e) => RecipeSummary.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<RecipeDetail> getRecipe(int id) async {
    final response = await _client.dio.get('/recipes/');
    return RecipeDetail.fromJson(response.data as Map<String, dynamic>);
  }
}
