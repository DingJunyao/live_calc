import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../repositories/price_repository.dart';
import '../../../shared/widgets/numeric_keypad.dart';

class QuickFillScreen extends ConsumerStatefulWidget {
  const QuickFillScreen({super.key});

  @override
  ConsumerState<QuickFillScreen> createState() => _QuickFillScreenState();
}

class _QuickFillScreenState extends ConsumerState<QuickFillScreen> {
  final _repo = PriceRepository();
  String? _selectedMerchantName;
  int? _selectedMerchantId;

  // Pricing rows
  final List<_PriceRow> _rows = [];
  bool _loading = false;

  // Merchant search / selection
  final _merchantSearchController = TextEditingController();
  List<Map<String, dynamic>> _merchants = [];
  List<Map<String, dynamic>> _filteredMerchants = [];

  @override
  void initState() {
    super.initState();
    _loadMerchants();
  }

  @override
  void dispose() {
    _merchantSearchController.dispose();
    for (final r in _rows) {
      r.nameController.dispose();
      r.priceController.dispose();
    }
    super.dispose();
  }

  Future<void> _loadMerchants() async {
    try {
      final resp = await _repo.client.dio.get('/merchants');
      final list = resp.data as List<dynamic>;
      setState(() {
        _merchants = list.cast<Map<String, dynamic>>();
        _filteredMerchants = _merchants;
      });
    } catch (_) {}
  }

  void _filterMerchants(String query) {
    setState(() {
      _filteredMerchants = _merchants.where((m) {
        final name = (m['name'] as String? ?? '').toLowerCase();
        return name.contains(query.toLowerCase());
      }).toList();
    });
  }

  void _selectMerchant(Map<String, dynamic> merchant) {
    setState(() {
      _selectedMerchantId = merchant['id'] as int?;
      _selectedMerchantName = merchant['name'] as String?;
      _merchantSearchController.text = _selectedMerchantName ?? '';
    });
    _loadHistoryProducts();
  }

  Future<void> _loadHistoryProducts() async {
    setState(() => _loading = true);
    try {
      final records = await _repo.getRecords(merchantId: _selectedMerchantId, pageSize: 20);
      final seen = <String>{};
      final products = <Map<String, dynamic>>[];
      for (final r in records) {
        final key = '${r.productId}_${r.productName}';
        if (seen.add(key)) {
          products.add({'id': r.productId, 'name': r.productName, 'unit': r.unit});
        }
      }
      setState(() {
        _rows.clear();
        for (final p in products) {
          _rows.add(_PriceRow(
            name: p['name'] as String,
            unit: p['unit'] as String? ?? '个',
            productId: p['id'] as int?,
          ));
        }
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  void _addRow({String? name, String? unit, int? productId}) {
    setState(() {
      _rows.add(_PriceRow(name: name ?? '', unit: unit ?? '个', productId: productId));
    });
  }

  Future<void> _saveAll() async {
    int saved = 0;
    for (final row in _rows) {
      final priceStr = row.priceController.text.trim();
      if (priceStr.isEmpty) continue;
      final price = double.tryParse(priceStr);
      if (price == null || price <= 0) continue;

      try {
        await _repo.client.dio.post('/products', data: {
          'name': row.nameController.text.trim(),
          'amount': price,
          'quantity': 1,
          'unit': row.unit,
          'merchant_id': _selectedMerchantId,
        });
        saved++;
      } catch (_) {}
    }

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已保存 $saved 条记录')),
      );
      context.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('快速填写')),
      body: Column(
        children: [
          // Step 1: Merchant selection
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('选择商家', style: theme.textTheme.titleSmall?.copyWith(color: theme.colorScheme.outline)),
                const SizedBox(height: 8),
                Autocomplete<Map<String, dynamic>>(
                  optionsBuilder: (textEditingValue) {
                    if (textEditingValue.text.isEmpty) return _merchants;
                    return _filteredMerchants;
                  },
                  displayStringForOption: (m) => m['name'] as String? ?? '',
                  onSelected: _selectMerchant,
                  fieldViewBuilder: (ctx, controller, focusNode, onSubmitted) {
                    WidgetsBinding.instance.addPostFrameCallback((_) {
                      if (_merchantSearchController.text != controller.text) {
                        controller.text = _merchantSearchController.text;
                      }
                    });
                    return TextField(
                      controller: controller,
                      focusNode: focusNode,
                      decoration: const InputDecoration(
                        hintText: '搜索或选择商家',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onChanged: _filterMerchants,
                      onSubmitted: (_) => onSubmitted(),
                    );
                  },
                ),
              ],
            ),
          ),

          if (_selectedMerchantId != null)
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _rows.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Text('暂无历史商品'),
                              const SizedBox(height: 8),
                              FilledButton.tonal(
                                onPressed: () => _addRow(name: '新商品'),
                                child: const Text('添加商品'),
                              ),
                            ],
                          ),
                        )
                      : Column(
                          children: [
                            // Price rows header
                            Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              child: Row(
                                children: [
                                  const Text('商品', style: TextStyle(fontWeight: FontWeight.bold)),
                                  const Spacer(),
                                  const Text('单价', style: TextStyle(fontWeight: FontWeight.bold)),
                                  const SizedBox(width: 80),
                                ],
                              ),
                            ),
                            const Divider(height: 1),
                            // Scrollable rows
                            Expanded(
                              child: ListView.builder(
                                itemCount: _rows.length + 1, // +1 for add button
                                itemBuilder: (ctx, i) {
                                  if (i == _rows.length) {
                                    return Padding(
                                      padding: const EdgeInsets.all(16),
                                      child: OutlinedButton.icon(
                                        onPressed: () => _addRow(),
                                        icon: const Icon(Icons.add),
                                        label: const Text('添加商品'),
                                      ),
                                    );
                                  }
                                  return _PriceRowWidget(
                                    row: _rows[i],
                                    onShowKeypad: () => _showKeypad(_rows[i]),
                                  );
                                },
                              ),
                            ),
                            // Submit button
                            SafeArea(
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: FilledButton(
                                  onPressed: _saveAll,
                                  child: const Text('保存所有价格'),
                                ),
                              ),
                            ),
                          ],
                        ),
            ),
        ],
      ),
    );
  }

  void _showKeypad(_PriceRow row) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => _PriceInputSheet(row: row),
    );
  }
}

