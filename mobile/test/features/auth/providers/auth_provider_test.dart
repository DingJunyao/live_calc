import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import '../../../../lib/features/auth/providers/auth_provider.dart';
import '../../../../lib/features/auth/repositories/auth_repository.dart';
import '../../../../lib/features/auth/models/login_request.dart';
import '../../../../lib/features/auth/models/user.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

void main() {
  late MockAuthRepository mockRepo;

  setUp(() {
    mockRepo = MockAuthRepository();
  });

  group('AuthNotifier', () {
    test('初始状态为 initial', () {
      final notifier = AuthNotifier(mockRepo);
      expect(notifier.state.status, AuthStatus.initial);
    });

    test('登录成功更新状态', () async {
      when(() => mockRepo.login(any())).thenAnswer((_) async => LoginResponse(
        accessToken: 'tok', refreshToken: 'ref',
      ));
      when(() => mockRepo.getCurrentUser()).thenAnswer((_) async => User(
        id: 1, username: 'test', email: 'test@test.com',
      ));

      final notifier = AuthNotifier(mockRepo);
      final success = await notifier.login('user', 'pass');

      expect(success, true);
      expect(notifier.state.status, AuthStatus.authenticated);
      expect(notifier.state.user?.username, 'test');
    });

    test('登录失败返回错误状态', () async {
      when(() => mockRepo.login(any())).thenThrow(Exception('invalid credentials'));

      final notifier = AuthNotifier(mockRepo);
      final success = await notifier.login('user', 'wrong');

      expect(success, false);
      expect(notifier.state.status, AuthStatus.error);
    });
  });
}
