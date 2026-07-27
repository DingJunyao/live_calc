// price_record.dart - 价格记录数据类型

/// 容错数值解析：后端 Decimal 字段会序列化成字符串（如 "6.88"），
/// 这里兼容 num / String / null 三种来源，避免类型转换崩溃。
double _toDouble(dynamic v, {double fallback = 0}) {
  if (v == null) return fallback;
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString()) ?? fallback;
}

int _toInt(dynamic v, {int fallback = 0}) {
  if (v == null) return fallback;
  if (v is int) return v;
  if (v is num) return v.toInt();
  return int.tryParse(v.toString()) ?? fallback;
}

class PriceRecord {
  final int id;
  final int productId;
  final String productName;
  final double price; // 记录总价（后端 price，Decimal → double）
  final double quantity; // 原始数量（后端 original_quantity）
  final String unit; // 原始单位（后端 original_unit）
  final int? merchantId;
  final String? merchantName;
  final String recordedAt;
  final String recordType; // 'purchase' | 'price'
  final String? notes;

  const PriceRecord({
    required this.id,
    required this.productId,
    required this.productName,
    required this.price,
    required this.quantity,
    required this.unit,
    this.merchantId,
    this.merchantName,
    required this.recordedAt,
    this.recordType = 'price',
    this.notes,
  });

  factory PriceRecord.fromJson(Map<String, dynamic> json) {
    return PriceRecord(
      id: _toInt(json['id']),
      productId: _toInt(json['product_id']),
      productName: (json['product_name'] as String?) ??
          (json['name'] as String?) ??
          '',
      price: _toDouble(json['price']),
      quantity: _toDouble(json['original_quantity'], fallback: 1),
      unit: (json['original_unit'] as String?) ??
          (json['unit'] as String?) ??
          '个',
      merchantId: json['merchant_id'] as int?,
      merchantName: json['merchant_name'] as String?,
      recordedAt: json['recorded_at'] as String? ??
          DateTime.now().toIso8601String(),
      recordType: json['record_type'] as String? ?? 'price',
      notes: json['notes'] as String?,
    );
  }

  /// 单价（每单位价格）；quantity 为 0 时退化为总价
  double get unitPrice => quantity > 0 ? price / quantity : price;
}
