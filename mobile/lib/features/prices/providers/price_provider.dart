import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/price_record.dart';
import '../repositories/price_repository.dart';

class PriceListState {
  final List<PriceRecord> records;
  final bool loading;
  final String? error;
  final int? filterMerchantId;
  final String? filterStartDate;
  final String? filterEndDate;

  const PriceListState({
    this.records = const [],
    this.loading = false,
    this.error,
    this.filterMerchantId,
    this.filterStartDate,
    this.filterEndDate,
  });

  PriceListState copyWith({
    List<PriceRecord>? records, bool? loading, String? error,
    int? filterMerchantId, String? filterStartDate, String? filterEndDate,
    bool clearFilters = false,
  }) {
    return PriceListState(
      records: records ?? this.records,
      loading: loading ?? this.loading,
      error: error ?? this.error,
      filterMerchantId: clearFilters ? null : (filterMerchantId ?? this.filterMerchantId),
      filterStartDate: clearFilters ? null : (filterStartDate ?? this.filterStartDate),
      filterEndDate: clearFilters ? null : (filterEndDate ?? this.filterEndDate),
    );
  }
}

class PriceListNotifier extends StateNotifier<PriceListState> {
  final PriceRepository _repository;
  PriceListNotifier(this._repository) : super(const PriceListState());

  Future<void> loadRecords() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final records = await _repository.getRecords(
        merchantId: state.filterMerchantId,
        startDate: state.filterStartDate,
        endDate: state.filterEndDate,
      );
      state = PriceListState(records: records);
    } on Exception catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  void setMerchantFilter(int? merchantId) {
    state = state.copyWith(filterMerchantId: merchantId);
    loadRecords();
  }

  void setDateFilter(String? start, String? end) {
    state = state.copyWith(filterStartDate: start, filterEndDate: end);
    loadRecords();
  }

  void clearFilters() {
    state = state.copyWith(clearFilters: true);
    loadRecords();
  }
}

final priceListProvider = StateNotifierProvider<PriceListNotifier, PriceListState>((ref) {
  return PriceListNotifier(PriceRepository());
});
