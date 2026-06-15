# 数据导出功能设计

> 个人中心「数据导出」功能的规格说明。菜谱/食材/营养/单位参考 `D:\code\HowToCook_json\out` 格式（HowToCook 兼容），其余数据制定独立规格，全部打包为 zip。

## 1. 概述

个人中心的「数据导出」菜单项目前无功能（[ProfileView.vue](../../../frontend/src/views/profile/ProfileView.vue) 仅有占位 `<v-list-item>`，无 `@click`）。本设计为其补全完整实现：后端新增导出端点，把当前用户可见的数据序列化为标准 JSON、连同图片打包成 zip，流式下载。

核心约束：
- 菜谱、食材、营养、单位四类**兼容 HowToCook 格式**，使现有导入服务（`enhanced_recipe_import_service`）能直接读取。
- 同时**扩展 id 与关联字段**，为将来的「数据恢复导入」留好无损还原的口子。
- 导出文件打包为单个 zip。

## 2. 目标与非目标

### 目标
- 个人中心点击导出，可选「全量」或「仅我的」两档，下载 zip。
- 菜谱/食材/营养/单位严格兼容 HowToCook 字段命名与结构。
- 全局库（食材/营养/单位/商品等）与账户私有数据（菜谱/价格记录/商家）均导出。
- 图片（菜谱图、商品本地图）打包进 zip，json 内用相对路径引用。
- 「仅我的」模式保证引用完整性：我引用到的管理员数据一并导出。
- 格式带 id 与关联冗余，为将来导入留余地。

### 非目标（YAGNI，本期不做）
- **导入功能**：本期只做导出。格式按可导入标准设计，但不实现、不测试导入。
- **账户设置数据导出**：地图配置、用户食材偏好、区域单位设置、实体单位覆盖——本期不导出。
- **派生/审计数据导出**：菜谱成本历史、AI 匹配记录、营养编辑历史、操作日志——本期不导出（可重建/审计性质）。
- 异步任务、下载链接管理、过期清理——同步流式即可，不引入任务队列。
- 废弃的 `IngredientDensity`（ingredient_densities 表）不导出。

## 3. 导出范围与归属

### 3.1 两档导出（scope）

端点接收 `scope` 查询参数：

| scope | 含义 | 账户私有数据（有 user_id） | 全局库（无 user_id，有 created_by） |
|-------|------|---------------------------|-------------------------------------|
| `full` | 全量 | 所有用户的数据 | 全部（不限创建者） |
| `mine` | 仅我的 | `user_id = 当前用户` | `created_by = 当前用户` 创建的，**+ 关联保证**（见 3.3） |

默认 `full`。

### 3.2 创建者判定依据
- 管理员：`User.is_admin = True`。
- 有 `user_id` 的表（Recipe / ProductRecord / Merchant / FavoriteMerchant）：按 `user_id` 判定归属。
- 无 `user_id` 但继承 `AuditMixin` 的表（Ingredient / NutritionData / Unit / UnitConversion / Product / ProductBarcode / ProductIngredientLink / IngredientCategory / IngredientHierarchy）：按 `created_by` 判定创建者。
- `EntityDensity` 不继承 AuditMixin、无创建者字段：在 `mine` 模式下按可达性过滤（见 3.3）。

### 3.3 「仅我的」关联保证（可达性遍历）

`mine` 模式不能只导「我创建的」，否则导入后引用会悬空。规则：**从我（或我的数据）出发，顺着外键可达的所有关联实体，无论创建者是谁，一律纳入导出集。**

遍历起点与边：

