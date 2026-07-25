class MealRecommendation {
  final String mealType; // breakfast, lunch, dinner
  final int? recipeId;
  final String? recipeName;
  final double? estimatedCost;
  final String? imageUrl;

  const MealRecommendation({
    required this.mealType,
    this.recipeId,
    this.recipeName,
    this.estimatedCost,
    this.imageUrl,
  });

  factory MealRecommendation.fromJson(Map<String, dynamic> json) {
    return MealRecommendation(
      mealType: json['meal_type'] as String? ?? '',
      recipeId: json['recipe_id'] as int?,
      recipeName: json['recipe_name'] as String?,
      estimatedCost: (json['estimated_cost'] as num?)?.toDouble(),
      imageUrl: json['image_url'] as String?,
    );
  }
}

class DailyRecommendation {
  final String date;
  final List<MealRecommendation> meals;

  const DailyRecommendation({required this.date, required this.meals});

  factory DailyRecommendation.fromJson(Map<String, dynamic> json) {
    return DailyRecommendation(
      date: json['date'] as String? ?? '',
      meals: (json['meals'] as List<dynamic>?)
              ?.map((e) => MealRecommendation.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
