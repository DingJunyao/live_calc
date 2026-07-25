class Merchant {
  final int id;
  final String name;
  final String? address;
  final double? latitude;
  final double? longitude;
  final String? phone;
  final int? productCount;

  const Merchant({
    required this.id, required this.name, this.address,
    this.latitude, this.longitude, this.phone, this.productCount,
  });

  factory Merchant.fromJson(Map<String, dynamic> json) {
    return Merchant(
      id: json['id'] as int, name: json['name'] as String? ?? '',
      address: json['address'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      phone: json['phone'] as String?,
      productCount: json['product_count'] as int?,
    );
  }
}
