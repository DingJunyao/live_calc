# 用户级默认单位配置

**日期**：2026-07-05
**分支**：`feat/user-default-units`
**计划**：[docs/superpowers/plans/2026-07-05-user-default-units.md](../docs/superpowers/plans/2026-07-05-user-default-units.md)
**设计**：[docs/superpowers/specs/2026-07-05-user-default-units-design.md](../docs/superpowers/specs/2026-07-05-user-default-units-design.md)

## 目标

在用户层面实现自定义默认单位（能量 / 质量 / 容积 / 价格记录四类偏好），替换前后端所有写死的「斤」/「kcal」默认值，并彻底删除 `Ingredient.default_unit_id` 字段。

## 后端

### 数据模型
- `User` 加 4 列：`default_energy_unit`（'kcal'|'kJ'）、`default_mass_unit_id`、`default_volume_unit_id`、`default_price_unit_id`（均 FK units.id，nullable，存量 NULL 由前端 fallback）。
- `Ingredient` 删 `default_unit_id` 列 + `default_unit` 关系。
- alembic 迁移 [20260705_0001](../backend/alembic/versions/20260705_0001_user_units_and_drop_ingredient_default_unit.py)（users 加列 + ingredients batch_alter drop column）。
- 三引擎 SQL（[sqlite 表重建](../backend/scripts/sql/20260705_user_units_sqlite.sql) / mysql / postgres / postgres_postgis），列结构按开发库实际 `.schema` 抄录。
- 开发库（create_all 建表、不走 alembic）备份后直接补（`livecalc.db.bak_20260705_222907`）。

### API
- `GET /auth/me` 返回 `unit_preferences`（后端 join units 解析单位名，前端免再查）。
- `PATCH /auth/me` 接收 4 字段 + 类型校验（mass/volume/price 必须单位类型匹配，energy ∈ {kcal,kJ}，支持 null 清除）。
- 新增 [test_user_unit_preferences.py](../backend/tests/test_user_unit_preferences.py) 5 例（NULL fallback / 设置 / 类型拒 / 能量拒 / null 清除）。

