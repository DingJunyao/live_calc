# 提议审核台 · 差异化富渲染 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 针对审核台三类「重灾」提议（菜谱编辑 / 营养数据 / 合并迁移）各配专用渲染器替代 JSON 兜底，CRUD 类现状不动；并修掉 recipe_edit 食材回滚遗留 bug。

**Architecture:** 前端建「渲染器注册表 + 分发 + 兜底」——`proposalRenderers.ts` 按 `entity_type`/`action` 选专用组件，未命中回退现状 `diffRows`（零风险）。后端 3 处配合：recipe_edit snapshot 存旧食材（+ 修 revert）、合并执行器 snapshot 冗余可读名、抽 USDA 只读预览函数 + 新端点。

**Tech Stack:** 后端 FastAPI + SQLAlchemy（TDD：`db_session` 内存库 + `SimpleNamespace` 直接测执行器）；前端 Vue 3 `<script setup lang="ts">` + Vuetify 3（无 i18n，中文硬编码；门禁用 `npm run build`）。

**上游设计：** [docs/superpowers/specs/2026-07-02-proposal-review-rich-rendering-design.md](../superpowers/specs/2026-07-02-proposal-review-rich-rendering-design.md)

---

## 现状速览（给零上下文工程师的背景）

- 审核台页面：[frontend/src/views/admin/ProposalsView.vue](../../frontend/src/views/admin/ProposalsView.vue)。详情区变更内容当前统一用 `diffRows` computed（第 937–962 行）做字段级 before/after 表，template 在第 338–364 行。
- `diffRows` 输入：`detailItem.snapshot`（before）+ `detailItem.payload`（after）；对嵌套对象/数组会退化成 `JSON.stringify`，看不出明细——本计划要替代的就是它（仅三类）。
- `Proposal` 类型在 [frontend/src/api/proposals.ts](../../frontend/src/api/proposals.ts)，`payload`/`snapshot` 都是 `Record<string, any>`。
- 后端提议框架：执行器在 [backend/app/services/proposals/executors/](../../backend/app/services/proposals/executors/)。`apply()` 返回 `ApplyResult(snapshot, revert_payload, summary)`，service 层 `_do_apply` 会把 `snapshot` 写进 `change_proposals.snapshot`（JSON 列）；`submit` 时若有 `build_snapshot()` 会预填 snapshot 供 pending 审核。
- 测试范式见 [backend/tests/test_entity_executors.py](../../backend/tests/test_entity_executors.py)：`db_session` fixture（conftest 内存 SQLite，StaticPool 单例，跨测试有残留→用独立大 id 隔离）+ `SimpleNamespace` 造 proposal + 直接调 executor。

**后端三个执行器现状关键点（本计划要改的）：**

| 执行器 | 文件 | snapshot 现状 | 问题 |
|---|---|---|---|
| `RecipeEditExecutor` | [recipe_edit.py](../../backend/app/services/proposals/executors/recipe_edit.py) | 仅 Recipe 标量列；食材在 `skip_fields` | 审核台无旧食材可 diff；revert 食材不回滚（第 95–97 行注释「简化回滚」实则啥也没做）；自带 `_json_safe` 把 Decimal→float（基类是→str，不一致） |
| `IngredientExecutor` merge | [ingredient.py](../../backend/app/services/proposals/executors/ingredient.py) 第 100–132 行 | 迁移明细只有 id（recipe_id/product_id/nutrition_id） | 前端渲染明细要再查库或只能显 id |
| `MerchantMergeExecutor` | [merchant_merge.py](../../backend/app/services/proposals/executors/merchant_merge.py) 第 75–90 行 | `product_records` 只有 id | 同上 |

**USDA 现状关键点：** [matcher.py](../../backend/app/services/usda/matcher.py) 内部 `_get_food_or_404`（171–180）+ `_build_nutrition_json`（120–168）已是「按 fdc_id 取三层营养结构」的完整逻辑，藏在写库函数 `match_ingredient` 里——抽出只读版即可。[api/usda.py](../../backend/app/api/usda.py) 有 `GET /search`、`GET /{fdc_id}` 模板可抄。

---

## 任务依赖图

```
Task 1 (recipe_edit snapshot+revert) ─┐
Task 2 (ingredient merge 冗余名)      │  后端独立，可并行
Task 3 (merchant_merge 冗余名)        │
Task 4 (抽 USDA 只读函数) ── Task 5 (preview-nutrition 端点) ─┐
                                                              │
Task 6 (前端 api 客户端 previewUsdaNutrients) ◄───────────────┤
                                                              │
Task 7 (NutritionDiff) ◄── Task 6                             │ 前端
Task 8 (MergeMapDiff) ◄── Task 2,3                            │
Task 9 (RecipeEditDiff) ◄── Task 1                            │
Task 10 (注册表 + ProposalsView 分发) ◄── Task 7,8,9          │
```

后端 Task 1–5 互相独立可并行；前端 Task 6 依赖 Task 5（端点要先在）；Task 10 依赖 7/8/9。

---

## Task 1: recipe_edit snapshot 存旧食材 + revert 回滚 + 统一 `_json_safe`

**Files:**
- Modify: `backend/app/services/proposals/executors/recipe_edit.py`（全文重构）
- Test: `backend/tests/test_recipe_edit_proposals.py`（新建）

**Step 1: 写失败测试**

新建 `backend/tests/test_recipe_edit_proposals.py`：

```python
"""recipe_edit 执行器：snapshot 存旧食材 + revert 食材回滚 单元测试。

直接用 db_session 内存库测执行器，不经 API 层（范式同 test_entity_executors.py）。
"""
from types import SimpleNamespace

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.services.proposals.executors.recipe_edit import RecipeEditExecutor


def _proposal(entity_id, update_data):
    return SimpleNamespace(
        id=88001, action="update", entity_id=entity_id,
        payload={"update_data": update_data}, snapshot=None, revert_payload=None,
        proposer_id=1,
    )


def _seed_recipe(db, rid=88001):
    """建一条菜谱 + 两个食材 + 一条旧食材引用，独立大 id 隔离残留。"""
    ing_a = db.query(Ingredient).filter(Ingredient.name == "测试原料A_88001").first()
    if ing_a is None:
        ing_a = Ingredient(name="测试原料A_88001", is_active=True)
        db.add(ing_a); db.flush()
    ing_b = db.query(Ingredient).filter(Ingredient.name == "测试原料B_88001").first()
    if ing_b is None:
        ing_b = Ingredient(name="测试原料B_88001", is_active=True)
        db.add(ing_b); db.flush()
    r = db.query(Recipe).filter(Recipe.id == rid).first()
    if r is None:
        r = Recipe(id=rid, name="测试菜谱_88001", servings=2)
        db.add(r); db.flush()
    # 清旧引用，建一条「旧食材」
    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == rid).delete()
    db.add(RecipeIngredient(
        recipe_id=rid, ingredient_id=ing_a.id, quantity="100", unit_id=None,
        is_optional=False, note="旧备注"))
    db.commit()
    return rid, ing_a.id, ing_b.id


def test_apply_snapshot_includes_old_ingredients(db_session):
    rid, ing_a_id, ing_b_id = _seed_recipe(db_session)
    ex = RecipeEditExecutor()
    p = _proposal(rid, {
        "ingredients": [
            {"ingredient_name": "测试原料B_88001", "quantity": "200"},
        ]
    })
    result = ex.apply(db_session, p)
    db_session.commit()

    snap = result.snapshot
    assert "old_ingredients" in snap
    old = snap["old_ingredients"]
    assert len(old) == 1
    # 冗余了可读名（前端 diff 直接用）
    assert old[0]["ingredient_name"] == "测试原料A_88001"
    assert old[0]["quantity"] == "100"


def test_revert_restores_ingredients(db_session):
    rid, ing_a_id, ing_b_id = _seed_recipe(db_session)
    ex = RecipeEditExecutor()
    p = _proposal(rid, {
        "ingredients": [
            {"ingredient_name": "测试原料B_88001", "quantity": "200"},
        ]
    })
    result = ex.apply(db_session, p)
    p.snapshot = result.snapshot
    p.revert_payload = result.revert_payload
    db_session.commit()

    # apply 后只剩原料 B
    rows = db_session.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == rid).all()
    assert len(rows) == 1 and rows[0].ingredient_id == ing_b_id

    ex.revert(db_session, p)
    db_session.commit()

    # revert 后恢复成原料 A（旧食材）
    rows = db_session.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == rid).all()
    assert len(rows) == 1
    assert rows[0].ingredient_id == ing_a_id
    assert rows[0].quantity == "100"


def test_build_snapshot_prefills_old_ingredients(db_session):
    """submit 时预填 snapshot（供 pending 审核看旧食材）。"""
    rid, _, _ = _seed_recipe(db_session)
    ex = RecipeEditExecutor()
    p = _proposal(rid, {"name": "改个名"})
    snap = ex.build_snapshot(db_session, p)
    assert "old_ingredients" in snap
    assert len(snap["old_ingredients"]) == 1
```

