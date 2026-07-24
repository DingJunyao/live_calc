class RecipeSummary {
  final int id;
  final String name;
  final String? description;
  final double? estimatedCost;
  final String? imageUrl;
  final int ingredientCount;
  final bool isPublic;

  const RecipeSummary({
    required this.id,
    required this.name,
    this.description,
    this.estimatedCost,
    this.imageUrl,
    this.ingredientCount = 0,
    this.isPublic = false,
  });

  factory RecipeSummary.fromJson(Map<String, dynamic> json) {
    return RecipeSummary(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      estimatedCost: (json['estimated_cost'] as num?)?.toDouble(),
      imageUrl: json['image_url'] as String?,
      ingredientCount: json['ingredient_count'] as int? ?? 0,
      isPublic: json['is_public'] as bool? ?? false,
    );
  }
}
*** Add File: mobile/lib/features/recipes/models/recipe_detail.dart
import 'recipe_summary.dart';

class RecipeIngredient {
  final String name;
  final double quantity;
  final String unit;
  final double? estimatedCost;

  const RecipeIngredient({
    required this.name,
    required this.quantity,
    required this.unit,
    this.estimatedCost,
  });

  factory RecipeIngredient.fromJson(Map<String, dynamic> json) {
    return RecipeIngredient(
      name: json['name'] as String? ?? json['ingredient_name'] as String? ?? '',
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0,
      unit: json['unit'] as String? ?? '个',
      estimatedCost: (json['estimated_cost'] as num?)?.toDouble(),
    );
  }
}

class RecipeStep {
  final int stepNumber;
  final String content;
  final String? imageUrl;

  const RecipeStep({required this.stepNumber, required this.content, this.imageUrl});

  factory RecipeStep.fromJson(Map<String, dynamic> json) {
    return RecipeStep(
      stepNumber: json['step_number'] as int? ?? 0,
      content: json['content'] as String? ?? '',
      imageUrl: json['image_url'] as String?,
    );
  }
}

class RecipeDetail {
  final int id;
  final String name;
  final String? description;
  final double? totalCost;
  final String? imageUrl;
  final List<RecipeIngredient> ingredients;
  final List<RecipeStep> steps;
  final String? tips;
  final bool isPublic;

  const RecipeDetail({
    required this.id,
    required this.name,
    this.description,
    this.totalCost,
    this.imageUrl,
    this.ingredients = const [],
    this.steps = const [],
    this.tips,
    this.isPublic = false,
  });

  factory RecipeDetail.fromJson(Map<String, dynamic> json) {
    return RecipeDetail(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      totalCost: (json['total_cost'] as num?)?.toDouble(),
      imageUrl: json['image_url'] as String?,
      ingredients: (json['ingredients'] as List<dynamic>?)
              ?.map((e) => RecipeIngredient.fromJson(e as Map<String, dynamic>))
              .toList() ?? [],
      steps: (json['steps'] as List<dynamic>?)
              ?.map((e) => RecipeStep.fromJson(e as Map<String, dynamic>))
              .toList() ?? [],
      tips: json['tips'] as String?,
      isPublic: json['is_public'] as bool? ?? false,
    );
  }
}
*** Add File: mobile/lib/features/recipes/repositories/recipe_repository.dart
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
    final response = await _client.dio.get('/recipes/$id');
    return RecipeDetail.fromJson(response.data as Map<String, dynamic>);
  }
}
*** Add File: mobile/lib/features/recipes/providers/recipe_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/recipe_summary.dart';
import '../models/recipe_detail.dart';
import '../repositories/recipe_repository.dart';

class RecipeListState {
  final List<RecipeSummary> recipes;
  final bool loading;
  final String? error;
  final String? searchQuery;

  const RecipeListState({
    this.recipes = const [],
    this.loading = false,
    this.error,
    this.searchQuery,
  });

  RecipeListState copyWith({
    List<RecipeSummary>? recipes, bool? loading, String? error, String? searchQuery,
  }) {
    return RecipeListState(
      recipes: recipes ?? this.recipes,
      loading: loading ?? this.loading,
      error: error ?? this.error,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class RecipeListNotifier extends StateNotifier<RecipeListState> {
  final RecipeRepository _repository;
  RecipeListNotifier(this._repository) : super(const RecipeListState());

  Future<void> loadRecipes({String? search}) async {
    state = state.copyWith(loading: true, error: null, searchQuery: search);
    try {
      final recipes = await _repository.getRecipes(search: search);
      state = RecipeListState(recipes: recipes);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final recipeListProvider = StateNotifierProvider<RecipeListNotifier, RecipeListState>((ref) {
  return RecipeListNotifier(RecipeRepository());
});

// Individual recipe detail
final recipeDetailProvider = FutureProvider.family<RecipeDetail, int>((ref, id) async {
  final repo = RecipeRepository();
  return repo.getRecipe(id);
});
