import 'package:dio/dio.dart';
import '../api/api_client.dart';

/// Probes whether the server is healthy by hitting the public `/auth/config`
/// endpoint. Only a 2xx response counts as reachable; connection errors and
/// non-2xx responses (e.g. 502 Bad Gateway, where the proxy replies but the
/// upstream app is down) are treated as transient and retried.
class ServerConnectionChecker {
  /// Returns true only if the server returned a 2xx response, false after
  /// [maxAttempts] failures. Callers should treat false as "server not ready,
  /// start over from server setup".
  static Future<bool> verify({
    int maxAttempts = 3,
    Dio? dio,
  }) async {
    final client = dio ?? ApiClient.instance.dio;
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        final response = await client.get('/auth/config');
        if (response.statusCode != null && response.statusCode! < 300) {
          return true;
        }
        // Non-2xx HTTP response (e.g. 502): gateway replied but the service
        // is not healthy, so retry like a transient connection error.
      } on DioException catch (e) {
        final code = e.response?.statusCode;
        if (code != null && code < 300) {
          return true;
        }
        // badResponse with non-2xx, or connection errors: fall through to retry.
      } catch (_) {
        // Unexpected error: fall through to retry.
      }
      if (attempt == maxAttempts) return false;
      await Future.delayed(const Duration(seconds: 1));
    }
    return false;
  }
}
