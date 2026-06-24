# 商家幽灵"商家2"修复

## 现象

[菜谱分析页](/recipes/337/analysis)「按商家预估成本」列表出现一个不存在的「商家2」，覆盖 1/12 种食材、成本 ¥3.95。数据库中没有名为"商家2"的商家。

## 根因

CONTAINS（子食材聚合）部分的 ProductRecord 查询**未过滤已关闭商家的价格记录**，导致三处代码配合出了问题：

1. **主查询**（`_add_merchant_prices_for`）正确过滤了 `Merchant.is_open == True` → 已关闭的千禧量贩（merchant_id=2, is_open=0）未加入 `merchant_names`
2. **CONTAINS 子食材查询**（原 [recipes.py:980-986](backend/app/api/recipes.py#L980-L986)）只查了 `ProductRecord.is_active == True`，**漏了 `Merchant.is_open == True` 过滤** → 千禧量贩的白砂糖价格记录进入 `child_costs_by_merchant`
3. **备用命名** `merchant_names.setdefault(mid, f"商家{mid}")` — 千禧量贩的 merchant_id=2 在 `merchant_names` 中不存在，兜底成"商家2"

## 触发链路

菜谱「香菇滑鸡」食材「糖」(ingredient_id=90) 没有直连商品/价格记录，走 CONTAINS 层级关系找到子食材「白砂糖」(ingredient_id=42)。白砂糖在千禧量贩有一条 ¥3.99 的价格记录，因查询没有 `is_open` 过滤而被纳入成本矩阵，但千禧量贩的商家名因 `is_open=0` 在主查询中被跳过，最终以"商家2"呈现。

## 修复

[recipes.py:980-990](backend/app/api/recipes.py#L980-L990) CONTAINS 子食材查询追加了两项改动：

1. 增加 `.join(Merchant, ProductRecord.merchant_id == Merchant.id).filter(Merchant.is_open == True)` — 与主查询保持一致的 `is_open` 过滤
2. 增加 `joinedload(ProductRecord.merchant)` — 并行的商家关系懒加载（配合第 3 项）
3. [recipes.py:1019-1022](backend/app/api/recipes.py#L1019-L1022) 商家名回退改为先查记录中的 `cr.merchant.name`，有值用值，无值才 `f"商家{mid}"` 兜底

## 验证

刷新菜谱分析页，「商家2」消失。按商家预估成本列表从 7 家变为 6 家，与数据库中的活跃商家数一致。
