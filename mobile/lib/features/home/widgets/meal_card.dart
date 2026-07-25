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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
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
        ),
      ),
    );
  }
}
