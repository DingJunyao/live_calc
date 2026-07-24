import '../../../core/api/api_client.dart';
import '../models/price_record.dart';

class PriceRepository {
  final ApiClient _client;
  PriceRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<List<PriceRecord>> getRecords({
    int? merchantId,
    String? startDate,
    String? endDate,
    int page = 1,
    int pageSize = 50,
  }) async {
    final params = <String, dynamic>{'page': page, 'page_size': pageSize};
    if (merchantId != null) params['merchant_id'] = merchantId;
    if (startDate != null) params['start_date'] = startDate;
    if (endDate != null) params['end_date'] = endDate;

    final response = await _client.dio.get('/products', queryParameters: params);
    final list = response.data as List<dynamic>;
    return list.map((e) => PriceRecord.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> createRecord({
    required String name,
    required double amount,
    double quantity = 1,
    String unit = '个',
    int? merchantId,
    int? ingredientId,
  }) async {
    final data = <String, dynamic>{
      'name': name,
      'amount': amount,
      'quantity': quantity,
      'unit': unit,
    };
    if (merchantId != null) data['merchant_id'] = merchantId;
    if (ingredientId != null) data['ingredient_id'] = ingredientId;
    await _client.dio.post('/products', data: data);
  }
}