```
我的菜谱 Recipe (user_id=我)
  ├─ RecipeIngredient.ingredient_id → Ingredient
  │    ├─ Ingredient.nutrition_id → NutritionData
  │    ├─ Ingredient.category_id → IngredientCategory
  │    ├─ Ingredient.default_unit_id / piece_weight_unit_id / serving_weight_unit_id → Unit
  │    ├─ Ingredient.id ← IngredientDensity.ingredient_id（废弃表，跳过）
  │    ├─ Ingredient.id ← EntityDensity(entity_type='ingredient')
  │    └─ IngredientHierarchy: parent_id/child_id 任一为该食材 → 对端 Ingredient（双向）
  ├─ RecipeIngredient.unit_id → Unit
  └─ Recipe.result_ingredient_id → Ingredient（成品关联，同上链）

我的价格记录 ProductRecord (user_id=我)
  ├─ ProductRecord.product_id → Product
  │    ├─ Product.ingredient_id → Ingredient（同上链）
  │    ├─ ProductBarcode.product_id
  │    └─ ProductIngredientLink.product_id → Ingredient
  ├─ ProductRecord.original_unit_id / standard_unit_id → Unit
  └─ ProductRecord.merchant_id → Merchant

我创建的商相关联
  └─ FavoriteMerchant（user_id=我）无下游依赖，叶子节点
```

实现为集合扩张：先装入「我的」直接数据，再迭代收集所有可达的 Ingredient / NutritionData / Unit / IngredientCategory / EntityDensity / Product / ProductBarcode / ProductIngredientLink / IngredientHierarchy 边，直到集合不再增长（不动点）。`Unit` 通过 `UnitConversion` 的 from/to 暴露的换算关系也一并带上相关 Unit。

> 注：IngredientHierarchy 双向遍历可能扩散较广（替代/回退链）。若扩散过深影响体积，可设最大跳数兜底（默认不设，保证完整性优先），并在 manifest 记录层级覆盖情况。

### 3.4 导出范围汇总

| 文件 | full 模式 | mine 模式 |
|------|-----------|-----------|
| `recipes/*.json` | 所有菜谱 | 我的菜谱（user_id=我） |
| `ingredients.json` | 全部食材 | 我创建的 + 可达食材 |
| `nutritions.json` | 全部营养 | 可达食材的营养 |
| `units.json` | 全部单位 | 我创建的 + 可达单位 |
| `unit_conversions.json` | 全部 | 端点单位在导出集内的换算 |
| `ingredient_categories.json` | 全部分类 | 可达分类 |
| `ingredient_hierarchy.json` | 全部层级 | 端点食材在导出集内的层级 |
| `entity_densities.json` | 全部 | 实体在导出集内的密度 |
| `products.json` | 全部商品 | 我创建的 + 可达商品（价格记录引用） |
| `product_barcodes.json` | 全部 | 导出集内商品的条码 |
| `product_ingredient_links.json` | 全部 | 导出集内商品的关联 |
| `price_records.json` | 所有记录 | 我的记录（user_id=我） |
| `merchants.json` | 所有商家 | 我的商家 + 价格记录引用的商家 |
| `favorite_merchants.json` | 所有收藏 | 我的收藏（user_id=我） |

## 4. 架构与端点

### 4.1 新增文件
- [backend/app/api/export.py](../../../backend/app/api/export.py) — 路由层，挂在 `/api/v1/export`。
- [backend/app/services/data_export_service.py](../../../backend/app/services/data_export_service.py) — 业务逻辑：查询、可达性遍历、序列化、打包。
- 在 [backend/app/main.py](../../../backend/app/main.py) 注册 `app.include_router(export.router, prefix="/api/v1/export", tags=["数据导出"])`。

### 4.2 端点
```
GET /api/v1/export/data?scope=full|mine
```
- 鉴权：JWT（复用现有 `get_current_user` 依赖）。
- 响应：`StreamingResponse`，`media_type="application/zip"`，`Content-Disposition: attachment; filename="export_YYYYMMDD_HHmmss.zip"`。
- 文件名时间戳由服务端生成（注意：服务端可用 `datetime.now()`，不受工作流脚本限制）。

