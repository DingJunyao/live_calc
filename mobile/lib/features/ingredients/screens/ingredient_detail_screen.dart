import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/ingredient_provider.dart';
import '../models/ingredient.dart';
import '../repositories/ingredient_repository.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

final ingredientDetailProvider = FutureProvider.family<Ingredient, int>((ref, id) async {
  return IngredientRepository().getIngredient(id);
});

class IngredientDetailScreen extends ConsumerWidget {
  final int id;
  const IngredientDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final async = ref.watch(ingredientDetailProvider(id));
    return async.when(
      loading: () => Scaffold(
        appBar: AppBar(),
        body: const LoadingIndicator(),
      ),
      error: (e, _) => Scaffold(
        appBar: AppBar(),
        body: ErrorDisplay(message: e.toString(), onRetry: () => ref.invalidate(ingredientDetailProvider(id))),
      ),
      data: (item) => Scaffold(
        appBar: AppBar(title: Text(item.name)),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (item.category != null) ...[
                Text('Category', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.outline)),
                Text(item.category!, style: theme.textTheme.bodyLarge),
                const SizedBox(height: 16),
              ],
              if (item.latestPrice != null) ...[
                Text('Latest Price', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.outline)),
                Text('\u00A5${item.latestPrice!.toStringAsFixed(2)}', style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

