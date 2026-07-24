import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class QuickEntryGrid extends StatelessWidget {
  const QuickEntryGrid({super.key});

  static const _entries = [
    _Entry('记价', Icons.receipt_long, '/prices', Color(0xFF1976D2)),
    _Entry('菜谱', Icons.restaurant, '/recipes', Color(0xFF388E3C)),
    _Entry('原料', Icons.science, '/ingredients', Color(0xFFE65100)),
    _Entry('商品', Icons.inventory_2, '/products', Color(0xFF6A1B9A)),
    _Entry('商家', Icons.store, '/merchants', Color(0xFF00838F)),
    _Entry('地图', Icons.map, '/merchants/map', Color(0xFFC62828)),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text('快捷入口', style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: Theme.of(context).colorScheme.outline,
          )),
        ),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              childAspectRatio: 1.1,
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
            ),
            itemCount: _entries.length,
            itemBuilder: (ctx, i) {
              final e = _entries[i];
              return Material(
                color: e.color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => context.go(e.route),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(e.icon, color: e.color, size: 28),
                      const SizedBox(height: 6),
                      Text(e.label, style: const TextStyle(fontSize: 12)),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _Entry {
  final String label;
  final IconData icon;
  final String route;
  final Color color;
  const _Entry(this.label, this.icon, this.route, this.color);
}
