# 商品加权价格机制 - 体验与口径修补

> 日期：2026-07-07
> 关联设计：[docs/superpowers/specs/2026-07-06-product-weighted-price-design.md](../docs/superpowers/specs/2026-07-06-product-weighted-price-design.md)
> 实现计划：[docs/plans/2026-07-07-product-weighted-price-refinements.md](../docs/plans/2026-07-07-product-weighted-price-refinements.md)
> 范围：前端（Vue/Vuetify）+ 后端（FastAPI），无表结构变更

## 背景

商品加权价格机制上线后，用户反馈 4 个体验/口径问题：

1. 「输入后回车添加多个别名」hint 与全局价格权重文本重叠
2. 普通用户编辑商品基本信息时，全局价格权重（仅管理员可改）仍显示无用的只读框
3. 权重用数字输入框不好用，应改滑块（参考层级关系强度）
4. 原料详情页「各商家价格」「价格趋势」里的平均未按商品权重加权

## 总原则（贯穿全部修补）

**权重只插手「平均值」语义**：加权 avg / 加权代表价 / 加权综合价。
`min` / `max` / `count` / 单条原始记录 / 各商家行 sparkline 迷你折线，**一律不动**。

## 修补详述

### 1. 权重编辑区重构（问题 1/2/3，前端两处同改）

`ProductDetail.vue` 基本信息编辑 + `IngredientDetail.vue` 商品行编辑对话框——两处控件本就同款，一并改：

