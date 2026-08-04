import '../../../core/api/api_client.dart';
import '../models/recipe_summary.dart';
import '../models/recipe_detail.dart';
import 'package:dio/dio.dart';

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

/// Vague quantity words -> estimated grams (aligned with Web VAGUE_QUANTITY_GRAM_MAP)
const _vagueQuantityGram = <String, double>{'\u9002\u91cf': 100, '\u5c11\u8bb8': 5};

/// Effective ingredient quantity for merchant price estimation
class IngredientQuantity {
  final double? qty;
  final String qtyDisplay;
  final String qtyUnit;
  const IngredientQuantity({
    this.qty,
    this.qtyDisplay = '',
    this.qtyUnit = '',
  });
}

String _fmtNum(double v) =>
    v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toString();

/// Extract effective quantity from quantity / quantity_range / original_quantity.
/// Logic mirrors Web getEffectiveQuantity.
IngredientQuantity resolveIngredientQuantity(RecipeIngredient ingredient) {
  var qty = ingredient.quantity != null
      ? double.tryParse(ingredient.quantity!)
      : null;
  var qtyDisplay = '';
  var qtyUnit = ingredient.unit ?? '';

  if (qty != null) {
    qtyDisplay = '';
  } else if (ingredient.quantityRange != null) {
    final min = ingredient.quantityRange!.min;
    final max = ingredient.quantityRange!.max;
    qty = (min + max) / 2;
    qtyDisplay = '-';
  }

  // Vague quantity fallback (e.g. '\u9002\u91cf' -> 100g)
  if (qty == null && ingredient.originalQuantity != null) {
    final orig = ingredient.originalQuantity!;
    for (final entry in _vagueQuantityGram.entries) {
      if (orig.contains(entry.key)) {
        qty = entry.value;
        qtyDisplay = '(g)';
        qtyUnit = 'g';
        break;
      }
    }
  }

  return IngredientQuantity(qty: qty, qtyDisplay: qtyDisplay, qtyUnit: qtyUnit);
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
  final int? ingredientId;
  final double cost;
  final String? quantity;
  final double unitPrice;
  final String? fallbackChain;
  const CostBreakdownItem({
    required this.ingredientName,
    this.recipeIngredientId,
    this.ingredientId,
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
      ingredientId: _toIntOrNull(json['ingredient_id']),
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
  final String? key;
  final String? nameZh;
  const NutritionItem(
      {required this.value,
      required this.unit,
      this.standard = '',
      this.nrpPct = 0,
      this.key,
      this.nameZh});
  factory NutritionItem.fromJson(Map<String, dynamic> json) {
    return NutritionItem(
      value: _toDouble(json['value']),
      unit: _str(json['unit']) ?? '',
      standard: _str(json['standard']) ?? '',
      nrpPct: _toDouble(json['nrp_pct']),
      key: _str(json['key']),
      nameZh: _str(json['name_zh']),
    );
  }
}

/// 单个食材的营养贡献（来自 /nutrition 接口 ingredient_details）
class IngredientNutritionDetail {
  final int? recipeIngredientId;
  final int? ingredientId;
  final String ingredientName;
  final Map<String, NutritionItem> nutritionContribution;
  const IngredientNutritionDetail({
    this.recipeIngredientId,
    this.ingredientId,
    required this.ingredientName,
    this.nutritionContribution = const {},
  });
  factory IngredientNutritionDetail.fromJson(Map<String, dynamic> json) {
    final contrib = <String, NutritionItem>{};
    final contribRaw = json['nutrition_contribution'] as Map?;
    if (contribRaw != null) {
      contrib.addEntries(contribRaw.entries.map((e) => MapEntry(
            e.key.toString(),
            NutritionItem.fromJson(e.value as Map<String, dynamic>),
          )));
    }
    return IngredientNutritionDetail(
      recipeIngredientId: _toIntOrNull(json['recipe_ingredient_id']),
      ingredientId: _toIntOrNull(json['ingredient_id']),
      ingredientName: _str(json['ingredient_name']) ?? '',
      nutritionContribution: contrib,
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
  final Map<String, NutritionItem> allNutrients;
  final List<IngredientNutritionDetail> ingredientDetails;
  const RecipeNutrition({
    required this.totalCalories,
    required this.totalProtein,
    required this.totalFat,
    required this.totalCarbs,
    this.perServingNutrients = const {},
    this.allNutrients = const {},
    this.ingredientDetails = const [],
  });
  factory RecipeNutrition.fromJson(Map<String, dynamic> json) {
    final core = <String, NutritionItem>{};
    final all = <String, NutritionItem>{};
    final perServing = json['per_serving_nutrition'] as Map?;
    if (perServing != null) {
      final coreMap = perServing['core_nutrients'] as Map?;
      if (coreMap != null) {
        core.addEntries(coreMap.entries.map((e) => MapEntry(
              e.key.toString(),
              NutritionItem.fromJson(e.value as Map<String, dynamic>),
            )));
      }
      final allMap = perServing['all_nutrients'] as Map?;
      if (allMap != null) {
        all.addEntries(allMap.entries.map((e) => MapEntry(
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
      allNutrients: all,
      ingredientDetails: ((json['ingredient_details'] as List?) ?? const [])
          .map((e) =>
              IngredientNutritionDetail.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// 成本趋势单点（来自 /cost-history-range 接口）
class CostHistoryPoint {
  final String date;
  final double minCost;
  final double maxCost;
  final double avgCost;
  final List<CostHistoryBreakdownItem> breakdown;
  const CostHistoryPoint({
    required this.date,
    required this.minCost,
    required this.maxCost,
    required this.avgCost,
    this.breakdown = const [],
  });

  /// 按比例缩放（用于份数调整后同步趋势图，与 Web 端 chartData 逻辑一致）
  CostHistoryPoint scaled(double ratio) => CostHistoryPoint(
        date: date,
        minCost: minCost * ratio,
        maxCost: maxCost * ratio,
        avgCost: avgCost * ratio,
        breakdown: breakdown
            .map((b) => b.copyWith(cost: b.cost * ratio))
            .toList(),
      );
  factory CostHistoryPoint.fromJson(Map<String, dynamic> json) {
    return CostHistoryPoint(
      date: _str(json['date']) ?? '',
      minCost: _toDouble(json['min_cost']),
      maxCost: _toDouble(json['max_cost']),
      avgCost: _toDouble(json['avg_cost']),
      breakdown: ((json['breakdown'] as List?) ?? const [])
          .map((e) => CostHistoryBreakdownItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// 成本趋势单点中的食材成本明细（用于堆叠面积图）
class CostHistoryBreakdownItem {
  final int? ingredientId;
  final String ingredientName;
  final double cost;
  const CostHistoryBreakdownItem({
    this.ingredientId,
    required this.ingredientName,
    required this.cost,
  });
  CostHistoryBreakdownItem copyWith({double? cost}) => CostHistoryBreakdownItem(
        ingredientId: ingredientId,
        ingredientName: ingredientName,
        cost: cost ?? this.cost,
      );
  factory CostHistoryBreakdownItem.fromJson(Map<String, dynamic> json) {
    return CostHistoryBreakdownItem(
      ingredientId: _toIntOrNull(json['ingredient_id']),
      ingredientName: _str(json['ingredient_name']) ?? '',
      cost: _toDouble(json['cost']),
    );
  }
}

/// 按商家维度计算的菜谱成本项（来自 /merchant-costs 接口）
class MerchantCostItem {
  final int merchantId;
  final String merchantName;
  final double coveredCost;
  final double externalCost;
  final double totalCost;
  final int coveredCount;
  final int totalIngredients;
  final List<String> missingIngredients;
  final List<String> fallbackChains;
  final bool isRecommended;
  const MerchantCostItem({
    required this.merchantId,
    required this.merchantName,
    required this.coveredCost,
    required this.externalCost,
    required this.totalCost,
    required this.coveredCount,
    required this.totalIngredients,
    this.missingIngredients = const [],
    this.fallbackChains = const [],
    this.isRecommended = false,
  });
  factory MerchantCostItem.fromJson(Map<String, dynamic> json) {
    return MerchantCostItem(
      merchantId: _toIntOrNull(json['merchant_id']) ?? 0,
      merchantName: _str(json['merchant_name']) ?? '',
      coveredCost: _toDouble(json['covered_cost']),
      externalCost: _toDouble(json['external_cost']),
      totalCost: _toDouble(json['total_cost']),
      coveredCount: _toIntOrNull(json['covered_count']) ?? 0,
      totalIngredients: _toIntOrNull(json['total_ingredients']) ?? 0,
      missingIngredients: ((json['missing_ingredients'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      fallbackChains: ((json['fallback_chains'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      isRecommended: json['is_recommended'] == true,
    );
  }
}

/// 菜谱按商家成本估算响应
class RecipeMerchantCost {
  final String currency;
  final List<MerchantCostItem> merchants;
  const RecipeMerchantCost({
    this.currency = 'CNY',
    this.merchants = const [],
  });
  factory RecipeMerchantCost.fromJson(Map<String, dynamic> json) {
    return RecipeMerchantCost(
      currency: _str(json['currency']) ?? 'CNY',
      merchants: ((json['merchants'] as List?) ?? const [])
          .map((e) => MerchantCostItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// 单个商家对某食材的最新价格（来自 latest-price-by-merchant 接口）
class MerchantPriceRecord {
  final int merchantId;
  final String merchantName;
  final double price;
  final String? unit;
  final double? totalCost;
  final bool isLowest;
  const MerchantPriceRecord({
    required this.merchantId,
    required this.merchantName,
    required this.price,
    this.unit,
    this.totalCost,
    this.isLowest = false,
  });
  factory MerchantPriceRecord.fromJson(Map<String, dynamic> json) {
    return MerchantPriceRecord(
      merchantId: _toIntOrNull(json['merchant_id']) ?? 0,
      merchantName: _str(json['merchant_name']) ??
          'merchant#',
      price: _toDouble(json['price']),
      unit: _str(json['unit']),
      totalCost: _toDoubleOrNull(json['total_cost']),
      isLowest: json['is_lowest'] == true,
    );
  }
}

/// 菜谱单个食材的商家比价结果
class MerchantPriceItem {
  final int recipeIngredientId;
  final int ingredientId;
  final String ingredientName;
  final String? qtyDisplay;
  final String? unit;
  final String? fallbackChain;
  final List<MerchantPriceRecord> prices;
  const MerchantPriceItem({
    required this.recipeIngredientId,
    required this.ingredientId,
    required this.ingredientName,
    this.qtyDisplay,
    this.unit,
    this.fallbackChain,
    this.prices = const [],
  });
}
