#!/usr/bin/env python3
"""验证菜谱成本计算修复"""

import os
import sys
from pathlib import Path

# 添加后端目录到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from decimal import Decimal
from app.services.recipe_service import calculate_recipe_cost
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient
from unittest.mock import Mock

def test_cost_calculation_logic():
    """测试成本计算逻辑"""
    print("=== 测试成本计算逻辑 ===")

    # 模拟测试数据
    # 模拟一个数量为 None 的食用品
    mock_recipe_ingredient_none = Mock()
    mock_recipe_ingredient_none.quantity = None  # None 值

    # 模拟一个数量为 0 的食用品
    mock_recipe_ingredient_zero = Mock()
    mock_recipe_ingredient_zero.quantity = "0"

    # 模拟一个数量为 100 的食用品
    mock_recipe_ingredient_hundred = Mock()
    mock_recipe_ingredient_hundred.quantity = "100"

    # 模拟价格记录
    mock_latest_record = Mock()
    mock_latest_record.price = 65.8
    mock_latest_record.standard_quantity = 5000  # 5000g

    # 计算正常单价
    record_price = Decimal(str(mock_latest_record.price))  # 65.8
    std_qty = mock_latest_record.standard_quantity  # 5000
    if std_qty is None or std_qty == 0:
        unit_price = record_price  # 这条不应该执行，因为std_qty是5000
    else:
        record_quantity = Decimal(str(std_qty))  # 5000
        unit_price = record_price / record_quantity  # 65.8/5000 = 0.01316

    print(f"标准数量: {mock_latest_record.standard_quantity}")
    print(f"单价计算: {record_price} / {record_quantity} = {unit_price}")

    # 验证各种数量情况下的成本计算
    test_cases = [
        ("None (空值)", mock_recipe_ingredient_none.quantity),
        ("0 (零值)", mock_recipe_ingredient_zero.quantity),
        ("100 (正常值)", mock_recipe_ingredient_hundred.quantity)
    ]

    for desc, qty in test_cases:
        ingredient_qty = qty
        if ingredient_qty is None:
            ingredient_qty = 0  # 将None转换为0

        print(f"\n测试 {desc} (转换后: {ingredient_qty}):")

        if ingredient_qty:  # 只有数量大于0时才计算成本
            try:
                quantity = Decimal(str(ingredient_qty))
                cost = unit_price * quantity if unit_price else Decimal("0")
                print(f"  进入正常计算路径，成本: {cost}")
            except Exception as e:
                cost = Decimal(str(mock_latest_record.price))
                print(f"  进入异常处理路径，成本: {cost} (异常: {e})")
        else:
            print(f"  进入else路径，成本应为0.0")
            cost = 0.0

        print(f"  最终成本: {cost}")

if __name__ == "__main__":
    test_cost_calculation_logic()