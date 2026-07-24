import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api/auth_interceptor.dart';
import '../models/login_request.dart';
import '../models/user.dart';
import '../repositories/auth_repository.dart';

enum AuthStatus { initial, authenticated, unauthenticated, loading, error }

class AuthState {
  final AuthStatus status;
  final User? user;
  final String? errorMessage;
  const AuthState({this.status = AuthStatus.initial, this.user, this.errorMessage});

  AuthState copyWith({AuthStatus? status, User? user, String? errorMessage}) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _repository;

  AuthNotifier(this._repository) : super(const AuthState());

  Future<void> checkAuth() async {
    final token = await AuthInterceptor.accessToken;
    if (token == null) {
      state = const AuthState(status: AuthStatus.unauthenticated);
      return;
    }
    state = const AuthState(status: AuthStatus.loading);
    try {
      final user = await _repository.getCurrentUser();
      state = AuthState(status: AuthStatus.authenticated, user: user);
    } catch (_) {
      await AuthInterceptor.clearTokens();
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  Future<bool> login(String username, String password) async {
    state = const AuthState(status: AuthStatus.loading);
    try {
      final response = await _repository.login(LoginRequest(username: username, password: password));
      try { await AuthInterceptor.saveTokens(response.accessToken, response.refreshToken); } catch (_) {}
      final user = await _repository.getCurrentUser();
      state = AuthState(status: AuthStatus.authenticated, user: user);
      return true;
    } on Exception catch (e) {
      state = AuthState(status: AuthStatus.error, errorMessage: e.toString());
      return false;
    }
  }

  Future<bool> register({
    required String username, required String email, required String password,
    String? phone, String? inviteCode,
  }) async {
    state = const AuthState(status: AuthStatus.loading);
    try {
      final response = await _repository.register(
        username: username, email: email, password: password,
        phone: phone, inviteCode: inviteCode,
      );
      try { await AuthInterceptor.saveTokens(response.accessToken, response.refreshToken); } catch (_) {}
      final user = await _repository.getCurrentUser();
      state = AuthState(status: AuthStatus.authenticated, user: user);
      return true;
    } on Exception catch (e) {
      state = AuthState(status: AuthStatus.error, errorMessage: e.toString());
      return false;
    }
  }

  Future<void> logout() async {
    await AuthInterceptor.clearTokens();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(AuthRepository());
});

final isLoggedInProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).status == AuthStatus.authenticated;
});


