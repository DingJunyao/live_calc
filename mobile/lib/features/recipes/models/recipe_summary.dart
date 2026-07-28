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

class RecipeSummary {
  final int id;
  final String name;
  final String? description;
  final double? estimatedCost;
  final String? imageUrl;
  final int servings;
  final bool isPublic;

  const RecipeSummary({
    required this.id,
    required this.name,
    this.description,
    this.estimatedCost,
    this.imageUrl,
    this.servings = 1,
    this.isPublic = false,
  });

  factory RecipeSummary.fromJson(Map<String, dynamic> json) {
    return RecipeSummary(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      estimatedCost: _toDoubleOrNull(json['estimated_cost']),
      imageUrl: _firstImageUrl(json),
      servings: (json['servings'] as num?)?.toInt() ?? 1,
      isPublic: json['is_public'] as bool? ?? false,
    );
  }
}
