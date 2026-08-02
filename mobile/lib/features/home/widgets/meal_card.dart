import 'package:flutter/material.dart';
import '../models/meal_recommendation.dart';

class MealCard extends StatelessWidget {
  final MealRecommendation meal;
  final VoidCallback? onTap;

  const MealCard({super.key, required this.meal, this.onTap});

  IconData _mealIcon(String type) {
    switch (type) {
      case 'breakfast': return Icons.free_breakfast;
      case 'lunch': return Icons.lunch_dining;
      case 'dinner': return Icons.dinner_dining;
      default: return Icons.restaurant;
    }
  }

  String _mealLabel(String type) {
    switch (type) {
      case 'breakfast': return '早餐';
      case 'lunch': return '午餐';
      case 'dinner': return '晚餐';
      default: return type;
    }
  }

  Widget _nutrientChip(IconData icon, String text, ThemeData theme) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: theme.colorScheme.outline),
        const SizedBox(width: 4),
        Text(text, style: theme.textTheme.bodySmall?.copyWith(
          color: theme.colorScheme.outline,
        )),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasNutrition = meal.calories != null ||
        meal.proteinG != null ||
        meal.carbsG != null ||
        meal.fatG != null;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(_mealIcon(meal.mealType), size: 40, color: theme.colorScheme.primary),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_mealLabel(meal.mealType), style: theme.textTheme.labelMedium?.copyWith(
                          color: theme.colorScheme.outline,
                        )),
                        const SizedBox(height: 4),
                        Text(meal.recipeName ?? '未设置', style: theme.textTheme.titleMedium),
                      ],
                    ),
                  ),
                  if (meal.estimatedCost != null)
                    Text('¥${meal.estimatedCost!.toStringAsFixed(1)}', style: theme.textTheme.titleMedium?.copyWith(
                      color: theme.colorScheme.primary,
                    )),
                ],
              ),
              if (hasNutrition) ...[
                const SizedBox(height: 12),
                const Divider(height: 1),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 16,
                  runSpacing: 6,
                  children: [
                    if (meal.calories != null)
                      _nutrientChip(Icons.local_fire_department, '${meal.calories!.round()} kcal', theme),
                    if (meal.proteinG != null)
                      _nutrientChip(Icons.egg_outlined, '${meal.proteinG!.toStringAsFixed(1)}g 蛋白', theme),
                    if (meal.carbsG != null)
                      _nutrientChip(Icons.grain, '${meal.carbsG!.toStringAsFixed(1)}g 碳水', theme),
                    if (meal.fatG != null)
                      _nutrientChip(Icons.water_drop_outlined, '${meal.fatG!.toStringAsFixed(1)}g 脂肪', theme),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
