# 原料详情页价格区间 1000 倍 bug + 最新价标签错位

**日期**：2026-07-07
**文件**：[IngredientDetail.vue](../frontend/src/views/ingredients/IngredientDetail.vue) 单文件，无表结构变更

## 现象

`/data/ingredients/142`（茄子）最新价格卡片显示「¥9.19/个」，右侧区间「¥0.01 - ¥0.01/千克」——单位打架（个 vs 千克）、区间 min==max==0.01 荒谬。

## 根因（两个独立 bug）

### Bug 1：最新价标签错位（priceUnitName vs 后端 mass 口径）

- 后端 [nutrition.py latest-price:941](../backend/app/api/nutrition.py#L941) 的 `target_unit_abbr` 取自 `current_user.default_mass_unit_id`（**质量偏好**，当前用户 billding = unit 2 = kg），逐条折算到 kg 再商品级加权。最近一天（2026-06-26）三条 1 斤记录（4.99/2.99/5.8 元）折 kg 等权加权 = (9.98+5.98+11.6)/3 = **9.186 ≈ 9.19 元/千克**。后端返回体含 `unit` 字段。
- 前端 [loadLatestPrice:3119](../frontend/src/views/ingredients/IngredientDetail.vue#L3119) **没取** `response.unit`，[模板:214](../frontend/src/views/ingredients/IngredientDetail.vue#L214) 硬贴 `priceUnitName`（=「个」，**价格偏好** unit 18）。标签「个」与数值实际单位「千克」错位。
- 同款错位还有 [:296](../frontend/src/views/ingredients/IngredientDetail.vue#L296)「商品加权综合价」。

### Bug 2：区间 0.01 是 1000 倍单位换算 bug（name vs abbr 错位）

[chartData:2961](../frontend/src/views/ingredients/IngredientDetail.vue#L2961) `defaultUnit = massUnitName.value` 取单位**名字「千克」**，但 [unitFactors 表:2983](../frontend/src/views/ingredients/IngredientDetail.vue#L2983) 的 key 全是**缩写**（`'kg': 1000`，无「千克」键）。

- `toFactor = unitFactors['千克']` = undefined → fallback `1`
- 单价转换 `originalUnitPrice × (toFactor/fromFactor) = (price/qty) × (1/500)`，本该 `×(1000/500)`，**少 1000 倍**
- 当天三条：4.99×(1/500)=0.00998、2.99×(1/500)=0.00598、5.8×(1/500)=0.0116，`toFixed(2)` **全部舍入成 0.01** → min==max==0.01

与 [VOLUME_MASS_CONVERSION_1000X_BUG](VOLUME_MASS_CONVERSION_1000X_BUG.md) 同源（SI 基准/单位 key 错位致 1000 倍）。后端 latest-price 用 `_mu.abbreviation`（缩写）没事，前端 chartData 偏用 name 踩坑。

## 修复（IngredientDetail.vue 3 处）

1. **解构加 massUnit**（[:1949](../frontend/src/views/ingredients/IngredientDetail.vue#L1949)）：`useUserUnits()` 返回值加 `massUnit`（含 abbreviation）。
2. **最新价 + 综合价标签**（[:214](../frontend/src/views/ingredients/IngredientDetail.vue#L214) / [:296](../frontend/src/views/ingredients/IngredientDetail.vue#L296)，replace_all `/{{ priceUnitName }}`→`/{{ massUnitName }}`）：与后端 mass 口径、区间 chartUnit 三方一致。
3. **chartData defaultUnit 改用缩写**（[:2961](../frontend/src/views/ingredients/IngredientDetail.vue#L2961)）：`massUnit.value?.abbreviation ?? '斤'`，堵 1000 倍 bug。附注释说明 name vs abbr 陷阱。

## 验证

- 静态：ProductDetail.vue 确认**无同款 bug**——其 [chartData:2086](../frontend/src/views/products/ProductDetail.vue#L2086) 用 `standard_quantity`（后端折算好的克数）+ `convertFromJin`（abbr 查 COMMON_SI_FACTORS），路径不同且正确。这也解释了为何只原料页出 0.01（两页 chartData 不同构，原料页是劣化版）。
- 构建：`npm run build` 通过（34.22s）。
- 数值手算：修复后最近一天区间 = 5.98/9.98/11.6 元/kg → 显示「¥5.98 - ¥11.60/千克」，最新价 9.19 落在区间内，自洽。
- 浏览器待验：刷新 `/data/ingredients/142` 看最新价「¥9.19/千克」、区间「¥5.98 - ¥11.60/千克」。

## 遗留（未做，供决策）

1. **后端 latest-price 口径**：现按 mass 偏好归一化（元/千克），趋势比较友好但不直观（茄子平时按个/斤卖）。若要让「最新价格」按「元/个」或「元/斤」显示，需改 [nutrition.py:941](../backend/app/api/nutrition.py#L941) `target_unit_abbr` 取 `default_price_unit_id`，且 count 单位（个）↔ mass 折算需 `piece_weight`（原料 142 `piece_weight=None`，还得补）。属产品设计决策，未动。
2. **IngredientDetail chartData 路径劣化**：现用 `original_quantity` + 自查 unitFactors（易错），ProductDetail 用 `standard_quantity` + `convertFromJin`（稳健）。长远应统一为后者（DRY + 消除 name/abbr 陷阱），本次只做最小修复堵 1000 倍。
