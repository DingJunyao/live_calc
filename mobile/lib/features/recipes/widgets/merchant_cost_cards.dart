import 'package:flutter/material.dart';
import '../repositories/recipe_repository.dart';

/// 按商家预估成本：横向滚动卡片（对齐 web MerchantCostCards）。
class MerchantCostCards extends StatelessWidget {
  final List<MerchantCostItem> merchants;
  final bool loading;
  const MerchantCostCards(
      {super.key, required this.merchants, this.loading = false});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Icon(Icons.store_outlined,
              color: theme.colorScheme.tertiary, size: 20),
          const SizedBox(width: 8),
          Text('按商家预估成本',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold)),
        ]),
        const SizedBox(height: 12),
        if (loading && merchants.isEmpty)
          const SizedBox(
            height: 140,
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          )
        else if (merchants.isEmpty)
          SizedBox(
            height: 140,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.store_outlined,
                      size: 40, color: theme.colorScheme.outline),
                  const SizedBox(height: 8),
                  Text('暂无商家价格数据',
                      style: TextStyle(color: theme.colorScheme.outline)),
                ],
              ),
            ),
          )
        else
          MediaQuery.withClampedTextScaling(
            maxScaleFactor: 1.3,
            child: SizedBox(
              height: 168,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: merchants.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, i) =>
                    _buildCard(context, theme, merchants[i]),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildCard(BuildContext context, ThemeData theme, MerchantCostItem m) {
    return Container(
      width: 220,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(
          color: m.isRecommended
              ? const Color(0xFFFF9800)
              : theme.colorScheme.outlineVariant,
          width: m.isRecommended ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(12),
        color: m.isRecommended
            ? (theme.brightness == Brightness.dark
                ? theme.colorScheme.surface
                : const Color(0xFFFFF8E1))
            : theme.colorScheme.surface,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
              child: Text(m.merchantName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodyLarge
                      ?.copyWith(fontWeight: FontWeight.w600)),
            ),
            if (m.isRecommended)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF9800),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text('最实惠 ✓',
                    style: TextStyle(
                        fontSize: 10,
                        color: Colors.white,
                        fontWeight: FontWeight.bold)),
              ),
          ]),
          const SizedBox(height: 4),
          Row(children: [
            Text('覆盖 ${m.coveredCount}/${m.totalIngredients} 种食材',
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.outline)),
            if (m.fallbackChains.isNotEmpty) ...[
              const SizedBox(width: 4),
              SizedBox(
                width: 20,
                height: 20,
                child: IconButton(
                  visualDensity: VisualDensity.compact,
                  constraints:
                      const BoxConstraints(minWidth: 20, minHeight: 20),
                  padding: EdgeInsets.zero,
                  iconSize: 14,
                  icon: Icon(Icons.info_outline,
                      color: theme.colorScheme.primary),
                  onPressed: () => _showFallbackDialog(context, m),
                ),
              ),
            ],
          ]),
          const SizedBox(height: 4),
          Text('¥${m.totalCost.toStringAsFixed(2)}',
              style: theme.textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 2),
          Text.rich(TextSpan(children: [
            TextSpan(
                text: '本店 ¥${m.coveredCost.toStringAsFixed(2)}',
                style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFF2E7D32),
                    fontWeight: FontWeight.w600)),
            if (m.externalCost > 0)
              TextSpan(
                text: '  外部 ¥${m.externalCost.toStringAsFixed(2)}',
                style: const TextStyle(fontSize: 12, color: Color(0xFFEF6C00)),
              ),
          ])),
          if (m.missingIngredients.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text('⚠ 需外购 ${m.missingIngredients.join('、')}',
                style: const TextStyle(fontSize: 11, color: Color(0xFFF9A825)),
                maxLines: 1,
                overflow: TextOverflow.ellipsis),
          ],
        ],
      ),
    );
  }

  void _showFallbackDialog(BuildContext context, MerchantCostItem m) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('根据以下食材计算价格：'),
        scrollable: true,
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final chain in m.fallbackChains)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(chain,
                    style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }
}
