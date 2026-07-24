import 'package:dio/dio.dart';
import '../../../core/api/api_client.dart';
import '../models/auth_config.dart';
import '../models/login_request.dart';
import '../models/user.dart';

class AuthRepository {
  final ApiClient _client;

  AuthRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<AuthConfig> getConfig() async {
    final response = await _client.dio.get('/auth/config');
    return AuthConfig.fromJson(response.data as Map<String, dynamic>);
  }

  Future<LoginResponse> login(LoginRequest request) async {
    final response = await _client.dio.post('/auth/login', data: request.toJson());
    return LoginResponse.fromJson(response.data as Map<String, dynamic>);
  }

  Future<LoginResponse> register({
    required String username,
    required String email,
    required String password,
    String? phone,
    String? inviteCode,
  }) async {
    final data = <String, dynamic>{'username': username, 'email': email, 'password': password};
    if (phone != null) data['phone'] = phone;
    if (inviteCode != null) data['invite_code'] = inviteCode;
    final response = await _client.dio.post('/auth/register', data: data);
    return LoginResponse.fromJson(response.data as Map<String, dynamic>);
  }

  Future<User> getCurrentUser() async {
    final response = await _client.dio.get('/auth/me');
    return User.fromJson(response.data as Map<String, dynamic>);
  }
}
