class RecipeSummary {
  final int id;
  final String name;
  final String? description;
  final double? estimatedCost;
  final String? imageUrl;
  final int ingredientCount;
  final bool isPublic;

  const RecipeSummary({
    required this.id,
    required this.name,
    this.description,
    this.estimatedCost,
    this.imageUrl,
    this.ingredientCount = 0,
    this.isPublic = false,
  });

  factory RecipeSummary.fromJson(Map<String, dynamic> json) {
    return RecipeSummary(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      estimatedCost: double.tryParse(json['estimated_cost']?.toString() ?? ''),
      imageUrl: json['image_url'] as String?,
      ingredientCount: (json['ingredient_count'] as num?)?.toInt() ?? ((json['ingredients'] as List?)?.length ?? 0),
      isPublic: json['is_public'] as bool? ?? false,
    );
  }
}

