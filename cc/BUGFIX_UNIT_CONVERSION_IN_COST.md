# 成本计算单位转换 & substitutable 回退修复

## 修复日期
2026-06-05

## 问题描述

### 问题 1：鸡蛋等 count 类型商品成本异常偏高
- **现象**：菜谱 349 中鸡蛋（50g）成本计算为 ¥31.33，远超合理范围
- **根因**：成本计算直接用价格记录的单价（¥/个）乘以菜谱数量（g），没有做单位转换
  - 鸡蛋价格：¥18.8 / 30个 = ¥0.6267/个
  - 菜谱用量：50（克，mass）
  - 错误计算：¥0.6267 × 50 = ¥31.33（把 50g 当成 50 个）
  - 正确计算：50g → 转换为 0.5个 → ¥0.6267 × 0.5 = ¥0.3133

### 问题 2：substitutable 关系不能作为价格回退源
- **现象**：菜谱 350 中「中筋面粉」没有成本，无法回退到「面粉」的价格
- **根因**：中筋面粉与面粉之间的层级关系是 `substitutable`（可替代）和 `contains`（包含），但回退查询只查 `fallback` 类型

## 修复方案

### 修改文件
- `backend/app/services/recipe_service.py`

### 修改内容

#### 1. 成本计算添加单位转换
在 `calculate_recipe_cost()` 和 `calculate_recipe_cost_trend()` 中，计算成本前通过 `UnitConversionService` 将菜谱用量单位转换为价格记录的单位：
- 引入 `UnitConversionService` 和 `Unit` 模型
- 当 `recipe_ingredient.unit_id` 与 `price_record.standard_unit_id` 不同时，调用 `UnitConversionService.convert()` 转换
- 传入 `entity_type="ingredient"` 和 `entity_id`，以利用 `entity_unit_overrides` 表中的精确换算（如鸡蛋 1个=55g）

#### 2. 回退查询扩展到 substitutable 关系
修改以下三处查询，将 `relation_type` 条件从仅 `FALLBACK` 扩展为 `FALLBACK + SUBSTITUTABLE`：
- `_get_ingredient_fallback()`（价格回退）
- `_get_ingredient_nutrition()`（营养回退）
- 批量计算的 `all_fallbacks` 查询（趋势图等批量场景）

## 验证结果
- 菜谱 349：鸡蛋成本从 ¥31.33 修正为 ¥0.3133 ✅
- 菜谱 350：中筋面粉成功回退到面粉价格 ¥0.995 ✅

## 备注
- `UnitConversionService` 的 `entity_unit_overrides` 查找只匹配 `from_unit_abbr`，mass→count 方向时不会命中注册在 count 单位名下的 override，退化为默认 100g/个
- 这是 `UnitConversionService` 自身的设计局限，不影响本次修复的正确性
