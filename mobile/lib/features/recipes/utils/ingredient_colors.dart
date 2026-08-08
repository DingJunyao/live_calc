import 'package:flutter/material.dart';

/// 食材配色工具——同种食材在成本占比、成本趋势、营养溯源三张图表中使用相同颜色。
/// 通过 ingredient_id 对色板长度取模取色（对齐 web utils/ingredientColors.ts）。
const INGREDIENT_COLOR_PALETTE = <Color>[
  Color(0xFFFF9800), Color(0xFF4CAF50), Color(0xFF2196F3), Color(0xFF9C27B0),
  Color(0xFFF44336), Color(0xFF00BCD4), Color(0xFFFF5722), Color(0xFF607D8B),
  Color(0xFFE91E63), Color(0xFF3F51B5), Color(0xFF009688), Color(0xFF795548),
  Color(0xFFCDDC39), Color(0xFFFFC107), Color(0xFF03A9F4), Color(0xFF8BC34A),
];

Color getIngredientColor(int? ingredientId) {
  if (ingredientId == null) return const Color(0xFFE0E0E0);
  return INGREDIENT_COLOR_PALETTE[ingredientId.abs() % INGREDIENT_COLOR_PALETTE.length];
}
