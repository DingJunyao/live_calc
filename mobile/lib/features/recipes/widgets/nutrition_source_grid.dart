import 'dart:math';
import 'package:flutter/material.dart';
import '../repositories/recipe_repository.dart';
import '../utils/ingredient_colors.dart';

/// NRV 指标白名单（对齐 web NRV_KEYS）
const nrvKeys = <String>{
  'energy', 'protein', 'fat', 'carbohydrate', 'fiber',
  'calcium', 'iron', 'sodium', 'potassium',
  'vitamin_a_rae', 'vitamin_c', 'vitamin_b1', 'vitamin_b2',
  'vitamin_b12', 'vitamin_d', 'vitamin_e', 'vitamin_k',
};

/// NRV 中文名（对齐 web NRV_LABELS）
const nrvLabels = <String, String>{
  'energy': '能量', 'protein': '蛋白质', 'fat': '脂肪', 'carbohydrate': '碳水化合物',
  'fiber': '膳食纤维', 'calcium': '钙', 'iron': '铁', 'sodium': '钠', 'potassium': '钾',
  'vitamin_a_rae': '维生素A', 'vitamin_c': '维生素C', 'vitamin_b1': '维生素B1',
  'vitamin_b2': '维生素B2', 'vitamin_b12': '维生素B12', 'vitamin_d': '维生素D',
  'vitamin_e': '维生素E', 'vitamin_k': '维生素K',
};

/// 营养排序（对齐 web nutrientSortOrder 前 17 项）
const _nutrientSortOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '钠',
  '膳食纤维', '钙', '铁', '钾',
  '维生素A', '维生素B1', '维生素B2', '维生素B12', '维生素C',
  '维生素D', '维生素E', '维生素K',
];

int sortIndex(String label) {
  final i = _nutrientSortOrder.indexOf(label);
  return i == -1 ? _nutrientSortOrder.length + label.length : i;
}

/// 单个营养素展示数据
class NutrientDisplay {
  final String key;
  final String label;
  final String totalText;
  final int? nrpPct;
  final String topContributors;
  final List<NutrientContributor> items;
  const NutrientDisplay({
    required this.key,
    required this.label,
    required this.totalText,
    this.nrpPct,
    required this.topContributors,
    required this.items,
  });
}

class NutrientContributor {
  final String name;
  final double value;
  final String unit;
  final Color color;
  const NutrientContributor({
    required this.name,
    required this.value,
    this.unit = '',
    required this.color,
  });
}

/// 构建营养溯源展示数据（对齐 web displayNutrients 逻辑：NRV 过滤、同名去重、Top2 贡献）
List<NutrientDisplay> buildNutrientDisplays(RecipeNutrition nutrition,
    {required bool showAll}) {
  final perServing = nutrition.perServingNutrients;
  if (perServing.isEmpty) return const [];
  final all = {...nutrition.allNutrients, ...perServing};

  // NRV 百分比映射（core 条目带 nrp_pct）
  final nrpPctMap = <String, double>{};
  for (final entry in perServing.entries) {
    final item = entry.value;
    if (item.key != null && item.nrpPct > 0) {
      nrpPctMap[item.key!] = item.nrpPct;
    }
  }

  final result = <NutrientDisplay>[];
  final usedLabels = <String>{};
  for (final entry in all.entries) {
    final key = entry.key;
    final item = entry.value;
    if (item.value <= 0) continue;
    final isNrv = nrvKeys.contains(key);
    if (!showAll && !isNrv) continue;

    // 中文名：perServing 的 key 已是中文；英文键映射
    final label = nrvLabels[key] ?? item.nameZh ?? key;
    if (showAll && usedLabels.contains(label)) continue;
    usedLabels.add(label);

    final contributors = <NutrientContributor>[];
    for (final d in nutrition.ingredientDetails) {
      final c = d.nutritionContribution[label] ??
          d.nutritionContribution[key];
      if (c != null && c.value > 0) {
        contributors.add(NutrientContributor(
          name: d.ingredientName.isEmpty ? '未知食材' : d.ingredientName,
          value: c.value,
          unit: c.unit,
          color: getIngredientColor(d.ingredientId),
        ));
      }
    }
    if (contributors.isEmpty) continue;
    contributors.sort((a, b) => b.value.compareTo(a.value));

    final total = contributors.fold<double>(0, (s, c) => s + c.value);
    final top2 = contributors.take(2).map((c) =>
        '${c.name} ${total > 0 ? (c.value / total * 100).round() : 0}%').join(' · ');

    result.add(NutrientDisplay(
      key: key,
      label: label,
      totalText: '${_fmt(item.value)}${item.unit}',
      // 兜底分支受合并顺序影响当前不可达（perServing 条目必先命中
      // item.nrpPct 分支），保留与 web 对齐
      nrpPct: item.nrpPct > 0
          ? item.nrpPct.round()
          : (nrpPctMap[key] ?? 0) > 0
              ? nrpPctMap[key]!.round()
              : null,
      topContributors: top2,
      items: contributors,
    ));
  }
  result.sort((a, b) => sortIndex(a.label).compareTo(sortIndex(b.label)));
  return result;
}

String _fmt(double v) => v == v.roundToDouble()
    ? v.toStringAsFixed(0)
    : v.toStringAsFixed(2);

/// 食材贡献总和（items 恒非空：buildNutrientDisplays 过滤了空贡献）
double _contribTotal(List<NutrientContributor> items) =>
    items.fold<double>(0, (s, c) => s + c.value);

