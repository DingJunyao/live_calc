# 半成品菜谱成本传递 · 实施计划

> **For Claude:** 配套设计文档见 [2026-06-15-semi-finished-recipe-cost-design.md](./2026-06-15-semi-finished-recipe-cost-design.md)。

**Goal:** 让原料能指向其制作菜谱，成本计算时商品无价则由制作菜谱成本推导单价，支持递归套娃与循环检测。

**Architecture:** 激活 `recipes.result_ingredient_id`（一对一绑定）+ 新增 `ingredients.serving_weight`；在 `recipe_service` 成本回退链「商品价之后、其它回退之前」插入「制作菜谱」一环，用「份 × 每份重」桥接每克单价；趋势函数用快照单价避免递归卡顿；前端复用现有 tooltip + 两端入口。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic（后端）；Vue 3 + Vuetify（前端）。

---

## 约定与前提

- **不执行 git 提交**：项目规矩，用户未要求则不动 git。每个任务以「构建/编译通过」为检查点，提交时机由用户决定。
- **验证标准**：后端无语法错误（`python -c "import app..."` 或服务自动重载无报错）；前端 `npm run build` 通过。
- **不启动服务**：前端/后端自动重载服务已在运行。
- **数据库迁移**：alembic + 四引擎 SQL 脚本（PostGIS 版本免，本特性与地理无关）。
- **现有可复用**：`result_ingredient_id` 已在 RecipeCreate/Update/Response schema 全部暴露；recipe update 用 `setattr` 通用循环，前端传值即落库，**菜谱侧 API 零改动**。

---

## Task 1: 后端 model 加 serving_weight 字段

**Files:**
- Modify: `backend/app/models/nutrition.py`（Ingredient 类，紧邻 piece_weight）

**步骤：**

1. 在 `Ingredient` 类 `piece_weight_unit_id` 之后新增两列（对称 piece_weight）：

```python
# 成品基准量（每份/每基准单位多重），用于"制作菜谱"成本换算
# 语义：servings 是它的倍数，total_yield = servings × serving_weight(折算为克)
serving_weight = Column(Numeric(10, 3), nullable=True)
serving_weight_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
```

2. 在 relationships 区新增（对称 `piece_weight_unit`）：

```python
serving_weight_unit = relationship("Unit", lazy="select", foreign_keys=[serving_weight_unit_id])
```

3. 验证：后端服务自动重载无报错。

---

## Task 2: alembic 迁移 + SQL 脚本

**Files:**
- Create: `backend/alembic/versions/20260615_0001_add_serving_weight_to_ingredients.py`
- Create: `backend/data/migrations/20260615_add_serving_weight.sqlite.sql`
- Create: `backend/data/migrations/20260615_add_serving_weight.mysql.sql`
- Create: `backend/data/migrations/20260615_add_serving_weight.postgres.sql`
（先确认 `backend/data/migrations/` 目录是否存在及命名规范，若不存在则按项目现有 SQL 脚本存放位置调整）

**步骤：**

1. 写 alembic 迁移（down_revision 取当前 head `20260614_195120`）：

```python
"""add serving_weight to ingredients

Revision ID: 20260615_0001
Revises: 20260614_195120
Create Date: 2026-06-15 10:00:00.000000

为 ingredients 新增 serving_weight + serving_weight_unit_id，
用于"半成品制作菜谱"的成本换算（成品基准量）。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260615_0001'
down_revision = '20260614_195120'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ingredients',
        sa.Column('serving_weight', sa.Numeric(10, 3), nullable=True))
    op.add_column('ingredients',
        sa.Column('serving_weight_unit_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_ingredients_serving_weight_unit_id', 'ingredients',
        'units', ['serving_weight_unit_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_ingredients_serving_weight_unit_id', 'ingredients', type_='foreignkey')
    op.drop_column('ingredients', 'serving_weight_unit_id')
    op.drop_column('ingredients', 'serving_weight')
```

> 注意：SQLite 的 ALTER TABLE 对 FK 约束支持有限，alembic 在 SQLite 下 create_foreign_key 可能被忽略或需 batch 模式。参考项目既有迁移的写法（如 `20260312_0001_add_piece_weight_to_ingredients.py`），与其保持一致。

2. 三套 SQL 脚本分别对应 SQLite / MySQL / PostgreSQL，内容为等价的 `ALTER TABLE ingredients ADD COLUMN ...`（MySQL/PG 含 FK 约束；SQLite 通常只加列）。

3. 应用迁移：用项目 SQLite MCP 或 `alembic upgrade head`（**仅在用户允许后执行数据库变更**；本计划默认不自动跑迁移，执行时与用户确认）。

