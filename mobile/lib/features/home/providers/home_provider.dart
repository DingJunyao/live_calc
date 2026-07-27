import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/meal_recommendation.dart';
import '../repositories/home_repository.dart';

class HomeState {
  final DailyRecommendation? recommendation;
  final bool loading;
  final bool generating;
  final String? error;

  const HomeState({
    this.recommendation,
    this.loading = false,
    this.generating = false,
    this.error,
  });

  HomeState copyWith({
    DailyRecommendation? recommendation,
    bool? loading,
    bool? generating,
    String? error,
  }) {
    return HomeState(
      recommendation: recommendation ?? this.recommendation,
      loading: loading ?? this.loading,
      generating: generating ?? this.generating,
      error: error ?? this.error,
    );
  }
}

String _friendlyError(DioException e) {
  if (e.type == DioExceptionType.connectionTimeout ||
      e.type == DioExceptionType.receiveTimeout) {
    return '网络连接超时，请检查网络后重试';
  }
  if (e.type == DioExceptionType.connectionError) {
    return '网络连接失败，请检查网络后重试';
  }
  if (e.response?.statusCode == 500) {
    return '服务器繁忙，请稍后重试';
  }
  if (e.response?.statusCode == 404) {
    return '请求的资源不存在';
  }
  return '加载失败，请稍后重试';
}

class HomeNotifier extends StateNotifier<HomeState> {
  final HomeRepository _repository;

  HomeNotifier(this._repository) : super(const HomeState());

  Future<void> _pollUntilReady() async {
    for (var i = 0; i < 60; i++) {
      await Future.delayed(const Duration(seconds: 1));
      final rec = await _repository.getTodayRecommendation();
      if (rec.status == 'ready') {
        state = HomeState(recommendation: rec);
        return;
      }
    }
    // Poll timed out — still generating
    state = state.copyWith(
      generating: false,
      error: '推荐正在生成中，请稍后刷新查看',
    );
  }

  Future<void> loadToday() async {
    state = state.copyWith(loading: true, error: null, generating: false);
    try {
      var rec = await _repository.getTodayRecommendation();

      if (rec.status == 'not_generated') {
        rec = await _repository.triggerGenerate();
      }

      if (rec.status == 'generating') {
        state = state.copyWith(loading: false, generating: true);
        await _pollUntilReady();
        return;
      }

      state = HomeState(recommendation: rec);
    } on DioException catch (e) {
      state = state.copyWith(loading: false, error: _friendlyError(e));
    } on Exception catch (_) {
      state = state.copyWith(loading: false, error: '加载失败，请稍后重试');
    }
  }

  Future<void> refresh() async {
    state = state.copyWith(loading: false, error: null, generating: true);
    try {
      var rec = await _repository.triggerGenerate();
      if (rec.status == 'generating') {
        await _pollUntilReady();
      } else {
        state = HomeState(recommendation: rec);
      }
    } on DioException catch (e) {
      state = state.copyWith(generating: false, error: _friendlyError(e));
    } on Exception catch (_) {
      state = state.copyWith(generating: false, error: '刷新失败，请稍后重试');
    }
  }
}

final homeProvider = StateNotifierProvider<HomeNotifier, HomeState>((ref) {
  return HomeNotifier(HomeRepository());
});