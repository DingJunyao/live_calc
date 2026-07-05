# 用户级默认单位配置 · 设计文档

**日期**：2026-07-05
**状态**：待实现
**作者**：brainstorming 会话产出

## 1. 概述

### 1.1 目标

在用户层面实现自定义默认单位。所有涉及单位展示/输入的地方，使用当前用户的默认单位偏好，取代此前散落在前后端各处写死的「斤」「kcal」等默认值。

### 1.2 背景

当前系统的默认单位全部硬编码：

- **价格记录 / 快速填写 / 粘贴导入**：默认「斤」，散落在 [ProductDetail.vue](../../../frontend/src/views/products/ProductDetail.vue)、[IngredientDetail.vue](../../../frontend/src/views/ingredients/IngredientDetail.vue)、[PricesView.vue](../../../frontend/src/views/prices/PricesView.vue)、[QuickFillView.vue](../../../frontend/src/views/prices/QuickFillView.vue)、[QuickPriceRecordDialog.vue](../../../frontend/src/components/prices/QuickPriceRecordDialog.vue)、[PricesView.vue](../../../frontend/src/views/prices/PricesView.vue)。
- **能量单位**：默认 `kcal`，写死在 `NUTRIENT_DEFINITIONS`——且 [ProductDetail.vue:1400](../../../frontend/src/views/products/ProductDetail.vue#L1400) 与 [IngredientDetail.vue:2152](../../../frontend/src/views/ingredients/IngredientDetail.vue#L2152) **各重复一份**。
- **原料实体**上有 `Ingredient.default_unit_id`（走审核框架、导入服务写死「斤」）；商品无自己的单位、靠原料的；`User` 表无任何单位偏好。

### 1.3 四类用户单位偏好

| 偏好 | 单位范围 | fallback |
|---|---|---|
| 能量单位 | `kcal` / `kJ` | `kcal` |
| 质量单位 | `g` / `kg` / `斤` / `两` / `磅` …（units 表 `unit_type='mass'`） | `斤` |
| 容积单位 | `mL` / `L` / `杯` / `汤匙` / `茶匙` …（units 表 `unit_type='volume'`） | `mL` |
| 价格记录单位 | 质量 + 容积 + 计数（`个` / `包` / `瓶` …）任意 | `斤` |

## 2. 决策摘要

| 维度 | 决定 |
|---|---|
| 三类→四类单位 | 分开：能量 / 质量 / 容积 / 价格记录（价格记录含计数单位） |
| 原料默认单位字段 | **彻底删除** `Ingredient.default_unit_id`（含外键 + index） |
| 质量单位用途 | 日常重量场景：价格趋势图表轴、半成品产出/商品规格质量类显示、菜谱原料质量类转换目标；**营养素各行保持自己习惯单位**（钙仍 mg） |
| 容积单位用途 | 与质量单位对称：体积类规格/产出量显示 + 菜谱原料体积类转换目标 |
| 能量单位用途 | 营养素能量行 + `daily_calorie_target` 输入框（跟随转换，库存 kcal 标准值） |
| 菜谱原料列表 | **点击才转换**：默认显原始写法，点击某行切换为用户单位，再点切回 |
| 存储 | `User` 表加 4 列 |
| 落地策略 | 一次到位 + 抽 composable + 合并 NUTRIENT_DEFINITIONS 重复（DRY） |

## 3. 数据模型变更

### 3.1 `User` 加 4 列

```
default_energy_unit     String(10), nullable       -- 'kcal' | 'kJ'
default_mass_unit_id    Integer, FK units.id, nullable
default_volume_unit_id  Integer, FK units.id, nullable
default_price_unit_id   Integer, FK units.id, nullable
```

存量用户 4 列保持 NULL，不回填，前端读到 NULL 时 fallback。

### 3.2 `Ingredient` 删字段

删除 `default_unit_id` 列（含外键约束 + index）。同步删除模型上的 `default_unit = relationship(...)` 关系。

存量 `ingredient.default_unit_id` 值随字段删除丢弃——这些值基本都是导入服务当年写死的「斤」id，丢弃无实质损失。

## 4. 数据库迁移

按项目规矩产出两类产物：

### 4.1 alembic 迁移

新增迁移文件：drop `ingredients.default_unit_id` + add `users` 4 列。

### 4.2 三引擎手动 SQL

- SQLite
- MySQL
- PostgreSQL（未启用 PostGIS）
- PostgreSQL（启用 PostGIS）—— 本变更与 PostGIS 无关，但仍按规范产出（与其它引擎等价）。

### 4.3 开发库直接补

⚠️ 本项目开发库（`backend/data/livecalc.db`）由 `Base.metadata.create_all()` 建表、**不走 alembic**（参见 [BUGFIX_共享转型表结构漂移](../../../cc/BUGFIX_共享转型表结构漂移.md) 教训）。`create_all` 只建新表、不 ALTER 老表。

因此迁移落地流程：

1. 备份开发库（`livecalc.db.bak_<timestamp>`）。
2. 直接对开发库执行 ALTER（drop column + add 4 columns）。SQLite 删列需表重建（交 alembic `batch_alter_table` 离线执行，不依赖 `alembic_version`）。
3. 完善 `backend/scripts/sql/` 下的 SQL 脚本为可直接手动执行版本（不依赖 alembic），覆盖三引擎。
4. ORM 层验证 SELECT/INSERT/属性访问全通。

## 5. 后端 API 变更

### 5.1 `GET /auth/me`

`UserResponse` 增 `unit_preferences` 字段。后端 join `units` 表解析名字，前端免再查：

```json
"unit_preferences": {
  "energy_unit": "kcal",
  "mass_unit":    { "id": 5, "name": "斤",   "abbreviation": "斤" },
  "volume_unit":  { "id": 8, "name": "毫升", "abbreviation": "mL" },
  "price_unit":   { "id": 5, "name": "斤",   "abbreviation": "斤" }
}
```

NULL 字段对应子对象为 `null`，前端自行 fallback。

### 5.2 `PATCH /auth/me`

`UserProfileUpdate` 加 4 个 Optional 字段：

```python
default_energy_unit: Optional[str] = None        # 校验 ∈ {'kcal','kJ'}
default_mass_unit_id: Optional[int] = None        # 校验存在 + unit_type='mass'
default_volume_unit_id: Optional[int] = None      # 校验存在 + unit_type='volume'
default_price_unit_id: Optional[int] = None       # 校验存在 + unit_type ∈ {'mass','volume','count'}
```

校验失败返回 400。支持传 `null` 清除偏好。

### 5.3 `create_ingredient` 与导入服务

- [ingredient_extended.py](../../../backend/app/api/ingredient_extended.py)：删除 `_get_default_mass_unit_id()` 辅助函数及其在 `create_ingredient` 的调用。
- [nutrition.py](../../../backend/app/api/nutrition.py)：`create_ingredient` 不再设 `default_unit_id`，返回体移除 `default_unit_id` / `default_unit_name`。
- 导入服务 [enhanced_recipe_import_service.py](../../../backend/app/services/enhanced_recipe_import_service.py)、[json_recipe_import_service.py](../../../backend/app/services/json_recipe_import_service.py)、[recipe_import_service.py](../../../backend/app/services/recipe_import_service.py)、[importer/howtocook.py](../../../backend/app/services/importer/importers/howtocook.py)：不再写入 `default_unit_id`。

### 5.4 审核框架

`IngredientExecutor`（[executors/](../../../backend/app/services/proposals/executors/)）的 snapshot/apply/payload 不再处理 `default_unit_id` 字段。

相关 schema（ingredients/nutrition 相关）删除 `default_unit_id` / `default_unit_name` 字段。

### 5.5 单位选项端点

设置 UI 复用现有 `GET /units/`，前端按 `unit_type` 筛 mass / volume / mass+volume+count。少改后端。

### 5.6 单位换算端点（菜谱原料点击转换复用）

已存在 `POST /units/convert`（[units.py:347](../../../backend/app/api/units.py#L347)），底层 `UnitConversionService.convert` 支持同类（mass↔mass、volume↔volume，按 `si_factor`）与跨类（mass↔volume，走原料密度）转换。菜谱原料点击转换直接复用，无需新端点。

## 6. 前端：单位工具 composable

新建 `frontend/src/composables/useUserUnits.ts`：

```ts
export function useUserUnits() {
  // 从 userStore 读 unit_preferences，NULL 时 fallback
  const energyUnit = computed(() => user.value?.unit_preferences?.energy_unit ?? 'kcal')
  const massUnit   = computed(() => user.value?.unit_preferences?.mass_unit   ?? FALLBACK_MASS)   // 斤
  const volumeUnit = computed(() => user.value?.unit_preferences?.volume_unit ?? FALLBACK_VOLUME) // mL
  const priceUnit  = computed(() => user.value?.unit_preferences?.price_unit  ?? FALLBACK_PRICE)  // 斤

  const massUnitName   = computed(() => massUnit.value?.name   ?? '斤')
  const volumeUnitName = computed(() => volumeUnit.value?.name ?? 'mL')
  const priceUnitName  = computed(() => priceUnit.value?.name  ?? '斤')

  // calorie 转换：库存 kcal，前端按 energyUnit 显示/输入
  const toDisplayCalorie   = (kcal: number) => energyUnit.value === 'kJ' ? kcal * 4.184 : kcal
  const fromDisplayCalorie = (v: number)   => energyUnit.value === 'kJ' ? v / 4.184 : v

  return { energyUnit, massUnit, volumeUnit, priceUnit,
           massUnitName, volumeUnitName, priceUnitName,
           toDisplayCalorie, fromDisplayCalorie }
}
```

## 7. 前端：个人中心设置 UI

[ProfileView.vue](../../../frontend/src/views/profile/ProfileView.vue) 设置列表新增「单位偏好」入口，打开对话框：

- **能量单位**：`v-select`，选项 `kcal` / `kJ`。
- **质量单位 / 容积单位 / 价格记录单位**：`v-autocomplete`，复用 `GET /units/`，按 `unit_type` 筛：
  - 质量：`mass`
  - 容积：`volume`
  - 价格记录：`mass` + `volume` + `count`
- 保存按钮 → `PATCH /auth/me` → `userStore.fetchUser()` 刷新。

## 8. 前端：daily_calorie_target 转换

[ProfileView.vue](../../../frontend/src/views/profile/ProfileView.vue) 饮食偏好对话框的「每日热量」输入框：

- 标签按 `energyUnit` 显示（`每日热量 (kcal)` 或 `每日热量 (kJ)`）。
- 打开对话框时：`form.daily_calorie_target = toDisplayCalorie(库存 kcal 值)`。
- 保存时：`PATCH` 提交 `fromDisplayCalorie(form.daily_calorie_target)` → 后端存 kcal。
- 后端 `daily_calorie_target` 字段语义不变（仍 kcal）。

## 9. 前端：接入点清单（写死「斤」/kcal 全量替换）

### 9.1 记价默认单位 → `priceUnitName`

| 文件 | 位置 | 现状 |
|---|---|---|
| ProductDetail.vue | `priceForm.unit`(1557,1571,1583,2686) | `'斤'` |
| IngredientDetail.vue | `priceForm.unit`(2099) | `'斤'` |
| PricesView.vue | `original_unit`(706) | `'斤'` |
| QuickFillView.vue | `unit`(436,457)、fallback 选项(392) | `'斤'` |
| QuickPriceRecordDialog.vue | `original_unit`(155)、`props.defaultUnit \|\| '斤'`(250) | `'斤'` |
| PasteImportDialog.vue | 解析时若文本无单位 | 用 `priceUnitName` 兜底 |

### 9.2 价格趋势图表 → `massUnitName`

- [ProductDetail.vue:2096](../../../frontend/src/views/products/ProductDetail.vue#L2096) `chartUnit = '斤'` → `massUnitName`；同步后端聚合的 `standard_unit` 折算目标对齐（避免「标 kg 实际折算到斤」）。
- [IngredientDetail.vue](../../../frontend/src/views/ingredients/IngredientDetail.vue) 价格趋势单位 → `massUnitName`。
- [PriceTrendChart.vue](../../../frontend/src/components/charts/PriceTrendChart.vue) 本身不改（`unit` 是 prop，由父组件传入）。

### 9.3 能量行 + NUTRIENT_DEFINITIONS 合并（DRY）→ `energyUnit`

详见 §11。

### 9.4 菜谱原料点击转换 → `massUnit` / `volumeUnit`

详见 §10。

### 9.5 半成品产出 / 商品规格显示 → `massUnit` / `volumeUnit`

`serving_weight`（半成品菜谱产出重量）等质量/体积字段的显示接入用户对应单位。**实现时用 `grep -n serving_weight` 定位全部显示点**（预期涉及原料详情/菜谱详情的产出量展示），逐一替换，避免遗漏。

## 10. 菜谱原料点击转换

[RecipeIngredientCard.vue](../../../frontend/src/components/recipes/RecipeIngredientCard.vue) 查看模式（line 100-113）改造：

**交互状态机（每行独立）：**

- 默认：显示原始写法（`ingredient.quantity + ingredient.unit`，与现状一致）。
- 点击行的数量区域 → 切换为用户单位显示：
  - 原料单位是质量类 → 转成 `massUnit`
  - 原料单位是体积类 → 转成 `volumeUnit`
  - 转换调用 `POST /units/convert`（跨类走原料密度），结果按 `(ingredient_id, fromUnit, toUnit)` session 缓存。
- 再点 → 切回原始。
- 「适量 / 少许 / 无法跨类（无密度）」→ 禁用切换并 tooltip 提示「该单位无法转换」。

**转换失败的优雅降级**：保持原始写法，不报错。

**移动端**：就地切换 + 小 chip 标识当前显示模式，不开新框。

## 11. NUTRIENT_DEFINITIONS 合并（DRY）

当前 [ProductDetail.vue:1399](../../../frontend/src/views/products/ProductDetail.vue#L1399) 与 [IngredientDetail.vue:2151](../../../frontend/src/views/ingredients/IngredientDetail.vue#L2151) 各有一份完全重复的 `NUTRIENT_DEFINITIONS`（30 行营养素定义）。

**合并方案**：

1. 抽离到 `frontend/src/composables/nutrientDefinitions.ts`（或 `constants/nutrientDefinitions.ts`）。
2. 导出 `buildNutrientDefinitions(energyUnit: string)` 函数：能量行的 `defaultUnit` 参数化为传入的 `energyUnit`，其它行保持各自习惯单位。
3. 两详情页改为 `import { buildNutrientDefinitions }` + `const NUTRIENT_DEFINITIONS = buildNutrientDefinitions(energyUnit)`。
4. 同步 [ProductDetail.vue:1469](../../../frontend/src/views/products/ProductDetail.vue#L1469) `getDefaultNutrientDef` 的能量默认单位。
5. [RecipeDetail.vue:599](../../../frontend/src/views/recipes/RecipeDetail.vue#L599) `coreNutritionItems` 的能量 `unit: 'kcal'` 也读 `energyUnit`。

**防回归**：合并后保证两详情页营养素编辑/显示行为与现状一致（除能量行跟随用户单位外）。

## 12. 不在范围内

- **密度单位**（`g/cm³` / `kg/m³`）：独立的密度单位制，保持现状切换，不接入用户质量/容积单位。
- **营养素各行习惯单位**（蛋白质 g、钙 mg、硒 μg…）：保持各自 `defaultUnit`，仅能量行跟随用户能量单位。
- **成本金额单位**（¥/元）：成本趋势是金额，非重量，不在本次范围。
- **后端 `daily_calorie_target` 存储**：语义仍 kcal，仅前端按能量单位显示/输入转换。

## 13. 测试策略

### 13.1 后端

- `test_auth_me`：GET 返回 `unit_preferences`（含 NULL fallback）；PATCH 4 字段写入 + 类型校验（mass_unit_id 传 volume 单位 id 应 400）+ 传 null 清除。
- `test_create_ingredient`：不再写 `default_unit_id`（字段已不存在）。
- `test_ingredient_executor`：snapshot/apply 不因缺失 `default_unit_id` 崩溃。
- 导入器测试：创建原料不再写 `default_unit_id`。

### 13.2 前端

- `useUserUnits`：fallback 正确（用户未设置时）；`toDisplayCalorie` / `fromDisplayCalorie` 双向转换正确（kcal↔kJ，因子 4.184）。
- NUTRIENT_DEFINITIONS 合并后两详情页行为不回归（能量行跟随 energyUnit，其它行不变）。

### 13.3 静态校验

- 后端 `py_compile` 全通过。
- 前端 `npm run build` 通过。
- grep `default_unit` / `'斤'` / `defaultUnit: 'kcal'` 全量扫尾，确认无遗漏写死点。

## 14. 风险与对策

| 风险 | 对策 |
|---|---|
| `Ingredient.default_unit_id` 删除波及面广（审核 / 导入 / schema / 前端） | 用 §9 清单 + grep 全量扫尾，逐点核防漏 |
| 单位转换精度（kcal↔kJ、mass↔mass、跨类密度） | 同类前端用 `si_factor`，跨类走后端 `UnitConversionService`（成熟） |
| 价格趋势图标签改 `massUnit` 但折算仍到「斤」 | 后端聚合的 `standard_unit` 折算目标与显示标签同步对齐 |
| NUTRIENT_DEFINITIONS 合并引入回归 | 抽公共函数 + 两处共用，测试覆盖营养素编辑流程 |
| 菜谱原料点击转换移动端空间局促 | 就地切换 + chip 标识，不开新框 |
| 开发库不走 alembic 致迁移漏 ALTER | 备份后直接补开发库 + SQL 脚本可独立执行（参既有教训） |

## 15. 落地顺序建议（供 writing-plans 参考）

1. 后端：模型 + 迁移 + alembic + 三引擎 SQL + 开发库补全。
2. 后端：`/auth/me` GET/PATCH + schema + create_ingredient/导入服务/审核框架去 `default_unit_id`。
3. 后端测试。
4. 前端：`useUserUnits` composable + `nutrientDefinitions.ts` 抽离。
5. 前端：个人中心设置 UI + `daily_calorie_target` 转换。
6. 前端：接入点清单逐项替换（记价默认 / 图表 / 能量行 / 菜谱原料点击转换 / 产出量显示）。
7. 全量 grep 扫尾 + build + 静态校验。
