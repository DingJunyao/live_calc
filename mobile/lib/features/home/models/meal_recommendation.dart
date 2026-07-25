class RecipeBrief {
  final int id;
  final String? name;
  final double? costEstimate;
  final List<String>? imageUrls;

  const RecipeBrief({required this.id, this.name, this.costEstimate, this.imageUrls});

  factory RecipeBrief.fromJson(Map<String, dynamic> json) {
    return RecipeBrief(
      id: (json['id'] as num?)?.toInt() ?? 0,
      name: json['name'] as String?,
      costEstimate: (json['cost_estimate'] as num?)?.toDouble(),
      imageUrls: (json['image_urls'] as List<dynamic>?)?.cast<String>(),
    );
  }
}

class MealRecommendation {
  final String mealType;
  final RecipeBrief? recipe;

  const MealRecommendation({required this.mealType, this.recipe});

  factory MealRecommendation.fromJson(Map<String, dynamic> json) {
    final recipeJson = json['recipe'] as Map<String, dynamic>?;
    return MealRecommendation(
      mealType: json['meal_type'] as String? ?? '',
      recipe: recipeJson != null ? RecipeBrief.fromJson(recipeJson) : null,
    );
  }
}

class DailyRecommendation {
  final String date;
  final List<MealRecommendation> recommendations;
  final String status;

  const DailyRecommendation({
    required this.date,
    this.recommendations = const [],
    this.status = 'ready',
  });

  factory DailyRecommendation.fromJson(Map<String, dynamic> json) {
    return DailyRecommendation(
      date: json['date'] as String? ?? '',
      status: json['status'] as String? ?? 'ready',
      recommendations: (json['recommendations'] as List<dynamic>?)
              ?.map((e) => MealRecommendation.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