**Step 2: 跑测试确认失败**

```bash
cd backend && uv run pytest tests/test_recipe_edit_proposals.py -v
```

预期：3 个全 FAIL（`old_ingredients` 不存在 / revert 没回滚 / 无 build_snapshot）。

**Step 3: 重写执行器**

把 `backend/app/services/proposals/executors/recipe_edit.py` 整体替换为：

```python
"""菜谱编辑执行器：已发布菜谱的修改走提议审核。

snapshot 在 apply/submit 时都存入 ``old_ingredients``（删除/替换前的旧食材列表，
含 ``ingredient_name``/``unit_name`` 等可读冗余名），供审核台双栏 diff 与
revert 食材回滚。复用基类 ``_json_safe``（Decimal→str 无损，与 CRUD 执行器一致）。
"""
from typing import Optional

from fastapi import HTTPException

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.executors._crud_base import _json_safe
from sqlalchemy.orm import load_only


class RecipeEditExecutor(ProposalExecutor):
    entity_type = "recipe_edit"

    def entity_label(self, db, proposal) -> Optional[str]:
        eid = proposal.entity_id
        if eid is None:
            return None
        r = db.query(Recipe).get(eid)
        return f"菜谱「{r.name}」" if r else None

    def validate(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")

    def preview(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        return {"recipe_id": proposal.entity_id, "name": r.name if r else None,
                "changes": list(proposal.payload.get("update_data", {}).keys())}

    # ---- 旧食材快照：apply 前 / submit 预填 共用 ----
    def _snapshot_old_ingredients(self, db, recipe_id) -> list:
        rows = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()
        # 批量取相关原料名 / 单位名，避免逐行查询风暴
        ing_ids = {r.ingredient_id for r in rows if r.ingredient_id}
        unit_ids = {r.unit_id for r in rows if r.unit_id}
        ing_map = {i.id: i.name for i in (
            db.query(Ingredient).filter(Ingredient.id.in_(ing_ids)).all()
        )} if ing_ids else {}
        unit_map = {u.id: u.name for u in (
            db.query(Unit).filter(Unit.id.in_(unit_ids)).all()
        )} if unit_ids else {}
        out = []
        for ri in rows:
            out.append({
                "id": ri.id,
                "ingredient_id": ri.ingredient_id,
                "ingredient_name": ing_map.get(ri.ingredient_id),
                "quantity": ri.quantity,
                "quantity_range": ri.quantity_range,
                "unit_id": ri.unit_id,
                "unit_name": unit_map.get(ri.unit_id),
                "is_optional": ri.is_optional,
                "note": ri.note,
                "original_quantity": ri.original_quantity,
            })
        return out

    def build_snapshot(self, db, proposal) -> dict:
        """submit 时预填 before（供 pending 审核看旧食材；apply 时被覆盖）。"""
        recipe_id = proposal.entity_id
        if recipe_id is None:
            return {}
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if recipe is None:
            return {}
        snap = {c.name: _json_safe(getattr(recipe, c.name))
                for c in recipe.__table__.columns}
        snap["old_ingredients"] = self._snapshot_old_ingredients(db, recipe_id)
        return snap

    def apply(self, db, proposal) -> ApplyResult:
        recipe_id = proposal.entity_id
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if recipe is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        update_data = proposal.payload.get("update_data", {})

        # 标量列快照（apply 前最新值）
        snapshot = {c.name: _json_safe(getattr(recipe, c.name))
                    for c in recipe.__table__.columns}
        # 旧食材快照（在替换前抓全量；审核台 diff + revert 回滚 都用它）
        snapshot["old_ingredients"] = self._snapshot_old_ingredients(db, recipe_id)

        model_cols = {c.name for c in Recipe.__table__.columns}
        skip_fields = {"id", "is_public", "user_id", "source", "created_at", "updated_at",
                       "created_by", "updated_by", "is_active", "ingredients"}

        # 全量替换食材
        if "ingredients" in update_data and update_data["ingredients"] is not None:
            db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id == recipe_id).delete()
            for ing_data in update_data["ingredients"]:
                ing = db.query(Ingredient).options(
                    load_only(Ingredient.id, Ingredient.name, Ingredient.is_active)
                ).filter(Ingredient.name == ing_data.get("ingredient_name")).first()
                if ing:
                    db.add(RecipeIngredient(
                        recipe_id=recipe_id,
                        ingredient_id=ing.id,
                        quantity=ing_data.get("quantity"),
                        quantity_range=ing_data.get("quantity_range"),
                        unit_id=ing_data.get("unit_id"),
                        is_optional=ing_data.get("is_optional", False),
                        note=ing_data.get("note"),
                        original_quantity=ing_data.get("original_quantity"),
                    ))

        # 更新所有匹配模型列的标量字段
        for k, v in update_data.items():
            if k in model_cols and k not in skip_fields and v is not None:
                setattr(recipe, k, v)

        db.flush()
        return ApplyResult(snapshot=snapshot, revert_payload=snapshot,
                           summary=f"编辑菜谱 {recipe.name}")

    def revert(self, db, proposal):
        recipe_id = proposal.entity_id
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        snap = proposal.snapshot or {}

        # 标量字段还原
        if recipe is not None:
            for k, v in snap.items():
                if k == "old_ingredients":
                    continue
                if hasattr(recipe, k):
                    setattr(recipe, k, v)

        # 食材回滚：删当前 + 按快照重建旧食材（不指定 id，让自增，避免主键冲突）
        old_ings = snap.get("old_ingredients")
        if old_ings is not None and recipe_id is not None:
            db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id == recipe_id
            ).delete(synchronize_session=False)
            for ing_data in old_ings:
                db.add(RecipeIngredient(
                    recipe_id=recipe_id,
                    ingredient_id=ing_data.get("ingredient_id"),
                    quantity=ing_data.get("quantity"),
                    quantity_range=ing_data.get("quantity_range"),
                    unit_id=ing_data.get("unit_id"),
                    is_optional=ing_data.get("is_optional", False),
                    note=ing_data.get("note"),
                    original_quantity=ing_data.get("original_quantity"),
                ))
            db.flush()
```

**注意点（实现里已处理，别改错）：**
- 删除了文件顶部自带的 `_json_safe`（Decimal→float），改 import 基类的（Decimal→str 无损，revert 时 Numeric 列 setter 自动转回）。这是顺手修的一个潜在精度/一致性隐患。
- `Unit` import 新增——`_snapshot_old_ingredients` 要查单位名。
- revert 不写死 `id`（旧行 id 已被 apply 删过，重建时让自增主键，安全）。
- `build_snapshot` 是新增——让 pending 审核期间也能看到旧食材（service.submit 会自动调它）。

**Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_recipe_edit_proposals.py -v
```

预期：3 个全 PASS。

**Step 5: 语法校验 + 回归**

```bash
cd backend && uv run python -m py_compile app/services/proposals/executors/recipe_edit.py
cd backend && uv run pytest tests/test_recipes.py tests/test_proposals_framework.py -v
```

预期：py_compile 无输出（成功）；回归测试不新增失败。

**Step 6: Commit**

```bash
git add backend/app/services/proposals/executors/recipe_edit.py backend/tests/test_recipe_edit_proposals.py
git commit -m "feat(proposals): recipe_edit snapshot 存旧食材 + revert 回滚 + 统一 _json_safe"
```

---

## Task 2: ingredient merge snapshot 冗余可读名

**Files:**
- Modify: `backend/app/services/proposals/executors/ingredient.py`（`_apply_merge` 的 snapshot 字典，约第 100–132 行；新增 `target_name`）
- Test: `backend/tests/test_ingredient_merge_proposals.py`（新建）

**Step 1: 写失败测试**

新建 `backend/tests/test_ingredient_merge_proposals.py`：

```python
"""ingredient merge 执行器：snapshot 迁移明细含可读名 单元测试。"""
from types import SimpleNamespace

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.product_entity import Product
from app.models.product_ingredient_link import ProductIngredientLink
from app.services.proposals.executors.ingredient import IngredientExecutor


def _seed(db, sid=770201, tid=770202, rid=770203, pid=770204):
    src = Ingredient(id=sid, name="源原料_770201", is_active=True)
    tgt = Ingredient(id=tid, name="目标原料_770202", is_active=True)
    db.add_all([src, tgt]); db.flush()
    recipe = Recipe(id=rid, name="受影响菜谱_770203", servings=1)
    db.add(recipe); db.flush()
    db.add(RecipeIngredient(recipe_id=rid, ingredient_id=sid,
                            quantity="50", is_optional=False))
    prod = Product(id=pid, name="关联商品_770204", ingredient_id=sid, is_active=True)
    db.add(prod); db.flush()
    db.add(ProductIngredientLink(product_id=pid, ingredient_id=sid))
    db.commit()
    return sid, tid, rid, pid


def test_merge_snapshot_has_readable_names(db_session):
    sid, tid, rid, pid = _seed(db_session)
    ex = IngredientExecutor()
    p = SimpleNamespace(
        id=770210, action="merge", entity_id=None,
        payload={"source_ids": [sid], "target_id": tid},
        snapshot=None, revert_payload=None, proposer_id=1,
    )
    result = ex.apply(db_session, p)
    db_session.commit()
    snap = result.snapshot

    assert snap["target_name"] == "目标原料_770202"
    # 菜谱引用项含 recipe_name
    ri = snap["recipe_ingredients"][0]
    assert ri["recipe_name"] == "受影响菜谱_770203"
    # 商品关联项含 product_name
    pl = snap["product_links"][0]
    assert pl["product_name"] == "关联商品_770204"
```

> 说明：`IngredientMerger.merge_ingredients` 内部会 `db.commit()`，测试里 apply 后数据已被合并服务改动，不影响断言 snapshot（snapshot 在合并前已抓取）。若合并服务因残留数据报错，把 `_seed` 的 id 再调大隔离。

**Step 2: 跑测试确认失败**

```bash
cd backend && uv run pytest tests/test_ingredient_merge_proposals.py -v
```

预期：FAIL（`KeyError: 'target_name'` / `recipe_name` 不存在）。

**Step 3: 给 snapshot 加冗余名**

在 `ingredient.py` 的 `_apply_merge` 里，定位 snapshot 字典（第 100–132 行那段），把 `recipe_ingredients` / `product_links` / `nutrition_mappings` 的列表推导 join 上可读名，并新增 `target_name`。

替换那段 snapshot 字典为：

```python
        # 批量取可读名（join 一次，避免逐项查询）
        recipe_ids = {r.recipe_id for r in db.query(RecipeIngredient)
                      .filter(RecipeIngredient.ingredient_id.in_(source_ids)).all()}
        product_ids = {l.product_id for l in db.query(ProductIngredientLink)
                       .filter(ProductIngredientLink.ingredient_id.in_(source_ids)).all()}
        nutrition_ids = {m.nutrition_id for m in db.query(IngredientNutritionMapping)
                         .filter(IngredientNutritionMapping.ingredient_id.in_(source_ids)).all()}
        recipe_name_map = {r.id: r.name for r in (
            db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
        )} if recipe_ids else {}
        product_name_map = {p.id: p.name for p in (
            db.query(Product).filter(Product.id.in_(product_ids)).all()
        )} if product_ids else {}
        # nutrition 名取 NutritionData.id→? 这里 nutrition_id 指 NutritionData 行，
        # 用其 usda_name 或 source 作可读标签（无统一 name 列）
        from app.models.nutrition_data import NutritionData
        nutrition_name_map = {n.id: (n.usda_name or n.source or f"#{n.id}") for n in (
            db.query(NutritionData).filter(NutritionData.id.in_(nutrition_ids)).all()
        )} if nutrition_ids else {}

        target = db.query(Ingredient).filter(Ingredient.id == target_id).first()

        snapshot = {
            "target_name": target.name if target else f"#{target_id}",
            "recipe_ingredients": [
                {"id": r.id, "recipe_id": r.recipe_id, "ingredient_id": r.ingredient_id,
                 "recipe_name": recipe_name_map.get(r.recipe_id),
                 "quantity": r.quantity, "quantity_range": r.quantity_range,
                 "unit_id": r.unit_id, "is_optional": r.is_optional, "note": r.note,
                 "original_quantity": r.original_quantity}
                for r in db.query(RecipeIngredient)
                    .filter(RecipeIngredient.ingredient_id.in_(source_ids)).all()
            ],
            "product_links": [
                {"id": l.id, "product_id": l.product_id, "ingredient_id": l.ingredient_id,
                 "product_name": product_name_map.get(l.product_id)}
                for l in db.query(ProductIngredientLink)
                    .filter(ProductIngredientLink.ingredient_id.in_(source_ids)).all()
            ],
            "nutrition_mappings": [
                {"id": m.id, "ingredient_id": m.ingredient_id, "nutrition_id": m.nutrition_id,
                 "nutrition_name": nutrition_name_map.get(m.nutrition_id),
                 "priority": m.priority, "confidence": m.confidence}
                for m in db.query(IngredientNutritionMapping)
                    .filter(IngredientNutritionMapping.ingredient_id.in_(source_ids)).all()
            ],
            "hierarchies": [
                {"id": h.id, "parent_id": h.parent_id, "child_id": h.child_id,
                 "relation_type": h.relation_type, "strength": h.strength}
                for h in db.query(IngredientHierarchy).filter(or_(
                    IngredientHierarchy.parent_id.in_(source_ids),
                    IngredientHierarchy.child_id.in_(source_ids))).all()
            ],
            "sources": [
                {"id": s.id, "is_merged": s.is_merged, "merged_into_id": s.merged_into_id,
                 "aliases": s.aliases, "name": s.name}
                for s in db.query(Ingredient).filter(Ingredient.id.in_(source_ids)).all()
            ],
        }
```

**注意：**
- 文件顶部需确保已 import `Recipe`、`Product`（`_apply_delete` 已 import `Product` 但在函数内；`Recipe` 在文件顶部已 import，确认即可）。若顶部未 import `Recipe`，加到顶部 import。`NutritionData` 在函数内 import（沿用文件已有惰性 import 风格）。
- 保留原 snapshot 里已有的所有键（`hierarchies`/`sources` 原样），**只增不改**，避免破坏 revert。

**Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_ingredient_merge_proposals.py -v
cd backend && uv run pytest tests/test_shared_data.py -v   # 含食材合并相关，回归
```

预期：新测试 PASS；`test_shared_data` 不新增失败。

**Step 5: 语法校验**

```bash
cd backend && uv run python -m py_compile app/services/proposals/executors/ingredient.py
```

**Step 6: Commit**

