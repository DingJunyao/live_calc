import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../models/price_record.dart';
import '../providers/price_provider.dart';
import '../../merchants/models/merchant.dart';
import '../../merchants/providers/merchant_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';
import '../../../shared/widgets/empty_state.dart';

class PriceListScreen extends ConsumerStatefulWidget {
  const PriceListScreen({super.key});

  @override
  ConsumerState<PriceListScreen> createState() => _PriceListScreenState();
}

class _PriceListScreenState extends ConsumerState<PriceListScreen> {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();
  bool _merchantsLoaded = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(priceListProvider.notifier).loadRecords();
      if (!_merchantsLoaded) {
        ref.read(merchantListProvider.notifier).load();
        _merchantsLoaded = true;
      }
    });
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      final notifier = ref.read(priceListProvider.notifier);
      if (notifier.canLoadMore) {
        notifier.loadRecords(loadMore: true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(priceListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('价格记录'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: state.loading
                ? null
                : () => ref.read(priceListProvider.notifier).loadRecords(),
            tooltip: '刷新',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildSearchBar(theme, state),
          Expanded(child: _buildBody(theme, state)),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/prices/quick-fill'),
        child: const Icon(Icons.add),
      ),
    );
  }

  // ---- Search + filter button ----

  Widget _buildSearchBar(ThemeData theme, PriceListState state) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '搜索商品…',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          ref.read(priceListProvider.notifier).setSearch('');
                        },
                      )
                    : null,
                isDense: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onChanged: (v) {
                ref.read(priceListProvider.notifier).setSearch(v);
                setState(() {});
              },
            ),
          ),
          const SizedBox(width: 8),
          _buildFilterButton(theme, state),
        ],
      ),
    );
  }

  Widget _buildFilterButton(ThemeData theme, PriceListState state) {
    final activeCount = ref.read(priceListProvider.notifier).activeFilterCount;
    final hasActive = activeCount > 0;
    return SizedBox(
      height: 48,
      child: Badge(
        isLabelVisible: hasActive,
        label: Text('$activeCount'),
        child: IconButton.filledTonal(
          icon: const Icon(Icons.tune),
          onPressed: () => _showFilterDialog(theme, state),
          tooltip: '筛选',
          style: hasActive
              ? IconButton.styleFrom(
                  backgroundColor: theme.colorScheme.primary,
                  foregroundColor: theme.colorScheme.onPrimary,
                )
              : null,
        ),
      ),
    );
  }

  void _showFilterDialog(ThemeData theme, PriceListState state) {
    final merchantState = ref.read(merchantListProvider);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => _FilterSheet(
        theme: theme,
        state: state,
       merchants: merchantState.items,
        onApply: ({
          required int? merchantId,
          required String? recordType,
          required String? startDate,
          required String? endDate,
        }) =>
            ref.read(priceListProvider.notifier).applyFilters(
                  merchantId: merchantId,
                  recordType: recordType,
                  startDate: startDate,
                  endDate: endDate,
                ),
      ),
    );
  }

  // ---- List body ----

  Widget _buildBody(ThemeData theme, PriceListState state) {
    if (state.loading && state.records.isEmpty) {
      return const LoadingIndicator(message: '加载中…');
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
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        itemCount: state.records.length + (state.hasMore ? 1 : 0),
        itemBuilder: (ctx, i) {
          if (i >= state.records.length) {
            return _buildLoadMoreIndicator(state);
          }
          return _buildRecordCard(theme, state.records[i]);
        },
      ),
    );
  }

  Widget _buildLoadMoreIndicator(PriceListState state) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Center(
        child: state.loadingMore
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : TextButton(
                onPressed: () => ref
                    .read(priceListProvider.notifier)
                    .loadRecords(loadMore: true),
                child: const Text('加载更多'),
              ),
      ),
    );
  }

  Widget _buildRecordCard(ThemeData theme, PriceRecord r) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: r.productId > 0
            ? () => context.push('/products/${r.productId}')
            : null,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: theme.colorScheme.primaryContainer,
                foregroundColor: theme.colorScheme.onPrimaryContainer,
                radius: 20,
                child: Text(
                  r.productName.isNotEmpty
                      ? r.productName.characters.first
                      : '?',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      r.productName,
                      style: theme.textTheme.titleSmall
                          ?.copyWith(fontWeight: FontWeight.w600),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '¥${r.price.toStringAsFixed(2)}'
                      ' / ${_fmtQty(r.quantity)}${r.unit}',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.primary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(
                          Icons.store_outlined,
                          size: 13,
                          color: theme.colorScheme.outline,
                        ),
                        const SizedBox(width: 3),
                        Flexible(
                          child: Text(
                            r.merchantName ?? '未知商家',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.outline,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Icon(
                          Icons.schedule,
                          size: 13,
                          color: theme.colorScheme.outline,
                        ),
                        const SizedBox(width: 3),
                        Flexible(
                          child: Text(
                            _formatTime(r.recordedAt),
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.outline,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.grey),
            ],
          ),
        ),
      ),
    );
  }

  /// 整数不带小数，否则最多两位并去掉尾随 0。
  String _fmtQty(double q) {
    if (q == q.truncateToDouble()) return q.toInt().toString();
    var s = q.toStringAsFixed(2);
    s = s.replaceFirst(RegExp(r'0+$'), '');
    s = s.replaceFirst(RegExp(r'\.$'), '');
    return s;
  }

  /// ISO 时间字符串 → "MM/dd HH:mm"。
  String _formatTime(String iso) {
    final dt = DateTime.tryParse(iso);
    if (dt == null) return iso;
    final local = dt.toLocal();
    return DateFormat('MM/dd HH:mm').format(local);
  }
}

