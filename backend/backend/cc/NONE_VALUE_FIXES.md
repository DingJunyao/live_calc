# None 值处理修复总结

## 修改概述
本次修改解决了在计算菜谱成本和营养素时未将 `None` 值视为 `0` 的问题。这个问题可能导致在处理空值时出现错误或异常。

## 关键修改

### 1. 后端服务文件
- **backend/app/services/recipe_service.py**
  - 修改了 `calculate_recipe_cost` 函数以正确处理 `None` 值
  - 修改了 `calculate_recipe_nutrition` 函数以处理各种可能的 `None` 值情况
  - 添加了对营养数据、参考量、单位等可能为 `None` 的字段的处理

- **backend/app/services/nutrition_calculator.py**
  - 修改了 `_parse_quantity` 函数以处理数量为 `None` 的情况
  - 修改了 `_calculate_scaled_nutrients`、`_accumulate_nutrients` 和 `_calculate_per_serving` 函数以处理可能的 `None` 值

### 2. 代码改进
- 添加了对营养数据中的 `value`、`unit`、`nrp_pct` 等字段为 `None` 的检查
- 在进行数学运算前验证值不为 `None`
- 确保所有计算都能处理空值而不引发异常

## 影响
- 菜谱成本计算现在能正确处理数量为 `None` 的原料
- 菜谱营养计算现在能正确处理营养数据中的空值
- 产品营养计算现在能正确处理数量为 `None` 的情况
- 系统整体的健壮性和容错能力得到提升

## 验证
- 通过测试脚本验证修改后的代码能够正确处理 `None` 值而不抛出异常
- 确认了核心计算逻辑在各种 `None` 值场景下都能正常工作