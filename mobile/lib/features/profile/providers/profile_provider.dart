import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/proposal.dart';
import '../models/user_place.dart';
import '../repositories/profile_repository.dart';

// -- Proposals --

class ProposalListState {
  final List<Proposal> items;
  final bool loading;
  final String? error;
  const ProposalListState({this.items = const [], this.loading = false, this.error});
  ProposalListState copyWith({List<Proposal>? items, bool? loading, String? error}) {
    return ProposalListState(items: items ?? this.items, loading: loading ?? this.loading, error: error ?? this.error);
  }
}

class ProposalListNotifier extends StateNotifier<ProposalListState> {
  final ProfileRepository _repo;
  ProposalListNotifier(this._repo) : super(const ProposalListState());

  Future<void> load() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final items = await _repo.getProposals();
      state = ProposalListState(items: items);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final proposalListProvider = StateNotifierProvider<ProposalListNotifier, ProposalListState>((ref) {
  return ProposalListNotifier(ProfileRepository());
});

// -- Places --

class PlaceListState {
  final List<UserPlace> items;
  final bool loading;
  final String? error;
  const PlaceListState({this.items = const [], this.loading = false, this.error});
  PlaceListState copyWith({List<UserPlace>? items, bool? loading, String? error}) {
    return PlaceListState(items: items ?? this.items, loading: loading ?? this.loading, error: error ?? this.error);
  }
}

class PlaceListNotifier extends StateNotifier<PlaceListState> {
  final ProfileRepository _repo;
  PlaceListNotifier(this._repo) : super(const PlaceListState());

  Future<void> load() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final items = await _repo.getPlaces();
      state = PlaceListState(items: items);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final placeListProvider = StateNotifierProvider<PlaceListNotifier, PlaceListState>((ref) {
  return PlaceListNotifier(ProfileRepository());
});