---

## Task 3: 后端 schema/api 暴露 serving_weight

**Files:**
- Modify: `backend/app/schemas/nutrition.py`（IngredientResponse 等）
- Modify: `backend/app/api/ingredient_extended.py`（update_ingredient @468、get_ingredient @807、create_ingredient @320）

**步骤：**

1. 先读 `update_ingredient` 与 `get_ingredient` 实现，确认字段处理方式（`setattr` 通用 / 白名单 / dict 构造）——`serving_weight` 对称 `piece_weight` 的处理路径加入。
2. 在原料相关 schema（响应/更新）补 `serving_weight` + `serving_weight_unit_id`（若 piece_weight 未单独建 schema，则跟随其 dict 传递方式）。
3. `get_ingredient` 详情接口返回中补这两个字段。
4. 验证：后端无报错；GET `/ingredients/{id}` 响应含新字段（默认 null）。

---

## Task 4: recipe_service 插入制作菜谱回退环（核心）

**Files:**
- Modify: `backend/app/services/recipe_service.py`

**步骤：**

1. 新增辅助函数 `_serving_weight_to_grams(db, ingredient) -> Optional[Decimal]`：用 `serving_weight` + `serving_weight_unit_id` + `density` 折算为克（复用 `UnitConversionService` 与 `_convert_record_to_price_per_gram` 思路）。无 `serving_weight` 返回 None。

2. 新增核心函数 `_get_cost_from_recipe(db, ingredient, user_id, as_of_date, visited)`：

```python
def _get_cost_from_recipe(db, ingredient, user_id, as_of_date, visited=None):
    """从制作菜谱推导原料每克成本。"""
    if not ingredient:
        return None
    recipe = db.query(Recipe).filter(
        Recipe.result_ingredient_id == ingredient.id,
        Recipe.is_active == True,
    ).first()
    if not recipe:
        return None
    # 循环检测：链上见过的菜谱直接放弃
    if visited is None:
        visited = set()
    if recipe.id in visited:
        return None
    visited = visited | {recipe.id}
    # 份重桥接
    sw_g = _serving_weight_to_grams(db, ingredient)
    if sw_g is None or sw_g <= 0:
        return None
    servings = recipe.servings or 1
    if servings <= 0:
        return None
    # 递归算制作菜谱成本（套娃），把 visited 透传下去
    recipe_cost = calculate_recipe_cost_as_of(
        recipe.id, user_id, as_of_date, db, visited=visited
    )
    if not recipe_cost:
        return None
    total_cost = Decimal(str(recipe_cost["total_cost"]))
    total_yield_g = Decimal(str(servings)) * sw_g
    if total_yield_g <= 0:
        return None
    return total_cost / total_yield_g, recipe  # 返回单价与菜谱对象（用于 chain 描述）
```

3. 给 `calculate_recipe_cost` / `calculate_recipe_cost_as_of` 增加可选 `visited: Optional[set] = None` 参数并透传（保持向后兼容）。在「直接商品价失败、尚未走 fallback」的位置插入对 `_get_cost_from_recipe` 的调用；命中时：
   - 用其每克单价 ×（菜谱用量折算为克）得该行成本；
   - `cost_breakdown` 记 `cost_source="recipe"`、`recipe_chain=f"{ingredient.name} ← 制作自「{recipe.name}」"`。

4. 循环检测贯穿：`calculate_recipe_cost_as_of` 调用 `_get_cost_from_recipe` 时把自身 recipe_id 纳入 visited，确保 A→B→A 立即断开。

5. 验证：
   - 设 185.result_ingredient_id=179、米饭 serving_weight=200(g)、蛋炒饭 280 含米饭 500mL；
   - 调 `calculate_recipe_cost(280, user_id, db)`，确认米饭行 `cost_source="recipe"`、金额合理。
   - 构造循环引用（A.result_ingredient_id 指向被 A 引用的原料）→ 不死循环。

---

## Task 5: cost_breakdown 字段对齐前端

**Files:**
- Modify: `backend/app/services/recipe_service.py`（已在 Task 4 一并产出）

**确认：** `cost_breakdown` 每项含 `recipe_chain`（命中制作菜谱时）与 `cost_source`（取值 `"recipe"`）。`calculate_recipe_cost_range_trend` 等批量函数中涉及单价的分支同步带 `cost_source`。

---

## Task 6: 趋势函数快照策略（性能暗礁）

**Files:**
- Modify: `backend/app/services/recipe_service.py`（`calculate_recipe_cost_range_trend`）

