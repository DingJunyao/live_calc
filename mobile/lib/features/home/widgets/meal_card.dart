import 'package:flutter/material.dart';
import '../models/meal_recommendation.dart';

class MealCard extends StatelessWidget {
  final MealRecommendation meal;
  final VoidCallback? onTap;
  final bool isRefreshing;
  final VoidCallback? onRefresh;

  const MealCard({
    super.key,
    required this.meal,
    this.onTap,
    this.isRefreshing = false,
    this.onRefresh,
  });

  IconData _mealIcon(String type) {
    switch (type) {
      case 'breakfast':
        return Icons.free_breakfast;
      case 'lunch':
        return Icons.lunch_dining;
      case 'dinner':
        return Icons.dinner_dining;
      default:
        return Icons.restaurant;
    }
  }

  String _mealLabel(String type) {
    switch (type) {
      case 'breakfast':
        return '早餐';
      case 'lunch':
        return '午餐';
      case 'dinner':
        return '晚餐';
      default:
        return type;
    }
  }

  Widget _nutrientChip(IconData icon, String text, ThemeData theme) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: theme.colorScheme.outline),
        const SizedBox(width: 4),
        Text(
          text,
          style: theme.textTheme.bodySmall
              ?.copyWith(color: theme.colorScheme.outline),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasImage = meal.imageUrl != null && meal.imageUrl!.isNotEmpty;
    final hasNutrition = meal.calories != null ||
        meal.proteinG != null ||
        meal.carbsG != null ||
        meal.fatG != null;
    final hasBody = hasNutrition || meal.estimatedCost != null;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (hasImage) _buildImageHeader(theme) else _buildTitleHeader(theme),
            if (hasBody)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
                child: Wrap(
                  spacing: 16,
                  runSpacing: 6,
                  children: [
                    if (meal.estimatedCost != null)
                      _nutrientChip(
                        Icons.payments_outlined,
                        '¥${meal.estimatedCost!.toStringAsFixed(1)}',
                        theme,
                      ),
                    if (meal.calories != null)
                      _nutrientChip(
                        Icons.local_fire_department,
                        '${meal.calories!.round()} kcal',
                        theme,
                      ),
                    if (meal.proteinG != null)
                      _nutrientChip(
                        Icons.egg_outlined,
                        '${meal.proteinG!.toStringAsFixed(1)}g 蛋白',
                        theme,
                      ),
                    if (meal.carbsG != null)
                      _nutrientChip(
                        Icons.grain,
                        '${meal.carbsG!.toStringAsFixed(1)}g 碳水',
                        theme,
                      ),
                    if (meal.fatG != null)
                      _nutrientChip(
                        Icons.water_drop_outlined,
                        '${meal.fatG!.toStringAsFixed(1)}g 脂肪',
                        theme,
                      ),
                  ],
                ),
              ),
            if (onRefresh != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 0, 4, 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton.icon(
                      onPressed: isRefreshing ? null : onRefresh,
                      icon: isRefreshing
                          ? SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  theme.colorScheme.primary,
                                ),
                              ),
                            )
                          : const Icon(Icons.refresh, size: 18),
                      label: const Text('换一个'),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildImageHeader(ThemeData theme) {
    return SizedBox(
      height: 140,
      width: double.infinity,
      child: Stack(
        fit: StackFit.expand,
        children: [
          Image.network(
            meal.imageUrl!,
            fit: BoxFit.cover,
            loadingBuilder: (context, child, progress) {
              if (progress == null) return child;
              return Container(
                color: theme.colorScheme.surfaceContainerHighest,
                child: const Center(
                  child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              );
            },
            errorBuilder: (_, __, ___) => Container(
              color: theme.colorScheme.surfaceContainerHighest,
              child: Center(
                child: Icon(
                  _mealIcon(meal.mealType),
                  size: 48,
                  color: theme.colorScheme.outline,
                ),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding: const EdgeInsets.fromLTRB(16, 28, 16, 12),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [Colors.black54, Colors.transparent],
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _mealLabel(meal.mealType),
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    meal.recipeName ?? '未设置',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTitleHeader(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Row(
        children: [
          Icon(
            _mealIcon(meal.mealType),
            size: 32,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _mealLabel(meal.mealType),
                  style: theme.textTheme.labelMedium
                      ?.copyWith(color: theme.colorScheme.outline),
                ),
                const SizedBox(height: 2),
                Text(
                  meal.recipeName ?? '未设置',
                  style: theme.textTheme.titleMedium,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
