import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/price_record.dart';
import '../repositories/price_repository.dart';

const int _pageSize = 20;

/// Sentinel so [PriceListState.copyWith] can tell "not provided" apart from
/// "explicitly set to null" for nullable filter fields.
const _absent = Object();

class PriceListState {
  final List<PriceRecord> records;
  final bool loading;
  final bool loadingMore;
  final String? error;
  final String searchQuery;
  final int? filterMerchantId;
  final String? filterRecordType; // 'purchase' | 'price' | null
  final String? filterStartDate;
  final String? filterEndDate;
  final int total;
  final int currentPage;
  final bool hasMore;

  const PriceListState({
    this.records = const [],
    this.loading = false,
    this.loadingMore = false,
    this.error,
    this.searchQuery = '',
    this.filterMerchantId,
    this.filterRecordType,
    this.filterStartDate,
    this.filterEndDate,
    this.total = 0,
    this.currentPage = 1,
    this.hasMore = true,
  });

  PriceListState copyWith({
    List<PriceRecord>? records,
    bool? loading,
    bool? loadingMore,
    String? error,
    String? searchQuery,
    Object? filterMerchantId = _absent,
    Object? filterRecordType = _absent,
    Object? filterStartDate = _absent,
    Object? filterEndDate = _absent,
    int? total,
    int? currentPage,
    bool? hasMore,
    bool clearError = false,
  }) {
    return PriceListState(
      records: records ?? this.records,
      loading: loading ?? this.loading,
      loadingMore: loadingMore ?? this.loadingMore,
      error: clearError ? null : (error ?? this.error),
      searchQuery: searchQuery ?? this.searchQuery,
      filterMerchantId: identical(filterMerchantId, _absent)
          ? this.filterMerchantId
          : filterMerchantId as int?,
      filterRecordType: identical(filterRecordType, _absent)
          ? this.filterRecordType
          : filterRecordType as String?,
      filterStartDate: identical(filterStartDate, _absent)
          ? this.filterStartDate
          : filterStartDate as String?,
      filterEndDate: identical(filterEndDate, _absent)
          ? this.filterEndDate
          : filterEndDate as String?,
      total: total ?? this.total,
      currentPage: currentPage ?? this.currentPage,
      hasMore: hasMore ?? this.hasMore,
    );
  }
}

class PriceListNotifier extends StateNotifier<PriceListState> {
  final PriceRepository _repository;
  Timer? _debounce;

  PriceListNotifier(this._repository) : super(const PriceListState());

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  String? get _recordTypesParam => state.filterRecordType;

  Future<void> loadRecords({bool loadMore = false}) async {
    final page = loadMore ? state.currentPage + 1 : 1;
    state = state.copyWith(
      loading: !loadMore,
      loadingMore: loadMore,
      clearError: true,
    );
    try {
      final result = await _repository.getRecords(
        search: state.searchQuery.isEmpty ? null : state.searchQuery,
        merchantId: state.filterMerchantId,
        recordTypes: _recordTypesParam,
        startDate: state.filterStartDate,
        endDate: state.filterEndDate,
        page: page,
        pageSize: _pageSize,
      );
      final records = loadMore
          ? [...state.records, ...result.records]
          : result.records;
      final hasMore = records.length < result.total;
      state = state.copyWith(
        records: records,
        total: result.total,
        currentPage: page,
        hasMore: hasMore,
        loading: false,
        loadingMore: false,
      );
    } on Exception catch (e) {
      state = state.copyWith(
        loading: false,
        loadingMore: false,
        error: e.toString(),
      );
    }
  }

  /// Debounced search — only reloads after the user stops typing.
  void setSearch(String query) {
    state = state.copyWith(searchQuery: query);
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      loadRecords();
    });
  }

  void setMerchantFilter(int? merchantId) {
    state = state.copyWith(filterMerchantId: merchantId);
    loadRecords();
  }

  void setRecordTypeFilter(String? recordType) {
    state = state.copyWith(filterRecordType: recordType);
    loadRecords();
  }

  void setDateFilter(String? start, String? end) {
   state = state.copyWith(filterStartDate: start, filterEndDate: end);
   loadRecords();
 }
  /// Apply all filter changes at once, then reload a single time.
  void applyFilters({
    required int? merchantId,
    required String? recordType,
    required String? startDate,
    required String? endDate,
  }) {
    state = state.copyWith(
      filterMerchantId: merchantId,
      filterRecordType: recordType,
      filterStartDate: startDate,
      filterEndDate: endDate,
    );
    loadRecords();
  }

  /// Number of active filter groups — used for the badge on the filter button.
  int get activeFilterCount {
    var count = 0;
    if (state.filterMerchantId != null) count++;
    if (state.filterRecordType != null) count++;
    if (state.filterStartDate != null || state.filterEndDate != null) {
      count++;
    }
    return count;
  }

  void clearFilters() {
    state = state.copyWith(
      filterMerchantId: null,
      filterRecordType: null,
      filterStartDate: null,
      filterEndDate: null,
    );
    loadRecords();
  }

  bool get canLoadMore =>
      state.hasMore && !state.loading && !state.loadingMore;
}

final priceListProvider =
    StateNotifierProvider<PriceListNotifier, PriceListState>((ref) {
  return PriceListNotifier(PriceRepository());
});
