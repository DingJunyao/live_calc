/// 营养成分默认展示项（与 Web 端 coreNutritionItems 一致）
const defaultNutrientKeys = ['能量', '蛋白质', '脂肪', '碳水化合物', '钠'];

/// 展开时营养素排序顺序（英文键已预先转为中文）
const nutrientSortOrder = [
  '能量',
  '蛋白质',
  '脂肪',
  '碳水化合物',
  '钠',
  '膳食纤维',
  '钙',
  '磷',
  '钾',
  '镁',
  '铁',
  '锌',
  '硒',
  '铜',
  '锰',
  '维生素A',
  '维生素B1',
  '维生素B2',
  '维生素B6',
  '维生素B12',
  '维生素C',
  '维生素D',
  '维生素E',
  '维生素K',
  '叶酸',
  '烟酸',
  '胆固醇',
  '饱和脂肪',
];

/// 英文 → 中文 营养素名映射
const englishToChineseNutrient = <String, String>{
  'energy': '能量',
  'calories': '能量',
  'protein': '蛋白质',
  'fat': '脂肪',
  'carbohydrate': '碳水化合物',
  'carbs': '碳水化合物',
  'sodium': '钠',
  'fiber': '膳食纤维',
  'calcium': '钙',
  'phosphorus': '磷',
  'potassium': '钾',
  'magnesium': '镁',
  'iron': '铁',
  'zinc': '锌',
  'selenium': '硒',
  'copper': '铜',
  'manganese': '锰',
  'vitamin_a': '维生素A',
  'vitamin_b1': '维生素B1',
  'thiamin': '维生素B1',
  'vitamin_b2': '维生素B2',
  'riboflavin': '维生素B2',
  'vitamin_b6': '维生素B6',
  'vitamin_b12': '维生素B12',
  'vitamin_c': '维生素C',
  'vitamin_d': '维生素D',
  'vitamin_e': '维生素E',
  'vitamin_k': '维生素K',
  'folate': '叶酸',
  'niacin': '烟酸',
  'cholesterol': '胆固醇',
  'saturated_fat': '饱和脂肪',
};

/// 中文键 → 展示标签
String nutrientDisplayLabel(String key) {
  switch (key) {
    case '热量':
      return '能量';
    default:
      return key;
  }
}

/// 营养素排序：按 nutrientSortOrder 中的位置排序，未列出的排在最后
int compareNutrients(String a, String b) {
  final ia = nutrientSortOrder.indexOf(a);
  final ib = nutrientSortOrder.indexOf(b);
  if (ia == -1 && ib == -1) return a.compareTo(b);
  if (ia == -1) return 1;
  if (ib == -1) return -1;
  return ia - ib;
}
