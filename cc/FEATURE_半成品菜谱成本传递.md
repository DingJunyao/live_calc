# 半成品菜谱成本传递

## 概述

支持「自制半成品」的成本传递：某些原料（如米饭）并非购买，而是由另一个菜谱（如蒸米饭）制作。允许原料指向其制作菜谱，使该原料的成本由制作菜谱推导，支持递归套娃与循环检测。

触发场景：蛋炒饭(280) 含「米饭」原料，而米饭由电饭煲蒸米饭(185) 制作。米饭无商品价时，其成本应由 185 的成本推导。

## 核心设计

| 决策 | 选择 |
|---|---|
| 绑定方式 | 原料级绑定（一处设置，处处生效） |
| 产量量化 | 绕开成品总产量，用「份 × 每份重」桥接 |
| 份重字段 | 新增 `ingredients.serving_weight`（不动 piece_weight） |
| 成本优先级 | 商品优先，无价才自制（制作菜谱作为回退链一环） |
| 营养传递 | 暂不做（用原料自身 USDA 数据） |

成本公式：`每克成本 = 制作菜谱总成本 ÷ (servings × serving_weight 折算为克)`

## 数据模型

- **激活 `recipes.result_ingredient_id`**（既有字段，原闲置）：本菜谱的成品原料，一对一。
- **新增 `ingredients.serving_weight` + `serving_weight_unit_id`**：成品基准量（每份多重），`servings` 是其倍数。

## 成本计算（recipe_service.py）

回退链：直接商品价 → **制作菜谱成本(NEW)** → FALLBACK/SUBSTITUTABLE → CONTAINS 子食材聚合。

- `_get_cost_from_recipe`：反查制作菜谱（`result_ingredient_id == 本原料`）、递归算其成本、份重桥接每克单价。
- `_serving_weight_to_grams`：份重按单位 + 密度折算为克。
- **循环检测**：`visited` 集合贯穿整条调用链，链上见过的菜谱直接放弃。
- `calculate_recipe_cost` / `calculate_recipe_cost_as_of` 均新增 `visited` 参数并透传。
- `cost_breakdown` 新增 `recipe_chain` + `cost_source="recipe"`。

## 改动文件

**后端：**
- `models/nutrition.py`：Ingredient 加 `serving_weight` / `serving_weight_unit_id` 及关系
- `api/ingredient_extended.py`：update/get ingredient 暴露 serving_weight；get_ingredient 反查制作菜谱（making_recipe_id/name）
- `schemas/nutrition.py`：IngredientResponse 加字段
- `services/recipe_service.py`：制作菜谱回退环、份重换算、循环检测、recipe_chain
- `alembic/versions/20260615_0001_add_serving_weight_to_ingredients.py`：迁移
- `scripts/add_serving_weight.sql`：SQLite/MySQL/PostgreSQL 兼容脚本

**前端：**
- `components/recipes/RecipeBasicCard.vue`：菜谱详情页「成品产出」选择与展示
- `views/ingredients/IngredientDetail.vue`：原料详情页「自制来源」选择 + 成品基准量输入 + 展示（保存时双重 PUT 同步 result_ingredient_id）
- `components/recipes/RecipeIngredientCard.vue`：成本明细 tooltip 加 recipe_chain 优先级

**附带修复：**
- alembic 坏链：`20260611_0001`（down_revision 写成文件名）、`20260614_195120`（down_revision=None 脱链）修正，使 `alembic heads/current` 恢复可用。
- `calculate_recipe_cost_as_of` 的 `unit_price * quantity`（Decimal×float）改为 `Decimal(str(quantity))`——制作菜谱/聚合命中 + 单位转换场景下的既有隐患。

## 数据库迁移

- alembic head：`20260615_0001`
- 开发库（SQLite）已直接 `ALTER TABLE` 添加 serving_weight 两列
- 其它引擎用 `scripts/add_serving_weight.sql`
- ⚠️ 开发库 `alembic_version` 表为空（schema 历来手动维护），**不可 `alembic upgrade head`**（会重跑全部历史迁移），仅靠 SQL/手动维护 schema

## 使用方式

1. **菜谱页**（如 185 蒸米饭）→ 编辑基本信息 →「成品产出」选米饭原料 → 保存
2. **原料页**（米饭）→ 编辑基本信息 →「自制来源」选蒸米饭菜谱 + 填成品基准量（如 200g）→ 保存
   （两处任一设置即可，底层同一字段 `result_ingredient_id`）
3. 蛋炒饭详情页成本明细中，米饭行显示「⤴ 由制作菜谱计算」，金额由蒸米饭成本推导

## 验证

- 185 设成品=米饭、米饭 `serving_weight=200g`
- 蛋炒饭 280 成本明细：米饭 `cost_source=recipe`，单价 `0.004362 元/克 = 185 成本(0.8724) ÷ 200g`，金额 `2.181 元`
- 链描述：`米饭 ← 制作自「电饭煲蒸米饭」`
- 其它原料各归各位（direct / fallback / contains_aggregation）
- 前端构建通过、后端导入无报错

## 已知限制

- `calculate_recipe_cost_range_trend`（成本区间趋势的批量优化版）**暂不支持**制作菜谱回退：该函数为独立批量实现，正确支持需重写其预加载逻辑。命中制作菜谱的原料在该趋势中按现有逻辑（无价则贡献 0）。`calculate_recipe_cost`、`calculate_recipe_cost_as_of`、`calculate_recipe_cost_trend`（逐天调 as_of）均已支持。
- 设计文档：[docs/plans/2026-06-15-semi-finished-recipe-cost-design.md](../docs/plans/2026-06-15-semi-finished-recipe-cost-design.md)
- 实施计划：[docs/plans/2026-06-15-semi-finished-recipe-cost-implementation.md](../docs/plans/2026-06-15-semi-finished-recipe-cost-implementation.md)
