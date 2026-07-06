# 商品加权价格机制

> 日期：2026-07-07
> 设计稿：[docs/superpowers/specs/2026-07-06-product-weighted-price-design.md](../docs/superpowers/specs/202607-06-product-weighted-price-design.md)
> 实现计划：[docs/superpowers/plans/2026-07-06-product-weighted-price.md](../docs/superpowers/plans/2026-07-06-product-weighted-price.md)

## 背景与问题

一个原料常挂多个商品，价格差别悬殊（有机 vs 普通、不同品牌）。原系统把「商品价」聚合为「原料价」时两套逻辑互相打架且各有偏置：

1. **原料最新价**（[nutrition.py:get_ingredient_latest_price](../backend/app/api/nutrition.py#L864)）：把原料下所有商品、最近一天的所有价格记录**按记录数简单平均** → 记录多的商品被无形放大。
2. **菜谱成本**（[recipe_service.py:calculate_recipe_cost](../backend/app/services/recipe_service.py#L719) 等 5 变体）：遍历商品**取第一个有记录的商品** → 选中哪个全看查询顺序，价格悬殊时成本飘忽。

## 方案：商品级两层加权平均

- **第一层（商品内）**：每个商品当日有效记录的均价 → 该商品代表单价
- **第二层（商品间）**：按商品权重加权平均 `Σ(pᵢ×wᵢ)/Σwᵢ`（仅 w>0 且当日有记录的商品）

记录数从此不再影响原料价，只有商品权重说了算。

## 决策摘要

| 维度 | 结论 |
|---|---|
| 权重作用域 | 全局默认 + 用户私有覆盖 |
| 数值表达 | 0-100 整数，默认 50（对齐 ingredient_hierarchy.strength） |
| 生效范围 | 价格计算链路：原料最新价、菜谱成本、sparkline |
| 全局权重写权限 | 仅管理员（普通用户连提议都不开） |
| 用户覆盖写权限 | 所有用户（个人偏好，不走审核） |
| 与 default_product_id | 统一为权重机制；字段保留不动（死字段，价格计算只认权重） |

## 数据模型

- [products.price_weight](../backend/app/models/product_entity.py)：`INTEGER NOT NULL DEFAULT 50`，CHECK 0-100（SQL 层）
- 新表 [user_product_weight_overrides](../backend/app/models/user_product_weight_override.py)：`(user_id, product_id, weight)` + AuditMixin 软删，`UNIQUE(user_id, product_id)`
- 权重读取优先级：用户覆盖(is_active) → Product.price_weight → 兜底 50（封装在 `_resolve_weight`）
- 迁移：[alembic 20260707_0001](../backend/alembic/versions/20260707_0001_product_price_weight.py) + 四套 SQL（[sqlite](../backend/scripts/sql/20260707_product_price_weight_sqlite.sql) / mysql / postgres，PostGIS 与普通 PG 同）+ 开发库直接补（备份 `livecalc.db.bak_20260707_weight`），现有商品回填 50

## 统一服务 [ingredient_price_service.py](../backend/app/services/ingredient_price_service.py)

- `_product_unit_price(records)`：商品内均价（standard_quantity 为 0/None 时按 price 兜底）
- `_aggregate_weighted(product_records)`：纯聚合（无 db），返回 `{unit_price, mode, participants, excluded}`，mode ∈ weighted/single/none
- `_resolve_weight(db, user_id, product)`：权重优先级
- `get_weighted_ingredient_price(db, ingredient_id, *, as_of_date, user_id, target_unit_abbr, mode)`：编排，mode ∈ as_of（成本语义，当天+前向填充）/ recent（最新价语义，最近有记录日）
- `resolve_direct_weighted_for_cost(...)`：成本场景 helper，返回 `(unit_price_decimal, participants, std_unit_id)`

## 改造点

| 场景 | 现状 | 改造 |
|---|---|---|
| [原料最新价](../backend/app/api/nutrition.py#L864) | 记录级简单平均 | 保留逐条折算到目标单位、聚合换 `_aggregate_weighted`，响应加 `participants/excluded/mode`（target 口径，方案 B） |
| [菜谱成本 calculate_recipe_cost](../backend/app/services/recipe_service.py#L719) | 取第一个有记录商品 | 调 `resolve_direct_weighted_for_cost`（standard 口径），加权无价走原回退链；878 单价重算段加 `unit_price is None` 防对占位记录重算 |
| 菜谱成本 as_of / range_as_of | 同上 | 同模式（as_of 加权优先+失败回退；range_as_of 加权分支算 min/max/avg 再 continue） |
| 菜谱成本 trend | 调 as_of 循环 | 自动受益（as_of 已改） |
| [sparklines 原料](../backend/app/api/sparklines.py) | 记录级日均 | `_daily_avg_for_product_ids` 加 `ingredient_id/user_id` 参数，商品级加权（用户覆盖优先于全局） |

**单位口径差异**（关键）：统一服务编排返回「元/standard_unit」（成本口径）；latest-price 要「元/目标单位（如斤）」。故 latest-price 不直接用编排，而是自己逐条折算到目标单位后调 `_aggregate_weighted`（target 口径，精确）。成本场景用编排（standard 口径，配合 recipe 用量转换段）。

## 权限固化

- 全局 `price_weight`：仅管理员可写。[update_product](../backend/app/api/products_entity.py#L369) 对普通用户 payload 的 `price_weight` 一律剔除（连审核提议都不开）。`ProductExecutor` 吃 CrudExecutorBase setattr，管理员 `apply_as_admin` 直写生效。
- 用户覆盖：仿 [user_preferences](../backend/app/api/user_preferences.py) 样板，独立端点 `GET/PUT/DELETE /products/{id}/my-weight`（[product_weight.py](../backend/app/api/product_weight.py)），不走审核。

## 前端

- [ProductDetail 基本信息](../frontend/src/views/products/ProductDetail.vue)：`basicEditForm` 加 `priceWeight/myWeight/globalWeightReadOnly`，管理员可改全局、普通用户只读全局、所有人可设「我的覆盖」；`saveBasicInfo` 分流写入
- [IngredientDetail 商品编辑对话框](../frontend/src/views/ingredients/IngredientDetail.vue)：`productForm` 同构，`openEditProductDialog` 拉取生效权重、`saveProduct` 编辑分支分流
- 原料详情最新价区：可折叠「加权明细」（参与商品/权重/当日单价/来源 + 被排除项及原因），透明追溯
- API client：[productWeight.ts](../frontend/src/api/productWeight.ts)（`getProductMyWeight/setProductMyWeight/deleteProductMyWeight`）

## 测试

[test_ingredient_price_service.py](../backend/tests/services/test_ingredient_price_service.py) **15 个全过**：
- 8 纯聚合（基础加权、比例加权、权重0排除、无记录排除+归一、单商品退化、全空 None、**记录数偏置修正**、0 数量兜底）
- 3 权重解析（覆盖>全局>50）
- 2 集成（as_of 加权、用户覆盖排除，in-memory SQLite 不碰开发库）
- 2 e2e（管理员全局权重 0 排除、不同用户不同加权价）

前端 `npm run build` 通过（ProductDetail 58.18 kB、IngredientDetail 90.61 kB）。

## 遗留与未覆盖

- **range_trend 批量趋势函数未改**（[calculate_recipe_cost_range_trend](../backend/app/services/recipe_service.py#L1166)）：它是性能优化批量版（单商品 `price_source_cache` + 二分查找逐天），改成多商品加权需重写整个批量算法、风险高。遗留影响：菜谱 sparkline（[sparklines.py:81](../backend/api/sparklines.py#L81) 调 range_trend）和菜谱成本区间趋势（[recipes.py:1417](../backend/app/api/recipes.py#L1417)）暂仍是「单商品」口径，与详情页（加权）不一致。建议后续单独设计批量加权算法。
- **菜谱成本 breakdown 的 `weighted_participants` 字段未加**：cost/as_of 改造时聚焦加权计算，cost_breakdown.append 未补 `weighted_participants` 字段，故菜谱成本明细 tooltip 暂不展示加权来源（原料详情最新价区的加权明细已展示）。
- `default_product_id` 字段保留不动（前后端均无业务消费，死字段），价格计算只认权重。

## 环境备注

- **subagent 不可用**：本环境 subagent 底层模型配置坏（两次「模型不存在」API 错误），subagent-driven-development 回退为 inline 执行。
- **venv 在项目根**（`d:\code\live_calc\.venv`，非 `backend/.venv` 后者是空壳）：后端命令在 backend 目录用 `../.venv\Scripts\python.exe`。
- 开发库走「直接补」惯例（不走 alembic，参见 CLAUDE.md），操作前已备份。
