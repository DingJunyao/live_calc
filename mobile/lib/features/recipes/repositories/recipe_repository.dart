import '../../../core/api/api_client.dart';
import '../models/recipe_summary.dart';
import '../models/recipe_detail.dart';

/// 防御性数值转换：后端 Decimal 字段会序列化为字符串（如 "12.50"）
double _toDouble(dynamic v, [double fallback = 0]) {
  if (v == null) return fallback;
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString()) ?? fallback;
}

String? _str(dynamic v) => v?.toString();

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

class RecipeRepository {
  final ApiClient _client;
  RecipeRepository({ApiClient? client})
      : _client = client ?? ApiClient.instance;

  Future<List<RecipeSummary>> getRecipes(
      {String? search, int page = 1, int pageSize = 50}) async {
    final params = <String, dynamic>{
      'skip': (page - 1) * pageSize,
      'limit': pageSize,
    };
    if (search != null) params['search'] = search;
    final response = await _client.dio.get('/recipes', queryParameters: params);
    final list = (response.data is List)
        ? response.data as List
        : (response.data['items'] as List);
    return list
        .map((e) => RecipeSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<RecipeDetail> getRecipe(int id) async {
    final response = await _client.dio.get('/recipes/$id');
    return RecipeDetail.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecipeCost> getRecipeCost(int id) async {
    final response = await _client.dio.get('/recipes/$id/cost');
    return RecipeCost.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecipeNutrition> getRecipeNutrition(int id) async {
    final response = await _client.dio.get('/recipes/$id/nutrition');
    return RecipeNutrition.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<CostHistoryPoint>> getRecipeCostHistory(int id,
      {int days = 30}) async {
    final response = await _client.dio.get(
      '/recipes/$id/cost-history-range',
      queryParameters: {'days': days, 'offset_days': 0},
    );
    final list = response.data as List? ?? const [];
    return list
        .map((e) => CostHistoryPoint.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Map<int, RecipeCostInfo>> getRecipesBatchCost(List<int> ids) async {
    if (ids.isEmpty) return {};
    final response =
        await _client.dio.post('/recipes/batch-cost', data: {'ids': ids});
    final data = response.data;
    if (data is! Map) return {};
    final result = <int, RecipeCostInfo>{};
    for (final entry in data.entries) {
      final id = int.tryParse('${entry.key}');
      if (id == null || entry.value is! Map) continue;
      final m = entry.value as Map;
      result[id] = RecipeCostInfo(
        estimatedCost: _toDoubleOrNull(m['estimated_cost']),
        calories: _toIntOrNull(m['calories']),
      );
    }
    return result;
  }
}

/// batch-cost 接口返回的单条成本/热量信息
class RecipeCostInfo {
  final double? estimatedCost;
  final int? calories;
  const RecipeCostInfo({this.estimatedCost, this.calories});
}

/// 单条食材成本明细（来自 /cost 接口的 cost_breakdown）
class CostBreakdownItem {
  final String ingredientName;
  final int? recipeIngredientId;
  final double cost;
  final String? quantity;
  final double unitPrice;
  final String? fallbackChain;
  const CostBreakdownItem({
    required this.ingredientName,
    this.recipeIngredientId,
    required this.cost,
    this.quantity,
    required this.unitPrice,
    this.fallbackChain,
  });
  factory CostBreakdownItem.fromJson(Map<String, dynamic> json) {
    return CostBreakdownItem(
      ingredientName: _str(json['ingredient_name']) ??
          _str(json['original_ingredient_name']) ??
          '',
      recipeIngredientId: _toIntOrNull(json['recipe_ingredient_id']),
      cost: _toDouble(json['cost']),
      quantity: json['quantity']?.toString(),
      unitPrice: _toDouble(json['unit_price']),
      fallbackChain: _str(json['recipe_chain']) ??
          _str(json['aggregation_chain']) ??
          _str(json['fallback_chain']),
    );
  }
}

/// 菜谱成本（来自 /cost 接口）
class RecipeCost {
  final double totalCost;
  final double costPerServing;
  final List<CostBreakdownItem> breakdown;
  const RecipeCost({
    required this.totalCost,
    required this.costPerServing,
    required this.breakdown,
  });
  factory RecipeCost.fromJson(Map<String, dynamic> json) {
    return RecipeCost(
      totalCost: _toDouble(json['total_cost']),
      costPerServing: _toDouble(json['cost_per_serving']),
      breakdown: ((json['cost_breakdown'] as List?) ?? const [])
          .map((e) => CostBreakdownItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class NutritionItem {
  final double value;
  final String unit;
  final String standard;
  final double nrpPct;
  const NutritionItem(
      {required this.value,
      required this.unit,
      this.standard = '',
      this.nrpPct = 0});
  factory NutritionItem.fromJson(Map<String, dynamic> json) {
    return NutritionItem(
      value: _toDouble(json['value']),
      unit: _str(json['unit']) ?? '',
      standard: _str(json['standard']) ?? '',
      nrpPct: _toDouble(json['nrp_pct']),
    );
  }
}

/// 菜谱营养（来自 /nutrition 接口）
class RecipeNutrition {
  final double totalCalories;
  final double totalProtein;
  final double totalFat;
  final double totalCarbs;
  final Map<String, NutritionItem> perServingNutrients;
  const RecipeNutrition({
    required this.totalCalories,
    required this.totalProtein,
    required this.totalFat,
    required this.totalCarbs,
    this.perServingNutrients = const {},
  });
  factory RecipeNutrition.fromJson(Map<String, dynamic> json) {
    final core = <String, NutritionItem>{};
    final perServing = json['per_serving_nutrition'] as Map?;
    if (perServing != null) {
      final coreMap = perServing['core_nutrients'] as Map?;
      if (coreMap != null) {
        core.addEntries(coreMap.entries.map((e) => MapEntry(
              e.key.toString(),
              NutritionItem.fromJson(e.value as Map<String, dynamic>),
            )));
      }
    }
    return RecipeNutrition(
      totalCalories: _toDouble(json['total_calories']),
      totalProtein: _toDouble(json['total_protein']),
      totalFat: _toDouble(json['total_fat']),
      totalCarbs: _toDouble(json['total_carbs']),
      perServingNutrients: core,
    );
  }
}

/// 成本趋势单点（来自 /cost-history-range 接口）
class CostHistoryPoint {
  final String date;
  final double minCost;
  final double maxCost;
  final double avgCost;
  const CostHistoryPoint({
    required this.date,
    required this.minCost,
    required this.maxCost,
    required this.avgCost,
  });

  /// 按比例缩放（用于份数调整后同步趋势图，与 Web 端 chartData 逻辑一致）
  CostHistoryPoint scaled(double ratio) => CostHistoryPoint(
        date: date,
        minCost: minCost * ratio,
        maxCost: maxCost * ratio,
        avgCost: avgCost * ratio,
      );
  factory CostHistoryPoint.fromJson(Map<String, dynamic> json) {
    return CostHistoryPoint(
      date: _str(json['date']) ?? '',
      minCost: _toDouble(json['min_cost']),
      maxCost: _toDouble(json['max_cost']),
      avgCost: _toDouble(json['avg_cost']),
    );
  }
}
