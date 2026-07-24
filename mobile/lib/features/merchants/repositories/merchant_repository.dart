import '../../../core/api/api_client.dart';
import '../models/merchant.dart';

class MerchantRepository {
  final ApiClient _client;
  MerchantRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<List<Merchant>> getMerchants({String? search, int page = 1, int pageSize = 50}) async {
    final params = <String, dynamic>{'page': page, 'page_size': pageSize};
    if (search != null) params['search'] = search;
    final response = await _client.dio.get('/merchants', queryParameters: params);
    final list = response.data as List<dynamic>;
    return list.map((e) => Merchant.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Merchant> getMerchant(int id) async {
    final response = await _client.dio.get('/merchants/$id');
    return Merchant.fromJson(response.data as Map<String, dynamic>);
  }
}