```bash
git add backend/app/services/proposals/executors/ingredient.py backend/tests/test_ingredient_merge_proposals.py
git commit -m "feat(proposals): 食材合并 snapshot 冗余可读名(recipe/product/nutrition/target)"
```

---

## Task 3: merchant_merge snapshot 冗余 product_name + target_name

**Files:**
- Modify: `backend/app/services/proposals/executors/merchant_merge.py`（`apply` 的 snapshot 字典，第 75–90 行）
- Test: `backend/tests/test_merchant_merge_proposals.py`（新建）

**Step 1: 写失败测试**

新建 `backend/tests/test_merchant_merge_proposals.py`：

```python
"""merchant_merge 执行器：snapshot 含 product_name/target_name 单元测试。"""
from datetime import date
from types import SimpleNamespace

from app.models.merchant import Merchant
from app.models.product_entity import ProductRecord
from app.services.proposals.executors.merchant_merge import MerchantMergeExecutor


def _seed(db, sid=770301, tid=770302):
    src = Merchant(id=sid, name="源商家_770301", is_open=True)
    tgt = Merchant(id=tid, name="目标商家_770302", is_open=True)
    db.add_all([src, tgt]); db.flush()
    # 一条价格记录挂在源商家
    db.add(ProductRecord(product_id=770399, merchant_id=sid, price=9.9,
                         record_date=date(2026, 7, 2), record_type="price",
                         user_id=1))
    db.commit()
    return sid, tid


def test_merge_snapshot_has_names(db_session):
    sid, tid = _seed(db_session)
    ex = MerchantMergeExecutor()
    p = SimpleNamespace(
        id=770310, action="merge", entity_id=None,
        payload={"source_ids": [sid], "target_id": tid},
        snapshot=None, revert_payload=None, proposer_id=1,
    )
    result = ex.apply(db_session, p)
    db_session.commit()
    snap = result.snapshot

    assert snap["target_name"] == "目标商家_770302"
    pr = snap["product_records"][0]
    assert "product_name" in pr   # 有该键（值可能为 None 若 product 不存在）


def test_revert_still_works_afteradding_names(db_session):
    sid, tid = _seed(db_session)
    ex = MerchantMergeExecutor()
    p = SimpleNamespace(
        id=770311, action="merge", entity_id=None,
        payload={"source_ids": [sid], "target_id": tid},
        snapshot=None, revert_payload=None, proposer_id=1,
    )
    result = ex.apply(db_session, p)
    p.snapshot = result.snapshot
    p.revert_payload = result.revert_payload
    db_session.commit()
    ex.revert(db_session, p)
    db_session.commit()
    # revert 后源商家复活
    m = db_session.query(Merchant).get(sid)
    assert m.is_open in (True, 1)
```

> 说明：`ProductRecord` 字段名（`record_date`/`record_type`/`user_id`）若与实际模型不符，按 [backend/app/models/product.py](../../backend/app/models/product.py) 的 `ProductRecord` 定义调整——快照抓的是 `merchant_id`，测试 seed 用最小字段即可。

**Step 2: 跑测试确认失败**

```bash
cd backend && uv run pytest tests/test_merchant_merge_proposals.py -v
```

预期：FAIL（`KeyError: 'target_name'`）。

**Step 3: 给 snapshot 加冗余名**

在 `merchant_merge.py` 的 `apply` 里，把 snapshot 字典（第 75–90 行）替换为：

```python
        # 批量取受影响价格记录的商品名 + 目标商家名
        pr_rows = db.query(ProductRecord).filter(
            ProductRecord.merchant_id.in_(source_ids)).all()
        product_ids = {r.product_id for r in pr_rows if r.product_id}
        from app.models.product_entity import Product
        product_name_map = {p.id: p.name for p in (
            db.query(Product).filter(Product.id.in_(product_ids)).all()
        )} if product_ids else {}
        target = db.query(Merchant).get(target_id)

        # 1. 快照所有受影响行（供 revert）
        snapshot = {
            "target_name": target.name if target else f"#{target_id}",
            "product_records": [
                {"id": r.id, "merchant_id": r.merchant_id,
                 "product_id": r.product_id,
                 "product_name": product_name_map.get(r.product_id)}
                for r in pr_rows
            ],
            "favorites": [
                {"id": f.id, "user_id": f.user_id, "merchant_id": f.merchant_id}
                for f in db.query(UserMerchantFavorite)
                    .filter(UserMerchantFavorite.merchant_id.in_(source_ids)).all()
            ],
            "sources": [
                {"id": m.id, "is_open": m.is_open, "name": m.name}
                for m in db.query(Merchant).filter(Merchant.id.in_(source_ids)).all()
            ],
        }
```

并把后面「2. 迁移 ProductRecord」那段原来重新查 `ProductRecord` 的语句改为直接复用 `pr_rows` 的 id 条件——其实**原 update 语句保持不变**（它用 `merchant_id.in_(source_ids)` 再查一次也没问题，只是 snapshot 提前查了 `pr_rows`）。保留原 update/delete/软停用逻辑不动。

**注意：** snapshot 新增了 `target_name`/`product_id`/`product_name` 键，**不删旧键**；revert 逻辑只读 `id`/`merchant_id` 等原键，新增键不影响 revert。

**Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_merchant_merge_proposals.py -v
```

预期：2 个全 PASS。

**Step 5: 语法校验**

```bash
cd backend && uv run python -m py_compile app/services/proposals/executors/merchant_merge.py
```

**Step 6: Commit**

```bash
git add backend/app/services/proposals/executors/merchant_merge.py backend/tests/test_merchant_merge_proposals.py
git commit -m "feat(proposals): 商家合并 snapshot 冗余 product_name/target_name"
```

---

## Task 4: 抽 `build_usda_nutrients_by_fdc` 只读函数

**Files:**
- Modify: `backend/app/services/usda/matcher.py`（新增只读函数，复用现有 `_get_food_or_404` + `_build_nutrition_json`）
- Test: `backend/tests/services/test_usda_matcher.py`（追加测试，文件已存在）

**Step 1: 写失败测试**

在 `backend/tests/services/test_usda_matcher.py` 末尾追加：

```python
def test_build_usda_nutrients_by_fdc_readonly(db_session):
    """build_usda_nutrients_by_fdc 按 fdc_id 返回三层结构，且不写库。"""
    from app.models.usda import UsdaFood, UsdaFoodNutrient
    from app.services.usda.matcher import build_usda_nutrients_by_fdc

    fdc = 770401
    db_session.add(UsdaFood(fdc_id=fdc, data_type="foundation",
                            description="Test Food 770401"))
    db_session.add(UsdaFoodNutrient(fdc_id=fdc, name="Energy", name_zh="能量",
                                    amount=250.0, unit_name="kcal"))
    db_session.commit()

    struct = build_usda_nutrients_by_fdc(db_session, fdc)
    assert "core_nutrients" in struct and "all_nutrients" in struct
    # 中文名「能量」落到 core
    assert "能量" in struct["core_nutrients"]
    assert struct["core_nutrients"]["能量"]["value"] == 250.0


def test_build_usda_nutrients_by_fdc_not_found(db_session):
    from fastapi import HTTPException
    from app.services.usda.matcher import build_usda_nutrients_by_fdc
    with pytest.raises(HTTPException) as exc:
        build_usda_nutrients_by_fdc(db_session, 770499)
    assert exc.value.status_code == 404
