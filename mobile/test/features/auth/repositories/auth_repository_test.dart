import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dio/dio.dart';
import '../../../../lib/core/api/api_client.dart';
import '../../../../lib/features/auth/repositories/auth_repository.dart';
import '../../../../lib/features/auth/models/login_request.dart';

class MockApiClient extends Mock implements ApiClient {}
class MockDio extends Mock implements Dio {}

void main() {
  late AuthRepository repository;
  late MockApiClient mockClient;
  late MockDio mockDio;

  setUp(() {
    mockClient = MockApiClient();
    mockDio = MockDio();
    when(() => mockClient.dio).thenReturn(mockDio);
    repository = AuthRepository(client: mockClient);
  });

  group('getConfig', () {
    test('返回 AuthConfig', () async {
      when(() => mockDio.get('/auth/config')).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        data: {'require_invite_code': false, 'allow_registration': true},
        statusCode: 200,
      ));

      final config = await repository.getConfig();
      expect(config.requireInviteCode, false);
      expect(config.allowRegistration, true);
    });
  });

  group('login', () {
    test('返回 LoginResponse', () async {
      when(() => mockDio.post(any(), data: any(named: 'data'))).thenAnswer((_) async => Response(
        requestOptions: RequestOptions(path: ''),
        data: {'access_token': 'abc', 'refresh_token': 'def', 'token_type': 'bearer'},
        statusCode: 200,
      ));

      final response = await repository.login(const LoginRequest(username: 'test', password: 'pass'));
      expect(response.accessToken, 'abc');
      expect(response.refreshToken, 'def');
    });
  });
}