- **去重叠**：别名 `v-combobox` 去掉 `persistent-hint`（聚焦时才显示 hint），权重区套 `mt-4` 与上方分隔。根子是 persistent-hint 常驻占行 + compact 密度紧贴下一字段 label。
- **普通用户不显示全局**：去掉「全局价格权重（仅管理员可改）」只读 `v-text-field`，普通用户该栏整块不渲染（管理员才见全局滑块）。
- **改滑块**：照搬 [关系强度 v-slider](../frontend/src/views/ingredients/IngredientDetail.vue#L1465) 样式（`thumb-label` + append 百分比 chip）。关键差别：关系强度 `min=1`（0=无意义），价格权重 **`min=0`**（0=排除该商品，设计文档明确定义有意义）。
- **「我的覆盖」用开关 + 滑块**：滑块无法表达「留空=用全局」，改用 `v-switch`「覆盖全局权重」勾选才出滑块，不勾 = 用全局（提交时 `deleteProductMyWeight`）。对应后端「有无覆盖记录」语义，比原 `clearable` 数字框直观。旁注「全局默认：N（不覆盖即用此值）」。

涉及：模板三件套、`basicEditForm`/`productForm` 加 `myWeightEnabled` 字段、`editBasicInfo`/`openEditProductDialog` 加载逻辑、`saveBasicInfo`/`saveProduct` 提交逻辑（按 `myWeightEnabled` 决定 set/delete）。

### 2. 原料价格趋势 avg 按商品权重加权（问题 4-a，前端）

[IngredientDetail.vue chartData](../frontend/src/views/ingredients/IngredientDetail.vue#L2965) 从「各商品记录简单平均」改为「按日 × 按商品权重加权」。商品详情页是单商品、无商品间权重维度，**不动**。

- 只改 `avg`：每商品当日均价 × 生效权重 Σ(pᵢwᵢ)/Σwᵢ（权重 0 排除）。
- `min`/`max`/`count` 原样（仍是当日全部记录的最低/最高/条数，记录级）。
- 单位转换逻辑（entity_unit_overrides / unitFactors）原样保留，只换聚合层。
- 权重数据源：新增 `productWeights` ref + `loadProductWeights`（调下面新端点），`loadData` 调一次。

文案：[PriceTrendChart.vue](../frontend/src/components/charts/PriceTrendChart.vue) 新增 `avgLabel` prop（默认「平均」），原料页传 `avg-label="加权平均"`（tooltip + series name）；商品页不传，保持「平均」（单商品简单平均，叫法准确）。

### 3. 各商家价格两处（问题 4-b/4-c，后端 + 前端）

- **同商家多商品按权（4-c）**：改 nutrition.py 的 [`_lookup_merchant_prices`](../backend/app/api/nutrition.py#L1062)。原 `merchant_latest[mid]` 只留最新一条记录（同商家多商品时偏到某商品）；改为按 `(merchant, product)` 各留最新一条 → 同商家内按商品权重加权（复用 [`_resolve_weight`](../backend/app/services/ingredient_price_service.py#L97)）。查询逻辑、单位折算、total_cost、子食材回退链（CONTAINS/FALLBACK）**全不动**，只换聚合层。权重仅作用于「商家代表价」这一平均语义。
- **列表底部加加权综合价（4-b）**：[IngredientDetail.vue](../frontend/src/views/ingredients/IngredientDetail.vue#L280) 各商家列表末尾加一行「商品加权综合价」，复用已加载的 `latestPrice`（即 `/nutrition/ingredients/{id}/latest-price` 的 `average_price`，已走统一加权服务）。零新接口。与上面「按商家看哪家便宜」是两个视角。

## 新增后端端点

`GET /api/v1/nutrition/ingredients/{id}/product-weights`（[nutrition.py](../backend/app/api/nutrition.py)）：返回原料下各有效商品的 `{product_id, name, global_weight, override_weight, effective_weight, source}`（覆盖>全局>50）。供前端价格趋势加权 avg 用——逐商品拉 `my-weight` 太慢（N 次请求），批量端点一次拿全。

## 关键技术点

- 复用现成 [`ingredient_price_service._resolve_weight`](../backend/app/services/ingredient_price_service.py#L97)（覆盖>全局>50，闭包内局部 import 避免任何循环依赖风险），不重写加权算法（守设计文档 4.5「不得重写」规矩）。
- `PriceRecord` 本就带 `product_id`（[IngredientDetail.vue:1819](../frontend/src/views/ingredients/IngredientDetail.vue#L1819)），chartData 按日×商品分组直接可用。
- 价格趋势「全部」大跨度性能：前端按日×商品聚合在客户端，复用现有 `loadChartPriceRecords` 分批累积机制，不改加载策略。

## 验证

- 后端：`pytest tests/test_ingredient_product_weights.py tests/test_ingredient_merchant_weighted.py` → **5 passed**（Task 1 端点 3 例：覆盖优先/空原料/None 兜底；Task 2 同商家加权 2 例：多商品加权(17.0)、权重 0 排除）；`py_compile` 通过。
- 前端：`npm run build` 通过（22.86s，无 TS/编译错误）。
- 浏览器实测：待用户核对（商品页滑块/开关/普通用户不显示全局；原料页趋势加权平均线 + 各商家综合价 + 同商家多商品代表价）。

## 补遗（2026-07-07 用户反馈：改权重后价格不刷新）

**现象**：原料详情页在「编辑商品」对话框里改了商品权重（全局/我的覆盖）或新增/删除商品后，最新价、各商家代表价、价格趋势仍显示旧值，需手动刷新。

**根因**：[`saveProduct`](../frontend/src/views/ingredients/IngredientDetail.vue#L2061) / [`deleteProduct`](../frontend/src/views/ingredients/IngredientDetail.vue#L2134) 保存成功后只更新了本地 `products.value`，没重拉依赖加权的数据——`latestPrice`（最新价，加权）、`merchantPrices`（各商家代表价，同商家多商品加权）、`productWeights`（趋势加权权重）。

**修复**：两处成功分支后统一调 `loadLatestPrice()` + `loadMerchantPrices()` + `loadProductWeights()`。`chartData` 是 computed，`productWeights` 一变它自动重算，无需单独刷新趋势图。覆盖三场景：
- 编辑商品改权重（我的覆盖对所有人立即生效、admin 全局立即生效、普通用户全局走提议 pending）
- 新增商品（改变加权分母）
- 删除商品（改变加权分母）

build 通过。

## 不在范围（YAGNI）

- ❌ 各商家行的 sparkline 迷你折线（定性看趋势，未点名的三处之外，不动）
- ❌ 商品详情页价格趋势 / 各商家价格（单商品，无商品间权重维度）
- ❌ min/max/count 改加权（用户明确：权重只管平均值）