```

> 说明：若该测试文件顶部没有 `import pytest`，加上。`db_session` 是 conftest 的内存库 fixture；若该模块已有自己的 db fixture 就用同名的。

**Step 2: 跑测试确认失败**

```bash
cd backend && uv run pytest tests/services/test_usda_matcher.py::test_build_usda_nutrients_by_fdc_readonly tests/services/test_usda_matcher.py::test_build_usda_nutrients_by_fdc_not_found -v
```

预期：FAIL（`ImportError: cannot import name 'build_usda_nutrients_by_fdc'`）。

**Step 3: 加只读函数**

在 `matcher.py` 的 `_get_food_or_404` 之后、`match_ingredient` 之前插入：

```python
def build_usda_nutrients_by_fdc(db: Session, fdc_id: int) -> dict:
    """按 fdc_id 取 USDA 营养素的三层结构（**只读**，不写 NutritionData/Product）。

    供审核台 NutritionDiff 渲染 ``usda_ingredient_match`` / ``usda_product_match``
    提议的「新值」预览——结构与 ``match_ingredient`` 写入的
    ``NutritionData.nutrients`` 一致（core_nutrients / all_nutrients / nutrient_details）。
    """
    _food, nutrients = _get_food_or_404(db, fdc_id)
    return _build_nutrition_json(nutrients)
```

**Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/services/test_usda_matcher.py -v
```

预期：含新测试在内全 PASS。

**Step 5: 语法校验**

```bash
cd backend && uv run python -m py_compile app/services/usda/matcher.py
```

**Step 6: Commit**

```bash
git add backend/app/services/usda/matcher.py backend/tests/services/test_usda_matcher.py
git commit -m "feat(usda): 抽 build_usda_nutrients_by_fdc 只读预览函数"
```

---

## Task 5: 新增 `GET /usda/preview-nutrition` 端点

**Files:**
- Modify: `backend/app/api/usda.py`（在 `/search` 之后、`/{fdc_id}` 之前插入新端点——**路由顺序关键**）
- Test: `backend/tests/test_usda_api.py`（追加测试）

**Step 1: 写失败测试**

在 `backend/tests/test_usda_api.py` 末尾追加（参考该文件已有测试的 fixture 用法，补 import 与 fixture 对齐）：

```python
def test_preview_nutrition_endpoint(client, usda_app_overrides):
    """GET /api/v1/usda/preview-nutrition?fdc_id=... 返回三层结构。"""
    from app.models.usda import UsdaFood, UsdaFoodNutrient
    from app.core.database import SessionLocal  # 或 TestingSessionLocal，按文件现有风格
    db = SessionLocal()
    db.add(UsdaFood(fdc_id=770501, data_type="foundation", description="Preview Food"))
    db.add(UsdaFoodNutrient(fdc_id=770501, name="Energy", name_zh="能量",
                            amount=100.0, unit_name="kcal"))
    db.commit(); db.close()

    resp = client.get("/api/v1/usda/preview-nutrition", params={"fdc_id": 770501})
    assert resp.status_code == 200
    body = resp.json()
    assert "core_nutrients" in body and "能量" in body["core_nutrients"]


def test_preview_nutrition_not_found(client, usda_app_overrides):
    resp = client.get("/api/v1/usda/preview-nutrition", params={"fdc_id": 770599})
    assert resp.status_code == 404
```

> **关键：** 先打开 `test_usda_api.py` 看它用的 client fixture 名字（可能叫 `client` / `test_client`）和 db 写入方式（`SessionLocal` 还是 `TestingSessionLocal`），**对齐现有风格**，不要照抄上面的 import。`usda_app_overrides` fixture 来自 conftest，已安装内存库 + FakeUser。

**Step 2: 跑测试确认失败**

```bash
cd backend && uv run pytest tests/test_usda_api.py::test_preview_nutrition_endpoint tests/test_usda_api.py::test_preview_nutrition_not_found -v
```

预期：FAIL（404 路由不存在）。

**Step 3: 加端点（注意路由顺序）**

在 `api/usda.py` 的 `search_usda` 之后、`get_usda_food`（`GET /{fdc_id}`）**之前**插入。顺序必须是：`/search` → `/preview-nutrition` → `/{fdc_id}`，否则 `preview-nutrition` 会被 `/{fdc_id}`（int 路径参数）吞掉返回 422。

```python
@router.get("/preview-nutrition")
async def preview_usda_nutrition(
    fdc_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """按 fdc_id 预览 USDA 营养素（只读，供审核台 NutritionDiff 渲染新值）。

    返回三层结构（core_nutrients / all_nutrients / nutrient_details），
    与 match_ingredient 写入 NutritionData.nutrients 的结构一致。
    """
    from app.services.usda.matcher import build_usda_nutrients_by_fdc
    return build_usda_nutrients_by_fdc(db, fdc_id)
```

> 不声明 `response_model`（直接返回 dict，结构由 matcher 保证），与写库路径结构对齐。

**Step 4: 跑测试确认通过**

```bash
cd backend && uv run pytest tests/test_usda_api.py -v
```

预期：含新测试在内全 PASS。

**Step 5: 语法校验**

```bash
cd backend && uv run python -m py_compile app/api/usda.py
```

**Step 6: Commit**

```bash
git add backend/app/api/usda.py backend/tests/test_usda_api.py
git commit -m "feat(usda): 新增 GET /usda/preview-nutrition 只读预览端点"
```

---

## Task 6: 前端 api 客户端补 `previewUsdaNutrients`

**Files:**
- Modify: `frontend/src/api/usda.ts`（文件已存在；新增一个函数）

**Step 1: 加函数**

打开 `frontend/src/api/usda.ts`，参考同文件现有函数（如 `searchUsda` / `getUsdaFood`）的 axios 实例 import 与调用风格，新增：

```typescript
/** 按 fdc_id 预览 USDA 营养素（三层结构，供审核台 NutritionDiff 渲染新值）。 */
export async function previewUsdaNutrients(
  fdcId: number,
): Promise<Record<string, any>> {
  const res = await api.get('/usda/preview-nutrition', { params: { fdc_id: fdcId } })
  return res.data
}
```

> 注意：`api` 实例的 import 与 `baseURL` 配置完全复用同文件现有写法（不要重复创建 axios 实例）。若文件里函数返回的是 `res.data` 以外的封装，对齐之。

**Step 2: 类型校验 + build**

```bash
cd frontend && npm run build
```

预期：build 通过（仅加了一个未使用函数，不影响产物）。

**Step 3: Commit**

```bash
git add frontend/src/api/usda.ts
git commit -m "feat(api): 新增 previewUsdaNutrients 客户端函数"
```

---

## Task 7: NutritionDiff.vue（营养 · 表格行对比）

**Files:**
- Create: `frontend/src/components/proposals/NutritionDiff.vue`

**Step 1: 建组件**

新建 `frontend/src/components/proposals/NutritionDiff.vue`：

