import 'recipe_summary.dart';

class RecipeIngredient {
  final String name;
  final double quantity;
  final String unit;
  final double? estimatedCost;

  const RecipeIngredient({
    required this.name,
    required this.quantity,
    required this.unit,
    this.estimatedCost,
  });

  factory RecipeIngredient.fromJson(Map<String, dynamic> json) {
    return RecipeIngredient(
      name: json['name'] as String? ?? json['ingredient_name'] as String? ?? '',
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0,
      unit: json['unit'] as String? ?? '个',
      estimatedCost: (json['estimated_cost'] as num?)?.toDouble(),
    );
  }
}

class RecipeStep {
  final int stepNumber;
  final String content;
  final String? imageUrl;

  const RecipeStep({required this.stepNumber, required this.content, this.imageUrl});

  factory RecipeStep.fromJson(Map<String, dynamic> json) {
    return RecipeStep(
      stepNumber: json['step_number'] as int? ?? 0,
      content: json['content'] as String? ?? '',
      imageUrl: json['image_url'] as String?,
    );
  }
}

class RecipeDetail {
  final int id;
  final String name;
  final String? description;
  final double? totalCost;
  final String? imageUrl;
  final List<RecipeIngredient> ingredients;
  final List<RecipeStep> steps;
  final String? tips;
  final bool isPublic;

  const RecipeDetail({
    required this.id,
    required this.name,
    this.description,
    this.totalCost,
    this.imageUrl,
    this.ingredients = const [],
    this.steps = const [],
    this.tips,
    this.isPublic = false,
  });

  factory RecipeDetail.fromJson(Map<String, dynamic> json) {
    return RecipeDetail(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      totalCost: (json['total_cost'] as num?)?.toDouble(),
      imageUrl: json['image_url'] as String?,
      ingredients: (json['ingredients'] as List<dynamic>?)
              ?.map((e) => RecipeIngredient.fromJson(e as Map<String, dynamic>))
              .toList() ?? [],
      steps: (json['steps'] as List<dynamic>?)
              ?.map((e) => RecipeStep.fromJson(e as Map<String, dynamic>))
              .toList() ?? [],
      tips: json['tips'] as String?,
      isPublic: json['is_public'] as bool? ?? false,
    );
  }
}