class _PriceRow {
  final TextEditingController nameController;
  final TextEditingController priceController;
  String unit;
  int? productId;

  _PriceRow({String name = '', this.unit = '个', this.productId})
      : nameController = TextEditingController(text: name),
        priceController = TextEditingController();
}

class _PriceRowWidget extends StatelessWidget {
  final _PriceRow row;
  final VoidCallback onShowKeypad;

  const _PriceRowWidget({required this.row, required this.onShowKeypad});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: row.nameController,
                  decoration: const InputDecoration(
                    labelText: '商品名',
                    border: InputBorder.none,
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 100,
                child: GestureDetector(
                  onTap: onShowKeypad,
                  child: AbsorbPointer(
                    child: TextField(
                      controller: row.priceController,
                      decoration: const InputDecoration(
                        labelText: '价格',
                        border: InputBorder.none,
                        isDense: true,
                        prefixText: '¥',
                      ),
                      keyboardType: TextInputType.none, // block system keyboard
                    ),
                  ),
                ),
              ),
              PopupMenuButton<String>(
                onSelected: (u) => row.unit = u,
                itemBuilder: (_) => '个,斤,克,千克,升,毫升,包,瓶,袋,箱'.split(',').map((u) =>
                  PopupMenuItem(value: u, child: Text(u))
                ).toList(),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).colorScheme.outline),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(row.unit),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PriceInputSheet extends StatefulWidget {
  final _PriceRow row;
  const _PriceInputSheet({required this.row});

  @override
  State<_PriceInputSheet> createState() => _PriceInputSheetState();
}

class _PriceInputSheetState extends State<_PriceInputSheet> {
  late String _display;

  @override
  void initState() {
    super.initState();
    _display = widget.row.priceController.text;
  }

  void _onKeyTap(String key) {
    setState(() {
      if (key == '⌫') {
        if (_display.isNotEmpty) _display = _display.substring(0, _display.length - 1);
      } else if (key == 'C') {
        _display = '';
      } else if (key == '✓') {
        widget.row.priceController.text = _display;
        Navigator.of(context).pop();
      } else if (key == '.') {
        if (!_display.contains('.')) _display += '.';
      } else {
        if (_display == '0' && key != '.') _display = '';
        _display += key;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            alignment: Alignment.centerRight,
            child: Text(
              '¥$_display',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
          ),
          NumericKeypad(
            onKeyTap: _onKeyTap,
            onConfirm: () {
              widget.row.priceController.text = _display;
              Navigator.of(context).pop();
            },
          ),
        ],
      ),
    );
  }
}
