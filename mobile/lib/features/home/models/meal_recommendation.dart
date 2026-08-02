class MealRecommendation {
  final String mealType; // breakfast, lunch, dinner
  final int? recipeId;
  final String? recipeName;
 final double? estimatedCost;
 final String? imageUrl;
  final double? calories;
  final double? proteinG;
  final double? carbsG;
  final double? fatG;

  const MealRecommendation({
    required this.mealType,
    this.recipeId,
    this.recipeName,
    this.estimatedCost,
    this.imageUrl,
    this.calories,
    this.proteinG,
    this.carbsG,
    this.fatG,
  });

  factory MealRecommendation.fromJson(Map<String, dynamic> json) {
    final recipe = json['recipe'] as Map<String, dynamic>?;
    final nutrition = recipe?['nutrition_per_serving'] as Map<String, dynamic>?;
    return MealRecommendation(
      mealType: json['meal_type'] as String? ?? '',
      recipeId: recipe?['id'] as int?,
      recipeName: recipe?['name'] as String?,
      estimatedCost: (recipe?['cost_estimate'] as num?)?.toDouble(),
      imageUrl: (recipe?['image_urls'] as List<dynamic>?)?.firstOrNull?.toString(),
      calories: (nutrition?['calories'] as num?)?.toDouble(),
      proteinG: (nutrition?['protein_g'] as num?)?.toDouble(),
      carbsG: (nutrition?['carbs_g'] as num?)?.toDouble(),
      fatG: (nutrition?['fat_g'] as num?)?.toDouble(),
    );
  }
}

class DailyRecommendation {
  final String date;
  final String status;
  final List<MealRecommendation> meals;

  const DailyRecommendation({required this.date, this.status = 'ready', this.meals = const []});

  factory DailyRecommendation.fromJson(Map<String, dynamic> json) {
    return DailyRecommendation(
      date: json['date'] as String? ?? '',
      status: json['status'] as String? ?? 'ready',
      meals: (json['recommendations'] as List<dynamic>?)
              ?.map((e) => MealRecommendation.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