```vue
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { previewUsdaNutrients } from '@/api/usda'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

interface NutrientEntry { value: number | null; unit: string }

function numOrNull(v: any): number | null {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

// 把多种形态统一成 {显示名 → {value, unit}}
//   - 三层结构 { core_nutrients, all_nutrients }（nutrition / product_nutrition / usda_product_match / USDA 返回）
//   - NutritionData 行数组（usda_ingredient_match 的 snapshot.old_nutrition_data）
function normalizeNutritionMap(source: any): Map<string, NutrientEntry> {
  const out = new Map<string, NutrientEntry>()
  if (!source) return out
  if (Array.isArray(source)) {
    for (const row of source) {
      const m = normalizeNutritionMap(row?.nutrients)
      for (const [k, v] of m) out.set(k, v)
    }
    return out
  }
  const core = source.core_nutrients
  if (core && typeof core === 'object') {
    for (const [name, entry] of Object.entries(core)) {
      const e = entry as any
      if (e && typeof e === 'object') {
        out.set(name, { value: numOrNull(e.value), unit: e.unit || '' })
      }
    }
  }
  const all = source.all_nutrients
  if (all && typeof all === 'object') {
    for (const [key, entry] of Object.entries(all)) {
      const e = entry as any
      if (e && typeof e === 'object') {
        const display = e.key || key
        if (!out.has(display)) {
          out.set(display, { value: numOrNull(e.value), unit: e.unit || '' })
        }
      }
    }
  }
  return out
}

const entityType = computed(() => props.proposal.entity_type)
const isUsda = computed(() =>
  entityType.value === 'usda_ingredient_match' || entityType.value === 'usda_product_match')

const beforeMap = computed(() => {
  const snap = props.proposal.snapshot || {}
  if (entityType.value === 'nutrition') return normalizeNutritionMap(snap.nutrients)
  if (entityType.value === 'product_nutrition') return normalizeNutritionMap(snap.old_custom_nutrition_data)
  if (entityType.value === 'usda_product_match') return normalizeNutritionMap(snap.old_custom_nutrition_data)
  if (entityType.value === 'usda_ingredient_match') return normalizeNutritionMap(snap.old_nutrition_data)
  return new Map<string, NutrientEntry>()
})

const afterMapFromPayload = computed(() => {
  const p = props.proposal.payload || {}
  if (entityType.value === 'nutrition') return normalizeNutritionMap(p.nutrients)
  if (entityType.value === 'product_nutrition') return normalizeNutritionMap(p.custom_nutrition_data)
  return new Map<string, NutrientEntry>()
})

const fdcId = computed(() => (props.proposal.payload || {}).fdc_id ?? null)
const usdaAfter = ref<Map<string, NutrientEntry>>(new Map())
const usdaLoading = ref(false)
const usdaError = ref(false)

async function loadUsdaAfter() {
  if (!isUsda.value || fdcId.value == null) return
  usdaLoading.value = true
  usdaError.value = false
  try {
    const struct = await previewUsdaNutrients(fdcId.value as number)
    usdaAfter.value = normalizeNutritionMap(struct)
  } catch {
    usdaError.value = true
    usdaAfter.value = new Map()
  } finally {
    usdaLoading.value = false
  }
}

watch(() => [props.proposal.id, fdcId.value], loadUsdaAfter, { immediate: true })

const afterMap = computed(() => (isUsda.value ? usdaAfter.value : afterMapFromPayload.value))

function sameNum(a: number | null, b: number | null): boolean {
  if (a === null && b === null) return true
  if (a === null || b === null) return false
  return Math.abs(a - b) < 1e-9
}

interface DiffRow { name: string; before: number | null; after: number | null; unit: string; changed: boolean }

const rows = computed<DiffRow[]>(() => {
  const names = new Set<string>([...beforeMap.value.keys(), ...afterMap.value.keys()])
  const list: DiffRow[] = []
  for (const name of names) {
    const b = beforeMap.value.get(name)
    const a = afterMap.value.get(name)
    const before = b?.value ?? null
    const after = a?.value ?? null
    list.push({
      name, before, after,
      unit: a?.unit || b?.unit || '',
      changed: !sameNum(before, after),
    })
  }
  return list.sort((x, y) => Number(y.changed) - Number(x.changed) || x.name.localeCompare(y.name))
})

const changedRows = computed(() => rows.value.filter(r => r.changed))
const unchangedRows = computed(() => rows.value.filter(r => !r.changed))
const showUnchanged = ref(false)

function formatVal(v: number | null): string {
  return v === null ? '—' : String(v)
}
</script>

<template>
  <div>
    <v-alert v-if="usdaError && isUsda" type="warning" variant="tonal" density="compact" class="mb-2">
      USDA 营养素预览不可用（fdc_id 可能已失效），仅显示当前值。
    </v-alert>
    <v-table v-if="rows.length" density="compact" class="nutrition-diff-table">
      <thead>
        <tr>
          <th class="text-caption text-medium-emphasis" style="width: 44%">营养素</th>
          <th class="text-caption text-medium-emphasis">当前</th>
          <th class="text-caption text-medium-emphasis">新值</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in (showUnchanged ? rows : changedRows)" :key="row.name" :class="{ 'nut-changed': row.changed }">
          <td>{{ row.name }}</td>
          <td>
            {{ formatVal(row.before) }}<span class="text-medium-emphasis ms-1">{{ row.unit }}</span>
          </td>
          <td>
            <span v-if="usdaLoading && isUsda" class="text-medium-emphasis">加载中…</span>
            <span v-else>
              {{ formatVal(row.after) }}<span class="text-medium-emphasis ms-1">{{ row.unit }}</span>
            </span>
          </td>
        </tr>
        <tr v-if="!showUnchanged && unchangedRows.length">
          <td colspan="3">
            <v-btn variant="text" size="small" @click="showUnchanged = true">
              ＋ 展开未变化的 {{ unchangedRows.length }} 项
            </v-btn>
          </td>
        </tr>
        <tr v-else-if="showUnchanged && unchangedRows.length">
          <td colspan="3">
            <v-btn variant="text" size="small" @click="showUnchanged = false">收起未变化项</v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
    <div v-else-if="usdaLoading && isUsda" class="text-caption text-medium-emphasis">USDA 营养素加载中…</div>
    <div v-else class="text-caption text-medium-emphasis">暂无营养素数据</div>
  </div>
</template>

<style scoped>
.nutrition-diff-table .nut-changed { background: rgba(255, 193, 7, 0.12); }
</style>
```

**Step 2: build 校验**

```bash
cd frontend && npm run build
```

预期：build 通过（组件暂未被引用，但语法/类型必须过关）。

**Step 3: Commit**

```bash
git add frontend/src/components/proposals/NutritionDiff.vue
git commit -m "feat(proposals): 新增 NutritionDiff 营养表格行对比渲染器"
```

---

## Task 8: MergeMapDiff.vue（合并 · 映射 + 计数 + 明细）

**Files:**
- Create: `frontend/src/components/proposals/MergeMapDiff.vue`

**Step 1: 建组件**

新建 `frontend/src/components/proposals/MergeMapDiff.vue`：

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

const entityType = computed(() => props.proposal.entity_type)
const isIngredient = computed(() => entityType.value === 'ingredient')
const snap = computed(() => props.proposal.snapshot || {})
const payload = computed(() => props.proposal.payload || {})

const sources = computed(() =>
  (snap.value.sources || []).map((s: any) => s.name || `#${s.id}`))
const targetName = computed(() => snap.value.target_name || `#${payload.value.target_id}`)

const impactCards = computed(() => {
  if (isIngredient.value) {
    return [
      { label: '菜谱引用', count: (snap.value.recipe_ingredients || []).length },
      { label: '商品关联', count: (snap.value.product_links || []).length },
      { label: '层级关系', count: (snap.value.hierarchies || []).length },
      { label: '营养映射', count: (snap.value.nutrition_mappings || []).length },
    ]
  }
  return [
    { label: '价格记录', count: (snap.value.product_records || []).length },
    { label: '收藏', count: (snap.value.favorites || []).length },
  ]
})

interface DetailRow { category: string; name: string }
const details = computed<DetailRow[]>(() => {
  const out: DetailRow[] = []
  if (isIngredient.value) {
    for (const r of (snap.value.recipe_ingredients || [])) {
      out.push({ category: '菜谱', name: r.recipe_name || `菜谱 #${r.recipe_id}` })
    }
    for (const l of (snap.value.product_links || [])) {
      out.push({ category: '商品', name: l.product_name || `商品 #${l.product_id}` })
    }
  } else {
    for (const r of (snap.value.product_records || [])) {
      out.push({ category: '价格记录', name: r.product_name || `记录 #${r.id}` })
    }
  }
  return out
})

const DETAIL_PREVIEW = 5
const showAllDetails = ref(false)
const visibleDetails = computed(() =>
  showAllDetails.value ? details.value : details.value.slice(0, DETAIL_PREVIEW))
</script>

