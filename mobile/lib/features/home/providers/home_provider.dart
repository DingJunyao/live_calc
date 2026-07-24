import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/meal_recommendation.dart';
import '../repositories/home_repository.dart';

class HomeState {
  final DailyRecommendation? recommendation;
  final bool loading;
  final String? error;

  const HomeState({this.recommendation, this.loading = false, this.error});

  HomeState copyWith({DailyRecommendation? recommendation, bool? loading, String? error}) {
    return HomeState(
      recommendation: recommendation ?? this.recommendation,
      loading: loading ?? this.loading,
      error: error ?? this.error,
    );
  }
}

class HomeNotifier extends StateNotifier<HomeState> {
  final HomeRepository _repository;

  HomeNotifier(this._repository) : super(const HomeState());

  Future<void> loadToday() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final rec = await _repository.getTodayRecommendation();
      state = HomeState(recommendation: rec);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  Future<void> refresh() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final rec = await _repository.refreshToday();
      state = HomeState(recommendation: rec);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final homeProvider = StateNotifierProvider<HomeNotifier, HomeState>((ref) {
  return HomeNotifier(HomeRepository());
});