**步骤：**

1. 预扫描阶段（批量预加载区）：识别菜谱中哪些原料绑定了制作菜谱，预先为每个制作菜谱计算「逐日总成本」（复用趋势已有逻辑），缓存为 `recipe_id -> {date -> total_cost}`。
2. 逐天循环中，命中制作菜谱的原料：从快照取当日制作菜谱总成本 → ÷(servings × serving_weight_g) 得每克单价 → 蛋谱用量折算为克相乘。不递归。
3. 边界：制作菜谱当日无成本快照 → 该原料当日跳过（与现有「无价跳过」一致）。
4. 验证：280 趋势图加载不卡顿、曲线含米饭贡献。

> 若时间或复杂度超预期，可降级：趋势图暂不支持制作菜谱回退（命中时按既有逻辑处理或标记），先保证详情页成本正确。届时与用户确认。

---

## Task 7: 前端 菜谱详情页「成品产出」入口

**Files:**
- Modify: `frontend/src/views/recipes/RecipeDetail.vue`（及编辑表单组件，如 `RecipeEditForm`/编辑弹窗）
- 可能 Modify: `frontend/src/api/recipes.ts`（确认 update payload 含 result_ingredient_id）

**步骤：**

1. 在菜谱编辑表单加「成品产出原料」选择器（搜索原料，存 result_ingredient_id）。
2. 详情页展示区：若 `result_ingredient_id` 有值，显示「⤴ 成品：{原料名}（本菜谱制作）」。
3. 更新请求 payload 带 `result_ingredient_id`（后端 setattr 自动落库）。
4. 验证：设 185 成品=米饭，保存成功，详情页显示。

---

## Task 8: 前端 原料详情页「自制来源」入口

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`
- Modify: 原料更新 API 客户端（serving_weight + 反向展示制作菜谱）

**步骤：**

1. 详情页加「自制来源」区：搜索选择制作菜谱（设置 → 后端通过该菜谱 result_ingredient_id 落库；或原料侧提交后由后端写对方菜谱字段，二选一，执行时定）。姐姐倾向：**原料页选择制作菜谱时，提交即设置该菜谱的 result_ingredient_id**（统一字段归属）。
2. 加「成品基准量」serving_weight + 单位输入。
3. 详情页展示：若存在制作菜谱，显示「← 由「{菜谱名}」制作，每份 {serving_weight}{单位}」。
4. 验证：米饭原料设自制来源=185 + serving_weight=200g，保存成功并回显。

---

## Task 9: 前端 成本明细 tooltip 加 recipe_chain

**Files:**
- Modify: `frontend/src/components/recipes/RecipeIngredientCard.vue:392`

**步骤：**

1. `getIngredientFallbackChain` 增 `recipe_chain` 优先级（最高）：

```typescript
const getIngredientFallbackChain = (ingredient) => {
  if (!props.costBreakdown) return null
  const item = props.costBreakdown.find((b) => b.recipe_ingredient_id === ingredient.id)
  if (item?.recipe_chain) return item.recipe_chain
  if (item?.aggregation_chain) return item.aggregation_chain
  return item?.fallback_chain || null
}
```

2. tooltip 文案微调（命中 recipe 时显示「由制作菜谱计算成本」语义），复用现有 `v-tooltip` + `mdi-information`。
3. 验证：280 成本明细米饭行出现 info 图标，hover 显示「米饭 ← 制作自「电饭煲蒸米饭」」。

---

## Task 10: 验证 + 文档

**步骤：**

1. 后端：`cd backend && python -c "import app.services.recipe_service"` 无报错。
2. 前端：`cd frontend && npm run build` 通过。
3. 手测全链路（米饭场景）：185 设成品=米饭 + 米饭 serving_weight；280 成本明细正确；米饭有商品价时优先商品价；大米涨价联动；循环不死锁；serving_weight 缺失降级。
4. 文档：
   - Create: `cc/FEATURE_半成品菜谱成本传递.md`（背景、设计要点、改动文件、迁移、验证）。
   - Modify: `CLAUDE.md` 项目索引「功能实现记录」追加一条链接。
5. **不提交 git**，告知用户可自行提交。

---

## 风险与回退

- **Task 4 循环检测**是安全底线，必须先于性能优化验证通过。
- **Task 6 性能**可降级处理（见该任务说明）。
- **字段语义** `serving_weight` 与 `piece_weight` 独立，互不污染；若后续发现重合需求再合并。
- 整体后向兼容：未绑定制作菜谱、未填 serving_weight 的原料，行为与现状完全一致。
