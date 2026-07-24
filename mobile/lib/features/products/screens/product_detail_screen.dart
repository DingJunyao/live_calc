import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/product_provider.dart';
import '../models/product.dart';
import '../repositories/product_repository.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

final productDetailProvider = FutureProvider.family<Product, int>((ref, id) async {
  return ProductRepository().getProduct(id);
});

class ProductDetailScreen extends ConsumerWidget {
  final int id;
  const ProductDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final async = ref.watch(productDetailProvider(id));
    return async.when(
      loading: () => Scaffold(
        appBar: AppBar(),
        body: const LoadingIndicator(),
      ),
      error: (e, _) => Scaffold(
        appBar: AppBar(),
        body: ErrorDisplay(message: e.toString(), onRetry: () => ref.invalidate(productDetailProvider(id))),
      ),
      data: (item) => Scaffold(
        appBar: AppBar(title: Text(item.name)),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (item.ingredientName != null) ...[
                Text('Ingredient', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.outline)),
                Text(item.ingredientName!, style: theme.textTheme.bodyLarge),
                const SizedBox(height: 16),
              ],
              if (item.barcode != null) ...[
                Text('Barcode', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.outline)),
                Text(item.barcode!, style: theme.textTheme.bodyLarge),
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

