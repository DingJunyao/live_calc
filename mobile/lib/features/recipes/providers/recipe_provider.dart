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
