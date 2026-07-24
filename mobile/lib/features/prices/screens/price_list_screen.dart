import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/price_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';
import '../../../shared/widgets/empty_state.dart';

class PriceListScreen extends ConsumerStatefulWidget {
  const PriceListScreen({super.key});

  @override
  ConsumerState<PriceListScreen> createState() => _PriceListScreenState();
}

class _PriceListScreenState extends ConsumerState<PriceListScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(priceListProvider.notifier).loadRecords());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(priceListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('价格记录')),
      body: _buildBody(theme, state),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/prices/quick-fill'),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody(ThemeData theme, PriceListState state) {
    if (state.loading && state.records.isEmpty) {
      return const LoadingIndicator(message: '加载中...');
    }
    if (state.error != null && state.records.isEmpty) {
      return ErrorDisplay(
        message: state.error!,
        onRetry: () => ref.read(priceListProvider.notifier).loadRecords(),
      );
    }
    if (state.records.isEmpty) {
      return const EmptyState(
        icon: Icons.receipt_long,
        title: '暂无价格记录',
        subtitle: '点击右下角按钮记下第一笔价格',
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(priceListProvider.notifier).loadRecords(),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: state.records.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final r = state.records[i];
          return ListTile(
            title: Text(r.productName),
            subtitle: Text(r.merchantName ?? ''),
            trailing: Text(
              '¥${r.unitPrice.toStringAsFixed(2)}',
              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
          );
        },
      ),
    );
  }
}