### 附带修复：PATCH /me detached user 写入失效 bug
`resolve_user_from_token`（[security.py:119](../backend/app/core/security.py#L119)）用独立 `SessionLocal()` 且 `finally: db.close()`，返回的 user 是 **detached**。原 `patch_me` 的 `setattr(current_user) + db.commit()` 不写库（detached 不在 session）、`db.refresh` 抛 `InvalidRequestError`。test_auth 从没测 PATCH /me 的 commit 路径，潜伏。改为在本请求 db 内 `db.query(User).filter(id=current_user.id).first()` 重新加载再写。该 bug 致此前 nutrition_goals/budget 的 PATCH 修改未真正持久化——本次一并修复。

### 清理 Ingredient.default_unit_id 全部下游（计划清单 + grep 补全）
计划列的 + grep 发现的遗漏一并清理：
- [ingredient_extended.py](../backend/app/api/ingredient_extended.py)：17 处（joinedload/返回键/create+update 签名/删 `_get_default_mass_unit_id`）。
- [nutrition.py](../backend/app/api/nutrition.py)：list/get/create/update ingredient（影子路由）+ 3 处运行时价格折算。
- 4 个导入服务（recipe/json/enhanced/howtocook）：不再写 `default_unit_id`。
- **计划遗漏、grep 补全**：
  - [recipes.py:848](../backend/app/api/recipes.py#L848) / [products_entity.py:309,688](../backend/app/api/products_entity.py#L309)：成本/价格折算 `if ingredient.default_unit` 分支删除，统一走既有「回退斤」逻辑。
  - [merchants.py](../backend/app/api/merchants.py)：SQL 删 `du` JOIN + 列，删「优先 default_unit 折算」块，回落「元/斤、元/L」。
  - [export/serializers.py:89](../backend/app/services/export/serializers.py#L89)：`default_unit_id` 留键设 None（HowToCook 格式对称）。
  - [export/reachability.py:110](../backend/app/services/export/reachability.py#L110)：单位收集元组去掉 `ing.default_unit_id`。
  - [product_split.py](../backend/app/services/proposals/executors/product_split.py)：删「取斤单位」死代码 + 参数。

### 验证
- compileall 通过；executor/提议/e2e/单位偏好 80 passed（2 基线无关失败：merchant 级联 + merge 消息格式）。
- 全量 22 failed/455 passed，失败均为基线既有的 auth/locations/nutrition(401)/USDA/AI 等无关模块，无 default_unit 引起的 500。

## 前端

### 新建 composable
- [useUserUnits.ts](../frontend/src/composables/useUserUnits.ts)：集中读用户单位偏好（NULL fallback 斤/mL/kcal），含 `toDisplayCalorie`/`fromDisplayCalorie`（kcal↔kJ ×4.184）。
- [nutrientDefinitions.ts](../frontend/src/composables/nutrientDefinitions.ts)：`buildNutrientDefinitions(energyUnit)` 参数化能量行 defaultUnit，消除 ProductDetail/IngredientDetail 两份完全重复的 30 项营养素定义（DRY）。

### 个人中心（ProfileView）
- 「单位偏好」入口 + 对话框（能量 v-select；质量/容积/记价 v-autocomplete 复用 `GET /units/` 按 unit_type 筛），PATCH /auth/me 保存。
- 「每日热量」输入框标签/min/max 跟随 energyUnit；open 用 toDisplayCalorie、save 用 fromDisplayCalorie（库存语义仍 kcal）。

### 接入点替换
- **记价默认 → priceUnitName**（8 文件）：ProductDetail/IngredientDetail（priceForm.unit、record.original_unit 兜底；删 currentIngredientDefaultUnit，overlaidDefaultUnitName 改 priceUnitName）、PricesView/QuickFillView/QuickPriceRecordDialog/PriceRecordForm（form.unit/original_unit）、PasteImportDialog（pastePriceParser 参数化 defaultUnit，调用方传 priceUnitName）。
- **价格趋势图表 → massUnitName**：ProductDetail chartUnit、IngredientDetail chartUnit。
- **能量行 → energyUnit**：ProductDetail/IngredientDetail/RecipeDetail 的 NUTRIENT_DEFINITIONS（computed buildNutrientDefinitions）+ 三处 coreNutritionItems（computed，能量 unit 读 energyUnit）。⚠️ 计划 Task 14 只提 RecipeDetail 的 coreNutritionItems，ProductDetail/IngredientDetail 的同名配置是 Task 21 扫尾 grep `unit: 'kcal'` 补出。
- **菜谱原料点击转换**（[RecipeIngredientCard.vue](../frontend/src/components/recipes/RecipeIngredientCard.vue)）：数量行 @click=toggleConvert，调 `POST /units/convert`（from_unit/to_unit 缩写）转用户 massUnit/volumeUnit（跨类走原料密度），双态显示 + 适量/无单位行禁用 + 结果按 displayServings 缩放。

### serving_weight（Task 20）
核查后**无需改动**：serving_weight 在 IngredientDetail 是编辑表单（用户自选 `serving_weight_unit_id`），显示用后端返回的 `serving_weight_unit_name`，无硬编码单位。ProposalsView 的 `份重(g)` 是审核台固定标签。RecipeDetail 不涉及 serving_weight 字段。

### 保留不改
`FALLBACK_UNITS` 兜底数组、单位下拉枚举（unitOptions 含「斤」作为选项）、单位换算表 key（如 `'斤': 500`）、`abbreviation === '斤'` 查找逻辑、pastePriceParser 默认参数 '斤'——这些都是兜底/枚举/查找语义，保留「斤」合理。

## 踩坑记录

1. **PATCH /me detached user bug**：见上「附带修复」。测试暴露的真 bug，此前 nutrition_goals 修改一直没生效。
2. **Unit import 误删**：Task 9 清理 ingredient_extended.py 时，误判 `Unit` 仅用于已删的 `_get_default_mass_unit_id`，删了 `from app.models.unit import Unit`——实际 `/units` 端点（get_units）也用 Unit。grep 确认后恢复。教训：删 import 前 grep 该 symbol 全部用法。
3. **计划清单遗漏**（两次）：
   - Phase C：default_unit 下游引用远不止 ingredient_extended + nutrition（还有 recipes/products_entity/merchants/export/product_split），靠 grep 全量扫尾补全。
   - Phase F：coreNutritionItems 在 ProductDetail/IngredientDetail 也有（计划只提 RecipeDetail），靠 grep `unit: 'kcal'` 补出。
4. **subagent 模型不可用**：Phase F 原计划派 4 个 subagent 并行处理前端接入，全因「模型不存在」API 错误失败，改手工完成。
5. **开发库有两个 .venv**：根目录（正确，CLAUDE.md 指定）+ backend/.venv（历史遗留），计划写的 `backend/.venv/Scripts/python.exe` 路径会撞空，统一用根 `.venv`。
6. **nutrition.py.bak2 被 git 跟踪**：仓库里的残留备份文件，Task 21 一并 git rm 清理。

## 落地顺序

1. Phase A 后端数据层（模型 + 迁移 + SQL + 开发库）
2. Phase B 后端 API（/auth/me + 测试 + 顺手修 detached user bug）
3. Phase C 后端清理 default_unit 全下游
4. Phase D 前端基础（useUserUnits + nutrientDefinitions DRY）
5. Phase E 前端个人中心（设置 UI + calorie 转换）
6. Phase F 前端接入点（记价 + 图表 + 菜谱转换）
7. Phase G 扫尾（grep + build + coreNutritionItems 补 + 记录要点）

7 个 Phase 分阶段提交（用户偏好），共 8 commit（A/B/C/D/E/F/G + G 扫尾）。
