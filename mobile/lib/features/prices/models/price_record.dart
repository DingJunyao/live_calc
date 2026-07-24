// price_record.dart - 价格记录数据模型

class PriceRecord {
  final int id;
  final int productId;
  final String productName;
  final double amount;
  final double quantity;
  final String unit;
  final int? merchantId;
  final String? merchantName;
  final String recordedAt;
  final String recordType; // 'price' or 'purchase'

  const PriceRecord({
    required this.id,
    required this.productId,
    required this.productName,
    required this.amount,
    required this.quantity,
    required this.unit,
    this.merchantId,
    this.merchantName,
    required this.recordedAt,
    this.recordType = 'price',
  });

  factory PriceRecord.fromJson(Map<String, dynamic> json) {
    return PriceRecord(
      id: json['id'] as int,
      productId: json['product_id'] as int? ?? 0,
      productName: json['product_name'] as String? ?? json['name'] as String? ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? 0,
      quantity: (json['quantity'] as num?)?.toDouble() ?? 1,
      unit: json['unit'] as String? ?? '个',
      merchantId: json['merchant_id'] as int?,
      merchantName: json['merchant_name'] as String? ?? json['merchant'] as String?,
      recordedAt: json['recorded_at'] as String? ?? DateTime.now().toIso8601String(),
      recordType: json['record_type'] as String? ?? 'price',
    );
  }

  double get unitPrice => quantity > 0 ? amount / quantity : amount;
}
