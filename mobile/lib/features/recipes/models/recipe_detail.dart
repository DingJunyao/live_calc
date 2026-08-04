import '../../../core/api/api_client.dart';

double? _toDoubleOrNull(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString());
}

int? _toIntOrNull(dynamic v) {
  if (v == null) return null;
  if (v is int) return v;
  if (v is num) return v.toInt();
  return int.tryParse(v.toString());
}

int _asInt(dynamic v, [int fallback = 0]) => _toIntOrNull(v) ?? fallback;

bool _asBool(dynamic v, [bool fallback = false]) =>
    v is bool ? v : (v is String ? v == 'true' : fallback);

String? _asString(dynamic v) => v?.toString();

String? _firstImageUrl(Map<String, dynamic> json) {
  final List? urls = (json['image_urls'] is List)
      ? json['image_urls'] as List
      : (json['images'] is List ? json['images'] as List : null);
  if (urls == null || urls.isEmpty) return null;
  final raw = urls.first?.toString();
  if (raw == null || raw.isEmpty) return null;
  if (raw.startsWith('http')) return raw;
  final base = ApiClient.instance.baseUrl;
  return base.isEmpty ? raw : '$base$raw';
}

class QuantityRange {
  final double min;
  final double max;
  const QuantityRange({required this.min, required this.max});

  factory QuantityRange.fromJson(dynamic v) {
    if (v is Map) {
      return QuantityRange(
        min: _toDoubleOrNull(v['min']) ?? 0,
        max: _toDoubleOrNull(v['max']) ?? 0,
      );
    }
    if (v is String) {
      final parts = v.split(RegExp(r'[-~]'));
      if (parts.length == 2) {
        return QuantityRange(
          min: double.tryParse(parts[0].trim()) ?? 0,
          max: double.tryParse(parts[1].trim()) ?? 0,
        );
      }
    }
    return const QuantityRange(min: 0, max: 0);
  }
}

class RecipeIngredient {
  final int? id;
  final int? ingredientId;
  final String name;
  final String? quantity;
  final QuantityRange? quantityRange;
  final String? unit;
  final bool isOptional;
  final String? note;
  final String? originalQuantity;

  const RecipeIngredient({
    this.id,
    this.ingredientId,
    required this.name,
    this.quantity,
    this.quantityRange,
    this.unit,
    this.isOptional = false,
    this.note,
    this.originalQuantity,
  });

  factory RecipeIngredient.fromJson(Map<String, dynamic> json) {
    return RecipeIngredient(
      id: _toIntOrNull(json['id']),
      ingredientId: _toIntOrNull(json['ingredient_id']),
      name: json['name'] as String? ?? json['ingredient_name'] as String? ?? '',
      quantity: json['quantity']?.toString(),
      quantityRange: json['quantity_range'] != null
          ? QuantityRange.fromJson(json['quantity_range'])
          : null,
      unit: _asString(json['unit']),
      isOptional: _asBool(json['is_optional']),
      note: _asString(json['note']),
      originalQuantity: json['original_quantity']?.toString(),
    );
  }
}

class RecipeStep {
  final int stepNumber;
  final String content;
  final String? imageUrl;
  final double? durationMinutes;
  final String? tips;

  const RecipeStep({
    required this.stepNumber,
    required this.content,
    this.imageUrl,
    this.durationMinutes,
    this.tips,
  });

  factory RecipeStep.fromJson(Map<String, dynamic> json) {
    return RecipeStep(
      stepNumber:
          _toIntOrNull(json['step']) ?? _toIntOrNull(json['step_number']) ?? 0,
      content: json['content'] as String? ?? '',
      imageUrl: _asString(json['image_url']),
      durationMinutes: _toDoubleOrNull(json['duration_minutes']),
      tips: _asString(json['tips']),
    );
  }
}

class RecipeDetail {
  final int id;
  final String name;
  final String? description;
  final String? category;
  final String? difficulty;
  final int servings;
  final List<String> tags;
  final String? imageUrl;
  final List<RecipeIngredient> ingredients;
  final List<RecipeStep> steps;
  final List<String> tips;
  final bool isPublic;

  const RecipeDetail({
    required this.id,
    required this.name,
    this.description,
    this.category,
    this.difficulty,
    this.servings = 1,
    this.tags = const [],
    this.imageUrl,
    this.ingredients = const [],
    this.steps = const [],
    this.tips = const [],
    this.isPublic = false,
  });

  factory RecipeDetail.fromJson(Map<String, dynamic> json) {
    final stepsJson = (json['cooking_steps'] is List)
        ? json['cooking_steps'] as List<dynamic>
        : (json['steps'] as List<dynamic>? ?? const []);
    final tipsRaw = json['tips'];
    final tipsList = <String>[];
    if (tipsRaw is List) {
      tipsList.addAll(
          tipsRaw.whereType<String>().where((s) => s.trim().isNotEmpty));
    } else if (tipsRaw is String && tipsRaw.trim().isNotEmpty) {
      tipsList.add(tipsRaw.trim());
    }
    return RecipeDetail(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
      description: _asString(json['description']),
      category: _asString(json['category']),
      difficulty: _asString(json['difficulty']),
      servings: _asInt(json['servings'], 1),
      tags: (json['tags'] as List?)?.map((e) => e.toString()).toList() ??
          const [],
      imageUrl: _firstImageUrl(json),
      ingredients: (json['ingredients'] as List<dynamic>?)
              ?.map((e) => RecipeIngredient.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      steps: stepsJson
          .map((e) => RecipeStep.fromJson(e as Map<String, dynamic>))
          .toList(),
      tips: tipsList,
      isPublic: _asBool(json['is_public']),
    );
  }
}
