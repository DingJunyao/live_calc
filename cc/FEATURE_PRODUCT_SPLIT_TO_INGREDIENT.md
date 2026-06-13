# 商品拆分为原料功能

## 概述

在商品详情页添加「拆分为原料」功能，允许将商品从当前原料中拆分出来，创建为独立的同名原料。

## 功能逻辑

1. 在商品详情页底部（删除按钮上方）添加「拆分为原料」按钮
2. 后端检查商品是否为当前原料的唯一活跃商品，若是则拒绝拆分
3. 创建同名新原料，将营养数据 mixin（商品自定义 + 原料营养）写入新原料
4. 商品关联到新原料，清空 `custom_nutrition_data`
5. 同名冲突时弹出重命名对话框
6. 拆分成功后跳转到新原料详情页

## API

- `POST /api/v1/products/entity/{product_id}/split-to-ingredient`
  - 可选参数 `new_name`：同名冲突时指定新名称
  - 返回 `{ message, ingredient_id, ingredient_name }`
  - 错误码：400（唯一商品/未关联原料）、403（无权限）、404（不存在）、409（同名冲突）

## 安全措施

- 权限校验：仅创建者或管理员可操作
- 名称空值校验
- `joinedload` 关联加载避免懒加载问题

## 修改文件

- `backend/app/api/products_entity.py` - 新增拆分 API 端点
- `frontend/src/views/products/ProductDetail.vue` - 按钮、对话框、交互逻辑

## Bug 修复：营养数据复制链路（2026-06-13）

功能上线后出现两个症状，根因不同，分两阶段修复。

### 阶段一：拆分后新原料无营养数据

**现象**：拆分后新原料和商品都没有营养数据。

**根因**：拆分时获取源原料营养调用 `_get_ingredient_nutrition_with_fallback()`，该函数查找逻辑有缺陷：

- 第 1 步查 `source='custom'`，USDA 导入数据是 `source='usda_import'`，不命中
- 第 2 步查 `id == ingredient.nutrition_id`，但实际 `Ingredient.nutrition_id` 多为 NULL（USDA 数据通过 `nutrition_data.ingredient_id` 关联），不命中
- 结果返回空 → merged 为空 → 不创建 NutritionData 记录

**修复**：将 `_get_ingredient_nutrition_with_fallback` 的查找逻辑与 `NutritionCalculator` 对齐：优先 `source='custom'`，其次 `is_verified=True`（覆盖 USDA 导入数据），最后 `nutrition_id` 外键回退。同时 `_merge_nutrition_data` 补全 `nutrient_details` 层避免 USDA 详细信息丢失。

### 阶段二：拆分后原料正常但商品页营养全为 0

**现象**：阶段一修复后，新原料详情页营养正常，但商品详情页营养值全为 0。

**根因**：前端商品页 `loadNutritionData` 调用的是 `GET /nutrition/products/{id}/nutrition`（nutrition.py），该端点走 `NutritionCalculator.calculate_product_nutrition` → `NutritionMixin.merge_nutrition_data`。`NutritionMixin._lookup_fallback_nutrition` 查找条件是 `ingredient_id == id AND is_verified == True`。但拆分写入新原料的 NutritionData 设置了 `is_verified=False`，导致：

- 原料详情页（`calculate_ingredient_nutrition` 优先查 `source='custom'`，不要求 is_verified）→ 正常
- 商品详情页（`NutritionMixin` 查 `is_verified=True`）→ 查不到 → 全 0

**修复**：拆分写入新原料的 NutritionData 设 `is_verified=True`，与 `edit_ingredient_nutrition`（用户手动编辑营养）行为一致。

### 阶段三：拆分后原料展示正常但编辑模式能量值错误

**现象**：拆分后原料详情页展示模式显示商品自定义的能量值（如 114 kcal），但点击编辑后显示 USDA 原始值（如 13 kcal）。

