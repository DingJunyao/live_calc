import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/product.dart';
import '../repositories/product_repository.dart';

class ProductListState {
  final List<Product> items;
  final bool loading;
  final String? error;
  final String? searchQuery;

  const ProductListState({this.items = const [], this.loading = false, this.error, this.searchQuery});

  ProductListState copyWith({List<Product>? items, bool? loading, String? error, String? searchQuery}) {
    return ProductListState(
      items: items ?? this.items,
      loading: loading ?? this.loading,
      error: error ?? this.error,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class ProductListNotifier extends StateNotifier<ProductListState> {
  final ProductRepository _repo;
  ProductListNotifier(this._repo) : super(const ProductListState());

  Future<void> load({String? search}) async {
    state = state.copyWith(loading: true, error: null, searchQuery: search);
    try {
      final items = await _repo.getProducts(search: search);
      state = ProductListState(items: items);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final productListProvider = StateNotifierProvider<ProductListNotifier, ProductListState>((ref) {
  return ProductListNotifier(ProductRepository());
});
