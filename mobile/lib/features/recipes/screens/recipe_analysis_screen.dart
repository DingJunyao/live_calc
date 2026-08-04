import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/recipe_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

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
    Future.microtask(
        () => ref.read(recipeDetailPageProvider(widget.id).notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(recipeDetailPageProvider(widget.id));
    final detail = state.detail;

    if (state.error != null && detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('成本分析')),
        body: ErrorDisplay(
          message: state.error!,
          onRetry: () =>
              ref.read(recipeDetailPageProvider(widget.id).notifier).load(),
        ),
      );
    }
    if (detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('成本分析')),
        body: const LoadingIndicator(message: '加载中...'),
      );
    }

    final breakdown = state.cost?.breakdown ?? [];
    final totalCost = state.cost?.totalCost ?? 0;
    final maxCost = breakdown.isEmpty
        ? 0.0
        : breakdown.map((i) => i.cost).reduce((a, b) => a > b ? a : b);

    return Scaffold(
      appBar: AppBar(title: Text('${detail.name} - 成本分析')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('成本分布',
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            if (state.loadingCost)
              const Center(
                  child: Padding(
                      padding: EdgeInsets.all(24),
                      child: CircularProgressIndicator()))
            else if (breakdown.isEmpty)
              Text('暂无食材成本数据',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.outline))
            else
              ...breakdown.map((item) {
                final pct = totalCost > 0 ? item.cost / totalCost * 100 : 0.0;
                final barWidth = maxCost > 0 ? item.cost / maxCost : 0.0;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                              child: Text(item.ingredientName,
                                  style: theme.textTheme.bodyMedium)),
                          Text('¥${item.cost.toStringAsFixed(2)}',
                              style: theme.textTheme.bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.bold)),
                          const SizedBox(width: 8),
                          Text('${pct.toStringAsFixed(1)}%',
                              style: theme.textTheme.labelSmall
                                  ?.copyWith(color: theme.colorScheme.outline)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: barWidth,
                          minHeight: 8,
                          backgroundColor:
                              theme.colorScheme.surfaceContainerHighest,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            const SizedBox(height: 16),
            if (!state.loadingCost) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(8)),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('总成本',
                        style: theme.textTheme.titleMedium
                            ?.copyWith(fontWeight: FontWeight.bold)),
                    Text('¥${totalCost.toStringAsFixed(2)}',
                        style: theme.textTheme.titleLarge
                            ?.copyWith(fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 32),
            // 营养信息
            Text('营养信息（每份）',
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            if (state.loadingNutrition)
              const Center(
                  child: Padding(
                      padding: EdgeInsets.all(24),
                      child: CircularProgressIndicator()))
            else if (state.nutrition == null)
              Text('暂无营养数据，需 USDA 匹配后显示',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.outline))
            else
              _buildNutritionRow(theme, state),
          ],
        ),
      ),
    );
  }

  Widget _buildNutritionRow(ThemeData theme, RecipeDetailPageState state) {
    final n = state.nutrition!;
    final servings = state.detail?.servings ?? 1;
    final core = n.perServingNutrients;
    final cal =
        core['能量']?.value ?? core['热量']?.value ?? n.totalCalories / servings;
    final protein = core['蛋白质']?.value ?? n.totalProtein / servings;
    final fat = core['脂肪']?.value ?? n.totalFat / servings;
    final carbs =
        core['碳水化合物']?.value ?? core['碳水']?.value ?? n.totalCarbs / servings;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _item(theme, Icons.local_fire_department, '热量',
              cal.toStringAsFixed(0), 'kcal'),
          _item(theme, Icons.fitness_center, '蛋白质', protein.toStringAsFixed(1),
              'g'),
          _item(theme, Icons.grain, '碳水', carbs.toStringAsFixed(1), 'g'),
          _item(theme, Icons.water_drop_outlined, '脂肪', fat.toStringAsFixed(1),
              'g'),
        ],
      ),
    );
  }

  Widget _item(
      ThemeData theme, IconData icon, String label, String value, String unit) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: theme.colorScheme.primary, size: 24),
        const SizedBox(height: 4),
        Text('$value$unit',
            style: theme.textTheme.titleSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        Text(label,
            style: theme.textTheme.labelSmall
                ?.copyWith(color: theme.colorScheme.outline)),
      ],
    );
  }
}
