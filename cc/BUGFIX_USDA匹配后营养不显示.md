# USDA 匹配后营养信息不显示修复

## 问题
原料匹配 USDA 食材后，原料详情页营养区仍为空（接口返回 404，前端 `nutritionData = null`）。

## 根因
原料营养查询走 `NutritionCalculator.calculate_ingredient_nutrition`（[backend/app/services/nutrition_calculator.py](../backend/app/services/nutrition_calculator.py)），它只取两类 `NutritionData`：

- `source == 'custom'`（用户编辑，最高优先）
- 否则 `is_verified == True`（已验证的其他来源）

两条都不命中时返回 `None` → `GET /nutrition/ingredients/{id}/nutrition` 抛 404。

而 `match_ingredient`（[backend/app/services/usda/matcher.py](../backend/app/services/usda/matcher.py)）写入的 `NutritionData` 是 `source="usda_manual_match"` 且**未设置 `is_verified`**（模型默认 `False`）。于是 calculator 查不到 → 显示空。

> 商品不受影响：商品走 `calculate_product_nutrition`，直接读 `Product.custom_nutrition_data`，不过滤 `source`/`is_verified`。

## 修复
`match_ingredient` 写入 `NutritionData` 时增加 `is_verified=True`。

理由：用户手动确认的匹配属已验证数据，置 `True` 使 calculator 的 `is_verified == True` 分支命中；`source` 仍保留 `usda_manual_match` 以追溯来源。不动 calculator 的过滤逻辑（那是 custom > verified 的有意优先级设计）。

```python
nd = NutritionData(
    ingredient_id=ingredient_id,
    source="usda_manual_match",
    is_verified=True,          # 新增
    ...
)
```

## 附带改进
`UsdaMatchDialog` 的「确认匹配」原先用浏览器原生 `confirm()`，改为 Vuetify 二级模态对话框：主对话框内点「确认匹配」→ 弹出二级确认对话框（带警告图标 + 不可撤销提示）→ 点「确认写入」才真正调用匹配接口。消除浏览器原生弹框，与 UI 风格统一。

## 善后（历史数据）
修复前匹配的原料写入的是 `is_verified=0` 记录，仍读不出来。重新对同一原料点一次「确认匹配」即可覆盖写入新数据（`is_verified=True`）；或执行一条 UPDATE（标准 SQL，SQLite/MySQL/PostgreSQL 通用，需开发者确认后自行执行）：

```sql
UPDATE nutrition_data SET is_verified = 1 WHERE source = 'usda_manual_match';
```

## NRV 未计算（第二轮修复）

### 问题
原料匹配 USDA 后营养能显示了，但核心营养素的 **NRV%**（营养素参考值百分比）一列全是 0 / 空。

### 根因
前端 `getNutritionNRV`（[IngredientDetail.vue](../frontend/src/views/ingredients/IngredientDetail.vue)）依赖每个营养素项的 `nrp_pct` + `standard` 字段：`standard==='无标准'` 或 `nrp_pct` 为 undefined/null → 显示 `-`，否则显示百分比。

正常导入（HowToCook `nutritions.json`）的每项**预带** `nrp_pct` + `standard`（[nutrition_import_service.py:455](../backend/app/services/nutrition_import_service.py)）；而 matcher 从 USDA 原始数据构建，entry 只有 `{value, unit, key}`，缺这俩字段 → NRV 空。

### 修复
1. 把 `NutritionCalculator.calculate_product_nutrition` 内嵌的 NRV 计算（`NRV_REF` + 单位换算 + `_calc_nrp_pct`）**提取为模块级** `calc_nrv_pct(display_name, value, unit)`（[nutrition_calculator.py](../backend/app/services/nutrition_calculator.py)），含单位规范化（支持 USDA 大写单位 G/MG/UG/KCAL/KJ）；商品逻辑改调它，行为等价、消除重复。
2. `matcher._build_nutrition_json` 写入时用 `calc_nrv_pct` 给核心营养素算 `nrp_pct` + `standard="中国GB标准"`；非核心标 `standard="无标准"`（前端显示 `-`），对齐导入格式。

验证：蛋白质 30g→50%、钙 80MG→10%、维A 400UG→50%、能量 836.8KJ→10%（KJ→kcal 换算）、饱和脂肪酸→None。

## USDA 搜索改 AND（功能调整）

### 需求
原搜索为 OR（空格分词，任一命中即召回），改为 **AND**：每个分词都必须命中，每个分词只要中文名或英文名任一子串命中即算该项通过。

### 修复
[backend/app/services/usda/search.py](../backend/app/services/usda/search.py) `_score`：任一 token 未命中直接 `return -1`（淘汰），全部命中才打分入选。测试 `test_usda_search.py` 同步从 OR 用例改为 AND 用例（`test_and_requires_all_tokens`、`test_and_token_matches_either_zh_or_en`）。

## 涉及文件
- [backend/app/services/usda/matcher.py](../backend/app/services/usda/matcher.py) —— `match_ingredient` 写入加 `is_verified=True`；`_build_nutrition_json` 带 `nrp_pct` + `standard`
- [backend/app/services/nutrition_calculator.py](../backend/app/services/nutrition_calculator.py) —— 提取模块级 `calc_nrv_pct`，`calculate_product_nutrition` 改调它
- [backend/app/services/usda/search.py](../backend/app/services/usda/search.py) —— `_score` 改 AND
- [frontend/src/components/usda/UsdaMatchDialog.vue](../frontend/src/components/usda/UsdaMatchDialog.vue) —— `confirm()` 改 Vuetify 二级模态对话框
