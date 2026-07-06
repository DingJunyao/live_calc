# 商品加权价格机制设计

> 日期：2026-07-06
> 状态：设计稿（待实现）
> 范围：后端（FastAPI）+ 前端（Vue 3）+ 数据库迁移

## 1. 背景与动机

一个原料（ingredient）常常挂多个商品（product），而这些商品价格可能差别悬殊——典型如「有机 vs 非有机」「不同品牌」「不同等级」。当前系统在把「商品价格」聚合为「原料价格」时，存在两套**互相不一致且各有偏置**的逻辑：

1. **原料详情页「最新价格」**（[nutrition.py:get_ingredient_latest_price](../../../backend/app/api/nutrition.py#L864)）：把该原料下所有商品、最近一天的所有价格记录**按记录数简单平均**。
   - 偏置：谁家价格记录多，谁就被无形放大。商品 A 有 3 条记录、商品 B 有 1 条，结果里 A 占了 75% 权重，与商品本身的代表性无关。

2. **菜谱成本计算**（[recipe_service.py:calculate_recipe_cost](../../../backend/app/services/recipe_service.py#L719) 及 4 个变体）：遍历该原料的商品，**取第一个有当天记录的商品**就跑路。
   - 偏置：选中哪个商品完全取决于查询返回顺序，价格悬殊时成本飘忽不定。

两套逻辑还会给出互相矛盾的数字（详情页显示一个价、菜谱成本算出另一个价）。

### 目标

引入**商品级价格权重**，把两套逻辑统一为「**商品间加权平均**」，让用户能显式控制每个商品在原料价格中的贡献度——类似已有的「原料关联强度」（[ingredient_hierarchy.strength](../../../backend/app/models/ingredient_hierarchy.py#L24)，0-100 整数）。

## 2. 决策摘要

| 维度 | 结论 |
|---|---|
| 权重作用域 | **全局默认 + 用户私有覆盖** |
| 与 `default_product_id` 关系 | 统一为权重机制；字段保留不动（死字段），价格计算只认权重 |
| 数值表达 | **0-100 整数，默认 50**（对齐 `strength`） |
| 生效范围 | 价格计算全链路：原料最新价、菜谱成本（5 变体）、趋势 sparkline、报告（复用） |
| 配置入口 | 商品详情基本信息 + 原料详情商品列表编辑 |
| 全局权重写权限 | **仅管理员**（普通用户连提议都不开） |
| 用户覆盖写权限 | 所有用户（个人偏好，不走审核） |
| 数据模型 | 方案 A：`Product` 加 `price_weight` 列 + 新建 `user_product_weight_overrides` 表 |

## 3. 数据模型

### 3.1 `products` 表加全局权重列

```
price_weight INTEGER NOT NULL DEFAULT 50
-- CHECK (price_weight BETWEEN 0 AND 100)
```

- 随商品走，全局共享。商品 update 已接 `ProductExecutor`（[executors/product.py](../../../backend/app/services/proposals/executors/product.py)），新增字段自动受审核框架保护。
- 加 `CHECK (0-100)` 约束防脏数据（项目既有 `strength` 没加 CHECK，本特性从严）。

### 3.2 新表 `user_product_weight_overrides`（用户私有覆盖）

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK→users.id, NOT NULL | 联合唯一 |
| product_id | INTEGER FK→products.id, NOT NULL | 联合唯一 |
| weight | INTEGER NOT NULL DEFAULT 50, CHECK 0-100 | |
| AuditMixin | | id / created_at / updated_at / created_by / updated_by / is_active |

约束与索引（对齐 [user_ingredient_preferences](../../../backend/app/models/user_ingredient_preference.py) 惯例）：

- `UNIQUE(user_id, product_id)` —— 单用户单商品一条覆盖
- `INDEX(user_id)`、`INDEX(product_id)`
- 软删走 `is_active`（与项目其他偏好表一致）

### 3.3 权重读取优先级

```
_resolve_weight(db, user_id, product) -> int:
    1. 查 user_product_weight_overrides (user_id, product_id, is_active=True) → 有则用
    2. 否则用 product.price_weight
    3. 兜底 50（防御性，正常不会走到）
```

### 3.4 迁移产物（按 CLAUDE.md 规矩）

- `backend/alembic/versions/20260707_0001_product_price_weight.py`
- `backend/scripts/sql/20260707_product_price_weight_sqlite.sql`
- `backend/scripts/sql/20260707_product_price_weight_mysql.sql`
- `backend/scripts/sql/20260707_product_price_weight_postgres.sql`
- PostgreSQL（启用 PostGIS）一项与普通 PostgreSQL 相同（本变更与 PostGIS 无关），在 SQL 脚本中注明即可，不单列文件。
- 开发库 `backend/data/livecalc.db` 直接补（项目不走 alembic 的惯例），操作前备份为 `livecalc.db.bak_<timestamp>`。

### 3.5 数据回填

现有商品全部置默认 50（等权）。等权 + 各商品记录数一致时，新算法与旧「简单平均」行为近似等价（仅有的差异是商品级 vs 记录级聚合维度），平滑过渡。

## 4. 聚合算法与统一服务（核心）

### 4.1 两层聚合（顺带修正记录数偏置）

```
第一层（商品内）：每个商品先算自己当天的代表单价
                 = 该商品当日有效记录的均价（无记录则该商品不参与）
第二层（商品间）：再按商品权重加权平均
```

记录数从此不再影响原料价，只有商品权重说了算。

### 4.2 加权公式

```
weighted_price = Σ(pᵢ × wᵢ) / Σ(wᵢ)    （仅对 wᵢ > 0 且当日有记录的商品 i）
```

### 4.3 边界处理

| 情况 | 处理 |
|---|---|
| 某商品当日无记录 | 不参与，权重在**剩余**有记录商品间重新归一（不是补 0） |
| 权重 = 0 | 等价于手动排除，不参与 |
| 仅 1 个商品有记录 | 退化为直接取它（加权退化为单价） |
| 全部商品都无记录 | 统一服务返回 None；**调用方走现有回退链**（食材 fallback / 子食材聚合 / 制作菜谱），回退链逻辑不动 |
| 商品间单位不同 | 第一层算单价时各自折算到目标单位（复用 `UnitConversionService`） |

### 4.4 统一服务（DRY）

新建 `backend/app/services/ingredient_price_service.py`：

```python
def get_weighted_ingredient_price(
    db, ingredient_id, *, as_of_date, user_id, target_unit_abbr
) -> WeightedPriceResult:
    """
    返回:
      unit_price: Optional[float]        # 加权单价（None 表示该原料当日无价）
      participants: list                 # 参与商品明细
                                         # [{product_id, name, weight, unit_price,
                                         #   record_count, weight_source}]
                                         # weight_source ∈ {"override","global","default"}
      excluded: list                     # 被排除的商品及原因（no_record / weight_zero）
      mode: "weighted" | "single" | "none"
    """
```

- 内部复用 `_get_price_records_for_date` / `_get_price_records_with_fallback`（[recipe_service.py](../../../backend/app/services/recipe_service.py#L124)），**不重写记录查询，只改聚合层**。
- 提供「当日有效记录」的统一获取口径，所有调用方共用。
- **口径差异说明**：`latest-price` 现用「最近 24 小时，否则最近有记录的那天」语义；`recipe_service` 现用「指定日期当天 + 前向填充」。统一服务以 `as_of_date` 入参，内部按调用场景选用对应口径（`latest-price` 传 `now` 走「最近」分支；成本计算传目标日期走「当天 + 前向填充」分支）。具体分支在实现计划中细化，本设计仅约束「不重写记录查询、只改聚合层」。

### 4.5 改造点（全部改为调统一服务）

| 场景 | 现状 | 改为 |
|---|---|---|
| [原料最新价](../../../backend/app/api/nutrition.py#L864) | 记录级简单平均 | 调统一服务，响应加 `participants` |
| [菜谱成本 5 变体](../../../backend/app/services/recipe_service.py#L719) | 取第一个有记录商品 | 调统一服务；回退链不变 |
| [sparklines `_daily_avg_for_product_ids`](../../../backend/app/api/sparklines.py#L25) | 按记录日均 | 按商品级均价再按权重加权 |
| 报告 | 复用 recipe_service | 自动受益，无需单独改 |

## 5. 后端改动清单

| 层 | 文件 | 改动 |
|---|---|---|
| Model | [product_entity.py](../../../backend/app/models/product_entity.py) | `Product` 加 `price_weight` |
| Model | 新建 `user_product_weight_override.py` | 用户覆盖表 |
| Model | `__init__.py` | 注册新模型 |
| Schema | product schema | 加 `price_weight` 字段 |
| Schema | 新建 `user_product_weight_override` schema | |
| Schema | 新建 `WeightedPriceResult` schema | 统一服务 / API 返回 |
| Service | 新建 `ingredient_price_service.py` | 统一加权服务 + `_resolve_weight` |
| Service | [recipe_service.py](../../../backend/app/services/recipe_service.py) | 5 个成本函数「取第一个商品」段 → 调统一服务；`_get_price_records_*` 与回退链不动 |
| API | [nutrition.py:get_ingredient_latest_price](../../../backend/app/api/nutrition.py#L864) | 调统一服务，响应加 `participants` |
| API | [sparklines.py](../../../backend/app/api/sparklines.py) | `_daily_avg_for_product_ids` 按商品级加权 |
| API | 新建用户覆盖端点 | `GET/PUT/DELETE /products/{id}/my-weight`（个人偏好，不走审核） |
| API | 商品 update 端点 | payload 接受 `price_weight`，但**仅管理员**字段生效；普通用户 payload 中该字段被忽略 |

### 5.1 权限固化

- **全局 `price_weight`**：仅管理员可写。商品 update 端点对普通用户 payload 里的 `price_weight` 一律忽略（连审核提议都不开，对齐「共享数据写限管理员」家规）。
- **用户覆盖**：所有用户自由写自己的（仿 [user_preferences.py](../../../backend/app/api/user_preferences.py) 现成套路），不走审核。

### 5.2 明确不改 / 不在范围

- `latest-price-by-merchant`：按商家列明细，不是聚合一个价，**不改**。
- K 线功能：已废弃，**移除出考量**。
- 营养计算、商品排序、推荐等**非价格场景**不使用权重。

## 6. 前端改动

### 6.1 配置入口（两处）

| 角色 | 全局权重 `price_weight` | 我的权重（覆盖） |
|---|---|---|
| 管理员 | 直接改（`apply_as_admin`） | 个人偏好，自由改 |
| 普通用户 | 只读 | 个人偏好，自由改 |

- [ProductDetail 基本信息](../../../frontend/src/views/products/ProductDetail.vue)：加 0-100 滑块 + 数字框（默认 50）。
- [IngredientDetail 商品列表编辑](../../../frontend/src/views/ingredients/IngredientDetail.vue)：每行商品一个权重控件。
- 两处均区分「全局 / 我的」两栏，普通用户的全局栏只读。

### 6.2 UX 细节

- 控件旁显示**当前生效值**（我的覆盖 → 全局 → 50 三级回退显示）。
- 权重为 0 时标灰提示「已排除」。
- **不做**「设为代表商品」快捷操作（纯手动调权重即可）。

### 6.3 加权来源展示（透明可追溯）

- **原料详情最新价区**：显示加权单价 + 可折叠「参与明细」（商品名 / 权重 / 当日单价 / 权重来源 override|global|default）。
- **菜谱成本明细 tooltip**：复用现有 `cost_breakdown` 的 `*_chain` 机制，新增 `weighted_participants` 字段，hover 可见该原料价如何加权而来。

## 7. `default_product_id` 处理

grep 实锤：[user_ingredient_preference.default_product_id](../../../backend/app/models/user_ingredient_preference.py#L14) 前端**零消费**、后端除 schema/model/CRUD 存取外**无任何业务消费**，是死字段。

**决策**：字段物理保留不动（删除需表迁移，节外生枝）。价格计算只认权重，该字段在权重机制下事实上被取代，UI 不再暴露它。日后若需复用该指针再说（YAGNI）。

## 8. 测试策略

| 类型 | 覆盖点 |
|---|---|
| 单元（统一服务） | 多商品加权 Σ(p×w)/Σw 算对；权重 0 排除；单商品退化；全无记录返回 None；权重优先级（覆盖 > 全局 > 50）；**记录数偏置修正**（记录多的商品不再被放大——回归断言） |
| 集成 | `latest-price` 返回 `participants`；菜谱成本多商品加权正确；不同用户看不同加权价（覆盖生效）；管理员改全局 → 生效、普通用户改全局被拒 |
| 兼容回归 | 等权（默认 50）+ 各商品记录数一致时，新算法 ≈ 旧简单平均 |

## 9. 实现风险点

- `recipe_service` 5 个成本变体（cost / cost_range_as_of / cost_range_trend / cost_as_of / cost_trend）改造量大，逐个对照避免遗漏；它们共享 `_get_price_records_*`，改聚合层时确保回退链衔接不串味。
- `CrudExecutorBase` 若有字段白名单，需加入 `price_weight`。
- 统一服务抽好后，`sparklines` 按日聚合必须复用同一份加权逻辑，不得重写。
- Decimal × float 隐患（参考项目既有修复）：加权计算注意类型一致。

## 10. 不在范围（YAGNI 收口）

- ❌ K 线功能（已废弃）
- ❌ `latest-price-by-merchant` 改造
- ❌ 权重用于营养 / 排序等非价格场景
- ❌ `default_product_id` 字段迁移（死字段保留）
- ❌ 「设为代表商品」快捷操作
- ❌ 商品 create 时的权重自定义（沿用默认 50，create 不在本次范围）

## 11. 关键代码位置参考

- 现状原料最新价：[nutrition.py:864](../../../backend/app/api/nutrition.py#L864)
- 现状菜谱成本：[recipe_service.py:719](../../../backend/app/services/recipe_service.py#L719)
- 价格记录工具：[recipe_service.py:68/124/174/385](../../../backend/app/services/recipe_service.py#L68)
- sparkline 聚合：[sparklines.py:25](../../../backend/app/api/sparklines.py#L25)
- 关联强度样板：[ingredient_hierarchy.py:24](../../../backend/app/models/ingredient_hierarchy.py#L24)
- 商品审核执行器：[executors/product.py](../../../backend/app/services/proposals/executors/product.py)
- 用户偏好样板：[user_ingredient_preference.py](../../../backend/app/models/user_ingredient_preference.py) / [user_preferences.py](../../../backend/app/api/user_preferences.py)