<template>
  <div>
    <!-- 合并方向 -->
    <div class="d-flex align-center flex-wrap mb-3 merge-direction">
      <div class="d-flex flex-wrap ga-1">
        <v-chip v-for="(s, i) in sources" :key="i" size="small" color="error" variant="tonal">
          <span class="text-decoration-line-through">{{ s }}</span>
        </v-chip>
      </div>
      <v-icon class="mx-2" size="small">mdi-arrow-right</v-icon>
      <v-chip size="small" color="success" variant="flat">{{ targetName }}</v-chip>
    </div>

    <!-- 源处理说明 -->
    <v-alert type="info" variant="tonal" density="compact" class="mb-3">
      源 {{ sources.length }} 个将软停用（保留名称追溯），所有引用迁至目标「{{ targetName }}」。
    </v-alert>

    <!-- 影响范围 -->
    <div class="text-subtitle-2 mb-2">影响范围</div>
    <v-row dense class="mb-2">
      <v-col v-for="card in impactCards" :key="card.label" cols="6" sm="3">
        <v-card variant="outlined" density="compact" class="text-center pa-2">
          <div class="text-h6">{{ card.count }}</div>
          <div class="text-caption text-medium-emphasis">{{ card.label }}</div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 迁移明细（默认展开） -->
    <div v-if="details.length" class="text-subtitle-2 mb-1">迁移明细</div>
    <v-list v-if="details.length" density="compact" class="bg-transparent">
      <v-list-item v-for="(d, i) in visibleDetails" :key="i" class="px-0">
        <template #prepend>
          <v-chip size="x-small" variant="outlined">{{ d.category }}</v-chip>
        </template>
        <v-list-item-title class="text-body-2">{{ d.name }}</v-list-item-title>
      </v-list-item>
      <v-list-item v-if="details.length > DETAIL_PREVIEW" class="px-0">
        <v-btn variant="text" size="small" @click="showAllDetails = !showAllDetails">
          {{ showAllDetails ? '收起' : `展开剩余 ${details.length - DETAIL_PREVIEW} 项` }}
        </v-btn>
      </v-list-item>
    </v-list>
  </div>
</template>

<style scoped>
.merge-direction { gap: 4px; }
</style>
```

**Step 2: build 校验**

```bash
cd frontend && npm run build
```

预期：build 通过。

**Step 3: Commit**

```bash
git add frontend/src/components/proposals/MergeMapDiff.vue
git commit -m "feat(proposals): 新增 MergeMapDiff 合并映射渲染器"
```

---

## Task 9: RecipeEditDiff.vue（菜谱 · 双栏并排）

**Files:**
- Create: `frontend/src/components/proposals/RecipeEditDiff.vue`

**Step 1: 建组件**

新建 `frontend/src/components/proposals/RecipeEditDiff.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { Proposal } from '@/api/proposals'

const props = defineProps<{ proposal: Proposal }>()

const snap = computed(() => props.proposal.snapshot || {})
const updateData = computed(() => (props.proposal.payload || {}).update_data || {})

// 标量字段 diff（上半段）：before=snapshot 标量列，after=update_data 标量字段
const META_KEYS = new Set([
  'id', 'is_public', 'user_id', 'source', 'created_at', 'updated_at',
  'created_by', 'updated_by', 'is_active', 'old_ingredients', 'ingredients', 'steps',
])
interface ScalarRow { field: string; before: any; after: any; kind: 'added' | 'removed' | 'changed' }
const scalarRows = computed<ScalarRow[]>(() => {
  const before = snap.value
  const after = updateData.value
  const keys = new Set<string>([...Object.keys(before), ...Object.keys(after)])
  const rows: ScalarRow[] = []
  for (const k of keys) {
    if (META_KEYS.has(k)) continue
    const hasB = k in before, hasA = k in after
    const b = before[k], a = after[k]
    let kind: ScalarRow['kind'] | null = null
    if (hasB && !hasA) continue                 // 仅旧的不展示
    if (!hasB && hasA) kind = 'added'
    else if (JSON.stringify(b) !== JSON.stringify(a)) kind = 'changed'
    if (!kind) continue
    rows.push({ field: k, before: hasB ? b : null, after: hasA ? a : null, kind })
  }
  return rows
})

// 食材双栏对齐（对齐键：ingredient_name）
interface IngItem { name: string; qty: string; unit: string; note: string }
interface IngRow { oldItem?: IngItem; newItem?: IngItem; kind: 'added' | 'removed' | 'changed' | 'unchanged' }

function fmtQty(q: any, qr: any): string {
  if (q != null && q !== '') return String(q)
  if (qr && typeof qr === 'object') {
    const min = (qr as any).min, max = (qr as any).max
    if (min != null && max != null) return `${min}~${max}`
  }
  return '—'
}

const oldIngs = computed<IngItem[]>(() =>
  ((snap.value.old_ingredients || []) as any[]).map(r => ({
    name: r.ingredient_name || `#${r.ingredient_id}`,
    qty: fmtQty(r.quantity, r.quantity_range),
    unit: r.unit_name || '',
    note: r.note || '',
  })))

const newIngs = computed<IngItem[]>(() =>
  ((updateData.value.ingredients || []) as any[]).map(r => ({
    name: r.ingredient_name || '',
    qty: fmtQty(r.quantity, r.quantity_range),
    unit: '',
    note: r.note || '',
  })))

const ingRows = computed<IngRow[]>(() => {
  const newMap = new Map<string, IngItem>()
  newIngs.value.forEach(i => newMap.set(i.name, i))
  const ordered: IngRow[] = []
  const seen = new Set<string>()
  for (const o of oldIngs.value) {
    seen.add(o.name)
    const n = newMap.get(o.name)
    if (n) {
      const changed = o.qty !== n.qty || o.note !== n.note
      ordered.push({ oldItem: o, newItem: n, kind: changed ? 'changed' : 'unchanged' })
    } else {
      ordered.push({ oldItem: o, kind: 'removed' })
    }
  }
  for (const n of newIngs.value) {
    if (!seen.has(n.name)) ordered.push({ newItem: n, kind: 'added' })
  }
  return ordered
})

const hasOldIngredients = computed(() => Array.isArray((snap.value as any).old_ingredients))

function formatValue(v: any): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
</script>

<template>
  <div>
    <!-- 基本字段 -->
    <div v-if="scalarRows.length" class="mb-4">
      <div class="text-subtitle-2 mb-2">基本字段</div>
      <v-table density="compact" class="diff-table">
        <tbody>
          <tr v-for="row in scalarRows" :key="row.field">
            <td class="text-caption text-medium-emphasis" style="width: 28%">{{ row.field }}</td>
            <td :class="['diff-cell', 'before', row.kind]">
              <span v-if="row.before === null" class="text-medium-emphasis">—</span>
              <span v-else>{{ formatValue(row.before) }}</span>
            </td>
            <td class="text-center text-medium-emphasis" style="width: 32px">→</td>
            <td :class="['diff-cell', 'after', row.kind]">
              <span v-if="row.after === null" class="text-medium-emphasis">—</span>
              <span v-else>{{ formatValue(row.after) }}</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <!-- 食材双栏 -->
    <div class="text-subtitle-2 mb-2">食材列表</div>
    <div v-if="!hasOldIngredients" class="text-caption text-medium-emphasis mb-2">
      历史提议，旧食材数据缺失（仅展示新食材）
    </div>
    <v-row dense>
      <v-col cols="6">
        <div class="text-caption text-medium-emphasis mb-1">当前</div>
        <div class="diff-pane diff-old">
          <template v-for="(row, i) in ingRows" :key="'o' + i">
            <div v-if="row.oldItem"
                 :class="['diff-line', row.kind === 'removed' ? 'del' : (row.kind === 'changed' ? 'mod-old' : '')]">
              <div class="text-body-2">{{ row.oldItem.name }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ row.oldItem.qty }} {{ row.oldItem.unit }}
                <span v-if="row.oldItem.note">· {{ row.oldItem.note }}</span>
              </div>
            </div>
          </template>
          <div v-if="!ingRows.some(r => r.oldItem)" class="text-caption text-medium-emphasis">（空）</div>
        </div>
      </v-col>
      <v-col cols="6">
        <div class="text-caption text-medium-emphasis mb-1">新</div>
        <div class="diff-pane diff-new">
          <template v-for="(row, i) in ingRows" :key="'n' + i">
            <div v-if="row.newItem"
                 :class="['diff-line', row.kind === 'added' ? 'add' : (row.kind === 'changed' ? 'mod-new' : '')]">
              <div class="text-body-2">{{ row.newItem.name }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ row.newItem.qty }} {{ row.newItem.unit }}
                <span v-if="row.newItem.note">· {{ row.newItem.note }}</span>
              </div>
            </div>
          </template>
          <div v-if="!ingRows.some(r => r.newItem)" class="text-caption text-medium-emphasis">（空）</div>
        </div>
      </v-col>
    </v-row>
  </div>
