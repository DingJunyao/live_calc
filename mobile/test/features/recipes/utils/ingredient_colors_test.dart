import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:com_a4ding_livecalc/features/recipes/utils/ingredient_colors.dart';

void main() {
  group('getIngredientColor', () {
    test('同一 ingredient_id 颜色一致', () {
      expect(getIngredientColor(3), getIngredientColor(3));
    });

    test('不同 id 从 16 色板取色（abs % 16）', () {
      expect(getIngredientColor(0), INGREDIENT_COLOR_PALETTE[0]);
      expect(getIngredientColor(16), INGREDIENT_COLOR_PALETTE[0]);
      expect(getIngredientColor(-1), INGREDIENT_COLOR_PALETTE[1]);
      expect(getIngredientColor(7), INGREDIENT_COLOR_PALETTE[7]);
    });

    test('null 返回灰色', () {
      expect(getIngredientColor(null), const Color(0xFFE0E0E0));
    });
  });
}
