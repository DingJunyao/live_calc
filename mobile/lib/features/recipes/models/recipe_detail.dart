import '../../../core/api/api_client.dart';

/// 兼容后端 Decimal 序列化为字符串（如 "12.50"）的情况；缺失时返回 null。
double? _toDoubleOrNull(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString());
}

/// 后端图片字段是 image_urls（已解析的 URL 列表，本地存储时为相对路径
/// /api/v1/static/images/...）。取首个；相对路径则拼接服务器 baseUrl。
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

/// 后端 tips 是 List[str]，这里合并为单段文字供界面展示。
String? _tipsToString(dynamic v) {
  if (v == null) return null;
  if (v is String) return v.isEmpty ? null : v;
  if (v is List) {
    final items = v.whereType<String>().where((s) => s.isNotEmpty).toList();
    return items.isEmpty ? null : items.join('；');
  }
  return null;
}

class RecipeIngredient {
  final String name;
  final String? quantity; // 后端为字符串，可能是 "100" 或范围 "80-120"，也可为空
  final String? unit;
  final double? estimatedCost;

  const RecipeIngredient({
    required this.name,
    this.quantity,
    this.unit,
    this.estimatedCost,
  });

  factory RecipeIngredient.fromJson(Map<String, dynamic> json) {
    return RecipeIngredient(
      name: json['name'] as String? ?? json['ingredient_name'] as String? ?? '',
      quantity: json['quantity']?.toString(),
      unit: json['unit'] as String?,
      estimatedCost: _toDoubleOrNull(json['estimated_cost']),
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
      stepNumber: (json['step'] as num?)?.toInt() ??
          (json['step_number'] as num?)?.toInt() ??
          0,
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
    final stepsJson = (json['cooking_steps'] is List)
        ? json['cooking_steps'] as List<dynamic>
        : (json['steps'] as List<dynamic>? ?? const []);
    return RecipeDetail(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      totalCost: _toDoubleOrNull(json['estimated_cost']),
      imageUrl: _firstImageUrl(json),
      ingredients: (json['ingredients'] as List<dynamic>?)
              ?.map((e) => RecipeIngredient.fromJson(e as Map<String, dynamic>))
              .toList() ?? [],
      steps: stepsJson
          .map((e) => RecipeStep.fromJson(e as Map<String, dynamic>))
          .toList(),
      tips: _tipsToString(json['tips']),
      isPublic: json['is_public'] as bool? ?? false,
    );
  }
}
