class UserPlace {
  final int id;
  final String name;
  final String? address;
  final double latitude;
  final double longitude;
  final String? kind; // home, company, custom

  const UserPlace({
    required this.id,
    required this.name,
    this.address,
    required this.latitude,
    required this.longitude,
    this.kind,
  });

  factory UserPlace.fromJson(Map<String, dynamic> json) {
    return UserPlace(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      address: json['address'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0,
      kind: json['kind'] as String?,
    );
  }
}
