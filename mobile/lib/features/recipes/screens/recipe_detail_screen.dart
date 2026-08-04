import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../models/recipe_detail.dart';
import '../providers/recipe_provider.dart';
import '../repositories/recipe_repository.dart';
import '../utils/nutrition_labels.dart';
import '../widgets/cost_trend_chart.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

class RecipeDetailScreen extends ConsumerStatefulWidget {
  final int id;
  const RecipeDetailScreen({super.key, required this.id});
  @override
  ConsumerState<RecipeDetailScreen> createState() => _RecipeDetailScreenState();
}

class _RecipeDetailScreenState extends ConsumerState<RecipeDetailScreen> {
  bool _showAllNutrients = false;

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
        appBar: AppBar(title: const Text('菜谱详情')),
        body: ErrorDisplay(
          message: state.error!,
          onRetry: () =>
              ref.read(recipeDetailPageProvider(widget.id).notifier).load(),
        ),
      );
    }
    if (detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('菜谱详情')),
        body: const LoadingIndicator(message: '加载中...'),
      );
    }

    final ratio = state.displayServings / detail.servings;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 220,
            pinned: true,
            title: Text(detail.name),
            actions: [
              IconButton(
                icon: const Icon(Icons.analytics_outlined),
                tooltip: '成本分析',
                onPressed: () => context.push('/recipes/${widget.id}/analysis'),
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              background: detail.imageUrl != null
                  ? Image.network(detail.imageUrl!, fit: BoxFit.cover)
                  : Container(color: theme.colorScheme.primaryContainer),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildHeader(theme, detail),
                  const SizedBox(height: 16),
                  _buildCostCard(theme, state, ratio),
                  const SizedBox(height: 16),
                  _buildIngredientsCard(theme, detail, state, ratio),
                  const SizedBox(height: 16),
                  _buildStepsCard(theme, detail),
                  const SizedBox(height: 16),
                  _buildNutritionCard(theme, state, ratio),
                  const SizedBox(height: 16),
                  if (detail.tips.isNotEmpty) ...[
                    _buildTipsCard(theme, detail.tips),
                    const SizedBox(height: 16),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---- 头部：分类 / 难度 / 份数 ----
  Widget _buildHeader(ThemeData theme, RecipeDetail detail) {
    final chips = <Widget>[];
    if (detail.category != null && detail.category!.isNotEmpty) {
      chips.add(_chip(
          theme,
          detail.category!,
          theme.colorScheme.primaryContainer,
          theme.colorScheme.onPrimaryContainer));
    }
    final diffLabel = _difficultyLabel(detail.difficulty);
    if (diffLabel != null) {
      chips.add(_chip(theme, diffLabel, theme.colorScheme.tertiaryContainer,
          theme.colorScheme.onTertiaryContainer));
    }
    chips.add(_chip(
        theme,
        '${detail.servings} 人份',
        theme.colorScheme.secondaryContainer,
        theme.colorScheme.onSecondaryContainer));
    if (!detail.isPublic) {
      chips.add(_chip(theme, '未发布', theme.colorScheme.errorContainer,
          theme.colorScheme.onErrorContainer));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(detail.name,
            style: theme.textTheme.headlineSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        if (detail.description != null && detail.description!.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(detail.description!,
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: theme.colorScheme.outline)),
        ],
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: chips),
      ],
    );
  }

  Widget _chip(ThemeData theme, String label, Color bg, Color fg) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration:
          BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
      child:
          Text(label, style: theme.textTheme.labelSmall?.copyWith(color: fg)),
    );
  }

  String? _difficultyLabel(String? d) {
    switch (d) {
      case 'simple':
        return '简单';
      case 'easy':
        return '容易';
      case 'medium':
        return '中等';
      case 'hard':
        return '困难';
      case 'expert':
        return '专家';
      default:
        return null;
    }
  }

  // ---- 成本估算 + 成本趋势 ----
  Widget _buildCostCard(
      ThemeData theme, RecipeDetailPageState state, double ratio) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.payments_outlined,
                    color: theme.colorScheme.tertiary, size: 20),
                const SizedBox(width: 8),
                Text('成本估算',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            Center(
              child: state.loadingCost
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : state.cost == null
                      ? Text('暂无成本数据',
                          style: theme.textTheme.bodyMedium
                              ?.copyWith(color: theme.colorScheme.outline))
                      : Text(
                          '¥${(state.cost!.totalCost * ratio).toStringAsFixed(2)}',
                          style: theme.textTheme.headlineMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: theme.colorScheme.tertiary),
                        ),
            ),
            const SizedBox(height: 16),
            CostTrendChart(
              points: state.costHistory.map((p) => p.scaled(ratio)).toList(),
              loading: state.loadingHistory,
              onRangeChange: (days) => ref
                  .read(recipeDetailPageProvider(widget.id).notifier)
                  .reloadHistory(days),
            ),
          ],
        ),
      ),
    );
  }

  // ---- 原料列表 ----
  Widget _buildIngredientsCard(ThemeData theme, RecipeDetail detail,
      RecipeDetailPageState state, double ratio) {
    final costMap = <int, CostBreakdownItem>{};
    if (state.cost != null) {
      for (final c in state.cost!.breakdown) {
        if (c.recipeIngredientId != null) {
          costMap[c.recipeIngredientId!] = c;
        }
      }
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.restaurant_menu,
                    color: theme.colorScheme.primary, size: 20),
                const SizedBox(width: 8),
                Text('原料',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const Spacer(),
                _ServingsStepper(
                  value: state.displayServings,
                  onChanged: (v) => ref
                      .read(recipeDetailPageProvider(widget.id).notifier)
                      .setServings(v),
                  canReset: state.displayServings != detail.servings,
                  onReset: () => ref
                      .read(recipeDetailPageProvider(widget.id).notifier)
                      .setServings(detail.servings),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (detail.ingredients.isEmpty)
              Text('暂无原料',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.outline))
            else
              Table(
                columnWidths: const {
                  0: FlexColumnWidth(),
                  1: FixedColumnWidth(88),
                  2: FixedColumnWidth(76),
                },
                defaultVerticalAlignment: TableCellVerticalAlignment.middle,
                children: [
                  for (final ing in detail.ingredients)
                    _buildIngredientRow(theme, ing, costMap[ing.id], ratio),
                ],
              ),
          ],
        ),
      ),
    );
  }

  TableRow _buildIngredientRow(ThemeData theme, RecipeIngredient ing,
      CostBreakdownItem? cb, double ratio) {
    final qtyText = _scaledQuantity(ing, ratio);
    final hasFallback =
        cb != null && cb.fallbackChain != null && cb.fallbackChain!.isNotEmpty;
    final canNavigate = ing.ingredientId != null;
    final onTap = canNavigate
        ? () => context.push('/ingredients/${ing.ingredientId}')
        : null;
    return TableRow(
      children: [
        // 名称（含可选标记、备注）
        InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 7),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    if (canNavigate)
                      Padding(
                        padding: const EdgeInsets.only(right: 2),
                        child: Icon(Icons.chevron_right,
                            size: 16, color: theme.colorScheme.outline),
                      ),
                    Flexible(
                      child: Text(ing.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodyLarge
                              ?.copyWith(fontWeight: FontWeight.w500)),
                    ),
                    if (ing.isOptional) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(
                            color: theme.colorScheme.secondaryContainer,
                            borderRadius: BorderRadius.circular(4)),
                        child: Text('可选',
                            style: theme.textTheme.labelSmall?.copyWith(
                                color: theme.colorScheme.onSecondaryContainer,
                                fontSize: 10)),
                      ),
                    ],
                  ],
                ),
                if (ing.note != null && ing.note!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(ing.note!,
                        style: theme.textTheme.labelSmall
                            ?.copyWith(color: theme.colorScheme.outline)),
                  ),
              ],
            ),
          ),
        ),
        // 用量
        InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 7),
            child: Text(qtyText,
                textAlign: TextAlign.right,
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.outline)),
          ),
        ),
        // 价格
        InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 7),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (hasFallback)
                  Tooltip(
                    message: '根据以下食材计算成本：\n${cb.fallbackChain}',
                    child: Icon(Icons.info_outline,
                        size: 14, color: theme.colorScheme.tertiary),
                  ),
                if (cb != null && cb.cost > 0) ...[
                  if (hasFallback) const SizedBox(width: 4),
                  Text('¥${(cb.cost * ratio).toStringAsFixed(2)}',
                      style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.primary,
                          fontWeight: FontWeight.bold)),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  /// 按份数比例缩放用量，与 Web 端 scaleQuantity 逻辑一致
  String _scaledQuantity(RecipeIngredient ing, double ratio) {
    if (ing.quantityRange != null && ing.quantityRange!.min > 0) {
      final min = (ing.quantityRange!.min * ratio);
      final max = (ing.quantityRange!.max * ratio);
      return '${_fmt(min)}~${_fmt(max)}${ing.unit != null ? ' ${ing.unit}' : ''}';
    }
    final num = double.tryParse(ing.quantity ?? '');
    if (num != null && num > 0) {
      return '${_fmt(num * ratio)}${ing.unit != null ? ' ${ing.unit}' : ''}';
    }
    if (ing.quantity != null && ing.quantity!.isNotEmpty) return ing.quantity!;
    if (ing.originalQuantity != null && ing.originalQuantity!.isNotEmpty) {
      return ing.originalQuantity!;
    }
    return '适量';
  }

  String _fmt(double n) {
    if (n == n.roundToDouble()) return n.toInt().toString();
    return n.toStringAsFixed(1).replaceFirst(RegExp(r'\.0$'), '');
  }

  // ---- 做法步骤 ----
  Widget _buildStepsCard(ThemeData theme, RecipeDetail detail) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.format_list_numbered,
                    color: theme.colorScheme.primary, size: 20),
                const SizedBox(width: 8),
                Text('做法步骤',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            if (detail.steps.isEmpty)
              Text('暂无步骤',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.outline))
            else
              ...detail.steps.asMap().entries.map((entry) {
                final index = entry.key;
                final step = entry.value;
                final num = step.stepNumber > 0 ? step.stepNumber : index + 1;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 28,
                        height: 28,
                        decoration: BoxDecoration(
                            color: theme.colorScheme.primary,
                            shape: BoxShape.circle),
                        child: Center(
                            child: Text('$num',
                                style: TextStyle(
                                    color: theme.colorScheme.onPrimary,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14))),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(step.content,
                                style: theme.textTheme.bodyLarge),
                            if (step.durationMinutes != null &&
                                step.durationMinutes! > 0) ...[
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  Icon(Icons.timer_outlined,
                                      size: 14,
                                      color: theme.colorScheme.outline),
                                  const SizedBox(width: 4),
                                  Text(
                                      '${step.durationMinutes!.toStringAsFixed(step.durationMinutes! == step.durationMinutes!.roundToDouble() ? 0 : 1)} 分钟',
                                      style: theme.textTheme.labelSmall
                                          ?.copyWith(
                                              color:
                                                  theme.colorScheme.outline)),
                                ],
                              ),
                            ],
                            if (step.tips != null && step.tips!.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                    color: theme.colorScheme.tertiaryContainer
                                        .withValues(alpha: 0.4),
                                    borderRadius: BorderRadius.circular(6)),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Icon(Icons.lightbulb_outline,
                                        size: 14,
                                        color: theme.colorScheme.tertiary),
                                    const SizedBox(width: 4),
                                    Expanded(
                                        child: Text(step.tips!,
                                            style: theme.textTheme.labelSmall
                                                ?.copyWith(
                                                    color: theme.colorScheme
                                                        .onTertiaryContainer))),
                                  ],
                                ),
                              ),
                            ],
                            if (step.imageUrl != null) ...[
                              const SizedBox(height: 8),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(8),
                                child: Image.network(step.imageUrl!,
                                    height: 150, fit: BoxFit.cover),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }

  // ---- 营养成分（表格 + 展开折叠 + NRV）----
  Widget _buildNutritionCard(
      ThemeData theme, RecipeDetailPageState state, double ratio) {
    final nutrition = state.nutrition;
    final core =
        nutrition?.perServingNutrients ?? const <String, NutritionItem>{};
    final otherCount =
        core.keys.where((k) => !defaultNutrientKeys.contains(k)).length;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.local_fire_department,
                    color: theme.colorScheme.primary, size: 20),
                const SizedBox(width: 8),
                Text('营养成分（每份）',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const Spacer(),
                if (!state.loadingNutrition && otherCount > 0)
                  TextButton.icon(
                    onPressed: () =>
                        setState(() => _showAllNutrients = !_showAllNutrients),
                    icon: Icon(
                        _showAllNutrients
                            ? Icons.expand_less
                            : Icons.expand_more,
                        size: 18),
                    label: Text(_showAllNutrients ? '收起' : '展开 +$otherCount 项'),
                    style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                  ),
              ],
            ),
            const Divider(height: 20),
            if (state.loadingNutrition)
              const Center(
                  child: Padding(
                      padding: EdgeInsets.all(16),
                      child: SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(strokeWidth: 2))))
            else if (nutrition == null || core.isEmpty)
              Text('暂无营养数据',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.outline))
            else
              _buildNutritionTable(theme, core, ratio),
          ],
        ),
      ),
    );
  }

  Widget _buildNutritionTable(
      ThemeData theme, Map<String, NutritionItem> core, double ratio) {
    // 构造行：默认 5 项优先，其余按排序顺序
    final rows = <String>[];
    // 能量键兼容（能量 / 热量）
    if (core.containsKey('能量')) {
      rows.add('能量');
    } else if (core.containsKey('热量')) {
      rows.add('热量');
    }
    for (final k in ['蛋白质', '脂肪', '碳水化合物', '钠']) {
      if (core.containsKey(k)) rows.add(k);
    }
    if (_showAllNutrients) {
      final otherKeys = core.keys
          .where((k) => !defaultNutrientKeys.contains(k) && k != '热量')
          .toList()
        ..sort(compareNutrients);
      rows.addAll(otherKeys);
    }

    const valueW = 70.0;
    const nrvW = 56.0;
    return Column(
      children: [
        // 表头
        Container(
          color: theme.colorScheme.surfaceContainerHighest,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          child: const Row(
            children: [
              Expanded(child: Text('营养素')),
              SizedBox(
                  width: valueW, child: Text('数量', textAlign: TextAlign.right)),
              SizedBox(
                  width: nrvW, child: Text('NRV%', textAlign: TextAlign.right)),
            ],
          ),
        ),
        // 数据行
        ...rows.asMap().entries.map((entry) {
          final key = entry.value;
          final item = core[key]!;
          final isLast = entry.key == rows.length - 1;
          final displayKey = nutrientDisplayLabel(key);
          final valueStr =
              '${(item.value * ratio).toStringAsFixed(1)} ${item.unit}';
          final nrv = _formatNrv(item);
          return Container(
            decoration: BoxDecoration(
                border: isLast
                    ? null
                    : Border(
                        bottom: BorderSide(
                            color: theme.colorScheme.outlineVariant,
                            width: 0.5))),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Row(
              children: [
                Expanded(child: Text(displayKey)),
                SizedBox(
                    width: valueW,
                    child: Text(valueStr, textAlign: TextAlign.right)),
                SizedBox(
                    width: nrvW, child: Text(nrv, textAlign: TextAlign.right)),
              ],
            ),
          );
        }),
        const SizedBox(height: 8),
        Text('NRV = 营养素参考值百分比',
            style: theme.textTheme.labelSmall
                ?.copyWith(color: theme.colorScheme.outline)),
      ],
    );
  }

  String _formatNrv(NutritionItem item) {
    if (item.standard == '无标准' || item.standard == '无标准值') return '-';
    if (item.nrpPct == 0) return '-';
    return '${item.nrpPct.toStringAsFixed(1)}%';
  }

  // ---- 小贴士 ----
  Widget _buildTipsCard(ThemeData theme, List<String> tips) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.lightbulb_outline,
                    color: theme.colorScheme.tertiary, size: 20),
                const SizedBox(width: 8),
                Text('小贴士',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            ...tips.map((tip) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        margin: const EdgeInsets.only(top: 6),
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                            color: theme.colorScheme.tertiary,
                            shape: BoxShape.circle),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                          child: Text(tip, style: theme.textTheme.bodyMedium)),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }
}

