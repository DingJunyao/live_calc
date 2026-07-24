import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/merchant.dart';
import '../repositories/merchant_repository.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

final merchantDetailProvider = FutureProvider.family<Merchant, int>((ref, id) async {
  return MerchantRepository().getMerchant(id);
});

class MerchantDetailScreen extends ConsumerWidget {
  final int id;
  const MerchantDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final async = ref.watch(merchantDetailProvider(id));
    return async.when(
      loading: () => Scaffold(
        appBar: AppBar(),
        body: const LoadingIndicator(),
      ),
      error: (e, _) => Scaffold(
        appBar: AppBar(),
        body: ErrorDisplay(message: e.toString(), onRetry: () => ref.invalidate(merchantDetailProvider(id))),
      ),
      data: (item) => Scaffold(
        appBar: AppBar(title: Text(item.name)),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (item.address != null) ...[
                Text('Address', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.outline)),
                const SizedBox(height: 4),
                Text(item.address!, style: theme.textTheme.bodyLarge),
                const SizedBox(height: 16),
              ],
              if (item.phone != null) ...[
                Text('Phone', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.outline)),
                const SizedBox(height: 4),
                Text(item.phone!, style: theme.textTheme.bodyLarge),
                const SizedBox(height: 16),
              ],
              if (item.productCount != null) ...[
                Text('Products', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.outline)),
                const SizedBox(height: 4),
                Text('${item.productCount} products', style: theme.textTheme.bodyLarge),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
