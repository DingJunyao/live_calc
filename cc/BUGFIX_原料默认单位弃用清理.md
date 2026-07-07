# 原料详情页「默认单位」弃用清理

**日期**：2026-07-07
**相关**：[FEATURE_用户级默认单位配置.md](FEATURE_用户级默认单位配置.md)（扫尾遗漏）
**文件**：[IngredientDetail.vue](../frontend/src/views/ingredients/IngredientDetail.vue) 单文件，无表结构变更

## 现象

用户反馈 `/data/ingredients/142` 的「默认单位」显示「个」，但「我明明设置了斤」；并要求针对原料的默认单位彻底弃用。

## 根因（三层语义错位）

数据库 + 代码取证（systematic-debugging 全流程）：

1. **展示行语义错位**：[IngredientDetail.vue:61-67](../frontend/src/views/ingredients/IngredientDetail.vue#L61) 基本信息展示行标签是「默认单位」，但绑的是 `overlaidDefaultUnitName`，该 computed 在 [:1953] 定义为 `priceUnitName`——即**用户级价格单位偏好**（非原料属性）。当前登录用户 `billding`（user 1）`default_price_unit_id = 18`，而 unit 18 = 「个」（count 类型）→ 显示「个」。用户在个人中心设的就是价格单位「个」，与原料无关。
2. **编辑字段是死字段**：[:130-140] 编辑表单还有 `basicEditForm.default_unit_id`，打开时 `ingredient.default_unit_id`（后端早不返回，恒 undefined）`|| jinUnitId` 永远回退「斤」；保存 payload 带 `default_unit_id`，但后端 [ingredient_extended.py](../backend/app/api/ingredient_extended.py) grep `default_unit` **零匹配**（不返回、不接收）→ 静默忽略。用户在编辑表单「设置斤」保存了个寂寞。
3. **后端早已废弃**：`ingredients` 表 PRAGMA 确认**无** `default_unit_id` 列（2026-07-05 FEATURE 删除）。前端基本信息区当时漏收拾。

标签「默认单位」+ 数据源「价格偏好」+ 编辑入口「通向虚空」，三层全错位 → 用户困惑。

## 修复

按用户「原料默认单位需要弃用」要求，清理 IngredientDetail.vue 全部残留（模板 + 脚本）：

- **模板**：
  - 删展示行 `<v-list-item> 默认单位 {{ overlaidDefaultUnitName }}`（基本信息区首项）。
  - 删编辑表单 `<v-autocomplete label="默认单位" v-model="basicEditForm.default_unit_id">`。
  - 价格显示两处 `{{ overlaidDefaultUnitName || '斤' }}` → `{{ priceUnitName }}`（[:233]/[:315]，`¥X/单位`；priceUnitName 在 [useUserUnits](../frontend/src/composables/useUserUnits.ts) 已含 fallback「斤」，去掉冗余 `|| '斤'`）。
- **脚本**：
  - 删 `Ingredient` 接口的 `default_unit_id?` / `default_unit_name?`（[:1795-1796]）。
  - 删 `overlaidDefaultUnitName` computed（[:1953]，就是 priceUnitName 别名，历史遗留）+ 其上方两行迁移注释，更新 TDZ 注释措辞。
  - 删 `basicEditForm.default_unit_id` 字段（[:2231]）、`startEditBasicInfo` 初始化（[:3799]）、`saveBasicInfo` payload（[:3829]）。
  - 删 `jinUnitId` 死代码（[:2186] 定义 + [:3775-3779] `loadUnits` 找斤赋值）——其唯一用途是给死字段兜底。
  - 更新 [:2266] TDZ 注释去掉 overlaidDefaultUnitName 提及。

## 验证

- 静态：grep `default_unit|overlaidDefaultUnit|jinUnitId` 在该文件 **零匹配**（ProposalsView.vue:1073 的 `default_unit_id:'unit'` 是审核台 entity_type 标签映射，无关，不动）。
- 构建：`npm run build` 通过（51.59s，IngredientDetail chunk 91.45 kB）。
- 浏览器待验：刷新 `/data/ingredients/142`，基本信息区不再有「默认单位」行；编辑表单不再有该字段；价格「¥X/单位」仍按用户价格偏好显示。

## 备注

- 原料级默认单位概念自 [FEATURE_用户级默认单位配置](FEATURE_用户级默认单位配置.md) 起已迁移到用户级偏好（质量/容积/记价/能量四类），原料不应再有「默认单位」属性。本次只是补齐前端遗漏的清理。
- 用户若想让某处显示「斤」而非「个」，应去个人中心改「价格单位」偏好（当前 = 个），而非原料详情页。
