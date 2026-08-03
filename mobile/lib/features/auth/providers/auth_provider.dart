import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import 'package:crypto/crypto.dart';
import '../../../core/api/api_client.dart';
import '../../../core/api/auth_interceptor.dart';
import '../../../core/services/server_connection_checker.dart';
import '../models/login_request.dart';
import '../models/user.dart';
import '../repositories/auth_repository.dart';

enum AuthStatus { initial, authenticated, unauthenticated, loading, error }

class AuthState {
  final AuthStatus status;
  final User? user;
  final String? errorMessage;
  // Set when the server could not be reached, so routing sends the user back
  // to server setup to start over (without wiping the saved address).
  final bool serverUnreachable;

  const AuthState({
    this.status = AuthStatus.initial,
    this.user,
    this.errorMessage,
    this.serverUnreachable = false,
  });

  AuthState copyWith({
    AuthStatus? status,
    User? user,
    String? errorMessage,
    bool? serverUnreachable,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      errorMessage: errorMessage ?? this.errorMessage,
      serverUnreachable: serverUnreachable ?? this.serverUnreachable,
    );
  }
}

const _serverDownMessage = '无法连接到服务器。请确认服务器已启动、地址正确，且当前网络可用，然后重试。';

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _repository;
  final Future<bool> Function() _checkConnection;

  AuthNotifier(
    this._repository, {
    Future<bool> Function()? checkConnection,
  })  : _checkConnection = checkConnection ?? ServerConnectionChecker.verify,
        super(const AuthState());

  /// Runs on startup. When a server is configured it first verifies the
  /// server is reachable, then restores the session via the saved token, or
  /// signs back in automatically using the remembered credentials.
  Future<void> checkAuth() async {
    // Only probe connectivity when a server is actually configured; otherwise
    // the user simply hasn't set one up yet.
    if (ApiClient.instance.baseUrl.isNotEmpty && !await _checkConnection()) {
      state = const AuthState(
        status: AuthStatus.unauthenticated,
        serverUnreachable: true,
        errorMessage: _serverDownMessage,
      );
      return;
    }

    final token = await AuthInterceptor.accessToken;
    if (token != null) {
      state = const AuthState(status: AuthStatus.loading);
      try {
        final user = await _repository.getCurrentUser();
        state = AuthState(status: AuthStatus.authenticated, user: user);
        return;
      } catch (_) {
        // Token invalid/expired: drop it and fall through to credential login.
        await AuthInterceptor.clearTokens();
      }
    }

    // No valid token: try to sign back in with the remembered credentials.
    final creds = await AuthInterceptor.savedCredentials;
    if (creds != null) {
      state = const AuthState(status: AuthStatus.loading);
      try {
        await _authenticate(creds.key, creds.value);
        return;
      } on Exception catch (_) {
        // Credentials no longer work; forget them.
        await AuthInterceptor.clearCredentials();
      }
    }

    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  Future<bool> login(String username, String password) async {
    state = const AuthState(status: AuthStatus.loading);

    // Verify connectivity first; three strikes and we start over.
    if (!await _checkConnection()) {
      state = const AuthState(
        status: AuthStatus.unauthenticated,
        serverUnreachable: true,
        errorMessage: _serverDownMessage,
      );
      return false;
    }

    try {
      await _authenticate(username, password);
      return true;
    } on Exception catch (e) {
      state = AuthState(
        status: AuthStatus.error,
        errorMessage: _friendlyLoginError(e),
      );
      return false;
    }
  }

  Future<bool> register({
    required String username,
    required String email,
    required String password,
    String? phone,
    String? inviteCode,
  }) async {
    final passwordHash = sha256.convert(utf8.encode(password)).toString();
    state = const AuthState(status: AuthStatus.loading);
    try {
      final response = await _repository.register(
        username: username,
        email: email,
        passwordHash: passwordHash,
        phone: phone,
        inviteCode: inviteCode,
      );
      await _persistSession(username, password, response);
      return true;
    } on Exception catch (e) {
      state = AuthState(
        status: AuthStatus.error,
        errorMessage: _friendlyLoginError(e),
      );
      return false;
    }
  }

  Future<void> logout() async {
    await AuthInterceptor.clearTokens();
    await AuthInterceptor.clearCredentials();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  /// Clears a previous "server unreachable" condition once the user has
  /// successfully reconnected from the server-config screen.
  void clearConnectionError() {
    if (state.serverUnreachable) {
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  /// Logs in and persists the session (tokens + credentials) so the next
  /// launch can skip the login screen entirely.
  Future<void> _authenticate(String username, String password) async {
    final passwordHash = sha256.convert(utf8.encode(password)).toString();
    final response = await _repository.login(
      LoginRequest(username: username, passwordHash: passwordHash),
    );
    await _persistSession(username, password, response);
  }

  Future<void> _persistSession(
    String username,
    String password,
    LoginResponse response,
  ) async {
    try {
      await AuthInterceptor.saveTokens(
          response.accessToken, response.refreshToken);
    } catch (_) {}
    try {
      await AuthInterceptor.saveCredentials(username, password);
    } catch (_) {}
    final user = await _repository.getCurrentUser();
    state = AuthState(status: AuthStatus.authenticated, user: user);
  }

  /// Maps raw login/register exceptions to short, user-facing messages.
  String _friendlyLoginError(Exception e) {
    if (e is DioException) {
      final code = e.response?.statusCode;
      if (code == 400 || code == 401 || code == 403) return '用户名或密码错误';
      if (code == 404) return '登录接口不存在，请确认服务器版本';
      if (code != null && code >= 500) return '服务器内部错误，请稍后重试';
      return '登录失败，请检查网络后重试';
    }
    return '登录失败，请稍后重试';
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(AuthRepository());
});

final isLoggedInProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).status == AuthStatus.authenticated;
});
