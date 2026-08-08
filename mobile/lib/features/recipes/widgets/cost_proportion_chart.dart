import 'dart:math';
import 'package:flutter/material.dart';
import '../repositories/recipe_repository.dart';
import '../utils/ingredient_colors.dart';

/// 单个成本占比段（进度条段 / 清单行共用）
class CostProportionItem {
  final String name;
  final double value;
  final Color color;
  const CostProportionItem(
      {required this.name, required this.value, required this.color});
}

/// 构建成本占比数据：降序，前 5 + 其余合并为「其他」（对齐 web CostProportionChart）。
List<CostProportionItem> buildCostProportionItems(
    List<CostBreakdownItem> breakdown) {
  if (breakdown.isEmpty) return const [];
  final items = breakdown
      .map((b) => CostProportionItem(
          name: b.ingredientName.isEmpty ? '未知食材' : b.ingredientName,
          value: b.cost,
          color: getIngredientColor(b.ingredientId)))
      .toList()
    ..sort((a, b) => b.value.compareTo(a.value));
  if (items.length > 6) {
    final top5 = items.sublist(0, 5);
    final otherValue = items.sublist(5).fold<double>(0, (s, i) => s + i.value);
    top5.add(CostProportionItem(
        name: '其他', value: otherValue, color: const Color(0xFFE0E0E0)));
    return top5;
  }
  return items;
}

/// 食材成本占比彩色进度条（标题行右侧显示总价，段宽 = 占比，点击段/清单行高亮）。
class CostProportionChart extends StatefulWidget {
  final List<CostBreakdownItem> breakdown;
  final double totalCost;
  final bool loading;
  const CostProportionChart({
    super.key,
    required this.breakdown,
    required this.totalCost,
    this.loading = false,
  });

  @override
  State<CostProportionChart> createState() => _CostProportionChartState();
}

class _CostProportionChartState extends State<CostProportionChart> {
  int _touchedIndex = -1;

  @override
  void didUpdateWidget(CostProportionChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.breakdown != widget.breakdown) {
      _touchedIndex = -1;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final items = buildCostProportionItems(widget.breakdown);
    final hasData = !widget.loading && items.isNotEmpty;
    // 总价：优先外部传入，否则按各项求和（保留原口径）
    final total = widget.totalCost > 0
        ? widget.totalCost
        : items.fold<double>(0, (s, i) => s + i.value);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.bar_chart_outlined,
                  color: theme.colorScheme.tertiary, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text('食材成本占比',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ),
              // 总价从圆环中心移至标题行右侧
              if (hasData && total > 0)
                Text('¥${total.toStringAsFixed(2)}',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
            ]),
            const SizedBox(height: 12),
            if (widget.loading)
              const SizedBox(
                  height: 140,
                  child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2)))
            else if (widget.breakdown.isEmpty)
              SizedBox(
                height: 140,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.bar_chart_outlined,
                          size: 40, color: theme.colorScheme.outline),
                      const SizedBox(height: 8),
                      Text('暂无成本数据',
                          style:
                              TextStyle(color: theme.colorScheme.outline)),
                    ],
                  ),
                ),
              )
            else
              _buildChart(theme, items, total),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(ThemeData theme, List<CostProportionItem> items, double total) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildBar(theme, items),
        const SizedBox(height: 8),
        // 清单（不限制总高，页面可滚）
        _buildList(theme, items, total),
      ],
    );
  }

  /// 彩色进度条：段宽 = 占比，段间 1px surface 色细缝防割裂，整条圆角占满宽度。
  Widget _buildBar(ThemeData theme, List<CostProportionItem> items) {
    return ClipRRect(
      key: const Key('cost_bar'),
      borderRadius: BorderRadius.circular(5),
      child: SizedBox(
        height: 10,
        width: double.infinity,
        child: Row(
          // stretch：让段在交叉轴上撑满高 10，否则默认 center 下 flex 子项高 0 不可见不可点
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < items.length; i++) ...[
              if (i > 0) Container(width: 1, color: theme.colorScheme.surface),
              Expanded(
                // 段宽 = 占比（无上界，单段再大也按实际比例画）；下界 1：零成本段保留可点的细缝
                flex: max(1, (items[i].value * 1000).round()),
                child: GestureDetector(
                  onTap: () => setState(() => _touchedIndex = i),
                  child: ColoredBox(color: items[i].color),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 食材清单：色块 + 名称 + 金额 + 百分比（点击行高亮对应段，对齐 web 图例点击显示金额）。
  Widget _buildList(ThemeData theme, List<CostProportionItem> items, double total) {
    return Column(
      children: [
        for (var i = 0; i < items.length; i++)
          InkWell(
            onTap: () => setState(() => _touchedIndex = i),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              key: Key('cost_row_$i'),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              decoration: BoxDecoration(
                color: _touchedIndex == i
                    ? items[i].color.withValues(alpha: 0.2)
                    : null,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                      color: items[i].color,
                      borderRadius: BorderRadius.circular(3)),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(items[i].name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium),
                ),
                Text('¥${items[i].value.toStringAsFixed(2)}',
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w600)),
                const SizedBox(width: 12),
                SizedBox(
                  width: 48,
                  child: Text(_pct(items[i], total),
                      textAlign: TextAlign.right,
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: theme.colorScheme.outline)),
                ),
              ]),
            ),
          ),
      ],
    );
  }

  String _pct(CostProportionItem item, double total) {
    if (total <= 0) return '';
    final pct = item.value / total * 100;
    return '${pct.toStringAsFixed(pct >= 100 ? 0 : 1)}%';
  }
}
