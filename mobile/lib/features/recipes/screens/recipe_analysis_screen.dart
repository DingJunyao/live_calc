import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/recipe_provider.dart';
import '../widgets/cost_proportion_chart.dart';
import '../widgets/cost_trend_stacked_chart.dart';
import '../widgets/nutrition_source_grid.dart';
import '../widgets/merchant_cost_cards.dart';
import '../widgets/merchant_price_matrix.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

/// 菜谱分析页：对齐 web RecipeAnalysisView.vue
/// AppBar = 菜谱名 + 「分析」chip；5 模块顺序：
/// ①成本占比 → ②成本趋势 → ③营养溯源 → ④商家成本卡片 → ⑤商家比价矩阵。
class RecipeAnalysisScreen extends ConsumerStatefulWidget {
  final int id;
  const RecipeAnalysisScreen({super.key, required this.id});
  @override
  ConsumerState<RecipeAnalysisScreen> createState() =>
      _RecipeAnalysisScreenState();
}

class _RecipeAnalysisScreenState extends ConsumerState<RecipeAnalysisScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      final notifier = ref.read(recipeDetailPageProvider(widget.id).notifier);
      // 趋势初始天数由 load(initialDays: 90) 单次请求传入，对齐 web
      // loadCostHistory('quarter')；不再额外 reloadHistory，避免与 load()
      // 内部 _loadHistory 双请求竞态（load 整态重建会清空先写入的 history）。
      // _loadHistory 默认 30 天保证详情页「月」初始一致。
      notifier.load(initialDays: 90);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(recipeDetailPageProvider(widget.id));
    final detail = state.detail;

    if (state.error != null && detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('菜谱分析')),
        body: ErrorDisplay(
          message: state.error!,
          onRetry: () =>
              ref.read(recipeDetailPageProvider(widget.id).notifier).load(),
        ),
      );
    }
    if (detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('菜谱分析')),
        body: const LoadingIndicator(message: '加载中...'),
      );
    }

    final breakdown = state.cost?.breakdown ?? const [];
    final totalCost = state.cost?.totalCost ?? 0;

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(detail.name,
                  maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text('分析',
                  style: theme.textTheme.labelSmall?.copyWith(
                      color: theme.colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ① 成本占比
            CostProportionChart(
              breakdown: breakdown,
              totalCost: totalCost,
              loading: state.loadingCost,
            ),
            const SizedBox(height: 16),
            // ② 成本趋势
            CostTrendStackedChart(
              points: state.costHistory,
              loading: state.loadingHistory,
              onFilterChange: (filter) {
                final days = costHistoryDays[filter] ?? 90;
                ref
                    .read(recipeDetailPageProvider(widget.id).notifier)
                    .reloadHistory(days);
              },
            ),
            const SizedBox(height: 16),
            // ③ 营养贡献溯源
            NutritionSourceGrid(
              nutrition: state.nutrition,
              loading: state.loadingNutrition,
            ),
            const SizedBox(height: 16),
            // ④ 按商家预估成本
            MerchantCostCards(
              merchants: state.merchantCosts?.merchants ?? const [],
              loading: state.loadingMerchantCosts,
            ),
            const SizedBox(height: 16),
            // ⑤ 商家比价推荐
            MerchantPriceMatrix(
              ingredients: detail.ingredients,
              prices: state.merchantPrices,
              loading: state.loadingMerchantPrices,
            ),
          ],
        ),
      ),
    );
  }
}
