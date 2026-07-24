import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/merchant_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';
import '../../../shared/widgets/empty_state.dart';

class MerchantListScreen extends ConsumerStatefulWidget {
  const MerchantListScreen({super.key});

  @override
  ConsumerState<MerchantListScreen> createState() => _MerchantListScreenState();
}

class _MerchantListScreenState extends ConsumerState<MerchantListScreen> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(merchantListProvider.notifier).load());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(merchantListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Merchants')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              decoration: const InputDecoration(hintText: 'Search...', prefixIcon: Icon(Icons.search)),
              onSubmitted: (v) => ref.read(merchantListProvider.notifier).load(search: v),
            ),
          ),
          Expanded(child: _buildContent(theme, state)),
        ],
      ),
    );
  }

  Widget _buildContent(ThemeData theme, MerchantListState state) {
    if (state.loading && state.items.isEmpty) return const LoadingIndicator(message: 'Loading...');
    if (state.error != null && state.items.isEmpty) {
      return ErrorDisplay(message: state.error!, onRetry: () => ref.read(merchantListProvider.notifier).load());
    }
    if (state.items.isEmpty) {
      return const EmptyState(icon: Icons.store, title: 'No Merchants', subtitle: 'Add merchants from the web app');
    }
    return RefreshIndicator(
      onRefresh: () => ref.read(merchantListProvider.notifier).load(),
      child: ListView.separated(
        padding: const EdgeInsets.all(12),
        itemCount: state.items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final item = state.items[i];
          return ListTile(
            title: Text(item.name),
            subtitle: (item.address != null || item.productCount != null)
                ? Text([if (item.address != null) item.address!, if (item.productCount != null) '${item.productCount} products']
                    .join(' - '))
                : null,
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/merchants/${item.id}'),
          );
        },
      ),
    );
  }
}
