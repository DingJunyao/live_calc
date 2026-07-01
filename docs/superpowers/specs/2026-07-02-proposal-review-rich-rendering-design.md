# 提议审核台 · 差异化富渲染

> 日期：2026-07-02
> 分支：`feat/multi-user-permissions`
> 上游：[MULTI_USER_PERMISSIONS.md](../../cc/MULTI_USER_PERMISSIONS.md)、[FEATURE_原料商品改删审核框架.md](../../cc/FEATURE_原料商品改删审核框架.md)
> 设计过程：superpowers:brainstorming（视觉伴侣 4 屏 mockup 校准方向/颗粒度/视觉/明细）

## 背景

提议审核台（[ProposalsView.vue](../../frontend/src/views/admin/ProposalsView.vue)）现状：所有 entity_type 统一用「字段 diff 表」（`diffRows`：snapshot before + payload after 逐字段对比）+ 复杂对象 `JSON.stringify` 兜底。

痛点：CRUD 类（原料/商品/单位等基本信息增删改）字段 diff 表勉强够用，但**重灾三类**退化成「单调字段」或「整块 JSON」：

- **营养数据**（nutrition / usda_ingredient_match / usda_product_match / product_nutrition）：嵌套 `{营养素→值}` 对象被 JSON 兜底，看不出哪个营养素变了
- **合并迁移**（ingredient action=merge / merchant_merge）：snapshot 多段引用数组 JSON，看不出谁并入谁、影响多大
- **菜谱编辑**（recipe_edit）：食材列表全量替换，数组 JSON，看不出增删改

## 目标

针对重灾三类各配**专用渲染器**替代 JSON 兜底；CRUD 类现状不动。

## 范围

**纳入**（3 类专用渲染器）：

- 菜谱：`recipe_edit`（食材列表；步骤同款）
- 营养：`nutrition` / `usda_ingredient_match` / `usda_product_match` / `product_nutrition`
- 合并：`ingredient` action=merge / `merchant_merge`

**不纳入**（现状 `diffRows` 够用）：

- CRUD 类：ingredient/unit/product/merchant/hierarchy/entity_unit_override/entity_density 的 create/update/delete
- `recipe` publish（is_public 简单字段）
- 未注册类型回退 `diffRows`（兜底）

## 设计决策（brainstorming 拍板）

| 维度 | 决定 | 备选 |
|---|---|---|
| 方向 | 针对每类定制渲染器 | — |
| 范围 | 重灾三类（CRUD 不动） | 只做菜谱 / 全 15 种 |
| 菜谱 diff 颗粒度 | **双栏并排**（左旧↔右新，整行红绿） | 行对齐字段 / 字符级文本 |
| 营养 diff 视觉 | **表格行对比**（营养素｜当前｜新值，变化黄底） | 双栏并排 |
| USDA 匹配新值来源 | **实时按 fdc_id 查 USDA 库**算新值 | 提交时预存 / 只显示「将替换」 |
| 合并明细 | **默认展开**（列迁移明细） | 默认折叠 |

## 架构

### 前端：渲染器注册表 + 分发 + 兜底

新建 `frontend/src/components/proposals/`：

| 组件 | 命中 | 职责 |
|---|---|---|
| `RecipeEditDiff.vue` | entity_type=`recipe_edit` | 标量字段 diffRows + 食材双栏并排 |
| `NutritionDiff.vue` | `nutrition` / `usda_ingredient_match` / `usda_product_match` / `product_nutrition` | 营养素表格（标准化 + 只列变化 + 可展开） |
| `MergeMapDiff.vue` | `ingredient` action=merge / `merchant_merge` | 源→目标映射 + 影响计数 + 明细展开 |

新建 `frontend/src/proposalRenderers.ts`：`entity_type (+ action) → 组件` 映射。

[ProposalsView.vue](../../frontend/src/views/admin/ProposalsView.vue) 详情区改造：按 `entity_type`/`action` 选渲染器；**未命中回退现状 `diffRows` 表**（CRUD 类原样，零风险）。

组件统一接口：`<component :proposal="detailItem" />`，内部自取 payload/snapshot/entity_label。

### 后端：3 处改动

1. **`recipe_edit` snapshot 扩展**（+ 修 revert 食材回滚遗留 bug）：apply 时把旧食材列表（`ingredient_id`/`name`/`quantity`/`unit_id`/`unit_name`/`note` 等）存进 snapshot；revert 用它恢复。现状 snapshot 只存 Recipe 标量列、ingredients 在 skip_fields 里，导致审核台无旧食材可 diff、revert 食材不回滚——一并修。
2. **USDA 营养素只读预览**：抽 matcher 内部「按 fdc_id 取 USDA 营养素」逻辑成只读函数 `build_usda_nutrients_by_fdc(fdc_id) -> {名→值}`，新端点 `GET /api/v1/usda/preview-nutrition?fdc_id=...`。供 NutritionDiff 渲染 usda_ 匹配类的「新值」（方案 a，纯读无锁问题）。
3. **合并 snapshot 冗余实体名**：ingredient/merchant merge 执行器存 snapshot 时，迁移项 join 上可读名（`recipe_name`/`product_name`/`merchant_name` 等），前端 MergeMapDiff 直接渲染明细、零查询。

## 三类渲染器详细设计

### RecipeEditDiff（菜谱 · 双栏并排）

数据：

- 旧食材：`snapshot.old_ingredients`（本次后端新增字段，含 `ingredient_id`/`name`/`quantity`/`unit_id`/`unit_name`/`note`）
- 新食材：`payload.update_data.ingredients`（每项 `ingredient_name`/`quantity`/`quantity_range`/`unit_id`/`is_optional`/`note`）

