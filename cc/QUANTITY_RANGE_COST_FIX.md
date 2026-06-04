# 修复：quantity_range 食材成本计算为 0 的问题

## 问题描述

在菜谱详情页面中，使用 `quantity_range`（用量区间，如 20-30 克）而非固定 `quantity` 的食材，其成本显示为 0。

例如菜谱 351「红烧排骨」中的五花肉，数据库记录为 `quantity=None`、`quantity_range={"max": 30.0, "min": 20.0}`，成本计算函数将 `None` 视为 0，导致五花肉花费显示为 0。

## 影响范围

全库共有 272 个食材项使用 `quantity_range` 而非固定 `quantity`，全部存在相同问题。

## 根因

`recipe_service.py` 中的三个成本计算函数都只检查 `recipe_ingredient.quantity`，将其为 `None` 时直接置为 0，没有检查 `quantity_range` 字段。

## 修复方案

1. 新增 `_get_effective_quantity(recipe_ingredient)` 辅助函数：
   - 优先使用 `quantity`（转为 Decimal）
   - 如果 `quantity` 为 None，则解析 `quantity_range` JSON，取最大值（偏保守的成本估算）
   - 如果解析失败，返回 Decimal("0")

2. 在三个函数中替换原来的 `ingredient_quantity = recipe_ingredient.quantity` + None 检查逻辑：
   - `calculate_recipe_cost`（实时成本计算）
   - `calculate_recipe_cost_range_as_of`（成本区间计算）
   - `calculate_recipe_cost_as_of`（历史成本计算）

## 影响

- 修复后，五花肉 20-30g 将使用平均值 25g 计算成本
- 以 12.9 元/斤（500g）计，成本约为 0.65 元
- 所有 272 个使用 `quantity_range` 的食材项将正确计算成本