</template>

<style scoped>
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }
.diff-pane { border: 1px solid rgba(var(--v-theme-on-surface), 0.12); border-radius: 6px; padding: 6px; min-height: 48px; }
.diff-line { padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; }
.diff-line.del { background: rgba(244, 67, 54, 0.10); text-decoration: line-through; }
.diff-line.add { background: rgba(76, 175, 80, 0.12); }
.diff-line.mod-old { background: rgba(244, 67, 54, 0.08); }
.diff-line.mod-new { background: rgba(76, 175, 80, 0.08); }
</style>
```

**Step 2: build 校验**

```bash
cd frontend && npm run build
```

预期：build 通过。

**Step 3: Commit**

```bash
git add frontend/src/components/proposals/RecipeEditDiff.vue
git commit -m "feat(proposals): 新增 RecipeEditDiff 食材双栏并排渲染器"
```

---

## Task 10: 渲染器注册表 + ProposalsView 分发改造

**Files:**
- Create: `frontend/src/proposalRenderers.ts`
- Modify: `frontend/src/views/admin/ProposalsView.vue`（详情区第 338–364 行替换 + script 加 import/computed）

**Step 1: 建注册表**

新建 `frontend/src/proposalRenderers.ts`：

```typescript
import type { Component } from 'vue'
import type { Proposal } from '@/api/proposals'
import RecipeEditDiff from '@/components/proposals/RecipeEditDiff.vue'
import NutritionDiff from '@/components/proposals/NutritionDiff.vue'
import MergeMapDiff from '@/components/proposals/MergeMapDiff.vue'

/**
 * 按 entity_type (+ action) 选专用渲染器。
 * 未命中返回 null —— 调用方回退现状 diffRows（CRUD 类零影响）。
 */
export function resolveProposalRenderer(p: Proposal): Component | null {
  const t = p.entity_type
  if (t === 'recipe_edit') return RecipeEditDiff
  if (t === 'nutrition' || t === 'product_nutrition'
      || t === 'usda_ingredient_match' || t === 'usda_product_match') {
    return NutritionDiff
  }
  if ((t === 'ingredient' && p.action === 'merge') || t === 'merchant_merge') {
    return MergeMapDiff
  }
  return null
}
```

**Step 2: 改 ProposalsView 的 script**

在 [ProposalsView.vue](../../frontend/src/views/admin/ProposalsView.vue) 的 `<script setup>` 顶部 import 区（约第 539–558 行那段 import 之后）加：

```typescript
import { resolveProposalRenderer } from '@/proposalRenderers'
```

在 `diffRows` computed 附近（约第 937 行附近，与其它 detail 相关 computed 同区）加一个 computed：

```typescript
const detailRenderer = computed(() => {
  const item = detailItem.value
  return item ? resolveProposalRenderer(item) : null
})
```

**Step 3: 改详情区 template（替换第 338–364 行整段「变更内容 diff」）**

把第 338–364 行那一整段（从 `<!-- 变更内容 diff -->` 到它对应的闭合 `</div>`，即包含 `diffRows` 那个 `<v-table>` 的外层 `<div class="mt-4">…</div>`）替换为：

```vue
          <!-- 变更内容 diff -->
          <div class="mt-4">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" start>mdi-compare-horizontal</v-icon>
              变更内容
              <span v-if="detailItem.action === 'delete'" class="text-caption text-medium-emphasis ms-2">（将删除）</span>
              <span v-else-if="detailItem.action === 'create'" class="text-caption text-medium-emphasis ms-2">（将新增）</span>
            </div>

            <!-- 专用渲染器（菜谱/营养/合并 三类） -->
            <component
              v-if="detailRenderer"
              :is="detailRenderer"
              :proposal="detailItem"
            />

            <!-- 兜底：CRUD 类字段 diff 表（现状逻辑，零改动） -->
            <template v-else>
              <v-table v-if="diffRows.length" density="compact" class="diff-table">
                <tbody>
                  <tr v-for="row in diffRows" :key="row.field">
                    <td class="text-caption text-medium-emphasis" style="width: 28%">{{ row.field }}</td>
                    <td :class="['diff-cell', 'before', row.kind]">
                      <span v-if="row.before === null" class="text-medium-emphasis">—</span>
                      <span v-else>{{ formatValue(row.before) }}</span>
                    </td>
                    <td class="text-center text-medium-emphasis" style="width: 32px">→</td>
                    <td :class="['diff-cell', 'after', row.kind]">
                      <span v-if="row.kind === 'removed'" class="text-medium-emphasis">（删除）</span>
                      <span v-else-if="row.after === null" class="text-medium-emphasis">—</span>
                      <span v-else>{{ formatValue(row.after) }}</span>
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <div v-else class="text-caption text-medium-emphasis">无变更字段（如仅触发动作，无数据变更）</div>
            </template>
          </div>
```

> 关键：兜底分支的 `<v-table>` 内容与原模板**逐字一致**（原样保留 `diffRows`/`formatValue`），CRUD 类视觉零变化。`diffRows` computed 与 `formatValue` 函数**不要删**——兜底分支还在用。

**Step 4: build 校验**

```bash
cd frontend && npm run build
```

预期：build 通过。

**Step 5: 手测关键路径（浏览器，开发者已起服务）**

打开审核台（管理员账号），分别在三类提议上验证：
1. 菜谱编辑提议 → 看到双栏食材 diff（左旧右新，增删红绿）
2. USDA 原料匹配提议（pending）→ 营养表格，新值栏异步加载 USDA
3. 食材/商家合并提议 → 源→目标映射 + 影响计数卡 + 迁移明细
4. 任意 CRUD 提议（如单位 create）→ 仍是原字段 diff 表（兜底未回归）

> 注：菜谱编辑提议需有「已发布菜谱被改」的 pending/applied 数据；若历史提议 snapshot 无 `old_ingredients`，左栏应显示「历史提议，旧食材数据缺失」降级提示。

**Step 6: Commit**

```bash
git add frontend/src/proposalRenderers.ts frontend/src/views/admin/ProposalsView.vue
git commit -m "feat(proposals): 审核台详情区按 entity_type 分发专用渲染器(兜底 diffRows)"
```

---

## 完成标准 / 验收

- [ ] 后端：`cd backend && uv run pytest tests/test_recipe_edit_proposals.py tests/test_ingredient_merge_proposals.py tests/test_merchant_merge_proposals.py tests/services/test_usda_matcher.py tests/test_usda_api.py -v` 全 PASS。
- [ ] 后端回归：`test_recipes.py` / `test_proposals_framework.py` / `test_shared_data.py` / `test_usda_match_proposals.py` 不新增失败（基线失败数不变）。
- [ ] 后端全部改动文件 `uv run python -m py_compile` 无报错。
- [ ] 前端：`cd frontend && npm run build` 通过。
- [ ] 浏览器实测三类渲染器呈现正确，CRUD 类兜底无回归（见 Task 10 Step 5）。
- [ ] 设计文档「兼容性与兜底」三条全落实：未注册类型回退 diffRows；recipe_edit 历史提议降级提示；USDA 预览失败不阻塞审核。

## 非范围（不在本计划内，YAGNI）

- CRUD 类（ingredient/unit/product/merchant/hierarchy/entity_unit_override/entity_density 的 create/update/delete）不升级渲染器。
- `recipe` publish（is_public 简单字段）不专用渲染。
- nutrition 端点补空 auto 未生效的旧 bug（与本设计无关）。
- 食材对齐键用 `ingredient_name`（payload 无稳定 id），同名不同食材理论上会混——审核场景罕见，接受。
