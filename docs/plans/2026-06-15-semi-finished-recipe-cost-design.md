# 半成品菜谱成本传递 · 设计文档

> 日期：2026-06-15
> 状态：设计已定稿，待实施

## 1. 背景与目标

### 问题

菜谱之间存在「成品依赖」关系：某些原料并非购买而来，而是由另一个菜谱制作。例如：

- 菜谱 **蛋炒饭 (280)** 含原料「米饭 (ingredient 179)」，用量 500 mL。
- 菜谱 **电饭煲蒸米饭 (185)** 以大米 + 水为原料，产出米饭。

当前成本计算把「米饭」当作普通商品处理：若米饭有价格记录则按价计算，否则走回退链（FALLBACK / SUBSTITUTABLE / CONTAINS）。它**无法表达「米饭由 185 制作，成本应取自 185」**这一事实。

### 目标

让原料能指向其「制作菜谱」，使得该原料在成本计算时：

1. 优先使用商品价格（如果有的话）；
2. 商品无价时，由制作菜谱的成本推导其单价；
3. 支持递归套娃（米饭 → 大米，若大米也是自制的）。

### 现状关键发现

- `recipes.result_ingredient_id` 字段**已存在**（[recipe.py:26](../../backend/app/models/recipe.py)），注释为「成品对应食材」，但全表为空、未被成本计算使用。
- 菜谱分类 `半成品` 仅 7 个；而米饭这类「自制半成品」实际分类是「主食」。**自制关系不应绑定菜谱分类**，应作为可任意建立的「原料 → 制作菜谱」关系。
- 成本回退链已成熟：`直接商品价 → FALLBACK/SUBSTITUTABLE → CONTAINS 子食材聚合`（[recipe_service.py](../../backend/app/services/recipe_service.py)）。

## 2. 核心设计决策（均已确认）

| # | 决策点 | 选择 |
|---|---|---|
| 1 | 绑定方式 | **原料级绑定**（一处设置，处处生效） |
| 2 | 产量量化难题 | **绕开**：用「份」+「每份重」桥接，不要求填成品总产量 |
| 3 | 份重字段 | **新增 `serving_weight` + `serving_weight_unit_id`**，不动 `piece_weight` |
| 4 | 成本优先级 | **商品优先，无价才自制**（制作菜谱作为回退链一环） |
| 5 | 营养传递 | **暂不做**，营养仍用原料自身 USDA 数据（YAGNI） |

### 产量难题的解法

成品总产量（如「一锅米饭出锅多重」）用户几乎无法准确填写，也无资料可查。设计将其拆解为两个可量化的小量：

```
半成品每克成本 = (制作菜谱总成本 ÷ servings) ÷ 每份克数
                       自动计算          已有字段      serving_weight
```

- 「做几份」(`servings`) — 用户必知，字段已存在；
- 「每份多重」(`serving_weight`) — 用户对单份的感知远强于总产量。

三个量里两个复用 / 自动算，避免新增难获取数据。

## 3. 数据模型变更

### 3.1 激活 `recipes.result_ingredient_id`

语义明确为「本菜谱的成品原料」，**一对一约束**：一个原料只能有一个制作菜谱（保持简单，YAGNI）。

设置示例：`recipes.id=185.result_ingredient_id = 179`（蒸米饭 → 成品是米饭）。

反向查询「某原料的制作菜谱」：

```sql
SELECT * FROM recipes
WHERE result_ingredient_id = :ingredient_id AND is_active = 1;
```

### 3.2 新增 `ingredients.serving_weight`

| 字段 | 类型 | 说明 |
|---|---|---|
| `serving_weight` | `NUMERIC(10,3)` | 成品基准量（每份多重/多大） |
| `serving_weight_unit_id` | `INTEGER` FK → `units.id` | 基准量单位 |

**语义**：「成品基准量」，`servings` 是它的倍数。

- 「2 碗饭 × 200g」：`serving_weight=200, servings=2`
- 「1 份糖浆 × 200 mL」：`serving_weight=200, servings=1`（退化情形）

**为何不复用 `piece_weight`**：`piece_weight` 服务于计数单位「1 个多重」（鸡蛋 50g/个），语义干净。米饭按「份 / mL」计量，与「个」是两套逻辑，合并会污染语义。

## 4. 成本计算逻辑改造

### 4.1 回退链插入「制作菜谱」

```
① 直接商品价          有就买现成的
② 制作菜谱成本 ★NEW   没价就自己做（本次核心）
③ FALLBACK/SUBSTITUTABLE
④ CONTAINS 子食材聚合
```

制作菜谱插在「商品价」之后、其它回退之前——「自己怎么做」比「拿别的凑」更权威。

### 4.2 每克成本计算

```python
def _get_cost_from_recipe(db, ingredient, user_id, as_of_date, visited):
    # 1. 反查：谁的 result_ingredient_id == 我
    recipe = db.query(Recipe).filter(
        Recipe.result_ingredient_id == ingredient.id,
        Recipe.is_active == True,
    ).first()
    if not recipe:
        return None

    # 2. 递归算制作菜谱自身的成本（支持套娃）
    recipe_cost = calculate_recipe_cost_as_of(
        recipe.id, user_id, as_of_date, db, visited
    )
    if not recipe_cost:
        return None

    # 3. 份重桥接 → 每克单价
    serving_weight_g = to_grams(ingredient.serving_weight,
                                ingredient.serving_weight_unit_id,
                                ingredient.density)
    total_yield_g = (recipe.servings or 1) * serving_weight_g
    if total_yield_g <= 0:
        return None
    return recipe_cost["total_cost"] / total_yield_g   # 元/克
```

