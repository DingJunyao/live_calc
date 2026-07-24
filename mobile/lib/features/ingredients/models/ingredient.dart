class Ingredient {
  final int id;
  final String name;
  final String? category;
  final String? categoryPath;
  final double? latestPrice;
  final String? unit;

  const Ingredient({
    required this.id,
    required this.name,
    this.category,
    this.categoryPath,
    this.latestPrice,
    this.unit,
  });

  factory Ingredient.fromJson(Map<String, dynamic> json) {
    return Ingredient(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      category: json['category'] as String?,
      categoryPath: json['category_path'] as String?,
      latestPrice: (json['latest_price'] as num?)?.toDouble(),
      unit: json['default_unit'] as String?,
    );
  }
}
