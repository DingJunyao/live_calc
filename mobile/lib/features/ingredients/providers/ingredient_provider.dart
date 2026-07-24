import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/ingredient.dart';
import '../repositories/ingredient_repository.dart';

class IngredientListState {
  final List<Ingredient> items;
  final bool loading;
  final String? error;
  final String? searchQuery;

  const IngredientListState({this.items = const [], this.loading = false, this.error, this.searchQuery});

  IngredientListState copyWith({List<Ingredient>? items, bool? loading, String? error, String? searchQuery}) {
    return IngredientListState(
      items: items ?? this.items,
      loading: loading ?? this.loading,
      error: error ?? this.error,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class IngredientListNotifier extends StateNotifier<IngredientListState> {
  final IngredientRepository _repo;
  IngredientListNotifier(this._repo) : super(const IngredientListState());

  Future<void> load({String? search}) async {
    state = state.copyWith(loading: true, error: null, searchQuery: search);
    try {
      final items = await _repo.getIngredients(search: search);
      state = IngredientListState(items: items);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final ingredientListProvider = StateNotifierProvider<IngredientListNotifier, IngredientListState>((ref) {
  return IngredientListNotifier(IngredientRepository());
});
