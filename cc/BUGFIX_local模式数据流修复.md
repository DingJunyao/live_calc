# local 模式数据流修复（菜谱/原料/商品详情）

纯前端本地模式（`VITE_STORAGE_MODE=local`，IndexedDB 存 `livecalc` 库）下一批「详情页数据对不上/缺失」修复。根因高度同构：**local handler 移植时与云模式 + 前端消费方的字段契约没对齐**（漏字段、漏参数、返回格式不一致）。逐条 trace 数据流（浏览器实测 + 代码对照）定位，全部 build/实测通过。

## 1. 菜谱 NRV 与数量对不上

**现象**：菜谱详情「营养成分」NRV% 与「数量」列口径拧着——数量显示每份实际量，NRV 却按「每 100g 菜谱」算。

**根因**：[recipes.ts getRecipeNutrition:351](../frontend/src/api/local/handlers/recipes.ts#L351) 组装 `per_serving_nutrition` 时，`nrp_pct` 直接用了 `aggregateIngredients` 返回的 `n.nrv_pct`，而 [nutritionAggregator.ts:77](../frontend/src/api/local/business/nutritionAggregator.ts#L77) 的 `nrv_pct` 是基于「每 100g」算（`calcNRV(name, amount/totalG*100)`）。云模式（[nutrition.py:1506](../backend/app/api/nutrition.py#L1506) `_calc_nrp(display_name, value, unit)`）基于每份 `value` 算。

**修复**：recipes.ts import `calcNRV`，组装时 `nrp_pct: calcNRV(n.nutrient_name, n.amount)`（基于每份实际量 `n.amount`）。两处（core_nutrients/all_nutrients）。

**验证**：蛋白质 4636.4g → NRV 7727.4%（=4636.4÷60×100），口径一致。

## 2. 原料详情价格记录显示所有商品（越界）

**现象**：原料详情（如西葫芦）的价格记录列表混入其他商品记录。

**根因**：[IngredientDetail loadPriceRecords:3248](../frontend/src/views/ingredients/IngredientDetail.vue#L3248) 请求 `/products` 传 `ingredient_id`，但本地 [products.ts listRecords:118](../frontend/src/api/local/handlers/products.ts#L118) 只认 `product_id/merchant_id/date`，**不认 `ingredient_id`** → 不过滤、全表返回（2370 条）。

**修复**：listRecords 加 `ingredient_id` 过滤——先 `getByIndex('products','by_ingredient_id', id)` 取该原料商品 id 集，再筛 `product_id ∈ 集合`。

**验证**：西葫芦只显示自己关联商品的 22 条。

## 3. 原料详情相关菜谱空白

**现象**：原料详情「相关菜谱」空白。

**根因**：云模式 `/nutrition/ingredients/:id/recipes`（[nutrition.py:795](../backend/app/api/nutrition.py#L795)）返回 `{items:[{id,name,...菜谱详情}]}`；本地 [nutrition.ts getIngredientRecipes:321](../frontend/src/api/local/handlers/nutrition.ts#L321) 只返回裸 `recipe_ingredients` 数组（无 items 包装、无菜谱字段），前端 [IngredientDetail loadRecipes:3380](../frontend/src/views/ingredients/IngredientDetail.vue#L3380) 读 `response.items` = undefined → 空。

**修复**：getIngredientRecipes 改为按 `by_ingredient_id` 查关联、去重 recipe_id、逐个取 recipes 详情，组装 `{items:[{id,name,images,category,difficulty,servings,is_public}], total}` 返回。`is_public` 缺省 `?? true`（local 单用户，可见性与发布无关，避免误标未发布，见 #6）。

**验证**：西葫芦显示「西葫芦炒鸡蛋」「韩式拌饭」2 个。

## 4. 菜谱食材计量单位全变「斤」（导入错配）

**现象**：菜谱详情各食材单位全是「斤」（如上汤娃娃菜娃娃菜 700 斤），导致成本/营养计算离谱。

**根因**：云模式 units seed 与本地 seed 的 **id 体系不同**——云（[main.py:64](../backend/app/main.py#L64)：米=1,千克=2,克=3,升=4...）vs 本地（千克=1,克=2,斤=3,升=4...）。云库 `unit_id=3`(克) 被本地直接保留解释为 id=3(斤)。而本地导入 [exportImport.ts uploadImport:375](../frontend/src/api/local/handlers/exportImport.ts#L375) **单菜谱格式分支漏传 `resolveLocalUnitId`**（数组分支 line 366 传了），导致 unit_id 不经名称重映射、直接保留 cloudId → 克(3)变斤(3)。recipe_ingredients 只存 unit_id 不存单位名，事后无法按名纠正。

**修复**：line 375 补传 `resolveLocalUnitId`，使云导出 ri 带的 `unit` 名称（serializers.py:196 `"unit": unit_name`）走名称匹配落到正确本地 id。

**尾巴**：存量错数据（unit_id 已错为 3）需**清空 `livecalc` IndexedDB 重新导入 ZIP** 才纠正（导入逻辑已修，重导会正确）。

## 5. 菜谱食材成本显示不出

**现象**：菜谱详情各食材成本列全是「-」。

**根因**：前端 [RecipeIngredientCard formatIngredientCost:447](../frontend/src/components/recipes/RecipeIngredientCard.vue#L447) 按 `recipe_ingredient_id` 匹配 `cost_breakdown`，但本地 [calculateCost](../frontend/src/api/local/business/costCalculator.ts) 的五个 `perIngredient.push` 分支**都没填 `recipe_ingredient_id`**，[getRecipeCost:203](../frontend/src/api/local/handlers/recipes.ts#L203) 的 cost_breakdown 映射也没透传 → 前端匹配全失败。注：`buildCostInput`/`batchCost` 构造 ingredients 时已带 `recipe_ingredient_id: ri.id`，calculateCost 里 `ing.recipe_ingredient_id` 拿得到。

**修复**：costCalculator.ts 五处 push 各补 `recipe_ingredient_id: ing.recipe_ingredient_id`；recipes.ts cost_breakdown 映射加 `recipe_ingredient_id: pi.recipe_ingredient_id`。

**验证**：娃娃菜 ¥1316、蒜 ¥29.80 等有值。

## 6. 相关菜谱全标「未发布」

**现象**：相关菜谱条目全带「未发布」chip，但菜谱实际 `is_public=true`。

**根因**：#3 修复时 getIngredientRecipes 返回字段漏了 `is_public`；模板 [IngredientDetail.vue:533](../frontend/src/views/ingredients/IngredientDetail.vue#L533) `v-if="!recipe.is_public"` → undefined → `!undefined`=true → 全标未发布。

**修复**：getIngredientRecipes 返回对象加 `is_public: rec.is_public ?? true`（见 #3）。

**验证**：「未发布」chip 消失。

## 7. 层级关系不显示

**现象**：原料详情「层级关系」空白（如五花肉该显示「属于猪肉」却没有）。

**根因**：云模式 `/ingredients/:id/hierarchy`（[ingredient_hierarchy.py:181](../backend/app/api/ingredient_hierarchy.py#L181) `HierarchyRelationsResponse`）返回 `{parent_relations, child_relations}`，每条含 `parent_name/child_name/relation_type/strength`；本地 [hierarchy.ts getHierarchy:5](../frontend/src/api/local/handlers/hierarchy.ts#L5) 返回 `{parents, children, relations:{as_parent, as_child}}`——字段名全不匹配，前端 [IngredientDetail loadHierarchy:3397](../frontend/src/views/ingredients/IngredientDetail.vue#L3397) 读 `parent_relations/child_relations` = undefined → 空。

**修复**：getHierarchy 对齐云模式格式——`asParent`(当前为父)→`child_relations`、`asChild`(当前为子)→`parent_relations`，批量查 ingredients 名补 `parent_name/child_name`，`relation_type`/`strength` 透传（兼容 `relationship_type`/`confidence` 旧名）。

**验证**：五花肉显示「所属关系：当前属于 猪肉（包含，强度 50%）」。

---

## 附：云模式「全量导出数据少」诊断（非 bug）

**现象**：用户反馈某次全量导出 ZIP 数据很少（merchants 0、price_records 0、hierarchy 0，且无 images/）。

**排查结论**：**导出代码没坏，也不是本次改动引入**（git 实锤本次只动 frontend local handler，后端零改动）。
- 用当前代码（d177bf4）+ 当前 SQLite 库复现 `build_export_zip('full')`，结果完整（merchants 8、price_records 2375、hierarchy 124、products 856）。
- [packaging.py:107](../backend/app/services/export/packaging.py#L107) full 模式 `_query` 不过滤全表导出；[reachability.py:53](../backend/app/services/export/reachability.py#L53) `collect_full_set` 设 `full_mode=True` 并填充全量 id 集；service 层 [__init__.py:7](../backend/app/services/export/__init__.py#L7) 正确透传 `scope`。
- 云库 merchants/hierarchy 的 `created_at` 都是 6 月，22:00 时早就在库里 → 排除「数据晚到」。
- 少的那个 ZIP（`products 615` 等）与当前 SQLite 库（`products 856`）快照不符 → **22:00 时后端连的是另一个较空的库**（`.env` 当时指向 PG/MySQL 的初始化库），之后切回 SQLite（数据完整）。

**图片 341 张未打包**：[_collect_image_files._handle:72](../backend/app/services/export/packaging.py#L72) 对 `http(s)://` 外链设计性跳过（旧时图存本地、现迁 OSS CDN）。非 bug，但用户要求全量导出该打包 → 另起特性「外链图打包导出」（见 [spec](../docs/superpowers/specs/2026-07-27-export-pack-remote-images-design.md) / [plan](../docs/superpowers/plans/2026-07-27-export-pack-remote-images.md)）。

---

**共性教训**：local handler 移植必须逐字段对照「云模式返回格式 + 前端消费字段名 + DB 存储字段名」三方契约，漏一个字段就是显示空白/错位；跨 id 体系（云 seed vs 本地 seed）不能直接保留 id，必须经名称重映射。数据库命名实测：local 用 `livecalc`（[database.ts:154](../frontend/src/api/local/database.ts#L154) `DB_NAME='livecalc'`），非设计文档写的 `livecalc_local`（后者是空壳遗物）。
