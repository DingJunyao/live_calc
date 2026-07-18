# 黑名单分组导入缺失修复

## 现象
个人中心「数据导出」产出的 zip 里**已包含**黑名单分组相关三表（`blacklist_groups.json` / `user_ingredient_blacklist.json` / `blacklist_group_subscriptions.json`），但在另一库「数据导入」后，黑名单分组定义、原料映射、个人黑名单、订阅**全都没回来**——数据「导出了却导不回」。

## 根因定位
三层证据（systematic-debugging，端到端实测而非看代码猜）：

1. **导出端完整且工作正常**——[packaging.py:314-385](backend/app/services/export/packaging.py#L314) 已有黑名单三表收集逻辑、manifest schema/counts 列了三表、[packaging.py:452-454](backend/app/services/export/packaging.py#L452) 写 zip；[serializers.py:437-470](backend/app/services/export/serializers.py#L437) 有三个序列化函数。实测 `build_export_zip(db, admin, 'full')` 产出 `blacklist_groups: 13`、errors 空、zip 含三个 json 文件。`BlacklistGroupSubscription.is_active` / `UserIngredientBlacklist.is_active` 看似可疑，实则继承自 [AuditMixin](backend/app/core/base_model.py#L17)，查询正常。

2. **确凿缺口在导入端**——[importer/importers/export.py](backend/app/services/importer/importers/export.py) 完全没有任何黑名单相关代码：`import_all` 调用链（units→…→price_records→images）无黑名单步骤、无 `_import_blacklist_*` 方法、`ReferenceMapping` 无 group 映射字段。导出包里的三个 json 被 `_load_json` 找不到对应消费方而默默忽略。

3. **附带诊断（非本次范围）**——当前开发库 `blacklist_group_ingredients` 表为空（13 个分组定义在、零原料映射）。源自 [allergen_seed.py](backend/app/services/allergen_seed.py) 的 `ingredient_names` 与库内实际原料名对不上，seed 时 `found_ids` 全空但仍建了空分组。属 seed 数据匹配问题，不是导出/导入代码 bug，本次不碰。

## 修复
单文件改动 [export.py](backend/app/services/importer/importers/export.py)，纯补导入端，导出端零动，无表结构变更：

1. **import 头部** 加 `BlacklistGroup` / `BlacklistGroupIngredient` / `BlacklistGroupSubscription` / `UserIngredientBlacklist` 四个模型。
2. **`ReferenceMapping`** 加 `blacklist_groups: dict[int, int]`（旧分组 id→新 id）。
3. **`import_all`** 在 `_import_price_records` 之后、`_import_images` 之前接入三步（各带 `cb` 阶段进度，复用本次会话已加的 progress_callback 范式）：`_import_blacklist_groups` → `_import_user_blacklist` → `_import_blacklist_subscriptions`。顺序保证分组定义先建、个人黑名单与订阅的 group_id 映射可用。
4. **三个方法 + 1 辅助**：
   - `_match_blacklist_group_by_name`：按 name 查 BlacklistGroup（**不过滤 is_active**，便于导入去重与复活）。
   - `_import_blacklist_groups`：分组是管理员维护的全局数据，**按 name 去重**——已存在只登记 `mapping.blacklist_groups[old]=new` 不重建（避免撞 `BlacklistGroup.name` 唯一约束）；新建按导入 `display_order`/`is_active`。原料映射按 `(group_id, ingredient_id)` 去重，`ingredient_id` 旧→新映射（`self.mapping.ingredients`），未命中按 `ingredient_name` 兜底（复用 `_match_ingredient_by_name`）。
   - `_import_user_blacklist`：绑当前导入用户，`(user_id, ingredient_id)` 去重，`blacklist_group_id` 映射。
   - `_import_blacklist_subscriptions`：绑当前导入用户，`(user_id, group_id)` 去重，`blacklist_group_id` 映射未命中时按 `blacklist_group_name` 兜底。

### 关键设计：统一「查含软删 → 复活 or 新建」范式
三张关系表（`BlacklistGroupIngredient` / `UserIngredientBlacklist` / `BlacklistGroupSubscription`）都有 unique 约束 + `is_active` 软删。导入时若只查 `is_active=True` 再新建，会和已软删行撞 unique 约束。故统一**先查不过滤 is_active**：存在则按需 `is_active=True` 复活（对齐 API [add_ingredients_to_group](backend/app/api/blacklist_groups.py#L146) 的处理），不存在才 add。一条范式贯穿三表，避免 unique 撞车且能完整恢复软删数据。

## 验证
- `py_compile` 通过。
- 临时 SQLite 库往返测试（跑完即删，不污染开发库），全断言通过：
  - 已存在分组按 name 映射不重建、新分组新建（stats `blacklist_groups=1`）。
  - 软删映射复活不计入新建、新映射新建、不存在原料跳过（stats `blacklist_group_ingredients=1`）。
  - 个人黑名单 2 条、分组归属正确（stats=2）。
  - 订阅 2 条，其中 id 未命中靠 name 兜底（stats=2）。
  - `mapping.blacklist_groups` 旧→新映射正确，软删行 `is_active` 复活为 True。

## 教训
- 「数据导出了却导不回」要分两端查：导出端代码「看着完整」不等于真产出，导入端「看着跑通」不等于真消费——必须端到端跑一遍看 json 内容 + 导入 stats。
- 软删 + unique 约束的表，导入去重必须「查含软删」，否则撞 unique。统一成一条范式比逐表特判省心。
