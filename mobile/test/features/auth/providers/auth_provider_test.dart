import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:flutter/services.dart';
import '../../../../lib/core/api/api_client.dart';
import '../../../../lib/core/api/auth_interceptor.dart';
import '../../../../lib/features/auth/providers/auth_provider.dart';
import '../../../../lib/features/auth/repositories/auth_repository.dart';
import '../../../../lib/features/auth/models/login_request.dart';
import '../../../../lib/features/auth/models/user.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

void main() {
  late MockAuthRepository mockRepo;
  // In-memory backing store for the mocked FlutterSecureStorage channels.
  final Map<String, String> secureStore = {};

  Future<dynamic> _secureStorageHandler(MethodCall call) async {
    final args = call.arguments is Map
        ? Map<String, dynamic>.from(call.arguments as Map)
        : <String, dynamic>{};
    switch (call.method) {
      case 'read':
        return secureStore[args['key']];
      case 'write':
        secureStore[args['key'] as String] = args['value'] as String;
        return null;
      case 'delete':
        secureStore.remove(args['key']);
        return null;
      case 'containsKey':
        return secureStore.containsKey(args['key']);
      case 'deleteAll':
        secureStore.clear();
        return null;
      case 'readAll':
        return secureStore;
      default:
        return null;
    }
  }

  AuthNotifier buildNotifier({required bool connected}) {
    return AuthNotifier(
      mockRepo,
      checkConnection: () async => connected,
    );
  }

  setUpAll(() {
    registerFallbackValue(const LoginRequest(username: '', passwordHash: ''));
    TestWidgetsFlutterBinding.ensureInitialized();
    for (final channel in [
      'plugins.it_nomads.com/flutter_secure_storage',
      'plugins.flutter.io/flutter_secure_storage',
      'plugins.flutter.io/flutter_secure_storage_windows',
      'plugins.flutter.io/flutter_secure_storage_linux',
      'plugins.flutter.io/flutter_secure_storage_macos',
      'plugins.flutter.io/flutter_secure_storage_web',
    ]) {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
              MethodChannel(channel), _secureStorageHandler);
    }
  });

  setUp(() {
    secureStore.clear();
    // Give the singleton a base URL so checkAuth's connectivity probe runs.
    ApiClient.instance.updateBaseUrl('https://example.test');
    mockRepo = MockAuthRepository();
  });

  group('AuthNotifier', () {
    test('初始状态为 initial', () {
      final notifier = AuthNotifier(mockRepo);
      expect(notifier.state.status, AuthStatus.initial);
      expect(notifier.state.serverUnreachable, false);
    });

    test('登录成功更新状态', () async {
      when(() => mockRepo.login(any())).thenAnswer(
          (_) async => LoginResponse(accessToken: 'tok', refreshToken: 'ref'));
      when(() => mockRepo.getCurrentUser()).thenAnswer((_) async => User(
            id: 1,
            username: 'test',
            email: 'test@test.com',
          ));

      final notifier = buildNotifier(connected: true);
      final success = await notifier.login('user', 'pass');

      expect(success, true);
      expect(notifier.state.status, AuthStatus.authenticated);
      expect(notifier.state.user?.username, 'test');
    });

    test('登录凭据错误显示友好提示', () async {
      when(() => mockRepo.login(any())).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/auth/login'),
        response: Response(
          requestOptions: RequestOptions(path: '/auth/login'),
          statusCode: 401,
        ),
        type: DioExceptionType.badResponse,
      ));

      final notifier = buildNotifier(connected: true);
      final success = await notifier.login('user', 'wrong');

      expect(success, false);
      expect(notifier.state.status, AuthStatus.error);
      expect(notifier.state.errorMessage, '用户名或密码错误');
      expect(notifier.state.serverUnreachable, false);
    });

    test('登录成功后保存凭据与 token，便于下次自动登录', () async {
      when(() => mockRepo.login(any())).thenAnswer(
          (_) async => LoginResponse(accessToken: 'tok', refreshToken: 'ref'));
      when(() => mockRepo.getCurrentUser()).thenAnswer((_) async => User(
            id: 1,
            username: 'test',
            email: 'test@test.com',
          ));

      final notifier = buildNotifier(connected: true);
      await notifier.login('myuser', 'mypassword');

      expect(await AuthInterceptor.accessToken, 'tok');
      final creds = await AuthInterceptor.savedCredentials;
      expect(creds, isNotNull);
      expect(creds!.key, 'myuser');
      expect(creds.value, 'mypassword');
    });

    test('checkAuth 用保存的凭据自动登录', () async {
      await AuthInterceptor.saveCredentials('remembered', 'secret');
      when(() => mockRepo.login(any())).thenAnswer((_) async =>
          LoginResponse(accessToken: 'tok2', refreshToken: 'ref2'));
      when(() => mockRepo.getCurrentUser()).thenAnswer((_) async => User(
            id: 2,
            username: 'remembered',
            email: 'r@r.com',
          ));

      final notifier = buildNotifier(connected: true);
      await notifier.checkAuth();

      expect(notifier.state.status, AuthStatus.authenticated);
      expect(notifier.state.user?.username, 'remembered');
      expect(await AuthInterceptor.accessToken, 'tok2');
    });

    test('checkAuth 无 token 且无凭据时为未登录状态', () async {
      final notifier = buildNotifier(connected: true);
      await notifier.checkAuth();

      verifyNever(() => mockRepo.login(any()));
      verifyNever(() => mockRepo.getCurrentUser());
      expect(notifier.state.status, AuthStatus.unauthenticated);
      expect(notifier.state.serverUnreachable, false);
    });

    test('checkAuth 用有效 token 恢复会话', () async {
      await AuthInterceptor.saveTokens('valid', 'refresh');
      when(() => mockRepo.getCurrentUser()).thenAnswer((_) async => User(
            id: 3,
            username: 'tokenuser',
            email: 't@t.com',
          ));

      final notifier = buildNotifier(connected: true);
      await notifier.checkAuth();

      verifyNever(() => mockRepo.login(any()));
      expect(notifier.state.status, AuthStatus.authenticated);
      expect(notifier.state.user?.username, 'tokenuser');
    });

    test('checkAuth 在 token 失效后回退到凭据登录', () async {
      await AuthInterceptor.saveTokens('stale', 'refresh');
      await AuthInterceptor.saveCredentials('fallback', 'secret');
      when(() => mockRepo.login(any())).thenAnswer((_) async =>
          LoginResponse(accessToken: 'fresh', refreshToken: 'ref3'));
      // First getCurrentUser (token check) fails, the second (after re-login) succeeds.
      final answers = [
        Exception('unauthorized'),
        User(id: 4, username: 'fallback', email: 'f@f.com'),
      ];
      var i = 0;
      when(() => mockRepo.getCurrentUser()).thenAnswer((_) async {
        final a = answers[i++];
        if (a is User) return a;
        throw a as Exception;
      });

      final notifier = buildNotifier(connected: true);
      await notifier.checkAuth();

      expect(notifier.state.status, AuthStatus.authenticated);
      expect(notifier.state.user?.username, 'fallback');
      expect(await AuthInterceptor.accessToken, 'fresh');
    });

    test('checkAuth 连续 3 次连不上服务器则标记不可达并从头开始', () async {
      final notifier = buildNotifier(connected: false);
      await notifier.checkAuth();

      verifyNever(() => mockRepo.login(any()));
      verifyNever(() => mockRepo.getCurrentUser());
      expect(notifier.state.status, AuthStatus.unauthenticated);
      expect(notifier.state.serverUnreachable, true);
      expect(notifier.state.errorMessage, contains('无法连接'));
    });

    test('登录时连不上服务器则标记不可达且不调用登录接口', () async {
      final notifier = buildNotifier(connected: false);
      final success = await notifier.login('user', 'pass');

      expect(success, false);
      expect(notifier.state.status, AuthStatus.unauthenticated);
      expect(notifier.state.serverUnreachable, true);
      verifyNever(() => mockRepo.login(any()));
    });

    test('clearConnectionError 清除不可达标志', () async {
      final notifier = buildNotifier(connected: false);
      await notifier.login('user', 'pass');
      expect(notifier.state.serverUnreachable, true);

      notifier.clearConnectionError();
      expect(notifier.state.serverUnreachable, false);
      expect(notifier.state.status, AuthStatus.unauthenticated);
    });
  });
}