### 4.3 两条必须守住的底线

1. **递归套娃**：第 2 步调用的就是同一个成本函数，天然支持多层（米饭 → 大米 → …）。
2. **循环检测**：`visited` 集合贯穿**整条调用链**（不可每层新开），链上见过的菜谱直接返回 None，断开循环。

### 4.4 成本明细产出

`cost_breakdown` 新增字段，与现有 `fallback_chain` / `aggregation_chain` 并列：

```json
{
  "ingredient_name": "米饭",
  "recipe_chain": "米饭 ← 制作自「电饭煲蒸米饭」",
  "cost_source": "recipe",
  ...
}
```

## 5. 单位换算链

整个方案最易翻车处。两道换算墙，都归一到「克」相乘：

**第一道墙：份重 → 每克成本**

`serving_weight` 可能是 g 或 mL，统一按自身单位 + 密度（`density` 字段，已有）折算成克：

```
米饭 serving_weight=200, unit=mL, density=0.8
  → serving_weight_g = 200 × 0.8 = 160g
每克成本 = 菜谱总成本 ÷ (servings × serving_weight_g)
```

**第二道墙：菜谱用量 → 克**

蛋炒饭里 500 mL 米饭，走同一套密度换算（复用 [recipe_service.py:271](../../backend/app/services/recipe_service.py) `_convert_record_to_price_per_gram` 思路）：

```
500 mL × 0.8 = 400g
400g × 每克成本 = 蛋炒饭里米饭的花费
```

**完整链**：

```
菜谱用量(任意单位) ──密度/单位转换──→ 克
                                     ×
            每克成本 = 菜谱总成本 ÷ (servings × 每份克数)
```

不引入新换算逻辑，仅把制作菜谱这条线接入现有基础设施。

## 6. API 与前端

### 6.1 后端接口（改动最小，不加新端点）

| 接口 | 改动 |
|---|---|
| 菜谱 create/update | schema 暴露 `result_ingredient_id`（确认是否已在 schema，否则补） |
| 原料 create/update | schema 增加 `serving_weight` + `serving_weight_unit_id` |
| `GET /recipes/{id}/cost` | 签名不变，内部逻辑变更，`cost_breakdown` 多 `recipe_chain` + `cost_source:"recipe"` |

### 6.2 前端入口（两端都给，底层同一字段）

- **A｜菜谱详情页**：「成品产出」区，选成品原料（正主入口，从「做菜」视角）。
- **B｜原料详情页**：「自制来源」区，选制作菜谱（从「这东西哪来的」视角）。

两端任一设置，另一端同步显示。

### 6.3 成本明细 tooltip

复用现有机制（[RecipeIngredientCard.vue:392](../../frontend/src/components/recipes/RecipeIngredientCard.vue) `getIngredientFallbackChain`）：

- 后端 `cost_breakdown` 增 `recipe_chain`；
- 前端该函数增 `recipe_chain` 优先级判断；
- 渲染复用 `v-tooltip` + `mdi-information`，零新组件。

## 7. 边界情况与性能

### 7.1 边界（必须堵的坑）

1. **除零**：`servings=0` 或 `serving_weight_g=0` → 本环 return None，走后续回退。
2. **制作菜谱被删 / 停用**：`is_active=False` 查不到 → 视为未绑，走老链。
3. **循环检测**：`visited` 贯穿整条调用链（见 4.3）。
4. **`serving_weight` 缺失**：本环失败，老实走商品价 / 回退，**绝不用半截数据算错成本**。

### 7.2 性能（最大暗礁）

[calculate_recipe_cost_range_trend](../../backend/app/services/recipe_service.py) 是把数据预加载到内存、逐天算的高度优化批量函数。一旦半成品递归，趋势图逐天 × 逐层递归会卡死。

**策略：趋势图里半成品用「快照单价」而非「实时递归」**——算趋势时先算一次制作菜谱当日成本得每克单价，缓存逐天复用。实施时重点打磨。

## 8. 数据库迁移

按项目硬规矩：

- alembic 迁移脚本；
- SQL 脚本覆盖：SQLite / MySQL / PostgreSQL / PostgreSQL+PostGIS。
  - 本特性与地理无关，**PostGIS 版本免**。
- 字段：`ingredients` 增 `serving_weight` + `serving_weight_unit_id`（`result_ingredient_id` 已存在，无需迁移）。

## 9. 后续 / 暂不做

- **营养传递**：若将来原料自身缺 USDA 数据、确需从制作菜谱推导营养，按相同「份重桥接」思路扩展（本设计已留好接口）。
- **趋势图实时递归**：当前以快照单价策略兜底，若精度需求提升再优化。

## 10. 验证清单

- [ ] 米饭绑定制谱 185 后，蛋炒饭 280 成本明细中「米饭」行 `cost_source="recipe"`、金额正确。
- [ ] 米饭有商品价时，仍优先走商品价。
- [ ] 制作菜谱成本变化（大米涨价）→ 米饭单价、蛋炒饭成本自动联动。
- [ ] 递归套娃（自制大米）能正确多层计算。
- [ ] 循环引用不致死循环。
- [ ] `serving_weight` 缺失时降级走商品价 / 回退。
- [ ] 趋势图不卡顿。
- [ ] 前后端构建通过、无语法错误。
