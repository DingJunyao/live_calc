class User {
  final int id;
  final String username;
  final String email;
  final String? phone;
  final bool isAdmin;
  final String? avatar;

  const User({
    required this.id,
    required this.username,
    required this.email,
    this.phone,
    this.isAdmin = false,
    this.avatar,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      username: json['username'] as String,
      email: json['email'] as String? ?? '',
      phone: json['phone'] as String?,
      isAdmin: json['is_admin'] as bool? ?? false,
      avatar: json['avatar'] as String?,
    );
  }
}
