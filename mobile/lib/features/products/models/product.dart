class Product {
  final int id;
  final String name;
  final int? ingredientId;
  final String? ingredientName;
  final double? latestPrice;
  final String? unit;
  final String? barcode;

  const Product({
    required this.id,
    required this.name,
    this.ingredientId,
    this.ingredientName,
    this.latestPrice,
    this.unit,
    this.barcode,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      ingredientId: json['ingredient_id'] as int?,
      ingredientName: json['ingredient_name'] as String?,
      latestPrice: (json['latest_price'] as num?)?.toDouble(),
      unit: json['unit'] as String?,
      barcode: json['barcode'] as String?,
    );
  }
}