### 4.3 前端
- [ProfileView.vue](../../../frontend/src/views/profile/ProfileView.vue)「数据导出」项加 `@click`，弹出选择对话框（全量 / 仅我的）。
- 确认后调用导出 API，`responseType: 'blob'`，触发浏览器下载，文件名取响应头 `Content-Disposition`。
- 下载期间显示 loading（数据量较大时耗时数秒到数十秒）。
- 可在 [frontend/src/api/](../../../frontend/src/api/) 下新增导出相关调用封装。

## 5. zip 结构

```
export_YYYYMMDD_HHmmss.zip
├── manifest.json                  # 导出清单
├── recipes/                       # 菜谱（每菜一文件，HowToCook 风格）
│   └── {菜名}.json
├── ingredients.json               # 食材（dict 聚合）
├── nutritions.json                # 营养（数组）
├── units.json                     # 单位（数组）
├── unit_conversions.json
├── ingredient_categories.json
├── ingredient_hierarchy.json
├── entity_densities.json
├── products.json
├── product_barcodes.json
├── product_ingredient_links.json
├── price_records.json
├── merchants.json
├── favorite_merchants.json
└── images/
    ├── recipes/                   # 菜谱图
    └── products/                  # 商品本地图
```

菜谱文件名：以菜谱 `name` 命名，做文件名安全化（去除 `/ \ : * ? " < > |`，长度截断）。重名时追加 `_{id}`。

## 6. 数据格式规格

### 通用约定
- HowToCook 原有字段保持其命名与结构（兼容）。
- 所有实体额外带 `id`；所有外键字段额外冗余一个 `_name` 字段（如 `ingredient_id` + `ingredient_name`），便于人眼阅读与导入容错。
- Decimal → float；datetime → ISO 8601 字符串；null 保持 null。
- HowToCook 有而我们数据库没有的字段，给 HowToCook 默认值（如 `is_approximate: false`）。

### 6.1 manifest.json
```json
{
  "format_version": "1.0",
  "app": "生计 - 生活成本计算器",
  "app_version": "0.2.0",
  "exported_at": "2026-06-15T14:30:00+08:00",
  "scope": "mine",
  "exported_by_user_id": 5,
  "schema": {
    "howto_cook_compatible": ["recipes", "ingredients", "nutritions", "units"],
    "extended": ["unit_conversions", "ingredient_categories", "ingredient_hierarchy",
                 "entity_densities", "products", "product_barcodes",
                 "product_ingredient_links", "price_records", "merchants",
                 "favorite_merchants"]
  },
  "counts": { "recipes": 12, "ingredients": 340, "nutritions": 300, "units": 48, "products": 200, "price_records": 475 },
  "image_summary": { "recipes": 8, "products": 3, "skipped_remote": 2 },
  "errors": [],
  "notes": ["2 个商品图片为外链 URL，无法打包"]
}
```

### 6.2 HowToCook 兼容三类

#### 菜谱 `recipes/{name}.json`
HowToCook 字段（保持兼容）：
- `name`, `source_file`（← Recipe.source）, `category`, `difficulty`, `total_time_minutes`, `servings`, `original_servings`（数据库无此字段，输出 `null`）, `images`（路径转换）, `ingredients[]`, `steps[]`（← Recipe.cooking_steps）, `tips`（← Recipe.tips）, `description`

扩展字段：
- `id`（Recipe.id）, `tags`（Recipe.tags）
- `result_ingredient_id`（成品关联，半成品成本传递用）
- `ingredients[]` 每项见下