/// 营养贡献溯源：单列卡片列表（标题行 箭头+名称+NRV%+总量 + 多色段进度条 + 可展开食材明细），
/// NRV 指标/全部折叠按钮切换（对齐 web NutritionSourceGrid）。
class NutritionSourceGrid extends StatefulWidget {
  final RecipeNutrition? nutrition;
  final bool loading;
  const NutritionSourceGrid({super.key, this.nutrition, this.loading = false});

  @override
  State<NutritionSourceGrid> createState() => _NutritionSourceGridState();
}

class _NutritionSourceGridState extends State<NutritionSourceGrid> {
  bool _showAll = false;
  // 已展开明细的营养素 key 集合
  final Set<String> _expanded = {};

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.food_bank_outlined,
                  color: theme.colorScheme.tertiary, size: 20),
              const SizedBox(width: 8),
              Text('营养贡献溯源',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const Spacer(),
              // 折叠按钮（下拉菜单式）：小屏下 2 段按钮拥挤，改为显示当前选择的菜单
              PopupMenuButton<bool>(
                key: const Key('show_all_menu'),
                initialValue: _showAll,
                tooltip: '显示范围',
                onSelected: (v) => setState(() => _showAll = v),
                itemBuilder: (context) => const [
                  PopupMenuItem(value: false, child: Text('NRV 指标')),
                  PopupMenuItem(value: true, child: Text('全部')),
                ],
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(_showAll ? '全部' : 'NRV 指标',
                      style: theme.textTheme.bodyMedium),
                  Icon(Icons.arrow_drop_down,
                      size: 20, color: theme.colorScheme.outline),
                ]),
              ),
            ]),
            const SizedBox(height: 12),
            if (widget.loading)
              const SizedBox(
                  height: 120,
                  child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2)))
            else if (widget.nutrition == null)
              SizedBox(
                height: 120,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.food_bank_outlined,
                          size: 40, color: theme.colorScheme.outline),
                      const SizedBox(height: 8),
                      Text('暂无营养数据',
                          style: TextStyle(color: theme.colorScheme.outline)),
                    ],
                  ),
                ),
              )
            else
              _buildList(theme),
          ],
        ),
      ),
    );
  }

  /// 单列全宽列表：每营养素一张卡片（保留空态分支）。
  Widget _buildList(ThemeData theme) {
    final displays =
        buildNutrientDisplays(widget.nutrition!, showAll: _showAll);
    if (displays.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
            child: Text('暂无营养数据',
                style: TextStyle(color: theme.colorScheme.outline))),
      );
    }
    return Column(
      children: [for (final d in displays) _buildItem(theme, d)],
    );
  }

  /// 单列卡片：标题行（箭头+名称+NRV%+总量）+ 多色段进度条 +（展开）食材明细。
  Widget _buildItem(ThemeData theme, NutrientDisplay d) {
    final expanded = _expanded.contains(d.key);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest
            .withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(8),
      ),
      child: InkWell(
        onTap: () => setState(() {
          if (expanded) {
            _expanded.remove(d.key);
          } else {
            _expanded.add(d.key);
          }
        }),
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(expanded ? Icons.expand_less : Icons.expand_more,
                    size: 18, color: theme.colorScheme.outline),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(d.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge
                          ?.copyWith(fontWeight: FontWeight.w600)),
                ),
                if (d.nrpPct != null) ...[
                  Text('NRV ${d.nrpPct}%',
                      style: theme.textTheme.labelSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(width: 8),
                ],
                Text(d.totalText,
                    style: theme.textTheme.labelMedium
                        ?.copyWith(fontWeight: FontWeight.w600)),
              ]),
              const SizedBox(height: 8),
              _buildBar(theme, d),
              if (expanded) ...[
                const SizedBox(height: 8),
                _buildDetailList(theme, d),
              ],
            ],
          ),
        ),
      ),
    );
  }

  /// 多色段进度条：段宽 = 食材贡献占比（对齐成本占比样式），
  /// 段间 1px surface 色细缝，stretch 撑满高度。
  Widget _buildBar(ThemeData theme, NutrientDisplay d) {
    final total = _contribTotal(d.items);
    return ClipRRect(
      key: const Key('nrv_bar'),
      borderRadius: BorderRadius.circular(5),
      child: SizedBox(
        height: 10,
        width: double.infinity,
        child: Row(
          // stretch：段在交叉轴上撑满高 10（否则 flex 子项 0 高不可见）
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < d.items.length; i++) ...[
              if (i > 0) Container(width: 1, color: theme.colorScheme.surface),
              Expanded(
                // 段宽 = 占比（无上界）；下界 1：零值段保留细缝
                flex: max(1, (d.items[i].value / total * 1000).round()),
                child: ColoredBox(color: d.items[i].color),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 食材贡献明细：色块 + 名称 + 贡献值（含单位）+ 占比（对齐成本占比清单行）。
  Widget _buildDetailList(ThemeData theme, NutrientDisplay d) {
    final total = _contribTotal(d.items);
    return Column(
      children: [
        for (final c in d.items)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                    color: c.color, borderRadius: BorderRadius.circular(3)),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(c.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodyMedium),
              ),
              Text('${_fmt(c.value)}${c.unit}',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(width: 12),
              SizedBox(
                width: 48,
                child: Text(_pct(c.value, total),
                    textAlign: TextAlign.right,
                    style: theme.textTheme.bodySmall
                        ?.copyWith(color: theme.colorScheme.outline)),
              ),
            ]),
          ),
      ],
    );
  }

  String _pct(double value, double total) {
    if (total <= 0) return '';
    final pct = value / total * 100;
    return '${pct.toStringAsFixed(pct >= 100 ? 0 : 1)}%';
  }
}