对齐键：`ingredient_name`（payload 用名字匹配，无稳定 id 传递）。

呈现：

- 标量字段（name/servings 等）上半段：复用现状 `diffRows` 表
- 食材下半段：双栏并排
  - 左（当前）：旧食材列表，被删/被改行红底
  - 右（新）：新食材列表，新增/改后行绿底
  - 同名对齐成行；增删整行红绿；改的行左右对应高亮
- 步骤（payload.update_data.steps 若存在）：同食材双栏逻辑（文本行对齐）

### NutritionDiff（营养 · 表格行对比）

数据标准化（4 种 snapshot 统一成 `{营养素名→值}`）：

| entity_type | before 来源 | after 来源 |
|---|---|---|
| `nutrition` | `snapshot.nutrients`（对象） | `payload.nutrients` |
| `product_nutrition` | `snapshot.old_custom_nutrition_data` | `payload.custom_nutrition_data` |
| `usda_product_match` | `snapshot.old_custom_nutrition_data` | 实时查 USDA by `fdc_id` |
| `usda_ingredient_match` | `snapshot.old_nutrition_data`（行数组 → 聚合成 {名→值}） | 实时查 USDA by `fdc_id` |

标准化层 `normalizeNutritionMap(source, kind)`：把「对象」和「NutritionData 行数组」两种形态统一成 `{营养素名→值}`。

呈现（mockup A）：

- 表格：营养素 ｜ 当前 ｜ 新值
- 变化行黄底
- 默认只列变化项；「＋ 展开未变化的 N 项」折叠其余
- USDA 类 after 异步加载（实时查库），加载中显示 skeleton

### MergeMapDiff（合并 · 映射 + 计数 + 明细）

数据：

- snapshot：迁移明细数组（`recipe_ingredients`/`product_links`/`nutrition_mappings`/`hierarchies` + `sources`）—— 冗余名后含 `recipe_name` 等
- payload：`source_ids` / `target_id`

呈现：

- **合并方向**：源 N 个（划线停用色）→ 目标 1 个（高亮）
- **影响范围**：计数卡片网格
  - 原料合并：菜谱引用 / 商品关联 / 层级关系 / 营养映射（四维）
  - 商家合并：价格记录 / 收藏
- **源处理说明**：软停用（is_merged=true，名称保追溯）
- **明细默认展开**：列出迁移明细（菜谱名/商品名，来自 snapshot 冗余名）；列表长时折叠剩余

## 数据流

```
GET /proposals/{id} → ProposalResponse(payload, snapshot, entity_label, ...)
  → ProposalsView 按 entity_type/action 分发
    ├─ recipe_edit → RecipeEditDiff（双栏，旧食材来自 snapshot.old_ingredients）
    ├─ nutrition/usda_*/product_nutrition → NutritionDiff（表格，标准化）
    │   └─ usda_* 的 after 异步：GET /usda/preview-nutrition?fdc_id=...
    ├─ ingredient merge / merchant_merge → MergeMapDiff（映射 + 明细）
    └─ 其他 → 现状 diffRows（兜底）
```

## 文件清单

### 前端新增
- `components/proposals/RecipeEditDiff.vue`
- `components/proposals/NutritionDiff.vue`
- `components/proposals/MergeMapDiff.vue`
- `proposalRenderers.ts`（注册表）

### 前端修改
- `views/admin/ProposalsView.vue`（详情区分发；现状 `diffRows` 作兜底保留）

### 后端修改
- `services/proposals/executors/recipe_edit.py`（snapshot 存旧食材 + revert 回滚 + `_json_safe`）
- `services/proposals/executors/ingredient.py`（merge snapshot 冗余 `recipe_name`/`product_name`）
- `services/proposals/executors/merchant_merge.py`（merge snapshot 冗余名）
- `services/usda/matcher.py` 或新模块（抽 `build_usda_nutrients_by_fdc` 只读函数）
- `api/usda.py`（新增 `GET /usda/preview-nutrition` 端点）

## 测试

- 后端：recipe_edit snapshot 旧食材 + revert 回滚；合并 snapshot 含名；USDA 预览端点返回 {名→值}
- 前端：`npm run build` 通过；三类组件渲染关键路径

## 兼容性与兜底

- 未注册 entity_type 回退 `diffRows`（CRUD 类、recipe publish 零影响）
- recipe_edit 历史提议（snapshot 无 `old_ingredients`）：降级——双栏左栏标「历史提议，旧食材数据缺失」，或实时查当前菜谱（applied 后不准，明确标注）
- USDA 预览失败（fdc_id 失效）：after 栏显示「USDA 数据不可用」，不阻塞审核

## 非范围 / 妥协

- CRUD 类不升级（现状够用，YAGNI）
- `recipe` publish（is_public 简单字段）不专用渲染
- nutrition 端点补空 auto 未生效（apply 内 set_policy 权宜）—— 与本设计无关，不修
- 食材对齐键用 `ingredient_name`（payload 无稳定 id），同名不同食材理论上会混——审核场景罕见，接受

## 决策记录

- **方案 1（注册表 + 专用组件）而非通用 diff 引擎**：三类语义不同（列表 / 嵌套对象 / 关系迁移），通用引擎对嵌套结构不友好
- **不取方案 3（纯前端实时 diff）**：applied/reverted 后历史提议 before 已变，diff 不准
- **菜谱双栏 C**：用户偏好 MediaWiki 经典版式（视觉伴侣探索路径 A→B→B→C 最终选 C）
- **营养表格 A**：营养素多，表格紧凑；只列变化 + 折叠避免长列表
- **USDA 实时查 a**：审核员能看具体换成啥，纯读无锁问题
- **合并明细展开乙**：信息全；取名由后端 snapshot 冗余名解决（前端零查询）