// ---- Filter bottom sheet ----

class _FilterSheet extends StatefulWidget {
  final ThemeData theme;
  final PriceListState state;
  final List<Merchant> merchants;
  final void Function({
    required int? merchantId,
    required String? recordType,
    required String? startDate,
    required String? endDate,
  }) onApply;

  const _FilterSheet({
    required this.theme,
    required this.state,
    required this.merchants,
    required this.onApply,
  });

  @override
  State<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<_FilterSheet> {
  late int? _merchantId;
  late String? _recordType;
  late String? _startDate;
  late String? _endDate;

  @override
  void initState() {
    super.initState();
    _merchantId = widget.state.filterMerchantId;
    _recordType = widget.state.filterRecordType;
    _startDate = widget.state.filterStartDate;
    _endDate = widget.state.filterEndDate;
  }

  bool get _hasActive =>
      _merchantId != null ||
      _recordType != null ||
      _startDate != null ||
      _endDate != null;

  void _apply() {
    widget.onApply(
      merchantId: _merchantId,
      recordType: _recordType,
      startDate: _startDate,
      endDate: _endDate,
    );
  }

  Future<void> _pickDate(bool isStart) async {
    final initial = DateTime.tryParse(
            isStart ? (_startDate ?? '') : (_endDate ?? '')) ??
        DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked != null) {
      setState(() {
        final s = DateFormat('yyyy-MM-dd').format(picked);
        if (isStart) {
          _startDate = s;
        } else {
          _endDate = s;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = widget.theme;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 8, 8),
              child: Row(
                children: [
                  Text('筛选条件',
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const Spacer(),
                  if (_hasActive)
                    TextButton.icon(
                      onPressed: () {
                        setState(() {
                          _merchantId = null;
                          _recordType = null;
                          _startDate = null;
                          _endDate = null;
                        });
                      },
                      icon: const Icon(Icons.clear_all, size: 18),
                      label: const Text('清除'),
                    ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Merchant dropdown
                  Text('商家', style: theme.textTheme.labelLarge),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      border:
                          Border.all(color: theme.colorScheme.outlineVariant),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<int?>(
                        value: _merchantId,
                        isExpanded: true,
                        hint: const Text('全部商家'),
                        items: [
                          const DropdownMenuItem<int?>(
                            value: null,
                            child: Text('全部商家'),
                          ),
                          ...widget.merchants.map(
                            (m) => DropdownMenuItem<int?>(
                              value: m.id,
                              child: Text(
                                m.name,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ),
                        ],
                        onChanged: (v) =>
                            setState(() => _merchantId = v),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                  // Record type chips
                  Text('记录类型', style: theme.textTheme.labelLarge),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      FilterChip(
                        label: const Text('购买'),
                        selected: _recordType == 'purchase',
                        onSelected: (_) => setState(() =>
                            _recordType = _recordType == 'purchase'
                                ? null
                                : 'purchase'),
                      ),
                      FilterChip(
                        label: const Text('比价'),
                        selected: _recordType == 'price',
                        onSelected: (_) => setState(() =>
                            _recordType = _recordType == 'price'
                                ? null
                                : 'price'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  // Date range
                  Text('日期范围', style: theme.textTheme.labelLarge),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _buildDateField(
                          theme,
                          label: '开始',
                          value: _startDate,
                          onTap: () => _pickDate(true),
                          onClear: () =>
                              setState(() => _startDate = null),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        child: Text('~',
                            style: theme.textTheme.bodyMedium),
                      ),
                      Expanded(
                        child: _buildDateField(
                          theme,
                          label: '结束',
                          value: _endDate,
                          onTap: () => _pickDate(false),
                          onClear: () =>
                              setState(() => _endDate = null),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            // Footer
            Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () {
                    _apply();
                    Navigator.of(context).pop();
                  },
                  child: const Text('确定'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDateField(
    ThemeData theme, {
    required String label,
    required String? value,
    required VoidCallback onTap,
    required VoidCallback onClear,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: const Icon(Icons.calendar_today, size: 18),
          suffixIcon: value != null
              ? IconButton(
                  icon: const Icon(Icons.clear, size: 18),
                  onPressed: onClear,
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          isDense: true,
        ),
        child: Text(value ?? ''),
      ),
    );
  }
}
