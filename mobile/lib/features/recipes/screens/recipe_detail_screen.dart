import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/recipe_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

class RecipeDetailScreen extends ConsumerWidget {
  final int id;
  const RecipeDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final asyncDetail = ref.watch(recipeDetailProvider(id));

    return asyncDetail.when(
      loading: () => Scaffold(
        appBar: AppBar(title: const Text('Recipe Detail')),
        body: const LoadingIndicator(message: 'Loading...'),
      ),
      error: (e, _) => Scaffold(
        appBar: AppBar(title: const Text('Recipe Detail')),
        body: ErrorDisplay(message: e.toString(), onRetry: () => ref.invalidate(recipeDetailProvider(id))),
      ),
      data: (detail) {
        return Scaffold(
          appBar: AppBar(title: Text(detail.name)),
          body: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (detail.imageUrl != null)
                  SizedBox(width: double.infinity, height: 200,
                    child: Image.network(detail.imageUrl!, fit: BoxFit.cover)),
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(detail.name, style: theme.textTheme.headlineSmall),
                      const SizedBox(height: 8),
                      if (detail.description != null)
                        Text(detail.description!, style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.outline)),
                      const SizedBox(height: 12),
                      if (detail.totalCost != null)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.primaryContainer,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text('\u00A5${detail.totalCost!.toStringAsFixed(2)}',
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: theme.colorScheme.onPrimaryContainer, fontWeight: FontWeight.bold)),
                        ),
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        onPressed: () => context.push('/recipes/$id/analysis'),
                        icon: const Icon(Icons.analytics_outlined),
                        label: const Text('Cost Analysis'),
                      ),
                      const SizedBox(height: 24),
                      Text('Ingredients', style: theme.textTheme.titleMedium),
                      const SizedBox(height: 12),
                      if (detail.ingredients.isEmpty)
                        Text('No ingredients', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.outline))
                      else
                        ...detail.ingredients.map((ing) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(children: [
                            Icon(Icons.circle, size: 8, color: theme.colorScheme.primary),
                            const SizedBox(width: 12),
                            Expanded(child: Text(ing.name)),
                            Text('${ing.quantity} ${ing.unit}', style: theme.textTheme.bodyMedium),
                            if (ing.estimatedCost != null) ...[
                              const SizedBox(width: 12),
                              Text('\u00A5${ing.estimatedCost!.toStringAsFixed(1)}',
                                style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.primary)),
                            ],
                          ]),
                        )),
                      const SizedBox(height: 24),
                      if (detail.steps.isNotEmpty) ...[
                        Text('Steps', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 12),
                        ...detail.steps.map((step) => Padding(
                          padding: const EdgeInsets.only(bottom: 16),
                          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Container(width: 28, height: 28,
                              decoration: BoxDecoration(color: theme.colorScheme.primary, shape: BoxShape.circle),
                              child: Center(child: Text('${step.stepNumber}',
                                style: TextStyle(color: theme.colorScheme.onPrimary, fontWeight: FontWeight.bold)))),
                            const SizedBox(width: 12),
                            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text(step.content, style: theme.textTheme.bodyLarge),
                              if (step.imageUrl != null) ...[
                                const SizedBox(height: 8),
                                ClipRRect(borderRadius: BorderRadius.circular(8),
                                  child: Image.network(step.imageUrl!, height: 150, fit: BoxFit.cover)),
                              ],
                            ])),
                          ]),
                        )),
                      ],
                      if (detail.tips != null) ...[
                        const SizedBox(height: 16),
                        Container(padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.tertiaryContainer.withOpacity(0.3),
                            borderRadius: BorderRadius.circular(8)),
                          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Icon(Icons.lightbulb_outline, color: theme.colorScheme.tertiary),
                            const SizedBox(width: 8),
                            Expanded(child: Text(detail.tips!)),
                          ]),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