// ---- 份数增减器 ----
class _ServingsStepper extends StatelessWidget {
  final int value;
  final ValueChanged<int> onChanged;
  final bool canReset;
  final VoidCallback onReset;
  const _ServingsStepper(
      {required this.value,
      required this.onChanged,
      required this.canReset,
      required this.onReset});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _stepBtn(theme, Icons.remove, () => onChanged(value - 1), value <= 1),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Text('$value 人份',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(fontWeight: FontWeight.bold)),
        ),
        _stepBtn(theme, Icons.add, () => onChanged(value + 1), false),
        if (canReset) ...[
          const SizedBox(width: 4),
          GestureDetector(
            onTap: onReset,
            child: Padding(
              padding: const EdgeInsets.only(left: 4),
              child: Icon(Icons.restart_alt,
                  size: 16, color: theme.colorScheme.outline),
            ),
          ),
        ],
      ],
    );
  }

  Widget _stepBtn(
      ThemeData theme, IconData icon, VoidCallback onTap, bool disabled) {
    return Material(
      color: disabled
          ? theme.colorScheme.surfaceContainerHighest
          : theme.colorScheme.primaryContainer,
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: disabled ? null : onTap,
        child: Padding(
            padding: const EdgeInsets.all(4), child: Icon(icon, size: 18)),
      ),
    );
  }
}
