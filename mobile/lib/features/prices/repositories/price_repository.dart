import '../../../core/api/api_client.dart';
import '../models/price_record.dart';

class PriceRepository {
  final ApiClient _client;
  ApiClient get client => _client;
  PriceRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  /// 获取价格记录列表。
  /// 后端 GET /products 使用 skip/limit 分页、merchant_ids（逗号分隔）筛选，
  /// 这里把外部的 page/pageSize 转成 skip/limit，并兼容 List 与 {items} 两种返回。
  Future<List<PriceRecord>> getRecords({
    int? merchantId,
    String? startDate,
    String? endDate,
    int page = 1,
    int pageSize = 50,
  }) async {
    final skip = (page - 1) * pageSize;
    final params = <String, dynamic>{
      'skip': skip,
      'limit': pageSize,
    };
    if (merchantId != null) params['merchant_ids'] = merchantId.toString();
    if (startDate != null) params['start_date'] = startDate;
    if (endDate != null) params['end_date'] = endDate;

    final response = await _client.dio.get('/products', queryParameters: params);
    final list = (response.data is List)
        ? response.data as List
        : (response.data['items'] as List);
    return list
        .map((e) => PriceRecord.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 新建价格记录。
  /// 后端 POST /products 需要 price/original_quantity/original_unit，
  /// 并通过 product_id 或 product_name 关联商品。
  Future<PriceRecord> createRecord({
    int? productId,
    String? productName,
    required double price,
    double quantity = 1,
    String unit = '个',
    int? merchantId,
    int? ingredientId,
    String recordType = 'purchase',
    String? notes,
    DateTime? recordedAt,
  }) async {
    final data = <String, dynamic>{
      'price': price,
      'original_quantity': quantity,
      'original_unit': unit,
      'record_type': recordType,
    };
    if (productId != null) {
      data['product_id'] = productId;
    } else if (productName != null && productName.isNotEmpty) {
      data['product_name'] = productName;
    }
    if (merchantId != null) data['merchant_id'] = merchantId;
    if (ingredientId != null) data['ingredient_id'] = ingredientId;
    if (notes != null) data['notes'] = notes;
    if (recordedAt != null) {
      data['recorded_at'] = recordedAt.toUtc().toIso8601String();
    }

    final response = await _client.dio.post('/products', data: data);
    return PriceRecord.fromJson(response.data as Map<String, dynamic>);
  }
}