`ingredients[]` 项（HowToCook + id）：
| 字段 | 来源 | 说明 |
|------|------|------|
| `ingredient_name` | Ingredient.name | HowToCook |
| `ingredient_id` | RecipeIngredient.ingredient_id | 扩展 |
| `quantity` | RecipeIngredient.quantity | String→float，无法解析时置 null 并写 `quantity_description` |
| `unit` | Unit.name | HowToCook 字符串 |
| `unit_id` | RecipeIngredient.unit_id | 扩展 |
| `quantity_range` | RecipeIngredient.quantity_range | HowToCook `{min,max}` |
| `original_quantity` | RecipeIngredient.original_quantity | HowToCook |
| `is_optional` | RecipeIngredient.is_optional | HowToCook |
| `is_approximate` | 默认 false | HowToCook，数据库无 |
| `is_estimated` | 默认 false | HowToCook，数据库无 |
| `note` | RecipeIngredient.note | HowToCook |
| `quantity_description` | 由 quantity 不可解析时填充 | HowToCook |

#### 食材 `ingredients.json`（dict，key=食材名）
HowToCook 字段：
```json
{
  "鸡蛋": {
    "name": "鸡蛋",
    "aliases": ["..."],
    "category": "禽蛋",            // IngredientCategory.display_name
    "usda_id": 171287,             // NutritionData.usda_id（关联营养）
    "usda_match_status": "matched" // 有 usda_id 则 matched，否则 unmatched
  }
}
```
扩展字段（加入每个食材对象）：`id`, `category_id`, `density`, `default_unit_id`, `piece_weight`, `piece_weight_unit_id`, `serving_weight`, `serving_weight_unit_id`, `nutrition_id`, `is_imported`, `is_merged`, `merged_into_id`。

#### 营养 `nutritions.json`（数组）
HowToCook 字段：`usda_id`, `ingredient_name`, `usda_name`, `nutrients[]`。
扩展字段：`id`（NutritionData.id）, `ingredient_id`, `source`, `reference_amount`, `reference_unit`, `match_confidence`, `raw_nutrients`。

> `nutrients[]` 结构转换：`NutritionData.nutrients` 是嵌套 JSON（`{core_nutrients, all_nutrients, nutrient_details}`），HowToCook 期望扁平数组 `[{name, name_en, value, unit, nrp_pct, standard}]`。转换策略：遍历 `all_nutrients`，`name`/`name_en` 通过 key→中英文名映射补全（参考 `nrv_standards` 表或内置映射）。同时保留 `raw_nutrients` 原始嵌套结构，保证恢复导入无损。

#### 单位 `units.json`（数组）
HowToCook 字段：`name`, `aliases`（数据库无别名列，输出 `[]`；缩写见 `abbreviation` 扩展字段）。
扩展字段：`id`, `abbreviation`, `unit_type`, `si_factor`, `unit_system`, `is_si_base`, `is_common`, `default_estimate`, `display_order`。

### 6.3 扩展知识库（独立规格，统一数组 + id + 关联名冗余）

- **unit_conversions.json**：`id`, `from_unit_id`, `from_unit_name`, `to_unit_id`, `to_unit_name`, `conversion_factor`, `formula`, `is_bidirectional`, `precision`
- **ingredient_categories.json**：`id`, `name`, `display_name`, `parent_category_id`, `sort_order`, `description`
- **ingredient_hierarchy.json**：`id`, `parent_id`, `parent_name`, `child_id`, `child_name`, `relation_type`, `strength`
- **entity_densities.json**：`id`, `entity_type`, `entity_id`, `entity_name`, `density`, `temperature`, `condition`, `source`, `confidence`（仅导出集内 `entity_type='ingredient'`/`'product'` 且实体存在者）
- **products.json**：`id`, `name`, `brand`, `barcode`(主条码), `image_url`, `ingredient_id`, `ingredient_name`, `tags`, `aliases`, `custom_nutrition_data`, `custom_nutrition_source`
- **product_barcodes.json**：`id`, `product_id`, `product_name`, `barcode`, `barcode_type`, `is_primary`, `is_active`
- **product_ingredient_links.json**：`id`, `product_id`, `product_name`, `ingredient_id`, `ingredient_name`

### 6.4 账户交易数据

