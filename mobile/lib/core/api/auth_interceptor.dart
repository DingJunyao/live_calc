import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:intl/intl.dart';

class AuthInterceptor extends Interceptor {
  final Dio _dio;
  final _storage = const FlutterSecureStorage();

  static const _tokenKey = 'auth_token';
  static const _refreshTokenKey = 'refresh_token';

  AuthInterceptor(this._dio);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final timezone = Intl.defaultLocale ?? DateTime.now().timeZoneName;
    options.headers['X-Timezone'] = timezone;
    _storage.read(key: _tokenKey).then((token) {
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      handler.next(options);
    });
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      final refreshToken = await _storage.read(key: _refreshTokenKey);
      if (refreshToken != null) {
        try {
          final resp = await _dio.post('/auth/refresh', data: {
            'refresh_token': refreshToken,
          });
          final newToken = resp.data['access_token'] as String;
          await _storage.write(key: _tokenKey, value: newToken);
          final retryOpts = err.requestOptions;
          retryOpts.headers['Authorization'] = 'Bearer $newToken';
          final retryResp = await _dio.fetch(retryOpts);
          handler.resolve(retryResp);
          return;
        } catch (_) {
          await _storage.delete(key: _tokenKey);
          await _storage.delete(key: _refreshTokenKey);
        }
      }
    }
    handler.next(err);
  }

  static Future<void> saveTokens(String accessToken, String refreshToken) async {
    final storage = const FlutterSecureStorage();
    await storage.write(key: _tokenKey, value: accessToken);
    await storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  static Future<void> clearTokens() async {
    final storage = const FlutterSecureStorage();
    await storage.delete(key: _tokenKey);
    await storage.delete(key: _refreshTokenKey);
  }

  static Future<String?> get accessToken => const FlutterSecureStorage().read(key: _tokenKey);
}

