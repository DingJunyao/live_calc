---
name: multiple-fallback-fix
description: 修复了当存在多个同优先级回退时仅尝试第一个的 bug
metadata:
  type: fix
---

# 多回退目标选择 Bug 修复

## 问题描述

鸡腿肉（ingredient_id=278）设置了两个回退关系：
- 鸡腿肉 → 大鸡腿（strength=50，无价格记录）
- 鸡腿肉 → 鸡腿（strength=50，有价格记录约 6.9/500g）

两个回退优先级相同（strength=50），但 `_get_ingredient_fallback` 仅用 `.first()` 取第一个结果（大鸡腿），大鸡腿无价格记录且自身无进一步回退，最终返回 None。导致鸡腿肉成本显示为 0。

## 根因

`backend/app/services/recipe_service.py` 中 `_get_ingredient_fallback` 和 `_get_ingredient_nutrition` 使用 `.first()` 获取回退层级，当存在多个同优先级的回退目标时，只会尝试第一个。

## 修改

将 `.first()` 改为 `.all()`，遍历所有回退父级按 `strength` 降序尝试，第一个找到价格/营养数据的直接返回。

**涉及文件：** `backend/app/services/recipe_service.py`

**修改内容包括：**
1. `_get_ingredient_fallback` — 遍历所有 fallback 层级
2. `_get_ingredient_nutrition` — 同上

## 验证

- Python 语法检查通过
- 数据库中存在：鸡腿（id=275）有产品且关联价格记录，回退应能正确找到价格

## 影响

此问题同时导致成本趋势图表不显示（因所有日期 avg_cost 均为 0，被过滤掉）。修复后成本图表也将恢复正常显示。
