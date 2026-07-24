class AuthConfig {
  final bool requireInviteCode;
  final bool allowRegistration;

  const AuthConfig({required this.requireInviteCode, required this.allowRegistration});

  factory AuthConfig.fromJson(Map<String, dynamic> json) {
    return AuthConfig(
      requireInviteCode: json['require_invite_code'] as bool? ?? false,
      allowRegistration: json['allow_registration'] as bool? ?? true,
    );
  }
}
