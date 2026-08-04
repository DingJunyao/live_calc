import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:com_a4ding_livecalc/core/services/server_connection_checker.dart';

class MockDio extends Mock implements Dio {}

void main() {
  late MockDio mockDio;

  setUp(() {
    mockDio = MockDio();
    registerFallbackValue(RequestOptions(path: '/auth/config'));
  });

  group('ServerConnectionChecker', () {
    test('2xx 响应视为可达', () async {
      when(() => mockDio.get('/auth/config')).thenAnswer((_) async => Response(
            requestOptions: RequestOptions(path: '/auth/config'),
            statusCode: 200,
            data: {'allow_registration': true},
          ));

      final reachable =
          await ServerConnectionChecker.verify(dio: mockDio, maxAttempts: 1);
      expect(reachable, true);
    });

    test('502 重试后仍失败则返回 false（不再误判为可达）', () async {
      when(() => mockDio.get('/auth/config')).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/auth/config'),
        response: Response(
          requestOptions: RequestOptions(path: '/auth/config'),
          statusCode: 502,
        ),
        type: DioExceptionType.badResponse,
      ));

      final reachable =
          await ServerConnectionChecker.verify(dio: mockDio, maxAttempts: 3);
      expect(reachable, false);
      // Should have retried 3 times.
      verify(() => mockDio.get('/auth/config')).called(3);
    });

    test('连接超时重试后失败返回 false', () async {
      when(() => mockDio.get('/auth/config')).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/auth/config'),
        type: DioExceptionType.connectionTimeout,
      ));

      final reachable =
          await ServerConnectionChecker.verify(dio: mockDio, maxAttempts: 2);
      expect(reachable, false);
      verify(() => mockDio.get('/auth/config')).called(2);
    });

    test('502 后恢复 2xx 则返回 true', () async {
      var attempt = 0;
      when(() => mockDio.get('/auth/config')).thenAnswer((_) async {
        attempt++;
        if (attempt == 1) {
          throw DioException(
            requestOptions: RequestOptions(path: '/auth/config'),
            response: Response(
              requestOptions: RequestOptions(path: '/auth/config'),
              statusCode: 502,
            ),
            type: DioExceptionType.badResponse,
          );
        }
        return Response(
          requestOptions: RequestOptions(path: '/auth/config'),
          statusCode: 200,
          data: {'allow_registration': true},
        );
      });

      final reachable =
          await ServerConnectionChecker.verify(dio: mockDio, maxAttempts: 3);
      expect(reachable, true);
      verify(() => mockDio.get('/auth/config')).called(2);
    });
  });
}
