import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/product_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';
import '../../../shared/widgets/empty_state.dart';

class ProductListScreen extends ConsumerStatefulWidget {
  const ProductListScreen({super.key});

  @override
  ConsumerState<ProductListScreen> createState() => _ProductListScreenState();
}

class _ProductListScreenState extends ConsumerState<ProductListScreen> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(productListProvider.notifier).load());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(productListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Product')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              decoration: const InputDecoration(hintText: 'Search', prefixIcon: Icon(Icons.search)),
              onSubmitted: (v) => ref.read(productListProvider.notifier).load(search: v),
            ),
          ),
          Expanded(child: _buildContent(theme, state)),
        ],
      ),
    );
  }

  Widget _buildContent(ThemeData theme, ProductListState state) {
    if (state.loading && state.items.isEmpty) return const LoadingIndicator(message: 'Loading...');
    if (state.error != null && state.items.isEmpty) {
      return ErrorDisplay(message: state.error!, onRetry: () => ref.read(productListProvider.notifier).load());
    }
    if (state.items.isEmpty) {
      return const EmptyState(icon: Icons.inventory_2, title: 'No Products', subtitle: 'Create products from the web app');
    }
    return RefreshIndicator(
      onRefresh: () => ref.read(productListProvider.notifier).load(),
      child: ListView.separated(
        padding: const EdgeInsets.all(12),
        itemCount: state.items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final item = state.items[i];
          return ListTile(
            title: Text(item.name),
            subtitle: item.ingredientName != null ? Text(item.ingredientName!) : null,
            trailing: item.latestPrice != null ? Text('\u00A5${item.latestPrice!.toStringAsFixed(2)}') : null,
            onTap: () => context.push('/products/${item.id}'),
          );
        },
      ),
    );
  }
}

