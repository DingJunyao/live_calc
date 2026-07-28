import '../../../core/api/api_client.dart';
import '../models/recipe_summary.dart';
import '../models/recipe_detail.dart';

class RecipeRepository {
  final ApiClient _client;
  RecipeRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

 Future<List<RecipeSummary>> getRecipes({String? search, int page = 1, int pageSize = 50}) async {
    // 后端 GET /recipes 使用 skip/limit 分页
    final params = <String, dynamic>{
      'skip': (page - 1) * pageSize,
      'limit': pageSize,
    };
    if (search != null) params['search'] = search;
    final response = await _client.dio.get('/recipes', queryParameters: params);
    final list = (response.data is List) ? response.data as List : (response.data['items'] as List);
    return list.map((e) => RecipeSummary.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<RecipeDetail> getRecipe(int id) async {
    final response = await _client.dio.get('/recipes/$id');
    return RecipeDetail.fromJson(response.data as Map<String, dynamic>);
  }
}

