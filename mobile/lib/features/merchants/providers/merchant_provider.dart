import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/merchant.dart';
import '../repositories/merchant_repository.dart';

class MerchantListState {
  final List<Merchant> items;
  final bool loading;
  final String? error;
  final String? searchQuery;

  const MerchantListState({this.items = const [], this.loading = false, this.error, this.searchQuery});

  MerchantListState copyWith({List<Merchant>? items, bool? loading, String? error, String? searchQuery}) {
    return MerchantListState(
      items: items ?? this.items,
      loading: loading ?? this.loading,
      error: error ?? this.error,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class MerchantListNotifier extends StateNotifier<MerchantListState> {
  final MerchantRepository _repo;
  MerchantListNotifier(this._repo) : super(const MerchantListState());

  Future<void> load({String? search}) async {
    state = state.copyWith(loading: true, error: null, searchQuery: search);
    try {
      final items = await _repo.getMerchants(search: search);
      state = MerchantListState(items: items);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final merchantListProvider = StateNotifierProvider<MerchantListNotifier, MerchantListState>((ref) {
  return MerchantListNotifier(MerchantRepository());
});