**根因**：能量营养素存在两套键名——USDA 导入数据用 `energy`，系统标准（前端 `NUTRIENT_DEFINITIONS`、商品保存格式）用 `energy_kcal`。拆分 merge 后，新原料的 `all_nutrients` 同时存在 `energy`（USDA 值）和 `energy_kcal`（商品值）两个同义键。而 `NutritionCalculator.NUTRIENT_NAMES` 只有 `energy_kcal`→"能量" 映射，缺少 `energy` 映射，导致：

- `energy`（13）→ 无映射，display 保留英文键 "energy"
- `energy_kcal`（114）→ 映射为 "能量"

`_calculate_scaled_nutrients` 返回的 all_nutrients 出现两个能量键：`energy`(13) 和 `能量`(114)。

- 展示模式：按中文键"能量"显示 → 114 ✓
- 编辑模式（`startEditNutrition`）：遍历 all_nutrients，`energy`(13) 先于 `能量`(114)，经 `NUTRIENT_PARENT_MAP` 归一去重后保留了先遍历的 → 13 ✗

**修复**：在 `NutritionCalculator.NUTRIENT_NAMES` 添加 `"energy": "能量"` 映射（与 `vitamin_a_rae` / `vitamin_a_iu` 两个英文键同映射到一个中文显示名的既有处理模式一致）。merge 顺序保证商品值（energy_kcal）后处理覆盖 USDA 值（energy），符合"商品自定义优先"语义。修复后 all_nutrients 只剩单一"能量"键=商品值，展示与编辑一致。

### 经验

系统中营养数据查找存在三套并行逻辑（`_get_ingredient_nutrition_with_fallback`、`NutritionCalculator`、`NutritionMixin`），查找条件不一致是 bug 温床。此外存在键名不统一问题（USDA 用 `energy`、系统用 `energy_kcal`），同义键共存导致展示/编辑/计算链路行为分裂。拆分等数据迁移操作需确保写入的数据满足所有读取链路（`is_verified` 标记、键名规范）。

## 实现日期

2026-06-13

## 阶段四：能量键名系统统一（energy_kcal / energy_kcal_alt → energy）

### 背景

调查发现 energy_kcal 和 energy_kcal_alt 均为 USDA 导入产物（分别来自"热量（Atwater 通用系数）"和"热量（Atwater 特定系数）"字段），而主数据使用 energy（来自"能量/Energy"字段）。三者同义分裂是阶段一~三 bug 的根源。

源数据分析（HowToCook_json/out/nutritions.json，552 食材）：
- `energy`：952 次（97.6%），来自"能量/Energy"
- `energy_kcal`：8 次，来自 Atwater 通用系数
- `energy_kcal_alt`：7 次，来自 Atwater 特定系数

### 修改范围

共修改 11 个文件，统一 energy_kcal → energy，energy_kcal_alt → energy：

**后端：**
- `nutrition_import_service.py` — CN_TO_KEY / EN_NAME_TO_KEY 能量映射统一为 energy
- `nutrition_calculator.py` — CORE_NUTRIENTS、NUTRIENT_NAMES
- `ingredient_extended.py` — 创建原料营养映射（2 处）
- `recipe_service.py` — 营养模板
- `nutrition_data.py` / `mixins/__init__.py` / `products_entity.py` — 注释/示例更新

**前端：**
- `ProductDetail.vue` — NUTRIENT_DEFINITIONS key、NUTRIENT_PARENT_MAP 删除能量同义映射
- `IngredientDetail.vue` — NUTRIENT_DEFINITIONS key、NUTRIENT_PARENT_MAP 删除能量同义映射
- `nutritionLabels.ts` — ENGLISH_TO_CHINESE_MAP 删除重复 energy_kcal，删除 energy_kcal_alt 标签

**数据迁移：**
- `backend/scripts/migrate_energy_keys.py` — 处理 nutrition_data.nutrients 和 products.custom_nutrition_data 中 energy_kcal/energy_kcal_alt 的键名与条目内 key 字段值统一
- dry-run 确认：9 条 nutrition_data 需迁移

### 执行迁移

```bash
cd backend
../.venv/Scripts/python scripts/migrate_energy_keys.py --dry-run   # 预览
../.venv/Scripts/python scripts/migrate_energy_keys.py             # 执行
```