- **price_records.json**：`id`, `product_id`, `product_name`, `merchant_id`, `merchant_name`, `price`, `currency`, `original_quantity`, `original_unit_id`, `original_unit_name`, `standard_quantity`, `standard_unit_id`, `standard_unit_name`, `record_type`, `exchange_rate`, `recorded_at`, `notes`
- **merchants.json**：`id`, `name`, `address`, `latitude`, `longitude`, `is_open`
- **favorite_merchants.json**：`id`, `name`, `type`, `latitude`, `longitude`

## 7. 图片处理

- 菜谱图物理目录：`backend/static/images/recipes/`，数据库 `Recipe.images` 存相对路径如 `/static/images/recipes/xxx.jpg`。
- 商品图：`Product.image_url`，若为本地 `/static/...` 路径则打包，若为 `http(s)://` 外链则跳过。
- 路径转换：json 内统一存 zip 内相对路径 `images/recipes/xxx.jpg`，剥离 `/static` 前缀与域名。
- 复制进 zip 的 `images/recipes/` 与 `images/products/`。
- 跳过的外链与缺失文件计入 `manifest.image_summary.skipped_remote` 与 `notes`。

## 8. 数据流

1. 前端 `GET /export/data?scope=mine`。
2. 后端校验 JWT → 取 `current_user`。
3. 查询账户私有数据（`mine`：按 user_id；`full`：全部）。
4. 若 `mine`：执行可达性遍历，扩张全局库导出集。
5. `full`：全局库全量查询。
6. 逐表序列化为目标格式（Decimal/datetime/路径转换）。
7. 收集图片文件列表。
8. `zipfile.ZipFile(BytesIO, 'w', ZIP_DEFLATED)` 写入所有 json 与图片。
9. `StreamingResponse` 流式吐出，前端 blob 下载。

## 9. 错误处理

- 单表查询/序列化失败：捕获异常，记 `manifest.errors`（表名 + 错误摘要），跳过该表，继续导出其余，不让单点失败毁掉整个导出。
- 图片缺失/外链：跳过 + 记 notes。
- 序列化类型转换：统一转换器，Decimal→float、datetime→ISO，避免 `json.dumps` 抛错。
- 端点级异常：返回 500 + 错误信息（复用全局异常处理器）。

## 10. 测试策略

- **单元测试**（`backend/tests/`）：
  - 各表序列化字段正确（菜谱/食材/营养/单位 HowToCook 兼容性 + id 扩展）。
  - 图片路径转换（`/static/images/recipes/x` → `images/recipes/x`）。
  - Decimal/datetime 序列化。
  - `mine` 模式可达性遍历：构造「我的菜谱引用管理员食材」场景，断言管理员食材被纳入。
- **集成测试**：
  - 端点返回 zip、`Content-Type` 正确、文件名带时间戳。
  - zip 可解压、结构完整、各 json 可被 `json.loads` 解析。
  - 图片存在于 `images/`。
- **HowToCook 兼容性测试**：
  - 导出的菜谱/食材/营养/单位能被现有 `enhanced_recipe_import_service` 解析（dry-run 解析，不实际写库），验证字段兼容。
- 前端：构建通过（`npm run build`）。

## 11. 实现顺序建议（供 writing-plans 参考）

1. 后端序列化层：逐表 `to_export_dict` 函数 + 类型转换器。
2. 可达性遍历（mine 模式）。
3. 打包服务 + 端点 + 路由注册。
4. 图片打包。
5. 前端对话框 + 下载。
6. 测试。

## 12. 参考与对称性

- HowToCook 格式权威定义：`D:\code\HowToCook_json\README.md` 的「输出说明」。
- 现有导入服务：[enhanced_recipe_import_service.py](../../../backend/app/services/enhanced_recipe_import_service.py)（按名字匹配原料、支持 zip 导入）。本导出格式与之对称，将来导入可复用其解析逻辑，并新增按 id 还原的恢复路径。
