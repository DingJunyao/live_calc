import '../../../core/api/api_client.dart';
import '../models/product.dart';

class ProductRepository {
  final ApiClient _client;
  ProductRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<List<Product>> getProducts({String? search, int page = 1, int pageSize = 50}) async {
    final params = <String, dynamic>{'page': page, 'page_size': pageSize};
    if (search != null) params['search'] = search;
    final response = await _client.dio.get('/products', queryParameters: params);
    final list = response.data as List<dynamic>;
    return list.map((e) => Product.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Product> getProduct(int id) async {
    final response = await _client.dio.get('/products/$id');
    return Product.fromJson(response.data as Map<String, dynamic>);
  }
}
