import 'package:dio/dio.dart';
import 'auth_interceptor.dart';

class ApiClient {
  static ApiClient? _instance;
  late final Dio dio;
  String _baseUrl = '';

  ApiClient._() {
    dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));
    dio.interceptors.add(AuthInterceptor(dio));
  }

  static ApiClient get instance {
    _instance ??= ApiClient._();
    return _instance!;
  }

  void updateBaseUrl(String baseUrl) {
    if (_baseUrl == baseUrl) return;
    _baseUrl = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    dio.options.baseUrl = '$_baseUrl/api/v1';
  }

  String get baseUrl => _baseUrl;
}
